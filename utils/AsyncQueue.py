import asyncio
import time
from dataclasses import dataclass
from typing import Any, Optional, Callable, AsyncGenerator, Dict
from contextlib import asynccontextmanager



@dataclass
class AsyncQueueMessage:
    type:str
    body :Any
    request_id: str
    user :str


class AsyncQueueIterator:
    """异步队列迭代器"""

    def __init__(self, queue: 'AsyncMessageQueue'):
        self.queue = queue
        self._closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._closed:
            raise StopAsyncIteration

        try:
            # 从队列获取消息，设置超时避免无限等待
            message = await asyncio.wait_for(
                self.queue._get_message(),
                timeout=self.queue.timeout
            )

            if message is None:  # 队列已关闭
                raise StopAsyncIteration

            return message

        except asyncio.TimeoutError:
            # 超时后立即重试，而不是递归调用
            if not self._closed and not self.queue._closed:
                return await self.__anext__()
            raise StopAsyncIteration

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._closed = True


class AsyncMessageQueue:
    """异步消息队列"""

    def __init__(self, name: str = "test_queue", timeout: float = 10):
        self.name = name
        self.timeout = timeout
        self._queue = asyncio.Queue()
        self._closed = False
        self._last_put_time = time.time()
        self._iterators = set()
        self._message_ready= asyncio.Event()

    async def put(self, message: AsyncQueueMessage):
        """优化的消息放入方法"""
        if self._closed:
            raise RuntimeError("队列已关闭")
        if self.name != message.request_id:
            raise RuntimeError("队列名称不匹配")

        # 立即放入消息，无需等待
        self._queue.put_nowait(message)
        self._message_ready.set()  # 立即通知有新消息
        self._last_put_time = time.time()

    async def _get_message(self) -> Optional[AsyncQueueMessage]:
        """内部方法：从队列获取消息"""
        if self._closed and self._queue.empty():
            return None
        try:
            message = await self._queue.get()
            return message
        except Exception:
            return None
        #return await self._get_message_optimized()

    async def _get_message_optimized(self) -> Optional[AsyncQueueMessage]:
        """优化的消息获取方法"""
        if self._closed and self._queue.empty():
            return None

        try:
            # 先尝试立即获取，避免不必要的等待
            if not self._queue.empty():
                message = self._queue.get_nowait()
                return message

            # 如果队列为空，等待消息就绪事件
            try:
                await asyncio.wait_for(self._message_ready.wait(), timeout=self.timeout)
                self._message_ready.clear()  # 清除事件状态

                if not self._queue.empty():
                    message = self._queue.get_nowait()
                    return message
            except asyncio.TimeoutError:
                pass

            return None

        except asyncio.QueueEmpty:
            return None
        except Exception as e:
            print(f"获取消息时出错: {e}")
            return None

    def iterator(self) -> AsyncQueueIterator:
        """获取异步迭代器"""
        iterator = AsyncQueueIterator(self)
        self._iterators.add(iterator)
        return iterator

    async def close(self):
        """关闭队列"""
        self._closed = True
        self._message_ready.set()  # 通知所有等待者

        # 关闭所有迭代器
        for iterator in self._iterators:
            iterator._closed = True

        # 向队列发送None作为结束信号
        try:
            await self._queue.put(None)
        except:
            pass

    @property
    def qsize(self):
        """队列大小"""
        return self._queue.qsize()

    @property
    def empty(self):
        """队列是否为空"""
        return self._queue.empty()


@dataclass
class QueueRequestContext:
    """请求上下文信息"""
    request_id: str
    user_id: str
    request_dict:dict
    created_at: float = time.time()
    timeout: float = 30.0  # 默认30秒超时
    priority: int = 0  # 优先级，数字越大优先级越高

class AsyncMessageQueueManager():

    def __init__(self, cleanup_interval: float = 60.0, max_queue_disactive_age: float = 60.0):
        # 根据request存储请求体和响应队列
        self._queues: Dict[str, AsyncMessageQueue] = {}
        # 根据request_id查询根据QueueRequestContext
        # 根据QueueRequestContext.request_id查询异步队列
        self._contexts: Dict[str, QueueRequestContext] = {}
        self._cleanup_interval = cleanup_interval
        self._max_queue_disactive_age = max_queue_disactive_age
        self._cleanup_task = None
        self._lock = asyncio.Lock()

    async def start(self):
        """启动管理器"""
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_queues())

    async def create_queue_by_context(self, context: QueueRequestContext) -> AsyncMessageQueue:
        """为请求创建专用队列"""
        async with self._lock:
            if context.request_id in self._queues:
                return self._queues[context.request_id]

            queue = AsyncMessageQueue(
                name=context.request_id,
                timeout=context.timeout
            )

            self._queues[context.request_id] = queue
            self._contexts[context.request_id] = context

            print(f"为请求 {context.request_id} 创建队列")
            return queue

    async def get_queue_by_request_id(self, request_id: str) -> Optional[AsyncMessageQueue]:
        """获取指定请求的队列"""
        if self._queues.get(request_id,None):
            return self._queues[request_id]
        else:
            return None

    async def remove_queue(self, request_id: str):
        """移除指定请求的队列"""
        async with self._lock:
            if request_id in self._queues:
                queue = self._queues.pop(request_id)
                self._contexts.pop(request_id, None)
                await queue.close()
                print(f"移除请求 {request_id} 的队列")

    async def _cleanup_expired_queues(self):
        """定期清理过期队列"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                current_time = time.time()
                expired_requests = []

                for request_id, context in self._contexts.items():
                    queue = self._queues.get(request_id, None)
                    if not queue:
                        continue
                    if current_time - queue._last_put_time > self._max_queue_disactive_age:
                        expired_requests.append(request_id)

                for request_id in expired_requests:
                    await self.remove_queue(request_id)
                    print(f"清理过期队列: {request_id}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"清理任务出错: {e}")

    @property
    def active_queues_count(self) -> int:
        """活跃队列数量"""
        return len(self._queues)




class MessageConsumer:
    """消息消费者"""

    def __init__(self, queue: AsyncMessageQueue, message_handler: Optional[Callable] = None):
        self.queue = queue
        self.message_handler = message_handler

    async def default_message_handler(self, message_body: str):
        """默认消息处理器"""
        print(f"默认处理器处理消息: {message_body}")
        await asyncio.sleep(10)  # 模拟处理时间

    async def consume(self):
        """消费消息"""
        async with self.queue.iterator() as queue_iter:
            async for message in queue_iter:
                try:
                    async with message.process():
                        message_body = message.body.decode()
                        print(f"收到消息: {message_body}")

                        # 使用自定义处理器或默认处理
                        if self.message_handler:
                            await self.message_handler(message_body)
                        else:
                            await self.default_message_handler(message_body)

                        # 检查是否需要停止
                        if self.queue.name in message_body:
                            print("收到退出信号，停止消费")
                            break

                except Exception as e:
                    print(f"处理消息时发生错误: {e}")


# 使用示例
async def custom_message_handler(message_body: str):
    """自定义消息处理器"""
    print(f"自定义处理器处理: {message_body}")
    await asyncio.sleep(0.2)



async def main():
    # 创建队列
    queue = AsyncMessageQueue("default", timeout=2.0)

    # 创建消费者
    consumer = MessageConsumer(queue, custom_message_handler)


    # 关闭队列
    await queue.close()


if __name__ == "__main__":
    asyncio.run(main())