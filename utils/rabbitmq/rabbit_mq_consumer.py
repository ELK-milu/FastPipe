import aio_pika.abc
from utils.rabbitmq import RABBIT_MQ_USER, RABBIT_MQ_PASSWORD, RABBIT_MQ_HOST
import asyncio
import aio_pika
from aio_pika import IncomingMessage
from typing import Optional, Callable


class RabbitMQConsumer:
    """RabbitMQ消费者服务类"""

    def __init__(self, queue_name: str = "test_queue", auto_delete: bool = True, durable: bool = False,
                 message_handler: Optional[Callable] = None, loop=None, no_ack: bool = True):
        self.connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self.channel: Optional[aio_pika.abc.AbstractChannel] = None
        self.consumer_tag: Optional[str] = None
        self.is_running = False
        self.queue_name = queue_name
        self.auto_delete = auto_delete  # 是否自动删除队列
        self.durable = durable  # 是否持久化队列
        self.message_handler: Optional[Callable] = message_handler
        self.loop = loop
        self.no_ack = no_ack  # 是否自动确认消息

    async def connect(self, loop=None):
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
        if self.consumer_tag and self.channel:
            try:
                await self.channel.close()
                print("消费者已取消")
            except Exception as e:
                print(f"取消消费者时出错: {e}")

        if self.connection:
            await self.connection.close()
            self.connection = None
            self.channel = None
            print("RabbitMQ连接已断开")

        self.is_running = False
        self.consumer_tag = None
    async def on_message(self, message: IncomingMessage):
        """内部消息处理方法,需要手动进行消息处理"""
        try:
            message_body = message.body.decode()

            # 使用自定义处理器或默认处理
            if self.message_handler:
                await self.message_handler(message_body)
            else:
                await self.default_message_handler(message_body)

            # 如果no_ack=False，需要手动确认消息
            #if not self.no_ack:
                #await message.ack()

        except Exception as e:
            print(f"处理消息时出错: {e}")
            # 如果no_ack=False，消息处理失败时拒绝消息
            #if not self.no_ack:
                #await message.nack(requeue=True)

    async def start_consumer(self):
        """启动消费者"""
        if self.is_running:
            print("消费者已在运行中")
            return

        await self.connect(self.loop)

        # 声明队列
        queue = await self.channel.declare_queue(
            self.queue_name,
            auto_delete=self.auto_delete,
            durable=self.durable
        )

        # 开始消费消息
        self.consumer_tag = await queue.consume(self.on_message, no_ack=self.no_ack)
        self.is_running = True

        print(f"消费者已启动，监听队列: {self.queue_name}")

    async def stop_consumer(self):
        """停止消费者"""
        if not self.is_running:
            print("消费者未在运行")
            return

        if self.consumer_tag and self.channel:
            try:
                await self.channel.basic_cancel(self.consumer_tag)
                print("消费者已停止")
            except Exception as e:
                print(f"停止消费者时出错: {e}")

        self.is_running = False
        self.consumer_tag = None

    async def default_message_handler(self, message_body: str):
        """默认消息处理器"""
        print(f"默认处理器接收到消息: {message_body}")
        # 模拟异步I/O操作
        await asyncio.sleep(0.1)

    def get_status(self):
        """获取消费者状态"""
        return {
            "is_running": self.is_running,
            "connection_open": self.connection is not None and not self.connection.is_closed,
            "consumer_tag": self.consumer_tag,
            "queue_name": self.queue_name
        }


# 使用示例
async def custom_message_handler(message_body: str):
    """自定义消息处理器"""
    print(f"自定义处理器处理消息: {message_body}")
    # 模拟一些异步处理
    await asyncio.sleep(1)


async def main():
    """主函数示例"""
    # 创建消费者实例
    consumer = RabbitMQConsumer(
        queue_name="test_queue",
        message_handler=custom_message_handler,
        no_ack=True  # 自动确认消息
    )

    try:
        # 启动消费者
        await consumer.start_consumer()

        # 让消费者运行一段时间
        print("消费者正在运行，按Ctrl+C停止...")

        # 这里可以做其他工作或者等待信号
        while consumer.is_running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("收到停止信号")
    except Exception as e:
        print(f"运行时出错: {e}")
    finally:
        # 清理资源
        await consumer.disconnect()


if __name__ == "__main__":
    # 方式1：使用asyncio.run (推荐)
    asyncio.run(main())

    # 方式2：使用事件循环 (与你原来的方式类似)
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # try:
    #     loop.run_until_complete(main())
    # finally:
    #     loop.close()