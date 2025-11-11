"""统一的错误处理和日志系统。

功能：
1. 结构化日志
2. 错误分类和处理
3. 性能监控
4. 用户友好的错误消息
"""

from __future__ import annotations

import sys
import logging
import traceback
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime
from enum import Enum


class ErrorCategory(Enum):
    """错误分类"""
    API_ERROR = "api_error"  # API 调用失败
    TOOL_ERROR = "tool_error"  # 工具执行错误
    VALIDATION_ERROR = "validation_error"  # 输入验证错误
    SYSTEM_ERROR = "system_error"  # 系统内部错误
    TIMEOUT_ERROR = "timeout_error"  # 超时错误
    CONFIGURATION_ERROR = "configuration_error"  # 配置错误


class MaxAIError(Exception):
    """基础异常类"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM_ERROR,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.user_message = user_message or self._generate_user_message()
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def _generate_user_message(self) -> str:
        """生成用户友好的错误消息"""
        category_messages = {
            ErrorCategory.API_ERROR: "外部服务调用失败，请稍后重试。",
            ErrorCategory.TOOL_ERROR: "工具执行出错，请检查输入参数。",
            ErrorCategory.VALIDATION_ERROR: "输入验证失败，请检查请求格式。",
            ErrorCategory.SYSTEM_ERROR: "系统内部错误，请联系管理员。",
            ErrorCategory.TIMEOUT_ERROR: "请求超时，请稍后重试。",
            ErrorCategory.CONFIGURATION_ERROR: "配置错误，请检查环境设置。",
        }
        return category_messages.get(self.category, "发生未知错误。")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error": True,
            "category": self.category.value,
            "message": self.user_message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


# 配置日志
def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """配置日志系统。
    
    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（可选）
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # 日志格式
    log_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)
    
    # 根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（可选）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(log_format)
        root_logger.addHandler(file_handler)
    
    # 禁用一些第三方库的日志
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取日志器。
    
    Args:
        name: 日志器名称（通常是模块名）
        
    Returns:
        日志器实例
    """
    return logging.getLogger(name)


def log_performance(func: Callable) -> Callable:
    """性能监控装饰器。
    
    记录函数执行时间和基本信息。
    """
    logger = get_logger(func.__module__)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        func_name = func.__name__
        
        logger.debug(f"开始执行: {func_name}")
        
        try:
            result = func(*args, **kwargs)
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.info(f"✅ {func_name} 完成 | 耗时: {elapsed_ms}ms")
            return result
            
        except Exception as e:
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"❌ {func_name} 失败 | 耗时: {elapsed_ms}ms | 错误: {e}")
            raise
    
    return wrapper


def handle_errors(
    default_category: ErrorCategory = ErrorCategory.SYSTEM_ERROR,
    user_message: Optional[str] = None
) -> Callable:
    """错误处理装饰器。
    
    捕获异常并转换为 MaxAIError。
    
    Args:
        default_category: 默认错误分类
        user_message: 自定义用户消息
    """
    def decorator(func: Callable) -> Callable:
        logger = get_logger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
                
            except MaxAIError:
                # 已经是 MaxAIError，直接抛出
                raise
                
            except TimeoutError as e:
                logger.error(f"超时错误: {e}")
                raise MaxAIError(
                    message=str(e),
                    category=ErrorCategory.TIMEOUT_ERROR,
                    user_message=user_message or "操作超时，请稍后重试。",
                    details={"original_error": str(e)}
                )
                
            except ValueError as e:
                logger.error(f"验证错误: {e}")
                raise MaxAIError(
                    message=str(e),
                    category=ErrorCategory.VALIDATION_ERROR,
                    user_message=user_message or "输入参数无效。",
                    details={"original_error": str(e)}
                )
                
            except Exception as e:
                logger.error(f"未预期的错误: {e}\n{traceback.format_exc()}")
                raise MaxAIError(
                    message=str(e),
                    category=default_category,
                    user_message=user_message,
                    details={
                        "original_error": str(e),
                        "error_type": type(e).__name__,
                        "traceback": traceback.format_exc()
                    }
                )
        
        return wrapper
    return decorator


def format_error_for_user(error: Exception) -> Dict[str, Any]:
    """将异常格式化为用户友好的错误响应。
    
    Args:
        error: 异常对象
        
    Returns:
        错误响应字典
    """
    if isinstance(error, MaxAIError):
        return error.to_dict()
    
    # 默认错误响应
    return {
        "error": True,
        "category": ErrorCategory.SYSTEM_ERROR.value,
        "message": "发生未知错误，请稍后重试。",
        "details": {
            "error_type": type(error).__name__,
            "error_message": str(error)
        },
        "timestamp": datetime.now().isoformat()
    }


def safe_execute(
    func: Callable,
    *args,
    default_return: Any = None,
    log_error: bool = True,
    **kwargs
) -> Any:
    """安全执行函数，捕获所有异常。
    
    Args:
        func: 要执行的函数
        *args: 位置参数
        default_return: 发生错误时的默认返回值
        log_error: 是否记录错误日志
        **kwargs: 关键字参数
        
    Returns:
        函数返回值或默认值
    """
    logger = get_logger(func.__module__)
    
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.error(f"执行 {func.__name__} 失败: {e}")
        return default_return


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(__name__)
        self.start_time: Optional[datetime] = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"⏱️ {self.name} 开始")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            elapsed_ms = int((datetime.now() - self.start_time).total_seconds() * 1000)
            
            if exc_type:
                self.logger.warning(f"❌ {self.name} 失败 | 耗时: {elapsed_ms}ms")
            else:
                self.logger.info(f"✅ {self.name} 完成 | 耗时: {elapsed_ms}ms")


# ===== 从 error_handler.py 迁移的功能 =====

def classify_error(error: Exception) -> ErrorCategory:
    """分类错误类型（兼容旧接口）"""
    error_msg = str(error).lower()
    error_type_name = type(error).__name__.lower()
    
    if "timeout" in error_msg or "timeout" in error_type_name:
        return ErrorCategory.TIMEOUT_ERROR
    elif "rate" in error_msg or "429" in error_msg:
        return ErrorCategory.API_ERROR
    elif "auth" in error_msg or "401" in error_msg or "403" in error_msg:
        return ErrorCategory.CONFIGURATION_ERROR
    elif "connection" in error_msg or "network" in error_msg:
        return ErrorCategory.API_ERROR
    elif "invalid" in error_msg or "validation" in error_msg:
        return ErrorCategory.VALIDATION_ERROR
    else:
        return ErrorCategory.SYSTEM_ERROR


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """带退避的重试装饰器"""
    import time
    
    def decorator(func: Callable) -> Callable:
        logger = get_logger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    error_category = classify_error(e)
                    
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ 第 {attempt + 1} 次尝试失败: {e}")
                        logger.info(f"🔄 {delay:.1f} 秒后重试...")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"❌ 所有重试均失败")
            
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


def with_fallback(fallback_func: Optional[Callable] = None, default_value: Any = None):
    """带降级方案的装饰器"""
    def decorator(func: Callable) -> Callable:
        logger = get_logger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_category = classify_error(e)
                logger.warning(f"⚠️ 主方案失败: {e}")
                
                if fallback_func:
                    logger.info(f"🔄 启用降级方案...")
                    try:
                        return fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"❌ 降级方案也失败: {str(fallback_error)}")
                
                if default_value is not None:
                    logger.info(f"📦 返回默认值")
                    return default_value
                
                raise
        
        return wrapper
    return decorator


# 兼容旧接口：ErrorType 作为 ErrorCategory 的别名
ErrorType = ErrorCategory


# 初始化日志系统
setup_logging(level="INFO")
