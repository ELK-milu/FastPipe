from functools import wraps
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from utils.httpManager import HTTPSessionManager
from loguru import logger


def handle_http_exceptions(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # 直接调用原函数，依赖由 FastAPI 管理
            result = await func(*args, **kwargs)
            return {"status": "success", "data": result}
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    return wrapper


def handle_streaming_http_exceptions(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # 直接返回原函数结果（可能是StreamingResponse）
            return await func(*args, **kwargs)
        except HTTPException:
            # 如果已经是HTTPException，直接抛出
            raise
        except Exception as e:
            logger.error(f"Streaming Error in {func.__name__}: {str(e)}")
            # 创建一个错误消息的生成器
            async def error_generator():
                yield f"data: [ERROR] {str(e)}\n\n"
            # 返回包含错误信息的流式响应
            return StreamingResponse(
                error_generator(),
                media_type="text/event-stream",
                status_code=500
            )

    return wrapper