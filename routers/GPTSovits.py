import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from schemas.difyRequest import DeleteRequest, RenameRequest, InputRequest
from schemas.request import AwakeModel
from services import handle_http_exceptions, handle_streaming_http_exceptions
from services.TTS.GPTSovits.Service import get_payload, GPTSovitsStreamGenerator, generate_stream, \
    GPTSovitsFullGenerator
from settings import CONFIG
from utils.httpManager import HTTPSessionManager

router = APIRouter(prefix='')

BASE_URL = CONFIG["TTS"]["GPTSoVITS"]["url"]
httpSessionManager = HTTPSessionManager(base_url=BASE_URL)
HEADER = {
    "Authorization": "",
    "Content-Type": "application/json",
    'Connection': 'Keep-Alive',
}

async def StartUp():
    await httpSessionManager.get_client()

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


async def GetGenerator(input_data: str):
    try:
        session = await httpSessionManager.get_client()
        return GPTSovitsFullGenerator(client=session,
                                   payload=get_payload(text = input_data,),
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
