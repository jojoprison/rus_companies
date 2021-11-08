import multiprocessing

from bs4 import BeautifulSoup

import asyncio
import datetime

# from db import conn
import utility.date_converter as dc
from utility.proxy.proxy import parse, random_proxy, prepare_for_request

import requests

company_category_url = 'https://www.rusprofile.ru/codes/'


class RusProfile:
    con = None
    loop = None

    async def get_company_list(self, list_url):
        bs = BeautifulSoup(list_url, 'html.parser')

        company_list = bs.find_all('div', class_='company-item')

        company_status_set = set()

        # loop = asyncio.get_event_loop()
        con_coroutine = DbConnect().get_connect()
        # con_res = loop.run_until_complete(con_coroutine)
        # self.con = con_res
        # print(con_res)

        con_task = asyncio.create_task(con_coroutine)
        self.con = await con_task

        for company in company_list:

            company_status = company.find('div', class_='company-item-status')

            if not company_status:
                company_title = company.find('div', class_='company-item__title')
                company_name = company_title.text.strip()

                company_internal_id = company_title.find('a').get('href')
                company_internal_id = int(company_internal_id.split('/')[-1])

                company_url = f'https://www.rusprofile.ru/id/{company_internal_id}'

                company_address = company.find('address').text.strip()

                company_info_list = company.find_all('div', 'company-item-info')

                company_director = company_info_list[0].find('dd').text

                law_data = company_info_list[1].find_all('dd')
                company_inn = int(law_data[0].text)
                company_ogrn = int(law_data[1].text)
                company_reg_date = law_data[2].text

                if len(law_data) == 4:
                    capital = law_data[3].text

                    capital_parts = capital.split(' ')
                    # добавляем все части числа кроме последней
                    capital = ''
                    for i in range(0, len(capital_parts) - 1):
                        capital += str(capital_parts[i])

                    capital = capital.strip().replace(',', '.')

                    company_capital = float(capital)
                else:
                    company_capital = None

                company_category = company_info_list[2].find('dd').text

                # TODO asyncio.gather(*coros)
                db_cor = self.add_company(company_name, company_url, None, None, company_address,
                                          company_director, company_category, company_inn, company_ogrn,
                                          company_capital, company_reg_date, company_internal_id)
                db_task = asyncio.create_task(db_cor)
                print(await db_task)
                # db_res = loop.run_until_complete(db_cor)
                # print(db_res)
            else:
                company_status_set.add(company_status.text)

    async def add_company(self, name, url, email, phone, address, director, category, inn, ogrn,
                          capital, reg_date, internal_id):

        email = ''
        phone = ''
        if not capital:
            capital = 0.

        reg_date_converted = dc.convert_reg_date(reg_date)
        reg_date = dc.prepare_to_db(reg_date_converted)

        is_exist = await self.con.fetchval('SELECT id FROM companies WHERE internal_id = $1',
                                           internal_id)

        if not is_exist:
            async with self.con.transaction():
                company_id = await self.con.fetchval('INSERT INTO companies(name, url, email, phone, address, '
                                                     'director, category, inn, ogrn, capital, reg_date, date_add, '
                                                     'internal_id) '
                                                     'VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13) '
                                                     'RETURNING id',
                                                     name, url, email, phone, address, director, category, int(inn),
                                                     ogrn, capital, reg_date, datetime.datetime.now(),
                                                     internal_id)

            return company_id
        else:
            return is_exist


    def parse(self):
        first_page_url = 'https://www.rusprofile.ru/codes/460000'

        req = requests.get(first_page_url)

        bs = BeautifulSoup(req.text, 'html.parser')

        ul_pages = bs.find('ul', class_='paging-list')
        page_count = ul_pages.find_all('li')[-2].text

        page_url_list = []

        # for page in range(2, int(page_count) + 1):
        for page in range(2, 4):
            page_url = first_page_url + '/' + str(page)
            page_url_list.append(page_url)

        print(page_url_list)

        self.loop = asyncio.get_event_loop()

        pool = multiprocessing.Pool(processes=2)

        pool_res = pool.map(self.do_cor, page_url_list)

        print(pool_res)
        # clear_res = [proxy for proxy in pool_res if proxy]


    def do_cor(self, page_url):

        proxy_str = random_proxy()
        proxy = parse(proxy_str)
        print(proxy)
        proxies = prepare_for_request(proxy)

        req = requests.get(page_url, proxies=proxies, timeout=30)

        cor = self.get_company_list(req.text)
        con_res = self.loop.run_until_complete(cor)

        return con_res


if __name__ == '__main__':

    print(datetime.datetime.now())

    # rus_profile = RusProfile()

    # rus_profile.parse()

    # coroutine = get_list_org_list(req.text)
    # loop.run_until_complete(coroutine)
