import asyncio
import websockets

request_data = {
    "text": "测试测试测试",
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

def GetPayLoad(message: str):
    request_data["text"] = message
    return request_data

async def tts_client():
    # 替换为你的WebSocket服务器地址
    uri = "ws://192.168.30.46:9880/ws/tts"

    try:
        async with websockets.connect(uri) as websocket:
            print("已连接到TTS服务器，输入文字开始对话（输入'quit'退出）")

            while True:
                # 从控制台获取用户输入
                message = input("请输入文字: ")

                if message.lower() == 'quit':
                    print("退出程序")
                    break

                # 发送消息到服务器
                await websocket.send(str(GetPayLoad(message)))
                print(f"已发送: {message}")

                # 接收服务器响应
                response = await websocket.recv()
                print(f"收到响应: {response}")

    except websockets.exceptions.ConnectionClosed:
        print("连接已关闭")
    except Exception as e:
        print(f"连接错误: {e}")


if __name__ == "__main__":
    asyncio.run(tts_client())
