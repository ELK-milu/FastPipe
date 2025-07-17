# 优化后的HTTP连接管理器 - 解决并发锁问题
import aiohttp
import asyncio
import time

import httpx
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


class HTTPSessionManager:
    """基于 httpx 的异步连接管理器"""

    def __init__(
            self,
            base_url: str = "http://192.168.30.46",
            timeout: float = 300.0,
            max_connections: int = 100,
            max_keepalive_connections: int = 50
    ):
        self._base_url = base_url
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._user_stats: Dict[str, UserStats] = {}
        self._lock = asyncio.Lock()

        # 连接池配置
        self._limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections
        )
        asyncio.run(self.get_client())

    async def get_client(self) -> httpx.AsyncClient:
        """获取共享的异步客户端（依赖注入用）"""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    self._client = httpx.AsyncClient(
                        base_url=self._base_url,
                        timeout=self._timeout,
                        limits=self._limits,
                        headers={
                            'User-Agent': 'LLM-Proxy-Server/1.0',
                            'Content-Type': 'application/json'
                        }
                    )
                    logger.info("HTTPX 客户端初始化完成")
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("HTTPX 客户端已关闭")

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

