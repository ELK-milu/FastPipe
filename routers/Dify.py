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
            ) as response:
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            raise

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
