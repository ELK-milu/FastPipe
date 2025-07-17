# Twitter's Snowflake algorithm implementation which is used to generate distributed IDs.
# https://github.com/twitter-archive/snowflake/blob/snowflake-2010/src/main/scala/com/twitter/service/snowflake/IdWorker.scala

import time

from . import WORKER_ID_BITS,DATACENTER_ID_BITS,SEQUENCE_BITS,TWEPOCH
from .exceptions import InvalidSystemClock


# 最大取值计算

# -1的原码为11111，左移5位后，得到1111100000
# 1111111111 和 1111100000按位异或得到0000011111，即为2^5-1
MAX_WORKER_ID = -1 ^ (-1 << WORKER_ID_BITS)  # 2**5-1 0b11111
MAX_DATACENTER_ID = -1 ^ (-1 << DATACENTER_ID_BITS)

# 移位偏移计算
WOKER_ID_SHIFT = SEQUENCE_BITS
DATACENTER_ID_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS
TIMESTAMP_LEFT_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS + DATACENTER_ID_BITS

# 序号循环掩码
SEQUENCE_MASK = -1 ^ (-1 << SEQUENCE_BITS)



class Snowflake(object):
    """
    用于生成IDs
    """

    def __init__(self, datacenter_id, worker_id, sequence=0):
        """
        初始化
        :param datacenter_id: 数据中心（机器区域）ID
        :param worker_id: 机器ID
        :param sequence: 序号
        """
        # sanity check
        if worker_id > MAX_WORKER_ID or worker_id < 0:
            raise ValueError('worker_id值越界')

        if datacenter_id > MAX_DATACENTER_ID or datacenter_id < 0:
            raise ValueError('datacenter_id值越界')

        self.worker_id = worker_id
        self.datacenter_id = datacenter_id
        self.sequence = sequence

        self.last_timestamp = -1  # 上次计算的时间戳

    def _gen_timestamp(self):
        """
        生成整数时间戳
        :return:int timestamp
        """
        return int(time.time() * 1000)

    def get_id(self):
        """
        获取新ID
        :return:
        """
        timestamp = self._gen_timestamp()

        # 时钟回拨
        if timestamp < self.last_timestamp:
            raise InvalidSystemClock

        # 若产生的ID在同一毫秒内，需要保证生成的ID不相同
        if timestamp == self.last_timestamp:
            # 计算下当前的sequence+1,按顺序+1后与mask相与，mask是全1的，即为2**12 -1 = 1111 1111 1111
            # 所以相与后只有0000 0000 0000才得到为0。当前毫秒内已经无可用seq
            # 所以需要放在下一毫秒再生成
            self.sequence = (self.sequence + 1) & SEQUENCE_MASK
            if self.sequence == 0:
                # 阻塞直到下一毫秒
                timestamp = self._til_next_millis(self.last_timestamp)
        # 否则当前时间大于上一毫秒，则进入了新的毫秒，则重新计数sequence
        else:
            self.sequence = 0

        self.last_timestamp = timestamp

        # 对应规则位左移并分别组合
        new_id = ((timestamp - TWEPOCH) << TIMESTAMP_LEFT_SHIFT) | (self.datacenter_id << DATACENTER_ID_SHIFT) | \
                 (self.worker_id << WOKER_ID_SHIFT) | self.sequence
        return new_id

    def _til_next_millis(self, last_timestamp):
        """
        等到下一毫秒，作为下一毫秒的头
        """
        timestamp = self._gen_timestamp()
        # 阻塞直到下一毫秒再生成新的ID
        while timestamp <= last_timestamp:
            timestamp = self._gen_timestamp()
        return timestamp
