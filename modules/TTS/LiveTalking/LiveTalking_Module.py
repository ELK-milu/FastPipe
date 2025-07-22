from modules import BaseModule, ModuleMessage
from services import StreamGenerator
from services.LiveTalking import extract_response


class LiveTalking_Module(BaseModule):
    async def type_show(self, input_data: str)->str:
        """重写这个代码，不用任何内容，通过指定Any的输入输出来告诉pipeline该模块接受的输入输出类型"""
        pass
    async def handle_request(self, request:ModuleMessage):
        """对模块输入请求进行内容提取的方法"""
        return request.body

    async def GetGenerator(self,input_data: str)->StreamGenerator:
        """从router创建的获取StreamGenerator的方法"""
        generator = await GetGenerator(input_data)
        return generator

    def ProcessResponseFunc(self, intput_data:str):
        """PipeLineMessage的封装方法"""
        return extract_response(intput_data)

    def extract_think_response(self, response):
        """
        处理流式和非流式响应，提取思考内容和最终响应
        """
        print("response:" + str(response))
        return response

