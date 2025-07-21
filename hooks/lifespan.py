import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from loguru import logger

from modules.LLM.Dify.Dify_LLM_Module import Dify_LLM_Module
from modules.pipeline.pipeline import PipeLine

# 创建Pipeline
pipeline = PipeLine.create_pipeline(
    Dify_LLM_Module,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.add("logs/file_{time}.log", rotation="500 MB", enqueue=True, level="INFO")
    """FastAPI lifespan事件管理器"""
    # 启动时执行
    yield
