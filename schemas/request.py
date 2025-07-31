from pydantic import BaseModel, ConfigDict


class RequestModel(BaseModel):
    """API响应模型"""
    pass

class PipeLineRequest(RequestModel):
    model_config = ConfigDict(extra='allow')
    # Required fields
    user: str
    Input: str
    text:str
    Entry: int

    conversation_id: str = ""
    message_id: str = ""

class AwakeModel(RequestModel):
    """Awake请求模型"""
    user: str = None
    voice: str = None