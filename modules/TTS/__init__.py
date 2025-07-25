from abc import abstractmethod
from typing import Optional, Any

from modules import BaseModule, ModuleMessage
from services import StreamGenerator
from utils.AsyncQueue import AsyncQueueMessage


class TTSModule(BaseModule):

    @abstractmethod
    async def type_show(self, input_data: str)->bytes:
        """重写这个代码，不用任何内容，通过指定Any的输入输出来告诉pipeline该模块接受的输入输出类型"""
        pass

    @abstractmethod
    async def handle_request(self, request:ModuleMessage):
        """对模块输入请求进行内容提取的方法"""
        return request.body

    @abstractmethod
    async def GetGenerator(self, message: ModuleMessage,input_data:Any)->Optional[StreamGenerator]:
        """从router创建的获取StreamGenerator的方法"""
        """
        generator = GetGenerator(input_data)
        return generator
        """
        pass

    @abstractmethod
    def ProcessResponseFunc(self, chunk:Any)->Any:
        """处理响应chunk的方法"""
        return None


    def ChunkWrapper(self, message: ModuleMessage,chunk:Any):
        """chunk最终输出前的封装方法"""
        return chunk

    async def PipeLineMessageWrapper(self, input_data:Any,message:ModuleMessage)->AsyncQueueMessage:
        """PipeLineMessage的封装方法"""
        queue_message = AsyncQueueMessage(type="audio",
                                          body=input_data,
                                          user=message.user,
                                          request_id=message.request_id)
        return queue_message

    async def NextModuleMessageWrapper(self, input_data:Any,message:ModuleMessage)->ModuleMessage:
        """ModuleMessage的封装方法"""
        message.type = "audio"
        message.body = input_data
        return message