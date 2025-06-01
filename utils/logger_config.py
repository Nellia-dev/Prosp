"""
Logger configuration for Nellia Prospector
Centralized logging setup with file rotation, structured logging, and performance tracking.
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger
import json
from datetime import datetime

class NelliaLogger:
    """Enhanced logger for Nellia Prospector with performance tracking"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.performance_data = {}
        self._setup_logger()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default logging configuration"""
        return {
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "log_to_file": os.getenv("LOG_TO_FILE", "true").lower() == "true",
            "log_file_path": os.getenv("LOG_FILE_PATH", "logs/nellia_prospector.log"),
            "enable_rich": True,
            "max_file_size": "10 MB",
            "retention_days": 30,
            "enable_json": False,
            "enable_performance_tracking": True
        }
    
    def _setup_logger(self):
        """Setup logger with configuration"""
        # Remove default handler
        logger.remove()
        
        # Create logs directory if it doesn't exist
        log_file_path = Path(self.config["log_file_path"])
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Console handler with colors
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        
        if self.config.get("enable_rich", True):
            logger.add(
                sys.stdout,
                format=console_format,
                level=self.config["level"],
                colorize=True,
                filter=self._should_log_to_console
            )
        else:
            simple_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"
            logger.add(
                sys.stdout,
                format=simple_format,
                level=self.config["level"],
                colorize=False,
                filter=self._should_log_to_console
            )
        
        # File handler
        if self.config.get("log_to_file", True):
            file_format = (
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}"
            )
            
            logger.add(
                self.config["log_file_path"],
                format=file_format,
                level=self.config["level"],
                rotation=self.config.get("max_file_size", "10 MB"),
                retention=f"{self.config.get('retention_days', 30)} days",
                encoding="utf-8",
                enqueue=True  # Thread-safe logging
            )
        
        # JSON file handler for structured logging
        if self.config.get("enable_json", False):
            json_log_path = str(log_file_path).replace('.log', '_structured.json')
            logger.add(
                json_log_path,
                format=self._json_formatter,
                level=self.config["level"],
                rotation=self.config.get("max_file_size", "10 MB"),
                retention=f"{self.config.get('retention_days', 30)} days",
                encoding="utf-8",
                serialize=True
            )
        
        # Performance log handler
        if self.config.get("enable_performance_tracking", True):
            perf_log_path = str(log_file_path).replace('.log', '_performance.log')
            logger.add(
                perf_log_path,
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | PERF | {message}",
                level="INFO",
                rotation="1 day",
                retention="7 days",
                filter=lambda record: record["extra"].get("performance", False)
            )
    
    def _should_log_to_console(self, record) -> bool:
        """Filter function to determine if message should go to console"""
        # Don't log performance data to console by default
        if record["extra"].get("performance", False):
            return False
        
        # In development mode, log more to console
        if os.getenv("DEVELOPMENT_MODE", "false").lower() == "true":
            return True
        
        # In production, limit console output
        return record["level"].no >= logger.level(self.config["level"]).no
    
    def _json_formatter(self, record) -> str:
        """Format log records as JSON"""
        log_entry = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "logger": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
            "module": record["module"],
            "thread": record["thread"].name if record["thread"] else None,
            "process": record["process"].name if record["process"] else None
        }
        
        # Add extra fields
        if record["extra"]:
            log_entry["extra"] = record["extra"]
        
        # Add exception info if present
        if record["exception"]:
            log_entry["exception"] = {
                "type": record["exception"].type.__name__ if record["exception"].type else None,
                "value": str(record["exception"].value) if record["exception"].value else None,
                "traceback": record["exception"].traceback if record["exception"].traceback else None
            }
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)
    
    def log_performance(self, operation: str, duration: float, **kwargs):
        """Log performance data"""
        if not self.config.get("enable_performance_tracking", True):
            return
        
        perf_data = {
            "operation": operation,
            "duration_seconds": round(duration, 4),
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        
        # Store in memory for aggregation
        if operation not in self.performance_data:
            self.performance_data[operation] = []
        
        self.performance_data[operation].append(duration)
        
        # Log to file
        logger.bind(performance=True).info(
            f"PERFORMANCE: {operation} took {duration:.4f}s",
            **perf_data
        )
    
    def log_agent_performance(self, agent_name: str, operation: str, duration: float, 
                            success: bool = True, **kwargs):
        """Log agent-specific performance"""
        self.log_performance(
            f"agent_{agent_name}_{operation}",
            duration,
            agent=agent_name,
            success=success,
            **kwargs
        )
    
    def log_llm_usage(self, provider: str, model: str, tokens_used: int, 
                     duration: float, **kwargs):
        """Log LLM API usage"""
        self.log_performance(
            "llm_api_call",
            duration,
            provider=provider,
            model=model,
            tokens_used=tokens_used,
            **kwargs
        )
    
    def log_batch_processing(self, batch_size: int, duration: float, 
                           success_count: int, error_count: int):
        """Log batch processing metrics"""
        self.log_performance(
            "batch_processing",
            duration,
            batch_size=batch_size,
            success_count=success_count,
            error_count=error_count,
            success_rate=success_count / batch_size if batch_size > 0 else 0
        )
    
    def get_performance_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics"""
        if operation and operation in self.performance_data:
            durations = self.performance_data[operation]
            return {
                "operation": operation,
                "count": len(durations),
                "total_time": sum(durations),
                "average_time": sum(durations) / len(durations),
                "min_time": min(durations),
                "max_time": max(durations)
            }
        
        # Return stats for all operations
        stats = {}
        for op, durations in self.performance_data.items():
            stats[op] = {
                "count": len(durations),
                "total_time": round(sum(durations), 4),
                "average_time": round(sum(durations) / len(durations), 4),
                "min_time": round(min(durations), 4),
                "max_time": round(max(durations), 4)
            }
        
        return stats
    
    def log_system_info(self):
        """Log system information"""
        import platform
        import psutil
        
        system_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "memory_total": f"{psutil.virtual_memory().total / (1024**3):.2f} GB",
            "memory_available": f"{psutil.virtual_memory().available / (1024**3):.2f} GB"
        }
        
        logger.info("System Information", **system_info)
    
    def create_context_logger(self, context: str) -> "ContextLogger":
        """Create a logger with context"""
        return ContextLogger(context, self)


