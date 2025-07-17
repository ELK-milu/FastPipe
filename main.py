import uvicorn
from fastapi import FastAPI

from hooks.lifespan import lifespan
from hooks.middlewares import db_session_middleware
from starlette.middleware.base import BaseHTTPMiddleware
from routers import seckill, Dify
from settings import FASTAPI_HOST, FASTAPI_PORT


app = FastAPI(lifespan=lifespan)
#app.add_middleware(BaseHTTPMiddleware,dispatch=db_session_middleware)

#app.include_router(seckill.router)
app.include_router(Dify.router)

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}



if __name__ == '__main__':
    uvicorn.run(app,host=FASTAPI_HOST, port=FASTAPI_PORT)
