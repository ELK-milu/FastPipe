import asyncio
import time
import uuid
import base64
import uvicorn
from fastapi import FastAPI
from starlette.responses import StreamingResponse

from hooks.lifespan import lifespan
from routers import seckill, Dify
from schemas.request import PipeLineRequest
from services import handle_streaming_http_exceptions
from settings import FASTAPI_HOST, FASTAPI_PORT
from modules.LLM.Dify.Dify_LLM_Module import Dify_LLM_Module
from modules.pipeline.pipeline import PipeLine
from utils.AsyncQueue import QueueRequestContext
from utils.AudioChange import convert_audio_to_wav

app = FastAPI(lifespan=lifespan)
from loguru import logger

# app.add_middleware(BaseHTTPMiddleware,dispatch=db_session_middleware)

# app.include_router(seckill.router)
app.include_router(Dify.router)

# 创建Pipeline
pipeline = PipeLine.create_pipeline(
    Dify_LLM_Module,
)


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/input")
async def concurrent_stream_response(request: PipeLineRequest):
    """支持多个并发请求的流式响应"""
    # 混合流需要重新封装下再输出
    request_id = uuid.uuid4().hex
    # 为每个请求创建独立的队列
    queue = await pipeline.get_or_create_queue_by_context(
        QueueRequestContext(request_id=request_id, user_id=request.user)
    )
    async def stream_generator():
        # 启动该请求的处理任务
        producer_task = asyncio.create_task(
            pipeline.process_request(request_id)
        )
        try:
            async for message_chunk in queue.iterator():
                if message_chunk:
                    # 检查结束标志
                    if hasattr(message_chunk, 'is_end') and message_chunk.is_end:
                        break
                    if isinstance(message_chunk, bytes):
                        # 二进制数据（如音频）编码为base64
                        wav_audio = convert_audio_to_wav(message_chunk, set_sample_rate=24000)
                        response_data = {
                            "type": "audio/wav",
                            "chunk": message_chunk.b64encode(wav_audio).decode("utf-8")
                        }
                    elif isinstance(message_chunk, str):
                        # 文本数据直接输出
                        response_data = {
                            "type": "text",
                            "chunk": message_chunk
                        }
                    else:
                        # 其他类型数据转换为字符串
                        response_data = {
                            "type": "text",
                            "chunk": str(message_chunk)
                        }
                    yield response_data


        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
        finally:
            # 清理任务和队列
            if not producer_task.done():
                producer_task.cancel()
            await pipeline.queue_manager.remove_queue(request_id)

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
