import asyncio

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from schemas.request import AwakeModel
from services.TTS.GPTSovits.Service import get_payload, GPTSovitsStreamGenerator, generate_stream, \
    GPTSovitsFullGenerator, TTSWebSocketClient, GPTSovitsWsGenerator
from settings import CONFIG, get_config

router = APIRouter(prefix='')

URL = get_config()["TTS"]["GPTSoVITS"]["ws"]

WS_CLIENT = TTSWebSocketClient(URL)

async def StartUp():
    global URL,WS_CLIENT
    WS_URL = get_config()["TTS"]["GPTSoVITS"]["ws"]
    WS_CLIENT = TTSWebSocketClient(WS_URL)
    await WS_CLIENT.connect()

async def Stop():
    await WS_CLIENT.disconnect()

async def GetStreamGenerator(input_data: str):
    pass
    '''
    try:
        session = await httpSessionManager.get_client()
        return GPTSovitsStreamGenerator(client=session,
                                        payload=get_payload(text = input_data,),
                                        header=HEADER,
                                        method="POST",
                                        url=WS_URL)
    except Exception as e:
        raise e
    '''


async def GetWSGenerator(input_data: str, ref_audio_path:str = "./GPT_SoVITS/models/佼佼仔_中立.wav", prompt_text:str = "今天，我将带领大家穿越时空，去到未来的杭州。"):
    try:
        await asyncio.sleep(0)
        return GPTSovitsWsGenerator(client=WS_CLIENT,
                                    payload=get_payload(text = input_data,ref_audio_path=ref_audio_path, prompt_text=prompt_text),
                                    header=None,
                                    method=None,
                                    url=URL)
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
