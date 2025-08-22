"""
问答处理Cog
处理消息监听、关键词触发和自动回复功能
"""

import asyncio
import re
from typing import List, Optional, Set

import discord
from discord.ext import commands

from utils.logger import get_logger
from utils.message_formatter import EmbedFormatter
from database import database
from config import config

logger = get_logger(__name__)

class QAHandlerCog(commands.Cog, name="问答处理"):
    """问答处理功能模块"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_logger(self.__class__.__name__)
        
        # 避免重复处理的消息缓存
        self.processed_messages: Set[int] = set()
        self.cache_max_size = 1000
        
        # SillyTavern相关关键词模式（更精确的匹配）
        self.keyword_patterns = [
            r'sillytavern|silly\s*tavern',
            r'st\s+(?:error|错误|问题|bug)',
            r'(?:openai|claude|gemini).{0,10}(?:api|连接|error)',
            r'character\s+card|角色卡',
            r'chat\s+completion|聊天完成',
            r'connection\s+failed|连接失败',
            r'api\s+(?:key|error|问题)',
            r'context\s+(?:length|长度)|上下文',
            r'tavern.{0,20}(?:error|错误|问题)',
            r'(?:配置|setting|config).{0,10}(?:error|错误|问题)'
        ]
        
        # 编译正则表达式以提高性能
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.UNICODE)
            for pattern in self.keyword_patterns
        ]
        
        # 排除的消息类型
        self.exclude_patterns = [
            r'^\s*[!/@#$%^&*()]+',  # 以特殊符号开头
            r'^\s*(?:hi|hello|你好)\s*$',  # 简单问候
            r'^\s*(?:thanks|谢谢|thx)\s*$',  # 简单感谢
        ]
        
        self.exclude_compiled = [
            re.compile(pattern, re.IGNORECASE | re.UNICODE)
            for pattern in self.exclude_patterns
        ]
    
    async def cog_load(self):
        """Cog加载时的初始化"""
        self.logger.info("问答处理模块已加载")
        self.logger.info(f"监听关键词模式: {len(self.keyword_patterns)} 个")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """监听所有消息，处理关键词触发"""
        # 基础过滤
        if not await self._should_process_message(message):
            return
        
        # 检查是否包含SillyTavern相关关键词
        if await self._contains_trigger_keywords(message.content):
            await self._handle_keyword_trigger(message)
        
        # 检查是否有图片附件且提及了相关关键词
        if message.attachments and await self._should_analyze_image(message):
            await self._handle_image_trigger(message)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """处理编辑后的消息"""
        # 只处理新增的关键词触发
        if (not await self._contains_trigger_keywords(before.content) and 
            await self._contains_trigger_keywords(after.content)):
            await self.on_message(after)
    
    async def _should_process_message(self, message: discord.Message) -> bool:
        """判断是否应该处理这条消息"""
        # 忽略机器人消息
        if message.author.bot:
            return False
        
        # 忽略空消息
        if not message.content.strip() and not message.attachments:
            return False
        
        # 检查消息是否已经处理过
        if message.id in self.processed_messages:
            return False
        
        # 检查是否在监控的频道中
        if not config.should_monitor_channel(message.channel.id):
            return False
        
        # 检查功能是否启用
        if not config.AUTO_REPLY_ENABLED:
            return False
        
        # 避免处理命令消息
        if message.content.startswith(('/', '!', '?', '.')):
            return False
        
        return True
    
    async def _contains_trigger_keywords(self, text: str) -> bool:
        """检查文本是否包含触发关键词"""
        if not config.KEYWORD_TRIGGER_ENABLED or not text:
            return False
        
        # 排除不相关的消息
        for pattern in self.exclude_compiled:
            if pattern.search(text):
                return False
        
        # 检查SillyTavern相关关键词
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                return True
        
        return False
    
    async def _should_analyze_image(self, message: discord.Message) -> bool:
        """判断是否应该分析图片"""
        # 必须有图片附件
        if not message.attachments:
            return False
        
        # 检查附件是否为图片
        image_attachments = [
            att for att in message.attachments
            if att.content_type and att.content_type.startswith('image/')
        ]
        
        if not image_attachments:
            return False
        
        # 检查消息内容是否暗示需要帮助
        help_keywords = [
            r'help|帮助|求助',
            r'error|错误|报错|bug',
            r'problem|问题|issue',
            r'什么意思|怎么办|怎么解决',
            r'看看|分析|诊断'
        ]
        
        for keyword in help_keywords:
            if re.search(keyword, message.content, re.IGNORECASE):
                return True
        
        # 如果图片文件名包含相关关键词
        for att in image_attachments:
            if re.search(r'error|screenshot|config|设置|错误', att.filename, re.IGNORECASE):
                return True
        
        return False
    
    async def _handle_keyword_trigger(self, message: discord.Message):
        """处理关键词触发的自动回复"""
        try:
            # 标记消息为已处理
            await self._mark_message_processed(message.id)
            
            # 提取触发的关键词（用于日志）
            triggered_keyword = await self._extract_triggered_keyword(message.content)
            
            # 记录关键词触发事件
            await database.record_keyword_trigger(
                user_id=message.author.id,
                channel_id=message.channel.id,
                keyword=triggered_keyword,
                message_content=message.content[:500]  # 限制长度
            )
            
            # 获取AI集成Cog来处理问题
            ai_cog = self.bot.get_cog("AI集成")
            if ai_cog:
                await ai_cog._handle_question(
                    question=message.content,
                    user=message.author,
                    channel=message.channel,
                    message=message
                )
            else:
                self.logger.error("找不到AI集成模块")
                
                error_embed = EmbedFormatter.create_error_embed(
                    "AI集成模块未加载，无法处理您的问题。",
                    title="模块错误",
                    user_name=message.author.display_name
                )
                await message.reply(embed=error_embed)
            
            self.logger.info(
                f"关键词触发: 用户 {message.author.display_name} "
                f"在频道 {message.channel.name} 触发了关键词 '{triggered_keyword}'"
            )
            
        except Exception as e:
            self.logger.error(f"处理关键词触发时发生错误: {e}")
            await database.log_error(
                error_type="keyword_trigger",
                error_message=str(e),
                user_id=message.author.id,
                channel_id=message.channel.id
            )
    
    async def _handle_image_trigger(self, message: discord.Message):
        """处理图片分析触发"""
        try:
            # 标记消息为已处理
            await self._mark_message_processed(message.id)
            
            # 获取第一个图片附件
            image_attachment = None
            for att in message.attachments:
                if att.content_type and att.content_type.startswith('image/'):
                    image_attachment = att
                    break
            
            if not image_attachment:
                return
            
            # 获取AI集成Cog来处理图片分析
            ai_cog = self.bot.get_cog("AI集成")
            if ai_cog:
                await ai_cog._handle_image_analysis(
                    attachment=image_attachment,
                    description=message.content,
                    user=message.author,
                    channel=message.channel,
                    message=message
                )
            else:
                self.logger.error("找不到AI集成模块")
            
            self.logger.info(
                f"图片分析触发: 用户 {message.author.display_name} "
                f"在频道 {message.channel.name} 发送了需要分析的图片"
            )
            
        except Exception as e:
            self.logger.error(f"处理图片触发时发生错误: {e}")
            await database.log_error(
                error_type="image_trigger",
                error_message=str(e),
                user_id=message.author.id,
                channel_id=message.channel.id
            )
    
    async def _mark_message_processed(self, message_id: int):
        """标记消息为已处理"""
        self.processed_messages.add(message_id)
        
        # 限制缓存大小
        if len(self.processed_messages) > self.cache_max_size:
            # 移除最旧的一半消息ID
            to_remove = len(self.processed_messages) - self.cache_max_size // 2
            for _ in range(to_remove):
                self.processed_messages.pop()
    
    async def _extract_triggered_keyword(self, text: str) -> str:
        """提取触发的关键词"""
        for i, pattern in enumerate(self.compiled_patterns):
            match = pattern.search(text)
            if match:
                return match.group()
        return "unknown"
    
    @commands.command(name="toggle_auto_reply", hidden=True)
    @commands.has_permissions(administrator=True)
    async def toggle_auto_reply(self, ctx):
        """切换自动回复功能（管理员命令）"""
        config.AUTO_REPLY_ENABLED = not config.AUTO_REPLY_ENABLED
        status = "启用" if config.AUTO_REPLY_ENABLED else "禁用"
        
        embed = EmbedFormatter.create_success_embed(
            f"自动回复功能已{status}",
            user_name=ctx.author.display_name
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="toggle_keyword_trigger", hidden=True)
    @commands.has_permissions(administrator=True) 
    async def toggle_keyword_trigger(self, ctx):
        """切换关键词触发功能（管理员命令）"""
        config.KEYWORD_TRIGGER_ENABLED = not config.KEYWORD_TRIGGER_ENABLED
        status = "启用" if config.KEYWORD_TRIGGER_ENABLED else "禁用"
        
        embed = EmbedFormatter.create_success_embed(
            f"关键词触发功能已{status}",
            user_name=ctx.author.display_name
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="qa_stats", hidden=True)
    @commands.has_permissions(administrator=True)
    async def qa_stats(self, ctx):
        """显示问答统计信息（管理员命令）"""
        stats = await database.get_system_stats()
        
        embed = discord.Embed(
            title="📊 问答系统统计",
            color=EmbedFormatter.COLORS[EmbedFormatter.MessageType.INFO]
        )
        
        embed.add_field(name="总问题数", value=stats.get('total_questions', 0), inline=True)
        embed.add_field(name="今日问题", value=stats.get('today_questions', 0), inline=True)
        embed.add_field(name="活跃用户", value=stats.get('total_users', 0), inline=True)
        embed.add_field(name="图片分析", value=stats.get('total_images', 0), inline=True)
        
        avg_time = stats.get('avg_response_time', 0)
        embed.add_field(
            name="平均响应时间", 
            value=f"{avg_time:.2f}s", 
            inline=True
        )
        
        embed.add_field(
            name="缓存状态", 
            value=f"{len(self.processed_messages)}/{self.cache_max_size}", 
            inline=True
        )
        
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    """设置Cog"""
    await bot.add_cog(QAHandlerCog(bot))
