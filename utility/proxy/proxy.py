import multiprocessing
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from requests.exceptions import ProxyError, ConnectTimeout, ConnectionError, ReadTimeout

from utility.proxy.proxydb import ProxyDB


class Proxy:
    ip = None
    port = None
    protocol = None
    country = None
    date_founded = None

    def __init__(self, ip, port, protocol, country, date_founded):
        self.ip = ip
        self.port = port
        self.protocol = protocol
        self.country = country
        self.date_founded = date_founded

    def signature(self):
        return self.ip + ':' + self.port

    def for_request(self):
        return self.protocol + '://' + self.ip + ':' + self.port

    def __str__(self):
        return self.for_request() + ' - ' + self.country \
               + ', ' + str(self.date_founded)

    def __repr__(self):
        return self.for_request() + ' - ' + self.country \
               + ', ' + str(self.date_founded)


def parse(proxy_str):
    if proxy_str.find('://') != -1:
        protocol, proxy_str = proxy_str.split('://')
        # ставим доп параметр сплиту, т.к. нам нужны разделить только первым двоеточием которое отделяет порт
        ip, proxy_str = proxy_str.split(':', 1)
        port, proxy_str = proxy_str.split(' - ')
        country, date_founded = proxy_str.split(', ')

        return Proxy(ip, port, protocol, country, date_founded)
    else:
        print('wrong proxy_str: ', proxy_str)
        return None


def index_page_free_proxy_list():
    req = requests.get('https://scrapingant.com/free-proxies/')

    soup = BeautifulSoup(req.text, 'html.parser')
    proxy_list = soup.find('table', class_='proxies-table').find_all('tr')

    # удаляем заголовки самой таблицы
    del proxy_list[0]

    result_proxy_list = []

    for proxy_tr in proxy_list:
        proxy_data = proxy_tr.find_all('td')

        if proxy_data[3].text.endswith('Unknown'):
            country = proxy_data[3].text.split(' ')[-1]
        else:
            country = ' '.join(proxy_data[3].text.split(' ')[1:])

        proxy = Proxy(
            # ip
            proxy_data[0].text,
            # port
            proxy_data[1].text,
            # protocol
            proxy_data[2].text,
            country,
            # date founded
            datetime.now()
        )

        # передаю именно строковое значение чтобы потом записать в файл writelines list[str]
        result_proxy_list.append(proxy)

    return result_proxy_list


def prepare_for_request(proxy):
    if proxy:
        proxy_req = proxy.for_request()

        proxies = {
            'http': proxy_req,
            'https': proxy_req
        }

        return proxies
    else:
        return None


class TestProxy:
    process_count = None
    db = None

    def __init__(self, process_count=25):
        self.process_count = process_count
        self.db = ProxyDB(process_count)

    def test_request(self, proxy_dict):

        # парсим проксю из строки
        proxy = parse(proxy_dict['str'])
        print('check:', proxy)

        # если получилось спарсить проксю из строки (иногда кривятся строки)
        if proxy:

            url = 'https://www.lagado.com/tools/proxy-test'
            # получаем словарь с проксями для корректного реквеста
            proxies = prepare_for_request(proxy)

            try:
                req = requests.get(url, proxies=proxies, timeout=15)

                # проверяю айпишник с сайта
                # bs = BeautifulSoup(req.text, 'html.parser')
                #
                # ip_addr = bs.find('b', string='IP Address')
                # print('ip: ', ip_addr.parent.text.split(' ')[-1])
                #
                # forwarder = bs.find('b', string='X-Forwarded-For')
                # print('forwarder: ', forwarder.parent.parent.find_all('td')[-1].text)

                self.db.mark_as_working(proxy_dict['id'])

                if req.status_code == 200:
                    return proxies.get('http')
                else:
                    print(req.status_code)
                    return None

            except (ConnectTimeout, ProxyError, ConnectionError, ReadTimeout):

                # прокся полетела с ошибкой - указываем, что тестировали ее
                self.db.increase_try_count(proxy_dict['id'])

                return None
        else:
            return None

    def test_proxies(self):

        # сразу обновляем список проксей, чтоб бежать по всем
        self.db.get_new_proxies()

        # забираем прокси из общего файла
        proxy_list = self.db.get_proxy_list()
        print(len(proxy_list))

        # downloader = multiprocessing.Process(target=get_req, args=(proxies,))
        # downloader.start()
        #
        # timeout = 10
        # time.sleep(timeout)
        #
        # downloader.terminate()

        # будет открыто максимум 50 процесса, остальные будут открыты после завершения предыдущих
        pool = multiprocessing.Pool(processes=self.process_count)

        pool_res = pool.map(self.test_request, proxy_list)
        clear_res = [proxy for proxy in pool_res if proxy]

        return clear_res
        # result = pool.apply_async(get_req, (proxy_list[0],))

        # try:
        #     res = result.get(timeout=10)
        #     print(res)
        # except (ProxyError, multiprocessing.context.TimeoutError) as ex:
        #     print('FUICK')
        #     print(ex)


if __name__ == '__main__':
    # get_new_proxies()

    process_count = 10

    test = TestProxy(process_count)

    res = test.test_proxies()
    print(len(res))
    print(res)

    # тестим удаление прокси из файла
    # lg = f'{get_project_root_path()}\\rus_companies\\parsed_sites\\list_org\\list_org_proxy_list.txt'
    # prox = 'HTTP://85.113.39.89:81 - Russia, 2021-06-03 14:56:48.220569'
    # print(delete_proxy(prox, lg))
