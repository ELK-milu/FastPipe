import asyncio
import json

import websockets


class WebSocketClient:
    def __init__(self, uri):
        self.uri = uri
        self.websocket = None
        self.connected = False

    async def connect(self):
        """建立WebSocket连接"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            print(f"Connected to {self.uri}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            print("Disconnected")


    async def receive_audio(self):
        """接收音频数据"""
        if not self.connected:
            print("Not connected.")
            return None

        audio_data = bytearray()
        try:
            async for message in self.websocket:
                if isinstance(message, str):
                    # 处理文本消息（控制信息）
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "start":
                        print(f"TTS started, media type: {data['data']['media_type']}")
                    elif msg_type == "end":
                        print("TTS completed successfully")
                        break
                    elif msg_type == "error":
                        print(f"Error: {data['data']['message']}")
                        return None
                    else:
                        print(f"Info: {data}")

                elif isinstance(message, bytes):
                    # 处理二进制消息（音频数据）
                    audio_data.extend(message)
                    print(f"Received audio chunk: {len(message)} bytes")

            return bytes(audio_data) if audio_data else None
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed during reception")
            return None
        except Exception as e:
            print(f"Error receiving audio: {e}")
            return None


    async def send_request_json(self, body):
        """发送TTS请求"""
        if not self.connected:
            print("Not connected. Please connect first.")
            return None

        try:
            await self.websocket.send(json.dumps(body))
            return True
        except Exception as e:
            print(f"Failed to send request: {e}")
            return False


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
        "text_split_method": "cut5",
        "media_type": "wav",
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



async def Test(wsClient:WebSocketClient):
    await wsClient.connect()
    await wsClient.send_request_json(get_payload("大家好，我是佼佼仔。"))
    await wsClient.disconnect()


if __name__ == '__main__':
    ws = WebSocketClient('ws://192.168.30.46:9880/ws/tts')
    asyncio.run(Test(ws))
