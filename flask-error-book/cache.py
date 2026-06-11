"""
Redis 缓存工具模块。
Redis 不可用时自动降级（返回 None 或不缓存），不影响主功能。
"""

from extensions import get_redis


def get_cache(key):
    """从 Redis 读取缓存值，Redis 不可用时返回 None"""
    client = get_redis()
    if client is None:
        return None
    try:
        return client.get(key)
    except Exception:
        return None


def set_cache(key, value, expire_seconds=300):
    """写入 Redis 缓存，Redis 不可用时静默跳过"""
    client = get_redis()
    if client is None:
        return
    try:
        client.setex(key, expire_seconds, value)
    except Exception:
        pass


def delete_cache(key):
    """删除缓存键"""
    client = get_redis()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception:
        pass


def invalidate_pattern(pattern):
    """按模式批量删除缓存键（如 'dashboard:*'）"""
    client = get_redis()
    if client is None:
        return
    try:
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)
    except Exception:
        pass


def cache_result(key_prefix, ttl=300):
    """
    缓存装饰器。用于包装返回值固定的函数。
    用法: @cache_result('subjects', ttl=600)
    Redis 不可用时等效于直接调用原函数。
    """
    import json
    from functools import wraps

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{func.__name__}"
            cached = get_cache(cache_key)
            if cached is not None:
                try:
                    return json.loads(cached)
                except Exception:
                    pass
            result = func(*args, **kwargs)
            try:
                set_cache(cache_key, json.dumps(result, default=str), expire_seconds=ttl)
            except Exception:
                pass
            return result
        return wrapper
    return decorator
