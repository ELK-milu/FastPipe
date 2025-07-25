import base64
import json
import os
from typing import AsyncGenerator

import aiofiles

from services import StreamGenerator
from utils.AudioChange import convert_audio_to_wav, convert_wav_to_pcm_simple
from utils.ConfigLoader import read_config


def GetAbsPath_File():
    """使用__file__获取路径 - 总是返回被调用函数所在文件的路径"""
    return os.path.dirname(os.path.abspath(__file__))

Module_Config = read_config(GetAbsPath_File() + "/Config.yaml")

def get_payload(text:str,ref_audio_path:str="./GPT_SoVITS/models/佼佼仔_中立.wav",prompt_text:str="今天，我将带领大家穿越时空，去到未来的杭州。"):
    payload = {
        "text": text,
        "text_lang": "zh",
        "ref_audio_path": ref_audio_path,
        "aux_ref_audio_paths": [],
        "prompt_text": prompt_text,
        "prompt_lang": "zh",
        "top_k": 5,
        "top_p": 1,
        "temperature": 1,
        "text_split_method": "cut6",
        "return_fragment": False,  # 确保分段返回片段
        "batch_size": 8,  # 增加batch_size以加速处理
        "batch_threshold": 0.75,
        "split_bucket": False,
        "speed_factor": 1.0,
        "streaming_mode": False,
        "seed": -1,
        "parallel_infer": True,  # 并行推理开启
        "repetition_penalty": 1.35,
        "sample_steps": 16
    }
    return payload


def get_voice(dict):
    reffile = Module_Config[dict["TTS"]["voice"]][dict["TTS"]["emotion"]]["reffile"]
    reftext = Module_Config[dict["TTS"]["voice"]][dict["TTS"]["emotion"]]["reftext"]
    return reffile,reftext


class GPTSovitsStreamGenerator(StreamGenerator):
    async def generate(self, process_func: callable = None):
        """生成流数据，但一次性返回完整的 bytes"""
        try:
            async with self.client.stream(
                    self.method,
                    self.url,
                    json=self.payload,
                    timeout=300.0,
                    headers=self.header
            ) as response:
                # 收集所有 chunks
                chunks = []
                async for chunk in response.aiter_bytes(chunk_size=None):
                    if chunk:
                        if process_func:
                            chunk = process_func(chunk)
                        chunks.append(chunk)
                # 合并所有 chunks 并一次性返回
                full_data = b''.join(chunks)
                yield full_data
        except Exception as e:
            raise e
        finally:
            pass


class GPTSovitsFullGenerator(StreamGenerator):
    async def generate(self, process_func: callable = None):
        """一次性获取完整音频数据"""
        try:
            response = await self.client.request(
                self.method,
                self.url,
                json=self.payload,
                timeout=300.0,
                headers=self.header
            )

            full_data = response.content
            if process_func:
                full_data = process_func(full_data)

            yield full_data

        except Exception as e:
            raise e

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
            wav_audio = convert_wav_to_pcm_simple(audio_data, set_sample_rate=24000)
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


def extract_response(intput_data:bytes):
    return intput_data