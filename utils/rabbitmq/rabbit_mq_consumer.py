import aio_pika.abc
from utils.rabbitmq import RABBIT_MQ_USER, RABBIT_MQ_PASSWORD, RABBIT_MQ_HOST
import asyncio
import aio_pika
import aio_pika.abc
from typing import Optional, Callable


class RabbitMQConsumer:
    """RabbitMQ消费者服务类"""

    def __init__(self, queue_name: str = "test_queue", auto_delete: bool = True,durable:bool=False,message_handler: Optional[Callable] = None,loop=None):
        self.connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self.channel: Optional[aio_pika.abc.AbstractChannel] = None
        self.consumer_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.queue_name = queue_name
        self.auto_delete = auto_delete  # 是否自动删除队列
        self.durable = durable  # 是否持久化队列
        self.message_handler: Optional[Callable] = message_handler
        self.loop = loop


    async def connect(self,loop=None):
        """建立RabbitMQ连接"""
        if self.connection is None:
            if loop is None:
                self.connection = await aio_pika.connect_robust(
                    f"amqp://{RABBIT_MQ_USER}:{RABBIT_MQ_PASSWORD}@{RABBIT_MQ_HOST}/"
                )
            else:
                self.connection = await aio_pika.connect_robust(
                    f"amqp://{RABBIT_MQ_USER}:{RABBIT_MQ_PASSWORD}@{RABBIT_MQ_HOST}/",
                    loop=loop
                )
            self.channel = await self.connection.channel()
            print("RabbitMQ消费者连接已建立")

    async def disconnect(self):
        """断开RabbitMQ连接"""
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass
            self.consumer_task = None

        if self.connection:
            await self.connection.close()
            self.connection = None
            self.channel = None
            print("RabbitMQ连接已断开")

    async def start_consumer(self):
        """启动消费者"""
        if self.is_running:
            return

        await self.connect(self.loop)

        # 声明队列
        queue = await self.channel.declare_queue(self.queue_name, auto_delete=self.auto_delete,durable=self.durable)

        async def consume_messages():
            """消费消息的内部函数"""
            try:
                async with queue.iterator() as queue_iter:
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
                                if queue.name in message_body:
                                    print("收到退出信号，停止消费")
                                    break

                        except Exception as e:
                            print(f"处理消息时出错: {e}")
            except asyncio.CancelledError:
                print("消费者任务被取消")
                raise
            except Exception as e:
                print(f"消费者运行时出错: {e}")
            finally:
                self.is_running = False

        self.consumer_task = asyncio.create_task(consume_messages())
        self.is_running = True

        print(f"消费者已启动，监听队列: {self.queue_name}")

    async def default_message_handler(self, message_body: str):
        """默认消息处理器"""
        print(f"接收到消息: {message_body}")
        # 在这里添加你的业务逻辑

    def get_status(self):
        """获取消费者状态"""
        return {
            "is_running": self.is_running,
            "connection_open": self.connection is not None and not self.connection.is_closed,
            "task_status": "running" if self.consumer_task and not self.consumer_task.done() else "stopped"
        }


if __name__ == "__main__":
    rabbit_mq_consumer = RabbitMQConsumer()
    loop = asyncio.new_event_loop()
    loop.run_until_complete(rabbit_mq_consumer.start_consumer(queue_name="test_queue",
                                                              loop=loop))
    loop.close()