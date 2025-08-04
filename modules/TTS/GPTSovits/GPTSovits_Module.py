import asyncio
import time
from typing import Any, Optional

import settings
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
        input = request.body
        context = await self.pipeline.get_context(request_id=request.request_id)
        post_dict = context.request_dict
        if post_dict.get("TTS") is None:
            print("未找到TTS")
            return None
        if post_dict["TTS"].get("enable",True) is False:
            return None
        return input

    async def heartbeat(self):
        """心跳方法"""
        print("GPTSovits_Module心跳")
        reffile = settings.CONFIG["TTS"]["GPTSoVITS"]["reffile"]
        reftext = settings.CONFIG["TTS"]["GPTSoVITS"]["reftext"]
        # TODO:
        #  GPTSoVITS不知为何有长时间不合成后，下一次开启合成就需要额外等待较长时间的情况（1-2秒）
        #  通过触发心跳保持合成小短句（合成时间在0.5秒内），可以通过减少调用频率来保持
        session = await GetGenerator(input_data="一",ref_audio_path = reffile,prompt_text = reftext)  # 触发心跳，保持连接
        async for chunk in session.generate(self.ProcessResponseFunc):
            pass

    async def ChunkWrapper(self, message: ModuleMessage,chunk:bytes):
        """chunk最终输出前的封装方法"""
        await asyncio.sleep(0)
        return chunk

    async def GetGenerator(self, message: ModuleMessage,input_data:str)->Optional[StreamGenerator]:
        if input_data is None:
            return None
        """从router创建的获取StreamGenerator的方法"""
        queueRequestContext = await self.pipeline.get_context(request_id=message.request_id)
        request_dict = queueRequestContext.request_dict
        reffile,reftext = get_voice(request_dict)
        generator = await GetGenerator(input_data, reffile, reftext)
        now_time = time.time()
        #print("LiveTalking_Module消息发送完毕，耗时:" +  str(now_time - message.start_time) + "秒")
        return generator


    def ProcessResponseFunc(self, chunk:bytes):
        """PipeLineMessage的封装方法"""
        return extract_response(chunk)

