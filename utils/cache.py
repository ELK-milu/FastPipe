from settings import REDIS_PASSWORD, REDIS_HOST, REDIS_PORT, REDIS_DB
from .single import SingletonMeta
import redis.asyncio as redis
import json
from datetime import datetime


class TLLRedis(metaclass=SingletonMeta):

    SECKILL_KEY = "seckill_{}"
    SECKILL_ORDER_KEY = "seckill_order_{user_id}_{seckill_id}"
    SECKILL_STOCK_KEY = "seckill_stock_{}"
    SECKILL_STOCK_LOCK_KEY = "seckill_stock_lock_{}"

    def __init__(self):
        self.client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD)

    async def set(self, key, value, ex=5*60*60):
        await self.client.set(key, value, ex)

    async def set_dict(self, key: str, value: dict, ex: int=5*60*60):
        await self.set(key, json.dumps(value), ex)

    async def get(self, key):
        value = await self.client.get(key)
        if type(value) == bytes:
            return value.decode('utf-8')
        return value

    async def get_dict(self, key: str):
        value = await self.get(key)
        if not value:
            return None
        return json.loads(value)

    async def delete(self, key):
        await self.client.delete(key)

    async def decrease(self, key, amount=1):
        await self.client.decrby(key, amount)

    async def increase(self, key, amount=1):
        await self.client.incrby(key, amount)

    async def close(self):
        await self.client.aclose()


tll_redis = TLLRedis()
