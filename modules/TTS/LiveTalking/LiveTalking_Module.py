from typing import Any, Optional

from modules import BaseModule, ModuleMessage
from routers.LiveTalking import GetGenerator
from services import StreamGenerator
from services.TTS.LiveTalking.LiveTalking import extract_response, get_voice


class LiveTalking_Module(BaseModule):
    async def type_show(self, input_data: str)->str:
        """重写这个代码，不用任何内容，通过指定Any的输入输出来告诉pipeline该模块接受的输入输出类型"""
        pass

    async def handle_request(self, request:ModuleMessage):
        print("LiveTalking收到消息:" + request.body)
        """对模块输入请求进行内容提取的方法"""
        return request.body


    async def GetGenerator(self, message: ModuleMessage,input_data:str)->Optional[StreamGenerator]:
        if input_data is None:
            return None
        """从router创建的获取StreamGenerator的方法"""
        queueRequestContext = await self.pipeline.get_context(request_id=message.request_id)
        request_dict = queueRequestContext.request_dict
        voice,emotion = get_voice(request_dict)
        generator = await GetGenerator(text=input_data,
                                       sessionid=request_dict.get("TTS").get("sessionid",0),
                                       voice= voice,
                                       emotion= emotion,)
        return generator

    def ProcessResponseFunc(self, intput_data:str):
        """PipeLineMessage的封装方法"""
        return extract_response(intput_data)

