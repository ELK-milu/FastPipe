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

httpSessionManager = HTTPSessionManager()


@router.get('/stream')
async def stream(session: aiohttp.ClientSession = Depends(httpSessionManager.get_session)):
    finalsession = SetSessionConfig(key="app-FHpDSmylxvZ8rHcdMWo4XgkE", session=session)
    payload = get_payload("你好，介绍下你自己")

    async def generate():
        try:
            async with finalsession.post(
                    'http://192.168.30.46/v1/chat-messages',
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)) as response:
                async for chunk in response.content.iter_any():
                    if chunk:  # 确保chunk不为空
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
async def order_list(session: aiohttp.ClientSession = Depends(httpSessionManager.get_session)):
    async with session.get('https://www.baidu.com/') as resp:
        assert resp.status == 200
        return await resp.text()
