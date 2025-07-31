from fastapi import APIRouter
from starlette.responses import StreamingResponse

from schemas.request import AwakeModel
from services.TTS.LiveTalking.Service import LiveTalkingStreamGenerator, get_payload, generate_stream
from settings import CONFIG
from utils.httpManager import HTTPSessionManager

router = APIRouter(prefix='')

BASE_URL = CONFIG["TTS"]["LiveTalking"]["url"]
httpSessionManager = HTTPSessionManager(base_url=f"{BASE_URL}")
HEADER = {
    'Authorization': "",
    'Content-Type': 'application/json',
    'Connection': 'Keep-Alive'
}

async def GetGenerator(text: str,sessionid:int,voice:str,emotion:str):
    try:
        session = await httpSessionManager.get_client()
        return LiveTalkingStreamGenerator(client=session,
                                          payload=get_payload(text=text,
                                                              sessionid=sessionid,
                                                              voice=voice,
                                                              interrupt=CONFIG["TTS"]["LiveTalking"]["interrupt"],
                                                              type=CONFIG["TTS"]["LiveTalking"]["type"],
                                                              emotion=emotion),
                                          header=HEADER,
                                          method="POST",
                                          url=f"{BASE_URL}/human")
    except Exception as e:
        raise e


@router.post("/awake")
async def Awake(payload: AwakeModel):
    user = payload.user
    voice = payload.voice

    return StreamingResponse(
        content=generate_stream(user, voice),
        media_type="text/event-stream",
    )

