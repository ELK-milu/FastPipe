import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from schemas.difyRequest import DeleteRequest, RenameRequest, InputRequest
from services import handle_http_exceptions, handle_streaming_http_exceptions
from services.LLM.Dify.Dify import get_payload, DifyStreamGenerator
from utils.httpManager import HTTPSessionManager

router = APIRouter(prefix='')

BASE_URL = "http://192.168.30.46/v1"
httpSessionManager = HTTPSessionManager(base_url="http://192.168.30.46/v1/chat-messages")
KEY = "app-FHpDSmylxvZ8rHcdMWo4XgkE"
HEADER = {
    'Authorization': f'Bearer {KEY}',
    'Content-Type': 'application/json',
    'Connection': 'Keep-Alive'
}


async def GetGenerator(input_data: str):
    try:
        session = await httpSessionManager.get_client()
        return DifyStreamGenerator(client=session,
                                   payload=get_payload(input_data),
                                   header=HEADER,
                                   method="POST",
                                   url="http://192.168.30.46/v1/chat-messages")
    except Exception as e:
        raise e


'''
@router.post('/dify/stream')
@handle_streaming_http_exceptions
async def stream(input: InputRequest, client: httpx.AsyncClient = Depends(httpSessionManager.get_client)):
    text = input.input_data
    payload = get_payload(text)
    generator = DifyStreamGenerator(client=client,
                                    payload=payload,
                                    header=HEADER,
                                    method="POST",
                                    url="http://192.168.30.46/v1/chat-messages")
    return StreamingResponse(
        generator.generate(),
        media_type="text/event-stream",
        headers={'Connection': 'keep-alive'}
    )
'''


@router.get("/messages")
@handle_http_exceptions
async def get_conversations(user: str, conversation_id: str,
                            session: httpx.AsyncClient = Depends(httpSessionManager.get_client)):
    """获取历史会话"""
    # 调用Dify API获取数据（示例实现）
    result = await session.get(url=f"{BASE_URL}/messages?user={user}&conversation_id={conversation_id}")
    return result.json()


@router.get("/conversations")
@handle_http_exceptions
async def get_conversations(user: str, last_id: str = None, limit: int = 20,
                            session: httpx.AsyncClient = Depends(httpSessionManager.get_client)):
    """获取用户会话列表"""
    result = await session.get(url=f"{BASE_URL}/conversations?user={user}&last_id={last_id}&limit={limit}",
                               headers=HEADER)
    # 调用Dify API获取数据（示例实现）
    return result.json()


@router.delete("/conversations/delete")
@handle_http_exceptions
async def delete_conversation(request: DeleteRequest,
                              session: httpx.AsyncClient = Depends(httpSessionManager.get_client)):
    """删除指定会话"""
    user = request.user
    conversation_id = request.conversation_id
    payload = {
        "user": user
    }
    result = await session.request(method="DELETE", url=f"{BASE_URL}/conversations/{conversation_id}", json=payload,
                                   headers=HEADER)
    # 调用Dify API删除会话
    return result.json()


@router.post("/conversations/rename")
@handle_http_exceptions
async def rename_conversation(request: RenameRequest,
                              session: httpx.AsyncClient = Depends(httpSessionManager.get_client)):
    """会话重命名"""
    name = request.get("name", None)
    user = request.get("user", None)
    conversation_id = request.get("conversation_id", None)
    payload = {
        "name": name,
        "auto_generate": False,
        "user": user
    }
    """会话重命名"""
    result = await session.post(url=f"{BASE_URL}/conversations/{conversation_id}/name", json=payload, headers=HEADER)
    # 调用Dify API更新会话名称
    return result.json()


@router.get("/messages/suggested")
@handle_http_exceptions
async def suggested(user: str, conversation_id: str,
                    session: httpx.AsyncClient = Depends(httpSessionManager.get_client)):
    print("test")
    print(f"url:{f"{BASE_URL}/messages/{conversation_id}/suggested?user={user}"}")
    result = await session.get(url=f"{BASE_URL}/messages/{conversation_id}/suggested?user={user}", headers=HEADER)
    # 调用Dify API更新会话名称
    return result.json()
