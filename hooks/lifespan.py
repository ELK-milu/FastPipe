import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from loguru import logger

from settings import FASTAPI_HOST, FASTAPI_PORT, GetPort


#from utils.rabbitmq.rabbit_mq_producer import rabbit_mq_producer
async def test():
    await asyncio.sleep(0)

StartUp : callable = test
Stop : callable = test

def SetCallBack(start_callback : callable, stop_callback : callable):
    global StartUp
    global Stop
    StartUp = start_callback
    Stop = stop_callback



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.add("logs/file_{time}.log", rotation="500 MB", enqueue=True, level="INFO")
    await asyncio.sleep(0.5)
    await StartUp()
    """FastAPI lifespan事件管理器"""
    # 启动时执行
    yield
    await Stop()