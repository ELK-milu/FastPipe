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
    if json_data['event'] == 'message':
        message = str(json_data['answer'])
    return message



class DifyStreamGenerator(StreamGenerator):
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
                    if chunk:
                        if process_func:
                            chunk = process_func(chunk)
                        yield chunk
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            raise
        finally:
            final_time = time.time()
