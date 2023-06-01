import asyncio
import aiomysql
import pymysql
import config as Config

class PoolMysqlAsync:

    def __init__(self, host = Config.MYSQL_HOST, database = 'mysql', user = Config.MYSQL_USER, password = Config.MYSQL_PASSWORD, port= Config.MYSQL_PORT ,loop=None, minsize=3, maxsize=5, return_dict=True, pool_recycle=7*3600, autocommit=True, charset="utf8mb4", **kwargs):
        self.db_args = {'host': host, 'db': database, 'user': user, 'password': password,'port':port, 'minsize': minsize, 'maxsize': maxsize, 'charset': charset, 'loop': loop, 'autocommit': autocommit, 'pool_recycle': pool_recycle,}
        if return_dict:
            self.db_args['cursorclass'] = aiomysql.cursors.DictCursor
        if kwargs:
            self.db_args.update(kwargs)
        PoolMysqlAsync.pool = None

    def release(self):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        if PoolMysqlAsync.pool is not None:
            PoolMysqlAsync.pool.terminate()
            PoolMysqlAsync.pool = None

    async def select_db(self, db):
        await aiomysql.select_db(db)

    async def init_pool(self):
        if not self.db_args['loop']:
            self.db_args['loop'] = asyncio.get_running_loop()
        PoolMysqlAsync.pool = await aiomysql.create_pool(**self.db_args)

    async def execute(self, query, *parameters, **kwparameters):
        if not PoolMysqlAsync.pool:
            await self.init_pool()
        async with PoolMysqlAsync.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(query, kwparameters or parameters)
                except Exception:
                    # https://github.com/aio-libs/aiomysql/issues/340
                    await conn.ping()
                    await cur.execute(query, kwparameters or parameters)
                    
                if query.upper().startswith("UPDATE") or query.upper().startswith("DELETE"):
                    return (cur.rowcount >= 1)
                return cur.lastrowid
            
    async def fetchone(self, query, *parameters, **kwparameters):
        if not PoolMysqlAsync.pool:
            await self.init_pool()
        async with PoolMysqlAsync.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(query, kwparameters or parameters)
                    ret = await cur.fetchone()
                except pymysql.err.InternalError:
                    await conn.ping()
                    await cur.execute(query, kwparameters or parameters)
                    ret = await cur.fetchone()
                return ret

    async def fetchall(self, query, *parameters, **kwparameters):
        if not PoolMysqlAsync.pool:
            await self.init_pool()
        async with PoolMysqlAsync.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(query, kwparameters or parameters)
                    ret = await cur.fetchall()
                except pymysql.err.InternalError:
                    await conn.ping()
                    await cur.execute(query, kwparameters or parameters)
                    ret = await cur.fetchall()
                return ret

    async def check_num_rows(self, table_name, field, value):
        sql = 'SELECT count(*) FROM {} WHERE {}=%s limit 1'.format(table_name, field) #{'count(*)': 0}
        res =  await self.fetchone(sql, value)
        return res['count(*)']

    async def get_num_rows(self, table_name ):
        sql = 'SELECT count(*) FROM {}'.format(table_name) #{'count(*)': 0}
        res =  await self.fetchone(sql)
        return res['count(*)']