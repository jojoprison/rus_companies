import asyncio
from sys import platform

import asyncpg


# старый код с асинхронщиной, меняю дабы наладить работу в многопроцессорности
class DbConnect:
    def __init__(self):
        self.connect = None

    async def get_pg_tt_connect(self):

        get_conn_task = asyncio.create_task(self._get_pg_local_connect())

        try:
            conn = await get_conn_task
            return conn

        except (OSError, asyncio.TimeoutError,
                asyncpg.CannotConnectNowError,
                asyncpg.PostgresConnectionError):
            await asyncio.sleep(1)

        except asyncpg.PostgresError as postgres_error:
            return postgres_error

    async def _get_pg_local_connect(self):
        # TODO get from config file
        params = {
            'database': 'rus_companies',
            'user': 'postgres',
            'password': 'postgres',
            'host': 'localhost',
        }

        print('connect local')

        # придумать где закрывать коннект к базе
        # con = await asyncpg.create_pool(**params)
        con = await asyncpg.connect(**params)

        return con

    # метод для теста асинк коннекта из других мест
    async def get_connect(self):
        if not self.connect:
            # получаем коннект к базе через текущий луп (т.к. файл запускается первым, то луп создается тута)
            self.connect = await self.get_pg_tt_connect()

        print('PUB DB location')

        return self.connect


# conn = asyncio.get_event_loop().run_until_complete(DbConnect().get_pg_tt_connect())
# print('PUB DB location')
