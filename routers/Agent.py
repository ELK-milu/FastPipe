import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from schemas.difyRequest import DeleteRequest, RenameRequest, InputRequest
from services import handle_http_exceptions, handle_streaming_http_exceptions
from services.LLM.Dify.Service import get_payload, DifyStreamGenerator
from settings import get_config
from utils.httpManager import HTTPSessionManager

router = APIRouter(prefix='')

BASE_URL = None
httpSessionManager : HTTPSessionManager = HTTPSessionManager()

