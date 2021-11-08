import multiprocessing
import random
from pathlib import Path

from utility.paths import get_project_root_path
from utility.proxy.proxy import parse, get_proxy_list, write_proxy_file

WORKING_FILENAME = f'{get_project_root_path()}/utility/proxy/working_proxy_list.txt'
LIST_ORG_FILENAME = f'{get_project_root_path()}/rus_companies/parsed_sites/list_org/list_org_proxy_list.txt'


# возвращает список проксей из файла, если есть
def get_list_org_proxy_list():

    proxy_file_path = Path(LIST_ORG_FILENAME)

    # проверяем наличие файла с бесплатными проксями
    if proxy_file_path.exists():

        with open(LIST_ORG_FILENAME) as file:
            proxy_list_str = file.readlines()

        return proxy_list_str
    else:
        return []


def list_org_random_proxy():
    file_proxy_ip_list = get_list_org_proxy_list()

    rand_proxy = random.choice(file_proxy_ip_list)

    return rand_proxy


def test_proxy(proxy_str):

    from parsed_sites.list_org.parser import ListOrg

    proxy = parse(proxy_str)

    # если получилось спарсить проксю из строки (иногда кривятся строки)
    if proxy:

        list_org = ListOrg(proxy)

        try:
            page_title = list_org.open_site().strip()

            if page_title.find('Каталог') != -1:
                # записываем прокси в файл для list_org
                write_proxy_file(proxy, LIST_ORG_FILENAME)
                return proxy

            return None

        except Exception:
            return None
    else:
        return None


def test_proxies():

    # забираем прокси из общего файла
    proxy_list = get_proxy_list()
    print(len(proxy_list))

    pool = multiprocessing.Pool(processes=5)

    pool_res = pool.map(test_proxy, proxy_list)
    clear_res = [str(proxy).replace('\n', '') for proxy in pool_res if proxy]

    return clear_res


if __name__ == '__main__':

    res = test_proxies()
    print(len(res))
    print(res)
