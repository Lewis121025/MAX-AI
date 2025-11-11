"""简单的性能和日志监控工具"""
import time
import functools
from datetime import datetime
from typing import Any, Callable
import logging

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """简单的性能监控器"""
    
    def __init__(self):
        self.metrics = {}
    
    def record(self, name: str, duration: float, success: bool = True):
        """记录一次操作"""
        if name not in self.metrics:
            self.metrics[name] = {
                'count': 0,
                'total_time': 0,
                'success': 0,
                'failure': 0,
                'min_time': float('inf'),
                'max_time': 0
            }
        
        m = self.metrics[name]
        m['count'] += 1
        m['total_time'] += duration
        m['min_time'] = min(m['min_time'], duration)
        m['max_time'] = max(m['max_time'], duration)
        
        if success:
            m['success'] += 1
        else:
            m['failure'] += 1
    
    def get_stats(self, name: str = None) -> dict:
        """获取统计信息"""
        if name:
            if name not in self.metrics:
                return {}
            m = self.metrics[name]
            return {
                'count': m['count'],
                'avg_time': m['total_time'] / m['count'] if m['count'] > 0 else 0,
                'min_time': m['min_time'] if m['min_time'] != float('inf') else 0,
                'max_time': m['max_time'],
                'success_rate': m['success'] / m['count'] * 100 if m['count'] > 0 else 0
            }
        else:
            return {k: self.get_stats(k) for k in self.metrics.keys()}
    
    def print_stats(self):
        """打印统计信息"""
        print("\n" + "=" * 70)
        print("📊 性能统计")
        print("=" * 70)
        
        for name, stats in self.get_stats().items():
            print(f"\n🔧 {name}")
            print(f"  调用次数: {stats['count']}")
            print(f"  平均耗时: {stats['avg_time']:.3f}s")
            print(f"  最小耗时: {stats['min_time']:.3f}s")
            print(f"  最大耗时: {stats['max_time']:.3f}s")
            print(f"  成功率: {stats['success_rate']:.1f}%")
        
        print("=" * 70)


# 全局监控器
monitor = PerformanceMonitor()


def track_performance(name: str = None):
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        func_name = name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            result = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                logger.error(f"❌ {func_name} 执行失败: {e}", exc_info=True)
                raise
            finally:
                duration = time.time() - start_time
                monitor.record(func_name, duration, success)
                
                if success:
                    logger.info(f"✅ {func_name} 完成 ({duration:.3f}s)")
                else:
                    logger.error(f"❌ {func_name} 失败 ({duration:.3f}s)")
        
        return wrapper
    return decorator


def log_event(level: str, message: str, **context):
    """记录事件日志"""
    log_func = getattr(logger, level.lower(), logger.info)
    
    # 格式化上下文
    context_str = " | ".join(f"{k}={v}" for k, v in context.items())
    full_message = f"{message} | {context_str}" if context else message
    
    log_func(full_message)


# 使用示例
if __name__ == "__main__":
    import random
    
    @track_performance("test_function")
    def test_function(duration: float):
        time.sleep(duration)
        if random.random() < 0.1:  # 10% 失败率
            raise Exception("随机失败")
        return "success"
    
    # 模拟一些调用
    print("🧪 运行性能测试...")
    for _ in range(10):
        try:
            test_function(random.uniform(0.1, 0.5))
        except:
            pass
    
    # 打印统计
    monitor.print_stats()
