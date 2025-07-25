import time
from typing import Any, Optional

from modules import BaseModule, ModuleMessage
from modules.TTS import TTSModule
from routers.GPTSovits import GetStreamGenerator, GetGenerator
from services import StreamGenerator
from services.TTS.GPTSovits.Service import get_voice, extract_response


class GPTSovits_Module(TTSModule):
    async def type_show(self, input_data: str)->bytes:
        """重写这个代码，不用任何内容，通过指定Any的输入输出来告诉pipeline该模块接受的输入输出类型"""
        pass

    async def handle_request(self, request:ModuleMessage):
        """对模块输入请求进行内容提取的方法"""
        return request.body

    def ChunkWrapper(self, message: ModuleMessage,chunk:bytes):
        """chunk最终输出前的封装方法"""
        return chunk

    async def GetGenerator(self, message: ModuleMessage,input_data:str)->Optional[StreamGenerator]:
        if input_data is None:
            return None
        """从router创建的获取StreamGenerator的方法"""
        queueRequestContext = await self.pipeline.get_context(request_id=message.request_id)
        request_dict = queueRequestContext.request_dict
        voice,emotion = get_voice(request_dict)
        generator = await GetGenerator(input_data=input_data)
        now_time = time.time()
        #print("LiveTalking_Module消息发送完毕，耗时:" +  str(now_time - message.start_time) + "秒")
        return generator


    def ProcessResponseFunc(self, chunk:bytes):
        """PipeLineMessage的封装方法"""
        return extract_response(chunk)

