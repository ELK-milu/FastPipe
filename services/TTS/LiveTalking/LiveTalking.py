import base64
import json
import os
from typing import AsyncGenerator

import aiofiles
import httpx
from services import StreamGenerator
from utils.AudioChange import convert_audio_to_wav
from utils.ConfigLoader import read_config


def GetAbsPath_File():
    """使用__file__获取路径 - 总是返回被调用函数所在文件的路径"""
    return os.path.dirname(os.path.abspath(__file__))

Module_Config = read_config(GetAbsPath_File() + "/Config.yaml")


async def generate_stream(user, voice) -> AsyncGenerator[str, None]:
    awakeText = Module_Config[voice]["awake_text"]

    # 第一条文本数据
    # 服务端替客户端处理成Json再返回
    final_json = json.dumps({
        "think": "",
        "response": awakeText,
        "conversation_id": "",
        "message_id": "",
        "Is_End": True
    })
    yield json.dumps({
        "type": "text",
        "chunk": final_json
    }) + "\n"

    # 第二条音频数据
    awakeAudioPath = GetAbsPath_File() + Module_Config[voice]["awake_audio"]
    print(awakeAudioPath)

    try:
        # 使用 aiofiles 进行异步文件读取
        async with aiofiles.open(awakeAudioPath, 'rb') as f:
            audio_data = await f.read()
            wav_audio = convert_audio_to_wav(audio_data, set_sample_rate=24000)
            yield json.dumps({
                "type": "audio/wav",
                "chunk": base64.b64encode(wav_audio).decode("utf-8")
            }) + "\n"
    except FileNotFoundError:
        yield json.dumps({
            "type": "error",
            "chunk": f"音频文件未找到: {awakeAudioPath}"
        }) + "\n"
    except Exception as e:
        yield json.dumps({
            "type": "error",
            "chunk": f"文件加载失败: {str(e)}"
        }) + "\n"



def get_config():
    return {
        "method": "POST",
        "url": "",
        "header": {
            "Authorization": "",
            "Content-Type": "application/json"
        }
    }

def SetSessionConfig(key:str,session: httpx.AsyncClient)->httpx.AsyncClient:
    session.headers.update({
        'Authorization': "",
        'Content-Type': 'application/json',
        'Connection': 'Keep-Alive'
    })
    return session

def get_payload(text:str,sessionid:int,voice:str,emotion:str,interrupt:bool=False,type:str="echo"):
    payload = {
        "text": text,
        "type": type,
        "interrupt": interrupt,
        "sessionid": sessionid,
        "voice": voice,
        "emotion": emotion
    }
    return payload

def extract_response(response):
    return ""

class LiveTalkingStreamGenerator(StreamGenerator):
    async def generate(self,process_func:callable = None):
        """生成流数据"""
        try:
            async with self.client.stream(
                    self.method,
                    self.url,
                    json=self.payload,
                    timeout=300.0,
                    headers=self.header
            ) as response:
                async for chunk in response.aiter_bytes():
                    if chunk:
                        if process_func:
                            chunk = process_func(chunk)
                        yield chunk
        except Exception as e:
            raise e
        finally:
            pass