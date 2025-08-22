"""
配置管理模块
统一管理所有配置选项
"""

import os
import logging
from typing import List, Optional
from dotenv import load_dotenv

class Config:
    """配置管理类"""
    
    def __init__(self):
        # 加载环境变量
        load_dotenv()
        
        # Discord配置
        self.DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
        if not self.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN 未设置，请在.env文件中配置")
        
        # Gemini AI配置
        self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
        self.GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')
        
        # 自定义API配置 (可选，用于OpenAI兼容接口)
        self.CUSTOM_API_ENDPOINT = os.getenv('CUSTOM_API_ENDPOINT')
        self.CUSTOM_API_KEY = os.getenv('CUSTOM_API_KEY')
        self.CUSTOM_API_MODEL = os.getenv('CUSTOM_API_MODEL', 'gpt-4o-mini')  # 默认模型
        
        # 管理员配置
        admin_users_str = os.getenv('ADMIN_USERS', '')
        self.ADMIN_USERS = [int(uid.strip()) for uid in admin_users_str.split(',') if uid.strip().isdigit()]
        
        # 频道配置
        monitor_channels_str = os.getenv('MONITOR_CHANNELS', '')
        self.MONITOR_CHANNELS = [int(cid.strip()) for cid in monitor_channels_str.split(',') if cid.strip().isdigit()]
        
        # 机器人设置
        self.BOT_PREFIX = os.getenv('BOT_PREFIX', '/')
        self.AUTO_REPLY_ENABLED = os.getenv('AUTO_REPLY_ENABLED', 'true').lower() == 'true'
        self.KEYWORD_TRIGGER_ENABLED = os.getenv('KEYWORD_TRIGGER_ENABLED', 'true').lower() == 'true'
        
        # 日志配置
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        # 数据库配置
        self.DATABASE_PATH = os.getenv('DATABASE_PATH', 'qa_bot.db')
        
        # SillyTavern相关关键词
        self.SILLYTAVERN_KEYWORDS = [
            'sillytavern', 'silly tavern', 'st',
            'character card', '角色卡', 'tavern',
            'chat completion', 'api error',
            '连接失败', '无法连接', 'connection failed',
            'openai', 'claude', 'gemini', 
            'token', 'context', '上下文',
            'error', '错误', '报错', 'bug',
            'config', 'setting', '配置', '设置'
        ]
        
        # AI请求限制
        self.MAX_TOKENS = 4000
        self.TEMPERATURE = 0.7
        self.REQUEST_TIMEOUT = 30
        
    def is_admin_user(self, user_id: int) -> bool:
        """检查用户是否为管理员"""
        return user_id in self.ADMIN_USERS
    
    def should_monitor_channel(self, channel_id: int) -> bool:
        """检查是否应该监听指定频道"""
        if not self.MONITOR_CHANNELS:  # 空列表表示监听所有频道
            return True
        return channel_id in self.MONITOR_CHANNELS
    
    def contains_trigger_keyword(self, text: str) -> bool:
        """检查文本是否包含触发关键词"""
        if not self.KEYWORD_TRIGGER_ENABLED:
            return False
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.SILLYTAVERN_KEYWORDS)

# 全局配置实例
config = Config()
