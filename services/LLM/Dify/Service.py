import json
import time

import httpx
from services import StreamGenerator
from loguru import logger

def SetSessionConfig(key:str,session: httpx.AsyncClient)->httpx.AsyncClient:
    session.headers.update({
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'Connection': 'Keep-Alive'
    })
    return session

def get_payload(text:str):
    payload = {
        "inputs": {},
        "query": text,
        "response_mode": "streaming",
        "conversation_id": "",
        "user": "user",
        "files": []
    }
    return payload


def extract_response(response):
    decoded_response = response.decode('utf-8')
    message = ""
    prefix = 'data: {"event": "message"'
    if not decoded_response.strip().startswith(prefix):
        return message
    data = decoded_response[6:]
    json_data = json.loads(data)
    #print(json_data)
    if json_data['event'] == 'message':
        message = str(json_data['answer'])
    return message


def extract_complete_response(response):
    decoded_response = response.decode('utf-8')
    prefix = 'data: {"event": "message'
    agent_mcp_prefix = 'data: {"event": "agent_log"'
    if decoded_response.strip().startswith(prefix):
        data = decoded_response[6:]
        # print(data)
        json_data = json.loads(data)
        if json_data['event'] == 'message' or json_data['event'] == 'message_end':
            return json_data
    elif decoded_response.strip().startswith(agent_mcp_prefix):
        data = decoded_response[6:]
        json_data = json.loads(data)
        if json_data['data']['status'] == 'success':
            #final_json = json_data['data']['data']['output']['tool_response']['tool_response']
            # 直接返回全部信息
            return json_data
    else:
        return ""


class DifyStreamGenerator(StreamGenerator):
    def __init__(self, client: httpx.AsyncClient, payload,header,method,url):
        super().__init__(client, payload,header,method,url)
        self._buffer = b''  # 用于缓存不完整的数据

    async def check_sse(self,chunk) -> [bool,str]:
        # 符合 SSE 格式的前缀代表收到新信息，输出老信息
        prefix = b'data: {"event"'
        if chunk.startswith(prefix):
            #print(f"check_sse:{chunk}")
            output_data = self._buffer
            self._buffer = chunk
            return True,output_data
        else:
            data = chunk[6:]
            self._buffer += data
            return False,None

    async def generate(self,process_func:callable = None):
        """生成流数据"""
        try:
            #yield "今天是星期三。"
            async with self.client.stream(
                    self.method,
                    self.url,
                    json=self.payload,
                    timeout=300.0,
                    headers=self.header
            ) as response:
                #yield "你好。"
                start_time = time.time()
                # logger.info(f"{start_time}开始发送请求")
                async for chunk in response.aiter_bytes():
                    # 只在接受完完整的sse格式数据后才处理
                    if chunk:
                        #print(f"Received chunk: {chunk}")
                        flag,final_chunk = await self.check_sse(chunk)
                        if flag and final_chunk:
                            if process_func:
                                final_chunk = process_func(final_chunk)
                            else:
                                final_chunk = json.loads(final_chunk.decode('utf-8')[6:])
                            # 返回json格式的数据bytes解码为字符串的数据
                            yield final_chunk
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            raise
        finally:
            final_time = time.time()
