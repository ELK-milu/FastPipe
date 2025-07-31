import asyncio
import json

from utils.rabbitmq import RABBIT_MQ_USER, RABBIT_MQ_PASSWORD, RABBIT_MQ_HOST
import aio_pika
import aio_pika.abc
from utils.single import SingletonMeta

from functools import wraps


def ensure_connection(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not self.is_running:
            await self.connect()

        if self.channel is None:
            raise RuntimeError("RabbitMQ channel is not initialized. Call connect() first.")

        return await func(self, *args, **kwargs)

    return wrapper

class RabbitMQProducer(metaclass=SingletonMeta):
    """RabbitMQ生产者服务类"""
    def __init__(self,publisher_confirms:bool=False):
        self.connection: aio_pika.abc.AbstractRobustConnection = None
        self.channel: aio_pika.abc.AbstractChannel = None
        self.is_running = False
        self.loop = None
        # 是否开启发布确认
        self.publisher_confirms = publisher_confirms

    async def connect(self):
        """建立RabbitMQ连接"""
        if self.connection is None:
            if self.loop is None:
                self.connection = await aio_pika.connect_robust(
                    f"amqp://{RABBIT_MQ_USER}:{RABBIT_MQ_PASSWORD}@{RABBIT_MQ_HOST}/"
                )
            else:
                self.connection = await aio_pika.connect_robust(
                    f"amqp://{RABBIT_MQ_USER}:{RABBIT_MQ_PASSWORD}@{RABBIT_MQ_HOST}/",
                    loop=self.loop
                )
            self.channel = await self.connection.channel()
            self.channel.publisher_confirms = self.publisher_confirms
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


    @ensure_connection
    async def declare_queue(self,queue_name:str, auto_delete:bool =True,durable:bool=False,time_out=1):
        """声明队列"""
        queue = await self.channel.declare_queue(
            queue_name,
            auto_delete=auto_delete,
            durable=durable,
            timeout=time_out,
        )
        #queue.arguments.setdefault("x-queue-mode", 60000)
        return queue

    @ensure_connection
    async def declare_exchange(self,exchange_name:str,type:aio_pika.ExchangeType,durable:bool = False,auto_delete:bool=True):
        """声明队列"""
        exchange = await self.channel.declare_exchange(
            exchange_name,
            type,
            durable=durable,
            auto_delete= auto_delete
        )
        return exchange

    @ensure_connection
    async def delete_exchange(self,exchange_name:str):
        """删除交换机"""
        await self.channel.exchange_delete(exchange_name)


    @ensure_connection
    async def publish(self, routing_key: str, message: str):
        """发布消息到指定路由键"""
        msg_type = await self.channel.default_exchange.publish(
            aio_pika.Message(body=message.encode()),
            routing_key=routing_key,
        )
        print(f"消息已发布到 {routing_key}: {message}")

    @ensure_connection
    async def broadcast(self, exchanger:str, message: str,
                        type:aio_pika.ExchangeType,delivery_mode:aio_pika.DeliveryMode =aio_pika.DeliveryMode.PERSISTENT,
                        durable:bool = False,auto_delete:bool=True, routing_key:str= ""):
        """发布消息到所有绑定的队列"""
        # 声明 fanout 类型的交换机
        exchange = await self.channel.declare_exchange(
            exchanger,
            type,
            durable=durable,
            auto_delete = auto_delete
        )
        board_message = aio_pika.Message(
            message.encode(),
            delivery_mode=delivery_mode,
        )
        # 发布消息到交换机（不指定路由键）
        await exchange.publish(board_message, routing_key=routing_key)


rabbit_mq_producer = RabbitMQProducer(publisher_confirms=False)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(rabbit_mq_producer.publish("test_queue","你好啊"))
    loop.close()