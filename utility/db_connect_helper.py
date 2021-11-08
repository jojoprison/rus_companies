import psycopg2
from psycopg2.pool import SimpleConnectionPool

from contextlib import contextmanager

import configparser


class DbConnectHelper:
    config_path = None
    conn_count = None

    def __init__(self, conn_count=5, config_path=None):
        self.conn_count = conn_count

        self.connection = None
        self.connection_pool = None

        # поле для пути к файлу конфигурации, заполняем в наследниках
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = None

    def get_single_connection(self):
        # ленивая инициализация соединения
        if not self.connection:
            config = configparser.ConfigParser()
            # забираем конфиг из файла по переданному пути
            config.read(self.config_path)
            db_config = config['db']

            self.connection = psycopg2.connect(
                database=db_config['database'], user=db_config['user'],
                password=db_config['password'])

        return self.connection

    def get_connection_pool(self):
        config = configparser.ConfigParser()
        # забираем конфиг из файла по переданному пути
        config.read(self.config_path)
        db_config = config['db']

        self.connection_pool = SimpleConnectionPool(minconn=1, maxconn=self.conn_count, database=db_config['database'],
                                                    user=db_config['user'],
                                                    password=db_config['password'])

        return self.connection_pool

    def get_connection_old(self):

        # ленивая инициализация соединения
        if not self.connection_pool:
            self.get_connection_pool()

        conn = self.connection_pool.getconn()

        return conn

    def return_conn_to_pool(self, conn):
        self.connection_pool.putconn(conn)

    # чтоб юзать коннект из пула с with
    @contextmanager
    def get_connection(self):

        # ленивая инициализация соединения
        if not self.connection_pool:
            self.get_connection_pool()

        conn = self.connection_pool.getconn()

        print(self.connection_pool)

        yield conn

        self.connection_pool.putconn(conn)

    def __del__(self):

        if self.connection:
            self.connection.close()

        if self.connection_pool:
            self.connection_pool.closeall()


if __name__ == '__main__':
    DbConnectHelper().get_connection_pool()
