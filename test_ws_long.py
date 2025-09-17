import asyncio
import websockets
import json
import argparse
import wave
import sys
from pathlib import Path
import time


class TTSWebSocketClient:
    def __init__(self, uri="ws://192.168.30.46:9880/ws/tts"):
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

    async def send_tts_request(self, text, **kwargs):
        """发送TTS请求"""
        if not self.connected:
            print("Not connected. Please connect first.")
            return None

        # 默认参数
        request_data = {
            "text": text,
            "text_lang": "zh",
            "ref_audio_path": "./GPT_SoVITS/models/佼佼仔_中立.wav",
            "aux_ref_audio_paths": [],
            "prompt_text": "今天，我将带领大家穿越时空，去到未来的杭州。",
            "prompt_lang": "zh",
            "top_k": 5,
            "top_p": 1,
            "temperature": 1,
            "text_split_method": "cut5",
            "media_type": "wav",
            "return_fragment": False,
            "batch_size": 8,
            "batch_threshold": 0.75,
            "split_bucket": False,
            "speed_factor": 1.0,
            "streaming_mode": False,
            "seed": -1,
            "parallel_infer": True,
            "repetition_penalty": 1.35,
            "sample_steps": 16
        }

        # 更新用户提供的参数
        request_data.update(kwargs)

        try:
            await self.websocket.send(json.dumps(request_data))
            print(f"TTS request sent: {text[:50]}...")
            return True
        except Exception as e:
            print(f"Failed to send request: {e}")
            return False

    async def receive_audio(self, save_path=None):
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

                else:
                    # 处理二进制消息（音频数据）
                    audio_data.extend(message)
                    print(f"Received audio chunk: {len(message)} bytes")

            # 保存音频文件
            if audio_data and save_path:
                output_path = Path(save_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, 'wb') as f:
                    f.write(audio_data)

                print(f"Audio saved to: {output_path}")
                print(f"File size: {len(audio_data)} bytes")

            return bytes(audio_data) if audio_data else None

        except websockets.exceptions.ConnectionClosed:
            print("Connection closed during reception")
            return None
        except Exception as e:
            print(f"Error receiving audio: {e}")
            return None

    async def tts_and_save(self, text, save_path, **kwargs):
        """完整的TTS流程：发送请求并接收音频"""
        success = await self.send_tts_request(text, **kwargs)
        if success:
            return await self.receive_audio(save_path)
        return None

async def batch_tts_process(texts,client, output_dir="./output"):
    """批量处理TTS"""

    if not await client.connect():
        return

    try:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for i, text in enumerate(texts):
            filename = output_path / f"tts_output_{i + 1:03d}.wav"
            print(f"\n处理第 {i + 1}/{len(texts)} 条: {text[:30]}...")

            start_time = time.time()
            audio_data = await client.tts_and_save(text, str(filename))
            end_time = time.time()

            if audio_data:
                print(f"完成，耗时: {end_time - start_time:.2f}秒")
            else:
                print("失败")

            # 可选：添加延迟避免服务器过载
            await asyncio.sleep(0.5)

    finally:
        await client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TTS WebSocket Client")
    parser.add_argument("--mode", choices=["interactive", "batch"], default="batch",
                        help="运行模式: interactive(交互式) 或 batch(批量处理)")
    parser.add_argument("--text", help="单条文本（用于测试）")
    parser.add_argument("--output", default="./test.wav", help="输出文件路径")

    args = parser.parse_args()

    client = TTSWebSocketClient()
    if args.mode == "batch":
        # 示例批量文本
        sample_texts = [
            "这是第一条测试文本",
            "这是第二条测试文本，稍长一些",
            "第三条测试文本，用于验证批量处理功能"
        ]
        asyncio.run(batch_tts_process(sample_texts,client))


        '''
        async def single_test():
            await client.connect()
            await client.tts_and_save(args.text, args.output)
            await client.disconnect()


        asyncio.run(single_test())
        '''
