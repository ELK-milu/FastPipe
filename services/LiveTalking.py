from services import StreamGenerator


def extract_response(response):
    return None

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