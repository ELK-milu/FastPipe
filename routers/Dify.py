import asyncio
import time
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from schemas import response
from services import handle_http_exceptions, handle_streaming_http_exceptions
from services.Dify import SetSessionConfig, get_payload
from utils.httpManager import HTTPSessionManager
from utils.auth import AuthHandler
import aiohttp

auth_handler = AuthHandler()

router = APIRouter(prefix='/test')

httpSessionManager = HTTPSessionManager(base_url="http://192.168.30.46/v1/chat-messages")


@router.get("/debug")
async def debug(client: httpx.AsyncClient = Depends(httpSessionManager.get_client)):
    # 方法1：通过实际请求检测
    async with client.stream("GET", "https://httpbin.org/get") as response:
        http_version = response.http_version  # 返回 "HTTP/1.1" 或 "HTTP/2"
        print(http_version)

@router.get('/stream')
async def stream(client: httpx.AsyncClient = Depends(httpSessionManager.get_client)):
    # 配置会话和请求参数
    finalsession = SetSessionConfig(key="app-FHpDSmylxvZ8rHcdMWo4XgkE", session=client)
    payload = get_payload("你好，介绍下你自己")

    async def generate():
        try:
            async with finalsession.stream(
                "POST",
                'http://192.168.30.46/v1/chat-messages',
                json=payload,
                timeout=300.0  # httpx 的超时单位为秒
            ) as response :
                start_time = time.time()
                #logger.info(f"{start_time}开始发送请求")
                async for chunk in response.aiter_bytes(chunk_size=1024):
                    if chunk:
                        yield chunk
                    await asyncio.sleep(0)  # 主动释放事件循环控制权
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            raise
        finally:
            final_time =  time.time()
            #logger.info(f"{final_time}请求结束,耗时:{final_time-start_time}s")

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={'Connection': 'keep-alive'}
    )

@router.get('/')
@handle_http_exceptions
async def order_list(session: httpx.AsyncClient = Depends(httpSessionManager.get_client)):
    async with session.get('https://www.baidu.com/') as resp:
        assert resp.status == 200
        return await resp.text()
