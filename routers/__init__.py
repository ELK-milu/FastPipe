import asyncio
import base64
import json
import time
import uuid
from fastapi import APIRouter
from loguru import logger
from starlette.responses import StreamingResponse
from schemas.request import PipeLineRequest
from services import handle_streaming_http_exceptions
from utils.AsyncQueue import QueueRequestContext
from utils.AudioChange import convert_wav_to_pcm_simple

router = APIRouter(prefix='')


async def test():
    await asyncio.sleep(0)

StartUp : callable = test
pipeline = None  # 初始化为 None，稍后通过 SetPipeLine 设置

def SetPipeLine(set_Pipeline):
    global pipeline
    pipeline = set_Pipeline

def SetStartUp(func : callable):
    global StartUp
    StartUp = func

@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/startup")
@handle_streaming_http_exceptions
async def root():
    await StartUp()
    return {"message": "Hello World"}

@router.get("/heartbeat")
async def process_input(user: str):
    """心跳请求"""
    await pipeline.heartbeat()
    return {"message": "Success"}


@router.get("/schema")
@handle_streaming_http_exceptions
async def get_schema():
    """返回API请求模式"""
    return PipeLineRequest.model_json_schema()


@router.post("/input")
async def concurrent_stream_response(request: PipeLineRequest):
    """支持多个并发请求的流式响应"""
    # 混合流需要重新封装下再输出
    request_id = uuid.uuid4().hex
    # 为每个请求创建独立的队列
    queue = await pipeline.get_or_create_queue_by_context(
        QueueRequestContext(request_id=request_id,
                            user_id=request.user,
                            request_dict=request.model_dump(),
                            )
    )
    async def stream_generator():
        start_time = time.time()
        first_str = False
        first_audio = False
        # 启动该请求的处理任务
        producer_task = asyncio.create_task(
            pipeline.process_request(
                text=request.text,
                user=request.user,
                request_id=request_id,
                type="str",
                entry=request.Entry
            )
        )
        try:
            async for message_chunk in queue.iterator():
                if message_chunk:
                    chunk = message_chunk.body
                    # 检查结束标志
                    if message_chunk.type == "end":
                        response_data = {
                            "type": "end",
                            "chunk": "[DONE]"
                        }
                    elif message_chunk.type == "audio":
                        # 二进制数据（如音频）编码为base64

                        if isinstance(chunk, bytes):
                            wav_audio = convert_wav_to_pcm_simple(chunk, set_sample_rate=24000)
                            response_data = {
                                "type": "audio/wav",
                                "chunk": base64.b64encode(wav_audio).decode("utf-8")
                            }
                        if not first_audio:
                            first_audio = True
                            logger.info("生成first_audio的耗时:" + str(time.time() - start_time))
                    elif message_chunk.type == "str":

                        if not first_str:
                            first_str = True
                            logger.info("生成first_str的耗时:" + str(time.time() - start_time))
                        # 文本数据直接输出
                        response_data = {
                            "type": "text",
                            "chunk": chunk
                        }
                    elif message_chunk.type == "info":
                        response_data = {
                            "type": "info",
                            "chunk": chunk
                        }
                    elif message_chunk.type == "error":
                        logger.error(str(chunk))
                        response_data = {
                            "type": "error",
                            "chunk": str(chunk)
                        }
                    elif message_chunk.type == "tool":
                        #print(chunk)
                        tool_output = chunk["data"]["data"]["output"]
                        #print("tool_output:", tool_output)
                        final_type = await get_tool_response_type(tool_output)
                        response_data = {
                            "type": final_type,
                            "chunk": tool_output["tool_response"]
                        }
                    response_data = json.dumps(response_data, ensure_ascii=False)
                    yield f"data: {response_data}\n\n"
                    if message_chunk.type == "end":
                        break
        except Exception as e:
            #raise e
            logger.error(str(e))
            response_data = {
                "type": "error",
                "chunk": str(e)
            }
            response_data = json.dumps(response_data, ensure_ascii=False)
            yield f"data: {response_data}\n\n"
            raise e
        finally:
            # 清理任务和队列
            if not producer_task.done():
                producer_task.cancel()

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
        }
    )

async def get_tool_response_type(tool_output: dict) -> str:
    if "pic" in tool_output['tool_call_name']:
        return "image"
