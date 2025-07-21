from schemas.request import RequestModel

class InputRequest(RequestModel):
    streamly: bool
    user: str
    input_data: str

class DeleteRequest(RequestModel):
    user:str
    conversation_id:str

class RenameRequest(RequestModel):
    name:str
    user:str
    conversation_id:str
