from fastapi import APIRouter
from starlette.responses import StreamingResponse

from schemas.request import AwakeModel
from services.TTS.LiveTalking.LiveTalking import LiveTalkingStreamGenerator, get_payload, generate_stream
from utils.httpManager import HTTPSessionManager

router = APIRouter(prefix='')

BASE_URL = "http://117.50.184.42:8010"
httpSessionManager = HTTPSessionManager(base_url=f"{BASE_URL}")
HEADER = {
    'Authorization': "",
    'Content-Type': 'application/json',
    'Connection': 'Keep-Alive'
}

async def GetGenerator(text: str,sessionid:int,voice:str,emotion:str):
    session = await httpSessionManager.get_client()
    return LiveTalkingStreamGenerator(client=session,
                                      payload=get_payload(text=text,
                                                          sessionid=sessionid,
                                                          voice=voice,
                                                          emotion=emotion),
                                      header=HEADER,
                                      method="POST",
                                      url=f"{BASE_URL}/human")


@router.post("/awake")
async def Awake(payload: AwakeModel):
    user = payload.user
    voice = payload.voice

    return StreamingResponse(
        content=generate_stream(user, voice),
        media_type="text/event-stream",
    )

