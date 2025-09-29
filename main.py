import asyncio

import uvicorn
from fastapi import FastAPI
from hooks.lifespan import lifespan, SetCallBack
from modules.TTS.GPTSovits.GPTSovit_ws_Module import GPTSovits_ws_Module
from modules.TTS.GPTSovits.GPTSovits_Module import GPTSovits_Module
from routers import Dify, LiveTalking, GPTSovits, router, SetPipeLine,GPTSovits_ws
from settings import FASTAPI_HOST, FASTAPI_PORT, set_port, set_config, GetPort
from modules.LLM.Dify.Dify_LLM_Module import Dify_LLM_Module
from modules.pipeline.pipeline import PipeLine

app = FastAPI(lifespan=lifespan)

# app.add_middleware(BaseHTTPMiddleware,dispatch=db_session_middleware)
app.include_router(router)
app.include_router(Dify.router)
app.include_router(GPTSovits.router)
# 创建Pipeline
pipeline = PipeLine.create_pipeline(
    Dify_LLM_Module,
    GPTSovits_Module
)

DEFAULT_YAML = "Config.yaml"
DEFAULT_PORT = 3421
async def StartUp():
    await Dify.StartUp()
    await GPTSovits.StartUp()
    await pipeline.StartUp()

async def Stop():
    await Dify.Stop()
    await GPTSovits.Stop()
    await pipeline.Stop()

if __name__ == '__main__':
    SetPipeLine(pipeline)
    SetCallBack(StartUp,Stop)
    set_port(DEFAULT_PORT)
    set_config(DEFAULT_YAML)
    uvicorn.run("main:app", host=FASTAPI_HOST, port=GetPort(),workers=1)