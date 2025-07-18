# 优化后的HTTP连接管理器 - 解决并发性能问题
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
        self.last_request_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'user_id': self.user_id,
            'total_requests': self.total_requests.value,
            'active_requests': self.active_requests.value,
            'last_request_time': self.last_request_time
        }


class HTTPSessionManager:
    """基于 httpx 的异步连接管理器 - 优化并发性能"""

    def __init__(
            self,
            base_url: str = "http://192.168.30.46",
            timeout: float = 300.0,
            max_connections: int = 1000,  # 增加连接池大小
            max_keepalive_connections: int = 500,  # 增加保活连接数
            keepalive_expiry: int = 120,  # 增加保活时间
    ):
        self._base_url = base_url
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._user_stats: Dict[str, UserStats] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

        # 优化连接池配置
        self._limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
        )

        # 优化超时配置
        self._timeout_config = httpx.Timeout(
            timeout=timeout,
            connect=30.0,  # 连接超时
            read=timeout,  # 读取超时
            write=30.0,  # 写入超时
            pool=10.0  # 连接池超时
        )

    async def get_client(self) -> httpx.AsyncClient:
        """获取共享的异步客户端（优化初始化）"""

        if not self._initialized:
            async with self._lock:
                if not self._initialized:
                    # 根据目标服务器特性选择HTTP版本
                    # 如果目标服务器支持HTTP/2且配置正确，保留http2=True
                    # 否则建议使用HTTP/1.1以获得更好的兼容性
                    self._client = httpx.AsyncClient(
                        http2=False,  # 暂时禁用HTTP/2，避免连接复用问题
                        base_url=self._base_url,
                        timeout=self._timeout_config,
                        limits=self._limits,
                        headers={
                            'Content-Type': 'application/json',
                            'Connection': 'keep-alive',  # 确保连接保活
                            'Keep-Alive': 'timeout=60, max=1000'
                        },
                        # 优化传输设置
                        transport=httpx.AsyncHTTPTransport(
                            retries=3,  # 自动重试
                            verify=False  # 如果是内网环境，可以禁用SSL验证
                        )
                    )
                    self._initialized = True
                    logger.info("HTTPX 客户端初始化完成 - 优化并发配置")
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._initialized = False
            logger.info("HTTPX 客户端已关闭")

    def if_user_exist(self, user_id: str) -> bool:
        """检查用户是否存在"""
        return user_id in self._user_stats

    async def add_user_stats(self, user_id: str) -> UserStats:
        """创建连接时调用，加入新用户统计"""
        if user_id not in self._user_stats:
            self._user_stats[user_id] = UserStats(user_id)
            logger.info(f"新用户加入: {user_id}")
        return self._user_stats[user_id]

    async def _get_user_stats(self, user_id: str) -> UserStats:
        """获取用户统计数据"""
        if self.if_user_exist(user_id):
            return self._user_stats[user_id]
        else:
            raise ValueError(f"用户不存在: {user_id}")

    async def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        if self._client and hasattr(self._client, '_transport'):
            transport = self._client._transport
            return {
                'total_connections': len(transport._pool._connections) if hasattr(transport, '_pool') else 0,
                'active_users': len(self._user_stats),
                'client_initialized': self._initialized
            }
        return {'error': 'Client not initialized'}

    async def warmup_connections(self, target_url: str = None, connections: int = 10):
        """预热连接池"""
        if not target_url:
            target_url = f"{self._base_url}/health"  # 假设有健康检查端点

        client = await self.get_client()
        tasks = []

        for i in range(connections):
            task = asyncio.create_task(self._warmup_single_connection(client, target_url))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"连接预热完成: {successful}/{connections} 成功")

    async def _warmup_single_connection(self, client: httpx.AsyncClient, url: str):
        """单个连接预热"""
        try:
            async with client.stream("GET", url, timeout=5.0) as response:
                await response.aread()
        except Exception as e:
            logger.debug(f"预热连接失败: {e}")
            raise