import uvicorn
from fastapi import FastAPI
from hooks.lifespan import lifespan
from modules.TTS.LiveTalking.LiveTalking_Module import LiveTalking_Module
from routers import Dify, LiveTalking, GPTSovits, SetPipeLine, SetStartUp, router
from settings import FASTAPI_HOST, FASTAPI_PORT, set_config, set_port, GetPort
from modules.LLM.Dify.Dify_LLM_Module import Dify_LLM_Module
from modules.pipeline.pipeline import PipeLine

app = FastAPI(lifespan=lifespan)

# app.add_middleware(BaseHTTPMiddleware,dispatch=db_session_middleware)
app.include_router(router)
app.include_router(Dify.router)
app.include_router(LiveTalking.router)
# 创建Pipeline
pipeline = PipeLine.create_pipeline(
    Dify_LLM_Module,
    LiveTalking_Module
)
DEFAULT_YAML = "VideoHumanConfig.yaml"
DEFAULT_PORT = 3422
async def StartUp():
    await Dify.StartUp()
    await LiveTalking.StartUp()
    await pipeline.StartUp()


if __name__ == '__main__':
    SetPipeLine(pipeline)
    SetStartUp(StartUp)
    set_port(DEFAULT_PORT)
    set_config(DEFAULT_YAML)
    uvicorn.run(app, host=FASTAPI_HOST, port=GetPort(),workers=1)
