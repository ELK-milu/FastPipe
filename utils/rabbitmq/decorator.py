from utils.rabbitmq.consumer_register_list import RabbitMQConsumerRegister
from functools import wraps

def RabbitListener(consumer_name: str, queue_name: str, auto_delete: bool = True, durable: bool = False,no_ack :bool = True):
    """
    类似Java @RabbitListener的装饰器
    用法:
    @rabbit_listener(consumer_name="my_consumer", queue_name="my_queue")
    def handle_message(message):
        print(f"Received: {message}")
    """

    def decorator(handler_func):
        @wraps(handler_func)
        def wrapper(*args, **kwargs):
            # 这里保留原始函数的调用能力
            return handler_func(*args, **kwargs)

        # 获取或创建单例的RabbitMQConsumerRegister实例
        consumer_register = RabbitMQConsumerRegister()

        # 注册消费者
        try:
            consumer_register.add_consumer(
                consumerName=consumer_name,
                queue_name=queue_name,
                auto_delete=auto_delete,
                durable=durable,
                message_handler=handler_func,
                no_ack= no_ack
            )
        except Exception as e:
            raise RuntimeError(f"Failed to register RabbitMQ listener: {e}")

        return wrapper

    return decorator