import asyncio
import json
import re
from typing import Optional

import loguru

from modules import BaseModule, ModuleMessage, ModuleChunkProtocol
from modules.LLM import LLMModule
from routers.Dify import GetGenerator
from services import StreamGenerator
from services.LLM.Dify.Service import extract_response, extract_complete_response
from utils.AsyncQueue import AsyncQueueMessage


class Dify_LLM_Module(LLMModule):
    class ModuleChunk(ModuleChunkProtocol):
        def __init__(self, user: str, request_id: str):
            self.user = user
            self.request_id = request_id
            self.tempResponse: str = ""
            self.WaitCount = 1
            self.sentences = []
            self.response = ""
            self.conversation_id = None
            self.message_id = None
            self.Is_End: bool = False

        def GetTempMsg(self):
            # 使用正向预查分割保留标点符号
            split_pattern = "，,!?。！？"
            # 作为预选的标点符号，需要满足特定条件才会切分
            binal_split_pattern = "、：:"
            final_split_pattern = fr'(?<=[{split_pattern}{binal_split_pattern}])'
            fragments = re.split(final_split_pattern, self.tempResponse)

            # 收集完整句子和未完成部分
            complete_sentences = []
            pending_fragment = ''
            for frag in fragments:
                if len(complete_sentences) >= self.WaitCount:
                    self.sentences = fragments
                    # self.tempResponse等于将未选用的部分句子拼接起来
                    self.tempResponse = ""
                    return self.sentences
                if re.search(rf'[{split_pattern}]$', frag):
                    complete_sentences.append(frag)
                elif re.search(rf'[{binal_split_pattern}]$', frag):
                    if len(frag) >= 10:
                        complete_sentences.append(frag)
                    else:
                        pending_fragment += frag
                else:
                    pending_fragment += frag
                    break

            # 如果没有完整句子，继续累积
            self.tempResponse = self.tempResponse
            self.sentences = []
            return self.sentences
        def ReadyToResponse(self) -> bool:
            if (self.GetTempMsg() == []):
                return False
            else:
                return True

        def get_chunks(self):
            final_text = ""
            for sentence in self.sentences:
                final_text += sentence
                self.response += sentence
            return final_text

        def GetThinking(self):
            return ""

        def GetResponse(self):
            return self.response

        def GetFinalContent(self):
            # 服务端替客户端处理成Json再返回
            self.final_json = json.dumps({
                "think": self.GetThinking(),
                "response": self.GetResponse(),
                "conversation_id": self.conversation_id,
                "message_id": self.message_id,
                "Is_End": self.Is_End
            }, ensure_ascii=False)
            return self.final_json

        def SetEnd(self, flag: bool):
            self.Is_End = flag

    async def type_show(self, input_data: str) -> str:
        """重写这个代码，不用任何内容，通过指定Any的输入输出来告诉pipeline该模块接受的输入输出类型"""
        pass

    async def handle_request(self, request: ModuleMessage):
        """对模块输入请求进行内容提取的方法"""
        input = request.body
        context = await self.pipeline.get_context(request_id=request.request_id)
        post_dict = context.request_dict
        if post_dict.get("LLM") is None:
            print("未找到TTS")
            return None
        if post_dict["LLM"].get("enable",True) is False:
            return None
        return input

    async def GetGenerator(self, message: ModuleMessage, input_data: str) -> Optional[StreamGenerator]:
        if input_data is None:
            return None
        """从router创建的获取StreamGenerator的方法"""
        generator = await GetGenerator(input_data)
        return generator

    async def ChunkWrapper(self, message: ModuleMessage, chunk: str) -> str:
        """chunk最终输出前的封装方法"""
        if self.request_chunks.get(message.request_id) is None:
            self.request_chunks[message.request_id] = self.ModuleChunk(message.user, message.request_id)

        temp_chunk = self.request_chunks[message.request_id]

        answer = ""
        if chunk['event'] == 'message':
            answer = str(chunk['answer'])
        elif chunk['event'] == 'message_end':
            # 此处信息在丢入MessageWrapper后会被返回给pipeline，但不会返回给下一个模块
            temp_chunk.SetEnd(True)
            # 把未输出的部分全部输出
            temp_chunk.response += temp_chunk.tempResponse
            return temp_chunk.tempResponse
        elif chunk['event'] == 'agent_log':
            # 对于mcp调用结果直接返回给pipeline
            queue_message = AsyncQueueMessage(type="tool",
                                              body=chunk,
                                              user=message.user,
                                              request_id=message.request_id)
            await self.pipeline.put_message(queue_message)
            return ""

        if not temp_chunk.conversation_id:
            temp_chunk.conversation_id = chunk["conversation_id"]

        if not temp_chunk.message_id:
            temp_chunk.message_id = chunk["message_id"]

        temp_chunk.tempResponse += answer

        # 按句输出
        if temp_chunk.ReadyToResponse():
            return temp_chunk.get_chunks()
        return ""

    async def finally_func(self,message: ModuleMessage):
        await asyncio.sleep(0)
        #temp_chunk = self.request_chunks[message.request_id]
        #finalcontent =  temp_chunk.GetFinalContent()
        #await self.module_output(finalcontent, message)

    async def MessageWrapper(self, input_data: str, message: ModuleMessage) -> tuple[ModuleMessage, AsyncQueueMessage]:
        # 封装Message的函数
        # 不要把作为结束的标识丢给下一个模块了
        if "conversation_id" in input_data:
            next_model_message = await self.NextModuleMessageWrapper(None, message)
        else:
            next_model_message = await self.NextModuleMessageWrapper(input_data, message)
        pipeline_message = await self.PipeLineMessageWrapper(input_data, message)
        return next_model_message, pipeline_message

    async def PutToPipe(self, input_data: AsyncQueueMessage):
        """将数据写入PipeLine的队列中"""
        temp_text = input_data.body
        request_chunk = self.request_chunks[input_data.request_id]
        final_json = request_chunk.GetFinalContent()
        input_data.body = final_json
        await self.pipeline.put_message(input_data)

    def ProcessResponseFunc(self, chunk: str):
        """PipeLineMessage的封装方法"""
        DifyText = extract_complete_response(chunk)
        return DifyText

    def extract_think_response(self, response):
        """
        处理流式和非流式响应，提取思考内容和最终响应
        """
        print("response:" + str(response))
        return response

    async def NextModuleMessageWrapper(self, input_data:str,message:ModuleMessage)->ModuleMessage:
        """ModuleMessage的封装方法"""
        message.type = "str"
        message.body = input_data
        loguru.logger.info(f"[Dify_LLM_Module] output: {message.body}")
        return message