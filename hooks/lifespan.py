import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from loguru import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.add("logs/file_{time}.log", rotation="500 MB", enqueue=True, level="INFO")
    """FastAPI lifespan事件管理器"""
    # 启动时执行
    yield
