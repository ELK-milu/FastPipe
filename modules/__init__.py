import inspect
import os
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING, Optional, Callable
from time import time
from attr import dataclass

if TYPE_CHECKING:
    from modules.pipeline.pipeline import PipeLine
from services import StreamGenerator
from utils.AsyncQueue import AsyncQueueMessage
from utils.ConfigLoader import read_config
from loguru import logger


@dataclass
class ModuleMessage():
    type:str
    body:Any
    user:str
    request_id: str


class BaseModule(ABC):
    def __init__(self):
        self.pipeline :Optional["PipeLine"] = None
        self.nextModel : BaseModule = None
        self.ENDSIGN = None
        self.logger = logger
        pass

    # 模块调用的起始点
    async def ModuleEntry(self, request:ModuleMessage):
        await self.main_loop(request)


    async def main_loop(self, message: ModuleMessage) -> Any:
        """模块的主要处理逻辑，子类必须实现"""
        # 在定义这个方法的时候需要指定input_data和函数输出的类型，用于pipeline检验当前模块所需的输入输出类型
        try:
            input_data = await self.handle_request(message)
            print(f"input_data:{input_data}")
            session = await self.GetGenerator(message,input_data)
            if not session:
                return None
            async for chunk in session.generate(self.ProcessResponseFunc):
                if chunk:
                    next_model_message,pipeline_message = await self.MessageWrapper(chunk,message)

                    if self.pipeline:
                        await self.PutToPipe(pipeline_message)
                    if self.nextModel:
                        await self.nextModel.ModuleEntry(next_model_message)
        except Exception as e:
            raise e

    @abstractmethod
    async def type_show(self, input_data: Any)->Any:
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
    def ProcessResponseFunc(self, intput_data:Any):
        """处理响应chunk的方法"""
        return None

    async def PipeLineMessageWrapper(self, input_data:Any,message:ModuleMessage)->AsyncQueueMessage:
        """PipeLineMessage的封装方法"""
        queue_message = AsyncQueueMessage(type=message.type,
                                          body=input_data,
                                          user=message.user,
                                          request_id=message.request_id)
        return queue_message

    async def NextModuleMessageWrapper(self, input_data:Any,message:ModuleMessage)->ModuleMessage:
        """ModuleMessage的封装方法"""
        message.body = input_data
        return message


    async def MessageWrapper(self, input_data:Any,message:ModuleMessage)->tuple[ModuleMessage,AsyncQueueMessage]:
        # 封装Message的函数
        next_model_message = await self.NextModuleMessageWrapper(input_data,message)
        pipeline_message = await self.PipeLineMessageWrapper(input_data,message)
        return next_model_message,pipeline_message


    async def PutToPipe(self, input_data:AsyncQueueMessage):
        """将数据写入PipeLine的队列中"""
        await self.pipeline.put_message(input_data)
