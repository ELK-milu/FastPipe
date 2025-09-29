import httpx
import asyncio
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from schemas.difyRequest import DeleteRequest, RenameRequest, InputRequest
from schemas.request import AwakeModel
from services import handle_http_exceptions, handle_streaming_http_exceptions
from services.TTS.GPTSovits.Service import get_payload, GPTSovitsStreamGenerator, generate_stream, \
    GPTSovitsFullGenerator
from settings import CONFIG, get_config
from utils.httpManager import HTTPSessionManager

router = APIRouter(prefix='')

BASE_URL = None
httpSessionManager : HTTPSessionManager = HTTPSessionManager()
HEADER = {
    "Authorization": "",
    "Content-Type": "application/json",
    'Connection': 'Keep-Alive',
}

async def Stop():
    pass
async def periodic_ping():
    """每秒调用一次ping函数"""
    while True:
        try:
            await ping()
        except Exception as e:
            print(f"Ping函数执行异常: {e}")
        await asyncio.sleep(60)


async def StartUp():
    global BASE_URL, httpSessionManager
    BASE_URL = get_config()["TTS"]["GPTSoVITS"]["url"]
    httpSessionManager = HTTPSessionManager(base_url=BASE_URL)
    await httpSessionManager.get_client()
    # 启动周期性ping任务
    asyncio.create_task(periodic_ping())


async def ping():
    import settings
    reffile = settings.CONFIG["TTS"]["GPTSoVITS"]["reffile"]
    reftext = settings.CONFIG["TTS"]["GPTSoVITS"]["reftext"]
    session = await GetGenerator(input_data="一", ref_audio_path=reffile, prompt_text=reftext)  # 触发心跳，保持连接
    async for chunk in session.generate():
        pass

async def GetStreamGenerator(input_data: str):
    try:
        session = await httpSessionManager.get_client()
        return GPTSovitsStreamGenerator(client=session,
                                   payload=get_payload(text = input_data,),
                                   header=HEADER,
                                   method="POST",
                                   url=BASE_URL)
    except Exception as e:
        raise e


async def GetGenerator(input_data: str,ref_audio_path:str = "./GPT_SoVITS/models/佼佼仔_中立.wav", prompt_text:str = "今天，我将带领大家穿越时空，去到未来的杭州。"):
    try:
        session = await httpSessionManager.get_client()
        return GPTSovitsFullGenerator(client=session,
                                   payload=get_payload(text = input_data,ref_audio_path=ref_audio_path, prompt_text=prompt_text),
                                   header=HEADER,
                                   method="POST",
                                   url=BASE_URL)
    except Exception as e:
        raise e



@router.get("/gpttest/{text}")
async def gpttest(text: str):
    generator = await GetStreamGenerator(text)
    return StreamingResponse(
        content=generator.generate(),
        media_type="text/event-stream",
    )

@router.post("/awake")
async def Awake(payload: AwakeModel):
    user = payload.user
    voice = payload.voice

    return StreamingResponse(
        content=generate_stream(user, voice),
        media_type="text/event-stream",
    )
