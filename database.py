"""
数据库管理模块
管理问答记录、用户统计和知识库数据
"""

import sqlite3
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path

from utils.logger import get_logger
from config import config

logger = get_logger(__name__)

class Database:
    """异步数据库管理类"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DATABASE_PATH
        self._ensure_db_directory()
    
    def _ensure_db_directory(self):
        """确保数据库目录存在"""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """初始化数据库表结构"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 问答记录表
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS qa_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        user_name TEXT NOT NULL,
                        channel_id INTEGER NOT NULL,
                        guild_id INTEGER,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        has_image BOOLEAN DEFAULT FALSE,
                        response_time REAL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 用户统计表
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS user_stats (
                        user_id INTEGER PRIMARY KEY,
                        user_name TEXT NOT NULL,
                        total_questions INTEGER DEFAULT 0,
                        total_images INTEGER DEFAULT 0,
                        avg_response_time REAL DEFAULT 0,
                        first_question_at DATETIME,
                        last_question_at DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 关键词触发记录表
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS keyword_triggers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        channel_id INTEGER NOT NULL,
                        keyword TEXT NOT NULL,
                        message_content TEXT NOT NULL,
                        triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 错误日志表
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS error_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        error_type TEXT NOT NULL,
                        error_message TEXT NOT NULL,
                        user_id INTEGER,
                        channel_id INTEGER,
                        traceback TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 知识库表
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_base (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        keyword TEXT NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        tags TEXT,
                        priority INTEGER DEFAULT 1,
                        usage_count INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 创建索引
                await db.execute("CREATE INDEX IF NOT EXISTS idx_qa_user_id ON qa_records(user_id)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_qa_created_at ON qa_records(created_at)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_kb_keyword ON knowledge_base(keyword)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_kb_category ON knowledge_base(category)")
                
                await db.commit()
                logger.info("数据库初始化完成")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    async def record_qa(
        self,
        user_id: int,
        user_name: str,
        channel_id: int,
        guild_id: Optional[int],
        question: str,
        answer: str,
        has_image: bool = False,
        response_time: float = None
    ) -> int:
        """
        记录问答会话
        
        Returns:
            新记录的ID
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO qa_records (
                        user_id, user_name, channel_id, guild_id, 
                        question, answer, has_image, response_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, user_name, channel_id, guild_id,
                    question, answer, has_image, response_time
                ))
                
                record_id = cursor.lastrowid
                await db.commit()
                
                # 更新用户统计
                await self._update_user_stats(user_id, user_name, has_image, response_time)
                
                logger.info(f"问答记录已保存，ID: {record_id}")
                return record_id
                
        except Exception as e:
            logger.error(f"保存问答记录失败: {e}")
            raise
    
    async def _update_user_stats(
        self,
        user_id: int,
        user_name: str,
        has_image: bool = False,
        response_time: float = None
    ):
        """更新用户统计信息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 检查用户是否存在
                cursor = await db.execute(
                    "SELECT total_questions, total_images, avg_response_time FROM user_stats WHERE user_id = ?",
                    (user_id,)
                )
                result = await cursor.fetchone()
                
                now = datetime.now()
                
                if result:
                    # 更新现有记录
                    total_questions, total_images, avg_response_time = result
                    new_total_questions = total_questions + 1
                    new_total_images = total_images + (1 if has_image else 0)
                    
                    # 计算新的平均响应时间
                    if response_time and avg_response_time:
                        new_avg_response_time = (avg_response_time * total_questions + response_time) / new_total_questions
                    else:
                        new_avg_response_time = response_time or avg_response_time
                    
                    await db.execute("""
                        UPDATE user_stats SET
                            user_name = ?, total_questions = ?, total_images = ?,
                            avg_response_time = ?, last_question_at = ?, updated_at = ?
                        WHERE user_id = ?
                    """, (
                        user_name, new_total_questions, new_total_images,
                        new_avg_response_time, now, now, user_id
                    ))
                else:
                    # 插入新记录
                    await db.execute("""
                        INSERT INTO user_stats (
                            user_id, user_name, total_questions, total_images,
                            avg_response_time, first_question_at, last_question_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_id, user_name, 1, 1 if has_image else 0,
                        response_time or 0, now, now
                    ))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"更新用户统计失败: {e}")
    
    async def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户统计信息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT user_name, total_questions, total_images, avg_response_time,
                           first_question_at, last_question_at
                    FROM user_stats WHERE user_id = ?
                """, (user_id,))
                
                result = await cursor.fetchone()
                if result:
                    return {
                        'user_name': result[0],
                        'total_questions': result[1],
                        'total_images': result[2],
                        'avg_response_time': result[3],
                        'first_question_at': result[4],
                        'last_question_at': result[5]
                    }
                return None
                
        except Exception as e:
            logger.error(f"获取用户统计失败: {e}")
            return None
    
    async def get_recent_questions(
        self,
        limit: int = 10,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """获取最近的问题记录"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT user_name, question, answer, has_image, response_time, created_at
                    FROM qa_records 
                    WHERE created_at >= ?
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (since, limit))
                
                results = await cursor.fetchall()
                return [
                    {
                        'user_name': row[0],
                        'question': row[1],
                        'answer': row[2],
                        'has_image': bool(row[3]),
                        'response_time': row[4],
                        'created_at': row[5]
                    }
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"获取最近问题失败: {e}")
            return []
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 总问题数
                cursor = await db.execute("SELECT COUNT(*) FROM qa_records")
                total_questions = (await cursor.fetchone())[0]
                
                # 今日问题数
                today = datetime.now().date()
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM qa_records WHERE DATE(created_at) = ?",
                    (today,)
                )
                today_questions = (await cursor.fetchone())[0]
                
                # 活跃用户数
                cursor = await db.execute("SELECT COUNT(*) FROM user_stats")
                total_users = (await cursor.fetchone())[0]
                
                # 平均响应时间
                cursor = await db.execute(
                    "SELECT AVG(response_time) FROM qa_records WHERE response_time IS NOT NULL"
                )
                avg_response_time = (await cursor.fetchone())[0] or 0
                
                # 图像分析数量
                cursor = await db.execute("SELECT COUNT(*) FROM qa_records WHERE has_image = TRUE")
                total_images = (await cursor.fetchone())[0]
                
                return {
                    'total_questions': total_questions,
                    'today_questions': today_questions,
                    'total_users': total_users,
                    'avg_response_time': avg_response_time,
                    'total_images': total_images
                }
                
        except Exception as e:
            logger.error(f"获取系统统计失败: {e}")
            return {}
    
    async def record_keyword_trigger(
        self,
        user_id: int,
        channel_id: int,
        keyword: str,
        message_content: str
    ):
        """记录关键词触发事件"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO keyword_triggers (user_id, channel_id, keyword, message_content)
                    VALUES (?, ?, ?, ?)
                """, (user_id, channel_id, keyword, message_content))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"记录关键词触发失败: {e}")
    
    async def log_error(
        self,
        error_type: str,
        error_message: str,
        user_id: int = None,
        channel_id: int = None,
        traceback: str = None
    ):
        """记录错误日志"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO error_logs (error_type, error_message, user_id, channel_id, traceback)
                    VALUES (?, ?, ?, ?, ?)
                """, (error_type, error_message, user_id, channel_id, traceback))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"记录错误日志失败: {e}")
    
    async def cleanup_old_records(self, days: int = 30):
        """清理旧记录"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            async with aiosqlite.connect(self.db_path) as db:
                # 清理旧的问答记录
                cursor = await db.execute(
                    "DELETE FROM qa_records WHERE created_at < ?",
                    (cutoff_date,)
                )
                deleted_qa = cursor.rowcount
                
                # 清理旧的关键词触发记录
                cursor = await db.execute(
                    "DELETE FROM keyword_triggers WHERE triggered_at < ?",
                    (cutoff_date,)
                )
                deleted_triggers = cursor.rowcount
                
                # 清理旧的错误日志
                cursor = await db.execute(
                    "DELETE FROM error_logs WHERE created_at < ?",
                    (cutoff_date,)
                )
                deleted_errors = cursor.rowcount
                
                await db.commit()
                
                logger.info(
                    f"清理完成: 删除了 {deleted_qa} 个问答记录, "
                    f"{deleted_triggers} 个触发记录, {deleted_errors} 个错误日志"
                )
                
        except Exception as e:
            logger.error(f"清理旧记录失败: {e}")

# 全局数据库实例
database = Database()
