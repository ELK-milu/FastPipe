import re
from typing import Optional

from modules import BaseModule, ModuleMessage, ModuleChunkProtocol
from modules.LLM import LLMModule
from routers.Dify import GetGenerator
from services import StreamGenerator
from services.LLM.Dify.Dify import extract_response


class Dify_LLM_Module(LLMModule):

    class ModuleChunk(ModuleChunkProtocol):
        def __init__(self, user:str, request_id: str):
            self.user = user
            self.request_id = request_id
            self.tempResponse :str = ""
            self.WaitCount = 1
            self.sentences = []

        def GetTempMsg(self):
            # 使用正向预查分割保留标点符号
            split_pattern = r'(?<=[，,!?。！？])'
            fragments = re.split(split_pattern, self.tempResponse)

            # 收集完整句子和未完成部分
            complete_sentences = []
            pending_fragment = ''

            for frag in fragments:
                if re.search(r'[，,!?。！？]$', frag):
                    complete_sentences.append(frag)
                    # 一旦有完整句子就返回，不再等待更多句子
                    if len(complete_sentences) >= self.WaitCount:
                        self.sentences = complete_sentences[:self.WaitCount]
                        self.tempResponse = ''.join(fragments[len(complete_sentences):])
                        return self.sentences
                else:
                    pending_fragment = frag
                    break

            # 如果没有完整句子，继续累积
            self.tempResponse = self.tempResponse
            self.sentences = []
            return self.sentences

        def ReadyToResponse(self) -> bool:
            if(self.GetTempMsg() == []):
                return False
            else:
                return True

        def get_chunks(self):
            final_text = ""
            for sentence in self.sentences:
                final_text += sentence
            return final_text

    async def type_show(self, input_data: str) -> str:
        """重写这个代码，不用任何内容，通过指定Any的输入输出来告诉pipeline该模块接受的输入输出类型"""
        pass

    async def handle_request(self, request: ModuleMessage):
        """对模块输入请求进行内容提取的方法"""
        return request.body

    async def GetGenerator(self, message: ModuleMessage, input_data: str) -> Optional[StreamGenerator]:
        if input_data is None:
            return None
        """从router创建的获取StreamGenerator的方法"""
        generator = await GetGenerator(input_data)
        return generator


    def ChunkWrapper(self, message: ModuleMessage,chunk:str)->str:
        """chunk最终输出前的封装方法"""
        if self.request_chunks.get(message.request_id) is None:
            print("添加modelChunk")
            self.request_chunks[message.request_id] = self.ModuleChunk(message.user, message.request_id)

        temp_chunk = self.request_chunks[message.request_id]

        temp_chunk.tempResponse += chunk
        if temp_chunk.ReadyToResponse():
            return temp_chunk.get_chunks()
        return ""


    def ProcessResponseFunc(self, intput_data: str):
        """PipeLineMessage的封装方法"""
        DifyText = extract_response(intput_data)
        return DifyText

    def extract_think_response(self, response):
        """
        处理流式和非流式响应，提取思考内容和最终响应
        """
        print("response:" + str(response))
        return response
