import aiofiles

MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'baidu123'
MYSQL_DB = 'tll_seckill_db'

# aiomysql
# pip install aiomysql
# asyncmy：在保存64位的整形时，有bug：Unexpected <class 'OverflowError'>: Python int too large to convert to C unsigned long
DB_URI = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"

# 这个地方是写死的，后续如果部署到服务器上，可以使用读取环境变量的形式
DATACENTER_ID = 0
WORKER_ID = 0


# redis配置
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = "difyai123456"

# fastapi
# FastAPI
from utils.gethost import get_host_ip
FASTAPI_HOST = get_host_ip()
FASTAPI_PORT = 3420

# refresh token
from datetime import timedelta

JWT_SECRET_KEY = "sdfdasdasdasdsf"
JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=15)


