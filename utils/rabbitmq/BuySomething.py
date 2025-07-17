from loguru import logger

from models import AsyncSessionFactory
from models.order import Order
from utils.cache import tll_redis
from utils.tllalipay import tll_alipay
import json

async def seckill_queue_handle(message_body: str):
    seckill_dict = json.loads(message_body)
    seckill_id = seckill_dict['seckill_id']
    user_id = seckill_dict['user_id']
    count = seckill_dict['count']
    address = seckill_dict['address']

    seckill = await tll_redis.get_seckill(seckill_id)
    if not seckill:
        logger.info(f'{seckill_id}秒杀商品不存在！')
    if count > seckill['sk_per_max_count']:
        logger.info(f"{user_id}抢购了{count}，超过了{seckill['sk_per_max_count']}")
    print(f"秒杀商品信息：{seckill}")
    async with AsyncSessionFactory() as session:
        async with session.begin():
            order = Order(
                user_id=user_id, seckill_id=seckill_id, count=count,
                amount=seckill['sk_price'] * count,
                address=address
            )
            session.add(order)
        await session.refresh(order, attribute_names=['seckill'])
    alipay_order = tll_alipay.app_pay(
        out_trade_no=str(order.id),
        total_amount=float(order.amount),
        subject=seckill['commodity']['title']
    )
    await tll_redis.add_order(order, alipay_order['alipay_order'])