class ContextLogger:
    """Logger with additional context"""
    
    def __init__(self, context: str, parent_logger: NelliaLogger):
        self.context = context
        self.parent = parent_logger
        self.context_logger = logger.bind(context=context)
    
    def info(self, message: str, **kwargs):
        self.context_logger.info(f"[{self.context}] {message}", **kwargs)
    
    def debug(self, message: str, **kwargs):
        self.context_logger.debug(f"[{self.context}] {message}", **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.context_logger.warning(f"[{self.context}] {message}", **kwargs)
    
    def error(self, message: str, **kwargs):
        self.context_logger.error(f"[{self.context}] {message}", **kwargs)
    
    def critical(self, message: str, **kwargs):
        self.context_logger.critical(f"[{self.context}] {message}", **kwargs)
    
    def exception(self, message: str, **kwargs):
        self.context_logger.exception(f"[{self.context}] {message}", **kwargs)
    
    def log_performance(self, operation: str, duration: float, **kwargs):
        self.parent.log_performance(f"{self.context}_{operation}", duration, **kwargs)


# Global logger instance
_logger_instance: Optional[NelliaLogger] = None

def setup_logging(config: Optional[Dict[str, Any]] = None) -> NelliaLogger:
    """Setup global logging configuration"""
    global _logger_instance
    _logger_instance = NelliaLogger(config)
    return _logger_instance

def get_logger() -> NelliaLogger:
    """Get the global logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = NelliaLogger()
    return _logger_instance

def get_context_logger(context: str) -> ContextLogger:
    """Get a logger with context"""
    return get_logger().create_context_logger(context)

# Performance tracking decorators
import functools
import time

def track_performance(operation_name: Optional[str] = None):
    """Decorator to track function performance"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                get_logger().log_performance(op_name, duration, success=True)
                return result
            except Exception as e:
                duration = time.time() - start_time
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                get_logger().log_performance(op_name, duration, success=False, error=str(e))
                raise
        return wrapper
    return decorator

def track_agent_performance(agent_name: str, operation: str):
    """Decorator to track agent performance"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                get_logger().log_agent_performance(agent_name, operation, duration, success=True)
                return result
            except Exception as e:
                duration = time.time() - start_time
                get_logger().log_agent_performance(agent_name, operation, duration, success=False, error=str(e))
                raise
        return wrapper
    return decorator

# Convenience functions
def log_info(message: str, **kwargs):
    """Log info message"""
    logger.info(message, **kwargs)

def log_debug(message: str, **kwargs):
    """Log debug message"""
    logger.debug(message, **kwargs)

def log_warning(message: str, **kwargs):
    """Log warning message"""
    logger.warning(message, **kwargs)

def log_error(message: str, **kwargs):
    """Log error message"""
    logger.error(message, **kwargs)

def log_critical(message: str, **kwargs):
    """Log critical message"""
    logger.critical(message, **kwargs)

def log_exception(message: str, **kwargs):
    """Log exception with traceback"""
    logger.exception(message, **kwargs)
