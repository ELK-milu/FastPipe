import asyncio
import uuid
from typing import List, Type, Dict, Optional, Callable
from aio_pika.abc import AbstractQueue
from modules import BaseModule, ModuleMessage
from schemas.request import PipeLineRequest
from utils.AsyncQueue import AsyncMessageQueue,AsyncQueueMessage,AsyncMessageQueueManager,QueueRequestContext



class PipeLine:
    def __init__(self, modules: List[Type[BaseModule]]):
        # 初始化模块实例
        self.modules = [m() for m in modules]
        self.config: Dict = None

        self.validated: bool = False
        self.consumer_task = None
        self.queue_manager = AsyncMessageQueueManager()
        self.StartUp()

    def StartUp(self):
        print(self.Validate())
        module_index = 0
        for module in self.modules:
            module.pipeline = self
            module.nextModel = self.modules[module_index + 1] if module_index < len(self.modules) - 1 else None
            module_index+=1
        pass

    def Validate(self) -> str:
        """验证Pipeline配置"""
        status = []
        try:
            self._validate_pipeline()
            status.append("✅ Pipeline验证通过")
            self.validated = True
        except Exception as e:
            status.append(f"❌ 验证失败: {str(e)}")
            self.validated = False

        pipe_structure = " -> ".join(
            [f"{type(inst).__name__}" for inst in self.modules]
        )
        status.append(f"当前Pipeline: {pipe_structure}")

        type_details = []
        for inst in self.modules:
            sig = inst.type_show.__annotations__
            type_details.append(
                f"{type(inst).__name__} "
                f"(输入: {sig['input_data']}, 输出: {sig['return']})"
            )
        status.append("类型详情:\n" + "\n".join(type_details))
        status.append("#################################################")
        return "\n".join(status)

    def _validate_pipeline(self) -> None:
        """验证Pipeline的类型兼容性"""
        if not self.modules:
            raise ValueError("Pipeline不能为空")

        for i in range(len(self.modules) - 1):
            curr = self.modules[i]
            next_mod = self.modules[i + 1]
            curr_output = curr.type_show.__annotations__['return']
            next_input = next_mod.type_show.__annotations__['input_data']

            if curr_output != next_input:
                raise TypeError(
                    f"类型不匹配: {type(curr).__name__} 输出 {curr_output} "
                    f"但 {type(next_mod).__name__} 期望 {next_input}"
                )

    async def put_message(self, Message:AsyncQueueMessage):
        # 此处不复用get_or_create_queue_context函数，因为put需要频繁调用，不需要每次都创建QueueRequestContext
        queue = await self.queue_manager.get_queue_by_request_id(Message.request_id)
        if queue:
            print("向队列" + Message.request_id + "添加信息:" + Message.body)
            await queue.put(Message)
        else:
            # 原则上来说不应该在这里创建队列，没有队列应当报错
            raise Exception("队列不存在")
            '''
            print("创建队列：" + Message.request_id)
            create_queue_request = QueueRequestContext(
                request_id=Message.request_id,
                user_id=Message.user,
                context={}
            )
            queue = await self.queue_manager.create_queue_by_context(create_queue_request)
            await queue.put(Message)
            '''

    async def get_queue(self, request_id: str) -> Optional[AsyncMessageQueue]:
        return await self.queue_manager.get_queue_by_request_id(request_id)
    async def get_context(self, request_id: str) -> QueueRequestContext:
        return self.queue_manager._contexts[request_id]

    async def get_or_create_queue_by_context(self, context: QueueRequestContext) -> Optional[AsyncMessageQueue]:
        queue =  await self.queue_manager.get_queue_by_request_id(context.request_id)
        if queue:
            pass
        else:
            print("创建队列：" + context.request_id)
            queue = await self.queue_manager.create_queue_by_context(context)
        return queue


    async def default_message_handler(self, message_body: str):
        """默认消息处理器"""
        print(f"接收到消息: {message_body}")


    @classmethod
    def create_pipeline(cls, *modules: Type[BaseModule]) -> 'PipeLine':
        """创建新的Pipeline实例"""
        return cls(list(modules))

    async def process_request(self,text:str,user:str,request_id: str,type:str="str",entry:int = 0):
        """处理特定请求"""
        try:
            test_message = ModuleMessage(
                type=type,
                body=text,
                user=user,
                request_id=request_id
            )
            await self.modules[entry].ModuleEntry(test_message)
        except Exception as e:
            error_message = AsyncQueueMessage(
                type="error",
                body=f"处理出错: {str(e)}",
                user=user,
                request_id=request_id
            )
            await self.put_message(error_message)
        finally:
            # 发送结束信号
            end_message = AsyncQueueMessage(
                type="end",
                body="[DONE]",
                user=user,
                request_id=request_id
            )
            end_message.is_end = True
            await self.put_message(end_message)
