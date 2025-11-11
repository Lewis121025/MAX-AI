"""缓存系统：提高性能并减少重复调用。"""

from __future__ import annotations

import json
import hashlib
import time
from typing import Any, Optional, Callable
from functools import wraps
import sqlite3
from pathlib import Path


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, db_path: str = "data/cache.db", ttl: int = 3600):
        """
        初始化缓存管理器。
        
        参数:
            db_path: SQLite数据库路径
            ttl: 缓存有效期（秒），默认1小时
        """
        self.db_path = db_path
        self.ttl = ttl
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT,
                created_at REAL,
                expires_at REAL
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)
        ''')
        
        conn.commit()
        conn.close()
    
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        key_data = {
            "func": func_name,
            "args": args,
            "kwargs": kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = time.time()
        cursor.execute(
            'SELECT value FROM cache WHERE key = ? AND expires_at > ?',
            (key, now)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存值"""
        if ttl is None:
            ttl = self.ttl
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = time.time()
        expires_at = now + ttl
        
        cursor.execute('''
            INSERT OR REPLACE INTO cache (key, value, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (key, json.dumps(value, default=str), now, expires_at))
        
        conn.commit()
        conn.close()
    
    def delete(self, key: str):
        """删除缓存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cache WHERE key = ?', (key,))
        conn.commit()
        conn.close()
    
    def clear_expired(self):
        """清除过期缓存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = time.time()
        cursor.execute('DELETE FROM cache WHERE expires_at <= ?', (now,))
        deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def clear_all(self):
        """清除所有缓存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cache')
        conn.commit()
        conn.close()
    
    def get_statistics(self) -> dict:
        """获取缓存统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = time.time()
        
        cursor.execute('SELECT COUNT(*) FROM cache')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM cache WHERE expires_at > ?', (now,))
        valid = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total": total,
            "valid": valid,
            "expired": total - valid
        }


cache_manager = CacheManager()


def cached(ttl: int = 3600):
    """缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = cache_manager._generate_key(func.__name__, args, kwargs)
            
            cached_value = cache_manager.get(key)
            if cached_value is not None:
                print(f"🔄 使用缓存: {func.__name__}")
                return cached_value
            
            result = func(*args, **kwargs)
            cache_manager.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator
