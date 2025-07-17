# 优化后的HTTP连接管理器 - 解决并发锁问题
import aiohttp
import asyncio
import time
from loguru import logger
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from collections import defaultdict
import threading
from utils.single import SingletonMeta


class ThreadSafeCounter:
    """线程安全的计数器"""

    def __init__(self, initial_value: int = 0):
        self._value = initial_value
        self._lock = threading.Lock()

    def increment(self) -> int:
        with self._lock:
            self._value += 1
            return self._value

    def decrement(self) -> int:
        with self._lock:
            self._value = max(0, self._value - 1)
            return self._value

    @property
    def value(self) -> int:
        with self._lock:
            return self._value


class UserStats:
    """用户统计信息 - 使用线程安全的计数器"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.total_requests = ThreadSafeCounter()
        self.active_requests = ThreadSafeCounter()
        self._last_request_time = time.time()
        self._time_lock = threading.Lock()

    def update_request_start(self):
        """更新请求开始统计"""
        self.active_requests.increment()
        self.total_requests.increment()
        with self._time_lock:
            self._last_request_time = time.time()

    def update_request_end(self):
        """更新请求结束统计"""
        self.active_requests.decrement()

    @property
    def last_request_time(self) -> float:
        with self._time_lock:
            return self._last_request_time

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'user_id': self.user_id,
            'total_requests': self.total_requests.value,
            'active_requests': self.active_requests.value,
            'last_request_time': self.last_request_time
        }


class HTTPSessionManager():
    """优化后的HTTP连接管理器"""

    def __init__(self,
                 base_url: str = "https://api.openai.com/v1",
                 max_concurrent_requests: int = 100,
                 request_timeout: int = 300,
                 max_requests_per_user: int = 10,
                 connector_limit: int = 100):
        """
        初始化会话管理器
        """
        self._base_url = base_url
        self._max_concurrent_requests = max_concurrent_requests
        self._request_timeout = request_timeout
        self._max_requests_per_user = max_requests_per_user
        self._connector_limit = connector_limit

        # 共享的HTTP session
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()

        # 请求管理 - 使用defaultdict和线程安全的用户统计
        self._user_stats: Dict[str, UserStats] = {}

        # 日志
        self._logger = logger

    async def _initialize_session(self):
        """初始化共享的HTTP session"""
        async with self._session_lock:
            if self._session is None:
                connector = aiohttp.TCPConnector(
                    limit=100,  # 总连接数限制
                    limit_per_host=50,  # 对单个主机的连接数限制
                    force_close=False,  # 允许连接重用
                    enable_cleanup_closed=True,  # 自动清理关闭的连接
                    keepalive_timeout=30  # 保持连接时间
                )

                timeout = aiohttp.ClientTimeout(total=self._request_timeout)

                self._session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={
                        'User-Agent': 'LLM-Proxy-Server/1.0',
                        'Content-Type': 'application/json'
                    }
                )

                self._logger.info("初始化共享HTTP session成功")

    async def get_session(self) -> aiohttp.ClientSession:
        """获取共享的HTTP session - 带重试机制"""
        if self._session is None or self._session.closed:
            await self._initialize_session()
        return self._session

    def if_user_exist(self, user_id: str) -> bool:
        """检查用户是否存在"""
        if user_id in self._user_stats:
            return True
        return False

    async def add_user_stats(self, user_id: str) -> UserStats:
        """创建连接时调用，加入新用户统计"""
        if user_id not in self._user_stats:
            self._user_stats[user_id] = UserStats(user_id)
            self._logger.info(f"新用户加入: {user_id}")
        return self._user_stats[user_id]

    async def _get_user_stats(self, user_id: str) -> UserStats:
        """获取用户统计数据"""
        if self.if_user_exist(user_id):
            return self._user_stats[user_id]
        else:
            raise ValueError(f"用户不存在: {user_id}")

    async def close_session(self):
        """关闭共享session"""
        async with self._session_lock:
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
                self._logger.info("共享HTTP session已关闭")
