import asyncio

import uvicorn
from fastapi import FastAPI
from starlette.responses import StreamingResponse

from hooks.lifespan import lifespan
from routers import seckill, Dify
from schemas.request import PipeLineRequest
from services import handle_streaming_http_exceptions
from settings import FASTAPI_HOST, FASTAPI_PORT
from hooks.lifespan import pipeline
from utils.AsyncQueue import QueueRequestContext

app = FastAPI(lifespan=lifespan)
from loguru import logger

# app.add_middleware(BaseHTTPMiddleware,dispatch=db_session_middleware)

# app.include_router(seckill.router)
app.include_router(Dify.router)


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/stream")
async def concurrent_stream_response(request_id: PipeLineRequest):
    """支持多个并发请求的流式响应"""

    # 为每个请求创建独立的队列
    queue = await pipeline.queue_manager.create_queue_by_context(
        QueueRequestContext(request_id="111", user_id="user")
    )

    async def stream_generator():
        # 启动该请求的处理任务
        producer_task = asyncio.create_task(
            pipeline.process_request("111")
        )

        try:
            async for message in queue.iterator():
                if message:
                    yield f"data: {message.body}\n\n"

                    # 检查结束标志
                    if hasattr(message, 'is_end') and message.is_end:
                        break

        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
        finally:
            # 清理任务和队列
            if not producer_task.done():
                producer_task.cancel()
            await pipeline.queue_manager.remove_queue("111")

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
        }
    )



if __name__ == '__main__':
    uvicorn.run(app, host=FASTAPI_HOST, port=FASTAPI_PORT)
