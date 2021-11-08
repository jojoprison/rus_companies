import datetime
import multiprocessing

import requests
from bs4 import BeautifulSoup

import datetime as dt
from dateutil.relativedelta import relativedelta

from requests.exceptions import ConnectionError, ReadTimeout, ChunkedEncodingError

import utility.date_converter as dc
from db import DbConnectHelper
from utility.proxy.proxy import parse, random_proxy, prepare_for_request

company_category_url = 'https://www.rusprofile.ru/codes/'


class RusProfile:
    con = None
    site_url = 'https://www.rusprofile.ru/'
    company_status_set = set()
    error_page_set = set()

    def get_company_list(self, page_data, page_url):
        bs = BeautifulSoup(page_data, 'html.parser')

        company_list = bs.find_all('div', class_='company-item')

        self.con = DbConnectHelper().get_single_connection()

        added_count = 0

        for company in company_list:

            # TODO сделать отдельный метод и вот тут проверять область по списку фила

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

                try:
                    company_inn = int(law_data[0].text)
                # (ValueError, IndexError)
                except Exception:
                    print('err inn: ', law_data)
                    company_inn = 0
                    self.error_page_set.add(page_url)
                try:
                    company_ogrn = int(law_data[1].text)
                except Exception:
                    print('err ogrn: ', law_data)
                    company_ogrn = 0
                    self.error_page_set.add(page_url)
                try:
                    company_reg_date = law_data[2].text
                except Exception:
                    print('err reg_date: ', law_data)
                    company_reg_date = '1 января 1970 г.'
                    self.error_page_set.add(page_url)

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

                try:
                    company_category = company_info_list[2].find('dd').text
                except Exception:
                    print('err reg_date: ', company_info_list)
                    company_category = 'temp'
                    self.error_page_set.add(page_url)

                company_id = self.add_company(company_name, company_url, None, None, company_address,
                                              company_director, company_category, company_inn, company_ogrn,
                                              company_capital, company_reg_date, company_internal_id,
                                              self.site_url)

                added_count += 1
            else:
                self.company_status_set.add(company_status.text)

        self.con.commit()

        return added_count, self.company_status_set, self.error_page_set

    def add_company(self, name, url, email, phone, address, director, category,
                    inn, ogrn, capital, reg_date, internal_id, site_url):

        email = ''
        phone = ''
        if not capital:
            capital = 0.

        reg_date_converted = dc.convert_reg_date(reg_date)
        reg_date = dc.prepare_to_db(reg_date_converted)

        cursor = self.con.cursor()

        cursor.execute('SELECT id FROM companies WHERE internal_id = %s', (internal_id,))
        is_exist = cursor.fetchone()

        if not is_exist:

            cursor.execute('INSERT INTO companies(name, url, email, phone, address, '
                           'director, category, inn, ogrn, capital, reg_date, date_add, '
                           'internal_id, site_url) '
                           'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) '
                           'RETURNING id',
                           (name, url, email, phone, address, director, category, int(inn),
                            ogrn, capital, reg_date, datetime.datetime.now(),
                            internal_id, site_url))

            company_id = cursor.fetchone()[0]

            cursor.close()

            return company_id
        else:
            return is_exist

    def parse_page(self, page_url):

        print('parse url: ', page_url)

        while True:

            proxy_str = random_proxy()
            proxy = parse(proxy_str)
            proxies = prepare_for_request(proxy)

            try:
                req = requests.get(page_url, proxies=proxies, timeout=30)

                # TODO мб потом убрать page_url как разберусь че там летит в law_data
                res = self.get_company_list(req.text, page_url)

                return res

            except (ConnectionError, ReadTimeout, ChunkedEncodingError):
                # print('fuck prox')
                pass

    def parse_category(self, first_page_url):

        start_time = dt.datetime.now()

        req = requests.get(first_page_url)

        bs = BeautifulSoup(req.text, 'html.parser')

        ul_pages = bs.find('ul', class_='paging-list')
        page_count = ul_pages.find_all('li')[-2].text

        page_url_list = []

        # for page in range(2, int(page_count) + 1):
        for page in range(2, int(page_count) + 1):
            page_url = first_page_url + '/' + str(page)
            page_url_list.append(page_url)

        pool = multiprocessing.Pool(processes=50)

        pool_res = pool.map(self.parse_page, page_url_list)

        added_count_list = []
        company_status_set = set()
        error_page_set = set()

        for res in pool_res:
            added_count_list.append(res[0])
            company_status_set.update(res[1])
            error_page_set.update(res[2])

        print(added_count_list)
        print(company_status_set)
        print(error_page_set)

        end_time = dt.datetime.now()
        print(relativedelta(end_time, start_time))
        # clear_res = [proxy for proxy in pool_res if proxy]


if __name__ == '__main__':
    rus_profile = RusProfile()

    # страничка с торговыми компаниями
    # first_page_url = 'https://www.rusprofile.ru/codes/460000'
    first_page_url = 'https://www.rusprofile.ru/codes/430000'

    rus_profile.parse_category(first_page_url)

    # res = rus_profile.parse_page('https://www.rusprofile.ru/codes/430000/3760')
    # print(res)

    # TODO парсить эмейли и телефоны внутри ссылок и на сайте чекера по ОГРН, заносить сайт с которого пару
    # TODO пробнуть в 50 процессов заносить данные

    # coroutine = get_list_org_list(req.text)
    # loop.run_until_complete(coroutine)
