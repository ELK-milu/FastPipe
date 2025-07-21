from pydantic import BaseModel

class RequestModel(BaseModel):
    """API响应模型"""
    pass

class PipeLineRequest(RequestModel):
    # Required fields
    user: str
    Input: str
    Entry: int

    # Optional fields with default values
    #streamly: bool = False
    #temperature: float = 0.7
    #max_length: int = 100
    conversation_id: str = ""
    message_id: str = ""
