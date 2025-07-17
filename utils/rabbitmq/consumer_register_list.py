import asyncio
from queue import Queue
from typing import Dict
from utils.rabbitmq.rabbit_mq_consumer import RabbitMQConsumer
from utils.single import SingletonMeta


##############此处为自行定义的消费者类###################

class RabbitMQConsumerRegister(metaclass=SingletonMeta):
    """RabbitMQ消费者注册类"""
    def __init__(self, consumerDict=None):
        self.consumerDict = consumerDict if consumerDict is not None else {}
        self.consumerPool : Queue[RabbitMQConsumer] = Queue()  # 用于存储消费者池

    def add_consumer(self, consumerName:str,queue_name: str, auto_delete: bool = True,durable:bool=False, message_handler=None):
        """添加消费者"""
        if self.consumerDict is None:
            self.consumerDict = {}

        if consumerName in self.consumerDict:
            raise ValueError(f"Consumer {consumerName} already exists.")

        try:
            # 检查池中是否有可用的消费者
            if not self.consumerPool.empty():
                consumer = self.consumerPool.get()
                consumer.queue_name = queue_name
                consumer.auto_delete = auto_delete
                consumer.durable = durable
                consumer.message_handler = message_handler
            else:
                consumer = RabbitMQConsumer(queue_name=queue_name,
                                            auto_delete=auto_delete,
                                            durable=durable,
                                            message_handler=message_handler)
            self.consumerDict[consumerName] = consumer
        except Exception as e:
            raise ValueError(f"Failed to add consumer {consumerName}: {e}")

    async def start(self):
        """启动消费者"""
        for consumer in self.consumerDict.values():
            await consumer.start_consumer()

    async def stop(self):
        """停止消费者"""
        for consumer in self.consumerDict.values():
            await consumer.disconnect()
            self.consumerPool.put(consumer)  # 将消费者放回池中

    async def start_consumer(self, consumerName: str):
        """启动指定消费者"""
        if consumerName in self.consumerDict:
            await self.consumerDict[consumerName].start_consumer()
        else:
            raise ValueError(f"Consumer {consumerName} not found.")

    async def stop_consumer(self, consumerName: str):
        """停止指定消费者"""
        if consumerName in self.consumerDict:
            consumer = self.consumerDict[consumerName]
            await consumer.disconnect()
            self.consumerPool.put(consumer)  # 将消费者放回池中
        else:
            raise ValueError(f"Consumer {consumerName} not found.")

    def check_consumer(self, consumerName: str):
        """检查消费者的状态"""
        if consumerName not in self.consumerDict:
            raise ValueError(f"Consumer {consumerName} not found.")
        return self.consumerDict[consumerName].get_status()


rabbitMQConsumerRegister = RabbitMQConsumerRegister()