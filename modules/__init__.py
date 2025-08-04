import asyncio
import inspect
import os
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING, Optional, Callable, Dict
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
    start_time: float = time()

class ModuleChunkProtocol():
    user: str
    request_id: str


class BaseModule(ABC):
    def __init__(self):
        self.pipeline :Optional["PipeLine"] = None
        self.nextModel : BaseModule = None
        self.ENDSIGN = None
        self.logger = logger
        # 根据请求存储的ModuleChunk，并非必需使用，若自定义模块时有需要借助其他类作为数据存储用，则需要在此定义
        self.request_chunks : Dict[str,ModuleChunkProtocol] ={}

    class ModuleChunk(ModuleChunkProtocol):
        def __init__(self, user:str, request_id: str):
            self.user = user
            self.request_id = request_id

    # 模块调用的起始点
    async def ModuleEntry(self, request:ModuleMessage):
        #await asyncio.create_task(self.main_loop(request))
        await self.main_loop(request)

    async def heartbeat(self):
        pass

    async def main_loop(self, message: ModuleMessage) -> Any:
        """模块的主要处理逻辑，子类必须实现"""
        # 在定义这个方法的时候需要指定input_data和函数输出的类型，用于pipeline检验当前模块所需的输入输出类型
        try:
            input_data = await self.handle_request(message)
            session = await self.GetGenerator(message,input_data)
            if not session:
                return None
            async for chunk in session.generate(self.ProcessResponseFunc):
                if chunk:
                    final_chunk = await self.ChunkWrapper(message,chunk)
                else:
                    final_chunk = None
                if final_chunk:
                    await self.module_output(final_chunk, message)
        except Exception as e:
            raise e
        finally:
            await self.finally_func(message)

    async def module_output(self, final_chunk:Any, message: ModuleMessage):
        next_model_message, pipeline_message = await self.MessageWrapper(final_chunk, message)
        if self.pipeline:
            await self.PutToPipe(pipeline_message)
        if self.nextModel:
            # task2 = asyncio.create_task(self.nextModel.ModuleEntry(next_model_message))
            await self.nextModel.ModuleEntry(next_model_message)

    @abstractmethod
    async def type_show(self, input_data: Any)->Any:
        """重写这个代码，不用任何内容，通过指定Any的输入输出来告诉pipeline该模块接受的输入输出类型"""
        pass

    async def finally_func(self,message: ModuleMessage):
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


    async def ChunkWrapper(self, message: ModuleMessage,chunk:Any):
        """chunk最终输出前的封装方法"""
        await asyncio.sleep(0)
        return chunk

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

    async def clear(self,request_id:str):
        if request_id in self.request_chunks:
            del self.request_chunks[request_id]
