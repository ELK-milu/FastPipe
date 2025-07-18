import asyncio
import time
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from schemas import response
from services import handle_http_exceptions, handle_streaming_http_exceptions
from services.Dify import SetSessionConfig, get_payload
from utils.httpManager import HTTPSessionManager
from utils.auth import AuthHandler
import aiohttp

auth_handler = AuthHandler()

router = APIRouter(prefix='/test')

# 优化HTTPSessionManager配置
httpSessionManager = HTTPSessionManager(
    base_url="http://192.168.30.46",
    max_connections=1000,  # 增加连接池
    max_keepalive_connections=500,  # 增加保活连接
    keepalive_expiry=120  # 增加保活时间
)


# 应用启动时预热连接池
@router.on_event("startup")
async def startup_event():
    await httpSessionManager.warmup_connections(
        target_url="http://192.168.30.46/v1/chat-messages",
        connections=100
    )


@router.get("/debug")
async def debug(client: httpx.AsyncClient = Depends(httpSessionManager.get_client)):
    # 方法1：通过实际请求检测
    async with client.stream("GET", "https://httpbin.org/get") as response:
        http_version = response.http_version  # 返回 "HTTP/1.1" 或 "HTTP/2"
        print(http_version)


@router.get('/stream')
async def stream(client: httpx.AsyncClient = Depends(httpSessionManager.get_client)):
    """优化后的流式传输接口"""
    request_start_time = time.time()

    # 配置会话和请求参数
    finalsession = SetSessionConfig(key="app-FHpDSmylxvZ8rHcdMWo4XgkE", session=client)
    payload = get_payload("你好，介绍下你自己")

    async def generate():
        connection_start_time = time.time()
        first_byte_time = None
        total_bytes = 0

        try:
            # 使用绝对URL而不是相对URL
            async with finalsession.stream(
                    "POST",
                    'http://192.168.30.46/v1/chat-messages',
                    json=payload,
                    timeout=httpx.Timeout(
                        timeout=300.0,
                        connect=10.0,  # 减少连接超时时间
                        read=300.0,
                        write=10.0,
                        pool=5.0  # 减少连接池获取超时
                    )
            ) as response:
                logger.info(f"连接建立耗时: {time.time() - connection_start_time:.3f}s")

                # 检查响应状态
                if response.status_code != 200:
                    logger.error(f"HTTP错误: {response.status_code}")
                    raise HTTPException(status_code=response.status_code, detail="Stream request failed")

                async for chunk in response.aiter_bytes(chunk_size=8192):  # 增加chunk大小
                    if chunk:
                        if first_byte_time is None:
                            first_byte_time = time.time()
                            logger.info(f"首字节接收耗时: {first_byte_time - connection_start_time:.3f}s")

                        total_bytes += len(chunk)
                        yield chunk


        except httpx.ConnectTimeout:
            logger.error("连接超时")
            raise HTTPException(status_code=504, detail="Connection timeout")
        except httpx.ReadTimeout:
            logger.error("读取超时")
            raise HTTPException(status_code=504, detail="Read timeout")
        except httpx.PoolTimeout:
            logger.error("连接池超时")
            raise HTTPException(status_code=503, detail="Connection pool timeout")
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Stream error: {str(e)}")
        finally:
            final_time = time.time()
            total_time = final_time - request_start_time
            logger.info(f"请求总耗时: {total_time:.3f}s, 传输字节数: {total_bytes}")

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'  # 禁用nginx缓冲
        }
    )


@router.get('/stream-batch')
async def stream_batch(
        concurrent_requests: int = 20,
        client: httpx.AsyncClient = Depends(httpSessionManager.get_client)
):
    """批量并发测试接口"""

    async def single_request(request_id: int):
        start_time = time.time()
        try:
            finalsession = SetSessionConfig(key="app-FHpDSmylxvZ8rHcdMWo4XgkE", session=client)
            payload = get_payload(f"请求 {request_id}: 你好，介绍下你自己")

            async with finalsession.stream(
                    "POST",
                    'http://192.168.30.46/v1/chat-messages',
                    json=payload,
                    timeout=httpx.Timeout(timeout=300.0, connect=10.0, pool=5.0)
            ) as response:
                total_bytes = 0
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    if chunk:
                        total_bytes += len(chunk)

                return {
                    'request_id': request_id,
                    'duration': time.time() - start_time,
                    'bytes': total_bytes,
                    'status': 'success'
                }
        except Exception as e:
            return {
                'request_id': request_id,
                'duration': time.time() - start_time,
                'error': str(e),
                'status': 'failed'
            }

    # 创建并发任务
    tasks = [single_request(i) for i in range(concurrent_requests)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 统计结果
    successful = [r for r in results if isinstance(r, dict) and r.get('status') == 'success']
    failed = [r for r in results if isinstance(r, dict) and r.get('status') == 'failed']

    return {
        'total_requests': concurrent_requests,
        'successful': len(successful),
        'failed': len(failed),
        'average_duration': sum(r.get('duration', 0) for r in successful) / len(successful) if successful else 0,
        'connection_stats': await httpSessionManager.get_connection_stats()
    }


@router.get('/')
@handle_http_exceptions
async def order_list(client: httpx.AsyncClient = Depends(httpSessionManager.get_client)):
    """优化后的普通HTTP请求"""
    try:
        response = await client.get('https://www.baidu.com/', timeout=30.0)
        return response.text
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/health')
async def health_check():
    """健康检查端点"""
    return {
        'status': 'ok',
        'timestamp': time.time(),
        'connection_stats': await httpSessionManager.get_connection_stats()
    }