import random

from utility.db_connect_helper import DbConnectHelper
from utility.paths import get_project_root_path

# путь к конфигу с БД проксей
CONFIG_PATH = f'{get_project_root_path()}/utility/proxy/proxy_db_config.ini'


class ProxyDB:

    def __init__(self, conn_count=25):
        # передаем конфиг, получаем коннект к базе
        self.db_helper = DbConnectHelper(conn_count, CONFIG_PATH)
        # self.con = self.db_helper.get_single_connection()

    # получаем коннект из пула
    def get_conn(self):
        return self.db_helper.get_connection()

    # возвращаем коннект в пул
    def return_conn(self, conn):
        self.db_helper.return_conn_to_pool(conn)

    # получаем свежие бесплатные прокси с сайта и пишем их в базу
    def get_new_proxies(self):

        from utility.proxy.proxy import index_page_free_proxy_list

        with self.get_conn() as conn:
            with conn.cursor() as cur:

                # забираем свежие фришные прокси с сайта
                index_free_proxy_list = index_page_free_proxy_list()
                # print('CURRENT FREE PROXIES: ', index_free_proxy_list)

                db_proxy_signature_list = self.get_proxy_signature_list(conn)
                # print('db:', db_proxy_signature_list)

                added = {'count': 0, 'proxies': []}

                for fresh_proxy in index_free_proxy_list:

                    fresh_proxy_signature = fresh_proxy.signature()

                    if fresh_proxy_signature not in db_proxy_signature_list:
                        cur.execute('INSERT INTO proxy(ip, port, signature, protocol, country, '
                                    'date_founded, str) '
                                    'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                                    (fresh_proxy.ip, fresh_proxy.port, fresh_proxy_signature,
                                     fresh_proxy.protocol, fresh_proxy.country,
                                     fresh_proxy.date_founded, str(fresh_proxy)))

                        added['count'] += 1
                        added['proxies'].append(fresh_proxy)

            conn.commit()

        # self.return_conn(conn)

        return added

    # возвращает список всех проксей из базы
    def get_proxy_list(self, working=False):

        # читать из файла с проверенными работающими проксями, или из файла со всеми
        if working:
            query = 'SELECT id, str FROM proxy WHERE working = TRUE'
        else:
            query = 'SELECT id, str FROM proxy'

        with self.get_conn() as conn:
            with conn.cursor() as cur:

                cur.execute(query)

                # наша стринговая прокся находится на первом месте в результирующем тупле
                proxy_list = [{'id': proxy_tuple[0], 'str': proxy_tuple[1]} for proxy_tuple in cur.fetchall()]

        return proxy_list

    # получаем список сигнатур всех проксей из базы
    def get_proxy_signature_list(self, conn=None):

        if conn:
            with conn.cursor() as cur:

                cur.execute('SELECT signature FROM proxy')

                proxy_signature_list = [proxy_signature_tuple[0] for proxy_signature_tuple in cur.fetchall()]
        else:
            with self.get_conn() as conn:
                with conn.cursor() as cur:

                    cur.execute('SELECT signature FROM proxy')

                    proxy_signature_list = [proxy_signature_tuple[0] for proxy_signature_tuple in cur.fetchall()]

        return proxy_signature_list

    def random_proxy(self):

        with self.get_conn() as conn:
            with conn.cursor() as cur:

                cur.execute('SELECT id, str FROM proxy ORDER BY random() LIMIT 1;')

                random_proxy = cur.fetchone()

        return random_proxy

    # сохраняем проксю в базе
    def save_proxy(self, proxy):

        proxy_signature = proxy.signature()

        with self.get_conn() as conn:
            # если прокси еще нет в файле
            # передаем в метод уже существующий конннект, чтоб новый не открывать в пуле
            if proxy_signature not in self.get_proxy_signature_list(conn):

                with conn.cursor() as cur:

                    cur.execute('INSERT INTO proxy(ip, port, signature, protocol, country, '
                                'date_founded, str) '
                                'VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id',
                                (proxy.ip, proxy.port, proxy_signature,
                                 proxy.protocol, proxy.country,
                                 proxy.date_founded, str(proxy)))

                    added_proxy_id = cur.fetchone()[0]

                    conn.commit()

                return added_proxy_id
            else:
                return None

    # деактивируем проксю, оставляем ее в базе на будущее
    def deactivate_proxy(self, proxy_id):

        with self.get_conn() as conn:
            with conn.cursor() as cur:
                inactivated_proxy_id = cur.execute('UPDATE proxy SET inactive = True WHERE id = %s',
                                                   (proxy_id,))
        conn.commit()

        return True

    # помечаем, что прокся работает
    def mark_as_working(self, proxy_id):

        with self.get_conn() as conn:
            with conn.cursor() as cur:

                cur.execute('UPDATE proxy SET working = True, try_connect = 0, inactive = False WHERE id = %s',
                            (proxy_id,))

        conn.commit()

        return True

    # увеличиваем кол-во попыток использования прокси
    def increase_try_count(self, proxy_id):

        with self.get_conn() as conn:
            with conn.cursor() as cur:

                cur.execute('SELECT try_connect FROM proxy WHERE id = %s',
                            (proxy_id,))

                try_connect_count = cur.fetchone()[0]

                # тестим проксю всего 5 раз. не прошла - пока-пока
                if try_connect_count >= 4:
                    is_inactive = True
                else:
                    is_inactive = False

                cur.execute('UPDATE proxy SET try_connect = %s + 1, inactive = %s, working = False '
                            'WHERE id = %s',
                            (try_connect_count, is_inactive, proxy_id,))

        conn.commit()

        return True

    # TODO del утилити метод когда переносил все из файла в базу
    def save_old_file(self):

        from utility.proxy.proxy import parse

        FREE_FILENAME = f'{get_project_root_path()}/utility/proxy/free_proxy_list.txt'
        WORKING_FILENAME = f'{get_project_root_path()}/utility/proxy/working_proxy_list.txt'

        proxy_file_name = FREE_FILENAME

        with open(proxy_file_name) as file:
            proxy_list_str = file.readlines()

        cur = self.con.cursor()

        db_proxy_signature_list = self.get_proxy_signature_list()

        for old_proxy_str in proxy_list_str:

            old_proxy = parse(old_proxy_str)
            old_proxy_signature = old_proxy.signature()

            if old_proxy_signature not in db_proxy_signature_list:
                cur.execute('INSERT INTO proxy(ip, port, signature, protocol, country, '
                            'date_founded, str) '
                            'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                            (old_proxy.ip, old_proxy.port, old_proxy_signature,
                             old_proxy.protocol, old_proxy.country,
                             old_proxy.date_founded, str(old_proxy)))

        cur.close()
        self.con.commit()


if __name__ == '__main__':
    proxy_db = ProxyDB(1)

    new = proxy_db.get_new_proxies()
    print(new)

    # oo = proxy_db.get_proxy_list()
    # print(oo)

    # proxy_db.increase_try_count(1)

    # proxy_db.mark_as_working(1)

    # proxy_db.save_old_file()

    # listt = proxy_db.get_proxy_list()
    # print(listt)

    # list_sing = proxy_db.get_proxy_signature_list()
    # print(list_sing)

    # temp_proxy = parse('HTTP://110.232.64.14:8080 - Indonesia, 2021-09-09 18:34:45.919244')

    # soso = proxy_db.save_proxy(temp_proxy)
    # print(soso)

    rand_prox = proxy_db.random_proxy()
    print(rand_prox)
