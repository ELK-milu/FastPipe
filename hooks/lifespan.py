import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from loguru import logger

from settings import FASTAPI_HOST, FASTAPI_PORT


#from utils.rabbitmq.rabbit_mq_producer import rabbit_mq_producer

async def awake():
    task = asyncio.create_task(awake_post())

async def awake_post():
    await asyncio.sleep(0.5)
    async with httpx.AsyncClient() as client:
        url = f"http://{FASTAPI_HOST}:{FASTAPI_PORT}/startup"
        response = await client.get(url)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.add("logs/file_{time}.log", rotation="500 MB", enqueue=True, level="INFO")
    await awake()
    """FastAPI lifespan事件管理器"""
    # 启动时执行
    yield
