"""
日志系统模块
统一管理日志输出和格式
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色  
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 获取颜色
        color = self.COLORS.get(record.levelname, '')
        
        # 格式化时间
        record.asctime = self.formatTime(record, '%Y-%m-%d %H:%M:%S')
        
        # 应用颜色
        if color:
            record.levelname = f"{color}{record.levelname}{self.RESET}"
            record.name = f"{color}{record.name}{self.RESET}"
        
        return super().format(record)

def setup_logger(name: str, level: str = 'INFO', log_file: Optional[str] = None) -> logging.Logger:
    """
    设置并返回日志记录器
    
    Args:
        name: 记录器名称
        level: 日志级别
        log_file: 日志文件路径（可选）
    
    Returns:
        配置好的日志记录器
    """
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建格式化器
    formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了文件路径）
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str, level: str = 'INFO') -> logging.Logger:
    """
    获取日志记录器的便捷函数
    
    Args:
        name: 记录器名称
        level: 日志级别
    
    Returns:
        日志记录器
    """
    return setup_logger(name, level)
