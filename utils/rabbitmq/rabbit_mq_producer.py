import asyncio
import json

from utils.rabbitmq import RABBIT_MQ_USER, RABBIT_MQ_PASSWORD, RABBIT_MQ_HOST
import aio_pika
import aio_pika.abc
from utils.single import SingletonMeta


class RabbitMQProducer(metaclass=SingletonMeta):
    """RabbitMQ生产者服务类"""
    def __init__(self):
        self.connection: aio_pika.abc.AbstractRobustConnection = None
        self.channel: aio_pika.abc.AbstractChannel = None
        self.is_running = False

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
            self.is_running = True
            print("RabbitMQ生产者连接已建立")

    async def disconnect(self):
        """断开RabbitMQ连接"""
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.channel = None
            self.is_running = False
            print("RabbitMQ连接已断开")

    async def publish(self, routing_key: str, message: str, loop=None):
        """发布消息到指定路由键"""
        if not self.is_running:
            await self.connect(loop)

        if self.channel is None:
            raise RuntimeError("RabbitMQ channel is not initialized. Call connect() first.")

        await self.channel.default_exchange.publish(
            aio_pika.Message(body=message.encode()),
            routing_key=routing_key
        )
        print(f"消息已发布到 {routing_key}: {message}")

    async def boardcast(self,exchanger:str, message: str,type:aio_pika.ExchangeType,durable:bool = False,routing_key:str="", loop=None):
        """发布消息到所有绑定的队列"""
        if not self.is_running:
            await self.connect(loop)

        if self.channel is None:
            raise RuntimeError("RabbitMQ channel is not initialized. Call connect() first.")

        # 声明 fanout 类型的交换机
        exchange = await self.channel.declare_exchange(
            exchanger,
            type,
            durable=durable
        )
        board_message = aio_pika.Message(
            message.encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        # 发布消息到交换机（不指定路由键）
        await exchange.publish(board_message, routing_key=routing_key)



rabbit_mq_producer = RabbitMQProducer()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(rabbit_mq_producer.publish("test_queue","你好啊",loop))
    loop.close()