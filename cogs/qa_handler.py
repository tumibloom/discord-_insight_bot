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
        
        # 内置的默认关键词模式（基础模式，不可删除）
        self.default_keyword_patterns = [
            r'sillytavern',
            r'silly\s*tavern', 
            r'st\s+(error|错误|问题|bug|报错)',
            r'tavern.*(error|错误|问题|报错|bug)',
            r'(openai|claude|gemini).*(api|连接|error|错误|key)',
            r'character\s*card',
            r'角色卡',
            r'chat\s*completion',
            r'聊天完成',
            r'connection\s*failed',
            r'连接失败',
            r'api\s*(key|error|错误|问题)',
            r'context.*length',
            r'上下文.*长度',
            r'(配置|setting|config).*(error|错误|问题)',
            # 添加一些测试用的简单关键词
            r'\bst\b',  # 单独的 "st"
            r'测试机器人',
            r'help.*sillytavern',
            r'sillytavern.*help'
        ]
        
        # 动态关键词模式（从数据库加载）
        self.dynamic_keyword_patterns = []
        
        # 合并的关键词模式
        self.keyword_patterns = self.default_keyword_patterns.copy()
        
        # 编译正则表达式以提高性能
        self.compiled_patterns = []
        
        # 加载动态关键词（异步任务）
        asyncio.create_task(self._load_dynamic_keywords())
        
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
        # 确保动态关键词已加载
        await self._load_dynamic_keywords()
        self.logger.info("问答处理模块已加载")
        self.logger.info(f"监听关键词模式: {len(self.keyword_patterns)} 个 (默认: {len(self.default_keyword_patterns)}, 动态: {len(self.dynamic_keyword_patterns)})")
    
    async def _load_dynamic_keywords(self):
        """从数据库加载动态关键词"""
        try:
            # 导入database模块以避免循环导入
            from database import database
            
            # 获取启用的动态关键词
            dynamic_keywords = await database.get_regex_keywords(enabled_only=True)
            self.dynamic_keyword_patterns = [kw['pattern'] for kw in dynamic_keywords]
            
            # 合并关键词
            self.keyword_patterns = self.default_keyword_patterns + self.dynamic_keyword_patterns
            
            # 重新编译正则表达式
            self.compiled_patterns = [
                re.compile(pattern, re.IGNORECASE | re.UNICODE)
                for pattern in self.keyword_patterns
            ]
            
            self.logger.info(f"加载了 {len(self.dynamic_keyword_patterns)} 个动态关键词")
            
        except Exception as e:
            self.logger.error(f"加载动态关键词失败: {e}")
            # 如果加载失败，至少确保默认关键词可用
            self.keyword_patterns = self.default_keyword_patterns.copy()
            self.compiled_patterns = [
                re.compile(pattern, re.IGNORECASE | re.UNICODE)
                for pattern in self.keyword_patterns
            ]
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """监听所有消息，处理关键词触发"""
        # 调试日志：记录收到的消息
        if not message.author.bot and message.content.strip():
            self.logger.debug(f"收到消息: {message.author.display_name} 在频道 {message.channel.id}: {message.content[:100]}")
        
        # 基础过滤
        if not await self._should_process_message(message):
            # 调试日志：记录为什么被过滤
            if not message.author.bot and message.content.strip():
                should_monitor = config.should_monitor_channel(message.channel.id)
                self.logger.debug(f"消息被过滤 - 频道监控: {should_monitor}, AUTO_REPLY: {config.AUTO_REPLY_ENABLED}")
            return
        
        # 检查是否包含SillyTavern相关关键词
        if await self._contains_trigger_keywords(message.content):
            self.logger.info(f"检测到关键词触发: {message.author.display_name} - {message.content[:50]}...")
            await self._handle_keyword_trigger(message)
        
        # 检查是否有图片附件且提及了相关关键词
        if message.attachments and await self._should_analyze_image(message):
            self.logger.info(f"检测到图片分析触发: {message.author.display_name}")
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
        for i, pattern in enumerate(self.compiled_patterns):
            if pattern.search(text):
                # 如果是动态关键词，记录触发次数
                if i >= len(self.default_keyword_patterns):
                    dynamic_pattern = self.keyword_patterns[i]
                    asyncio.create_task(self._increment_keyword_trigger(dynamic_pattern))
                return True

        return False
    
    async def _increment_keyword_trigger(self, pattern: str):
        """增加关键词触发计数（异步）"""
        try:
            from database import database
            await database.increment_keyword_trigger(pattern)
        except Exception as e:
            self.logger.error(f"更新关键词触发计数失败: {e}")
    
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
            
            # 检查消息是否包含图片附件
            image_attachment = None
            for att in message.attachments:
                if att.content_type and att.content_type.startswith('image/'):
                    image_attachment = att
                    break
            
            # 如果有图片附件，优先进行图片分析
            if image_attachment:
                # 先发送图片分析占位消息
                placeholder_embed = EmbedFormatter.create_thinking_embed(message.author.display_name)
                placeholder_embed.add_field(
                    name="🔔 图片+文本分析中",
                    value="检测到您的问题包含图片，正在进行综合分析，请稍候...",
                    inline=False
                )
                
                placeholder_msg = await message.reply(embed=placeholder_embed)
                self.logger.info(f"✅ 已发送图片分析占位消息，消息ID: {placeholder_msg.id}")
                
                # 记录关键词触发事件（图片类型）
                await database.record_keyword_trigger(
                    user_id=message.author.id,
                    channel_id=message.channel.id,
                    keyword=f"{triggered_keyword} (with image)",
                    message_content=message.content[:500]  # 限制长度
                )
                
                # 获取AI集成Cog来处理图片分析
                ai_cog = self.bot.get_cog("AI集成")
                if ai_cog:
                    await ai_cog._handle_image_analysis(
                        attachment=image_attachment,
                        description=message.content,
                        user=message.author,
                        channel=message.channel,
                        message=message,
                        placeholder_message=placeholder_msg  # 传递占位消息
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
                    f"关键词+图片触发: 用户 {message.author.display_name} "
                    f"在频道 {message.channel.name} 触发了关键词 '{triggered_keyword}' (包含图片)"
                )
                
            else:
                # 没有图片，进行普通文本问答
                # 先发送占位消息
                placeholder_embed = EmbedFormatter.create_thinking_embed(message.author.display_name)
                placeholder_embed.add_field(
                    name="  🔁正在处理中",
                    value="检测到您的问题，正在调用AI分析，请稍候...",
                    inline=False
                )
                
                placeholder_msg = await message.reply(embed=placeholder_embed)
                self.logger.info(f"✅ 已发送占位消息，消息ID: {placeholder_msg.id}")
                
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
                        message=message,
                        placeholder_message=placeholder_msg  # 传递占位消息
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
            
            # 先发送占位消息
            placeholder_embed = EmbedFormatter.create_thinking_embed(message.author.display_name)
            placeholder_embed.add_field(
                name="📸 图片分析中",
                value="正在分析您上传的图片，请稍候...",
                inline=False
            )
            
            placeholder_msg = await message.reply(embed=placeholder_embed)
            
            # 获取AI集成Cog来处理图片分析
            ai_cog = self.bot.get_cog("AI集成")
            if ai_cog:
                await ai_cog._handle_image_analysis(
                    attachment=image_attachment,
                    description=message.content,
                    user=message.author,
                    channel=message.channel,
                    message=message,
                    placeholder_message=placeholder_msg  # 传递占位消息
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
        await ctx.send(embed=embed, ephemeral=True)
    
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
        await ctx.send(embed=embed, ephemeral=True)
    
    @commands.command(name="qa_stats", hidden=True)
    @commands.has_permissions(administrator=True)
    async def qa_stats(self, ctx):
        """显示问答统计信息（管理员命令）"""
        from utils.message_formatter import MessageType
        stats = await database.get_system_stats()
        
        embed = discord.Embed(
            title="📊 问答系统统计",
            color=EmbedFormatter.COLORS[MessageType.INFO]
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
        
        await ctx.send(embed=embed, ephemeral=True)
    
    # ==================== 动态关键词管理命令 ====================
    
    @discord.app_commands.command(name="keyword-add", description="添加新的正则关键词（管理员）")
    @commands.has_permissions(administrator=True) 
    @discord.app_commands.describe(
        pattern="正则表达式模式",
        description="关键词描述（可选）"
    )
    async def add_keyword_cmd(self, interaction: discord.Interaction, pattern: str, description: str = None):
        """添加新的正则关键词"""
        # 检查权限
        if not interaction.user.guild_permissions.manage_messages:
            embed = EmbedFormatter.create_error_embed(
                "权限不足",
                "需要管理消息权限才能使用此命令。",
                user_name=interaction.user.display_name
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 验证正则表达式
        try:
            re.compile(pattern, re.IGNORECASE | re.UNICODE)
        except re.error as e:
            embed = EmbedFormatter.create_error_embed(
                "正则表达式无效",
                f"错误：{e}",
                user_name=interaction.user.display_name
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 添加到数据库
        from database import database
        success = await database.add_regex_keyword(pattern, description, interaction.user.id)
        
        if success:
            # 重新加载关键词
            await self._load_dynamic_keywords()
            
            embed = EmbedFormatter.create_success_embed(
                "关键词添加成功",
                f"正则模式：`{pattern}`\n描述：{description or '无'}",
                user_name=interaction.user.display_name
            )
        else:
            embed = EmbedFormatter.create_error_embed(
                "添加失败",
                "关键词可能已存在或数据库错误。",
                user_name=interaction.user.display_name
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.app_commands.command(name="keyword-remove", description="删除正则关键词（管理员）")
    @commands.has_permissions(administrator=True)
    @discord.app_commands.describe(pattern="要删除的正则表达式模式")
    async def remove_keyword_cmd(self, interaction: discord.Interaction, pattern: str):
        """删除正则关键词"""
        # 检查权限
        if not interaction.user.guild_permissions.manage_messages:
            embed = EmbedFormatter.create_error_embed(
                "权限不足",
                "需要管理消息权限才能使用此命令。",
                user_name=interaction.user.display_name
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 从数据库删除
        from database import database
        success = await database.remove_regex_keyword(pattern)
        
        if success:
            # 重新加载关键词
            await self._load_dynamic_keywords()
            
            embed = EmbedFormatter.create_success_embed(
                "关键词删除成功",
                f"已删除正则模式：`{pattern}`",
                user_name=interaction.user.display_name
            )
        else:
            embed = EmbedFormatter.create_error_embed(
                "删除失败",
                "关键词不存在或数据库错误。",
                user_name=interaction.user.display_name
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.app_commands.command(name="keyword-toggle", description="切换关键词启用状态（管理员）")
    @commands.has_permissions(administrator=True)
    @discord.app_commands.describe(pattern="要切换状态的正则表达式模式")
    async def toggle_keyword_cmd(self, interaction: discord.Interaction, pattern: str):
        """切换关键词启用状态"""
        # 检查权限
        if not interaction.user.guild_permissions.manage_messages:
            embed = EmbedFormatter.create_error_embed(
                "权限不足",
                "需要管理消息权限才能使用此命令。",
                user_name=interaction.user.display_name
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 切换状态
        from database import database
        new_state = await database.toggle_regex_keyword(pattern)
        
        if new_state is not None:
            # 重新加载关键词
            await self._load_dynamic_keywords()
            
            status = "启用" if new_state else "禁用"
            embed = EmbedFormatter.create_success_embed(
                f"关键词已{status}",
                f"正则模式：`{pattern}`",
                user_name=interaction.user.display_name
            )
        else:
            embed = EmbedFormatter.create_error_embed(
                "操作失败",
                "关键词不存在或数据库错误。",
                user_name=interaction.user.display_name
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.app_commands.command(name="keyword-list", description="查看所有关键词")
    async def list_keywords_cmd(self, interaction: discord.Interaction):
        """查看所有关键词"""
        try:
            from database import database
            from utils.message_formatter import MessageType
            
            # 获取所有关键词（包括禁用的）
            keywords = await database.get_regex_keywords(enabled_only=False)
            
            if not keywords:
                embed = EmbedFormatter.create_info_embed(
                    "关键词列表",
                    "暂无动态关键词。\n\n💡 使用 `/keyword-add` 添加新的关键词。",
                    user_name=interaction.user.display_name
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # 准备分页内容
            items_per_page = 5
            pages = []
            
            for i in range(0, len(keywords), items_per_page):
                page_keywords = keywords[i:i + items_per_page]
                
                embed = discord.Embed(
                    title="📝 动态关键词列表",
                    color=EmbedFormatter.COLORS[MessageType.INFO]
                )
                
                for kw in page_keywords:
                    status = "✅" if kw['enabled'] else "❌"
                    trigger_count = kw.get('trigger_count', 0)
                    description = kw.get('description') or "无描述"
                    
                    embed.add_field(
                        name=f"{status} `{kw['pattern']}`",
                        value=f"**描述：** {description}\n**触发次数：** {trigger_count}\n**创建时间：** {kw['created_at'][:16]}",
                        inline=False
                    )
                
                embed.set_footer(text=f"第 {i//items_per_page + 1} 页 / 共 {(len(keywords)-1)//items_per_page + 1} 页 | 总共 {len(keywords)} 个关键词")
                pages.append(embed)
            
            if len(pages) == 1:
                await interaction.response.send_message(embed=pages[0], ephemeral=True)
            else:
                from utils.pagination_view import EmbedPaginationView
                view = EmbedPaginationView(pages)
                await interaction.response.send_message(embed=pages[0], view=view, ephemeral=True)
                
        except Exception as e:
            self.logger.error(f"查看关键词列表失败: {e}")
            embed = EmbedFormatter.create_error_embed(
                "查看失败",
                f"无法获取关键词列表：{str(e)}",
                user_name=interaction.user.display_name
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.app_commands.command(name="keyword-reload", description="重新加载关键词（管理员）")
    async def reload_keywords_cmd(self, interaction: discord.Interaction):
        """重新加载关键词"""
        # 检查管理员权限
        if not interaction.user.guild_permissions.administrator:
            embed = EmbedFormatter.create_error_embed(
                "权限不足",
                "需要管理员权限才能使用此命令。",
                user_name=interaction.user.display_name
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # 重新加载关键词
            await self._load_dynamic_keywords()
            
            embed = EmbedFormatter.create_success_embed(
                "关键词重新加载完成",
                f"共加载 {len(self.keyword_patterns)} 个关键词\n- 默认关键词：{len(self.default_keyword_patterns)} 个\n- 动态关键词：{len(self.dynamic_keyword_patterns)} 个",
                user_name=interaction.user.display_name
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            self.logger.error(f"重新加载关键词失败: {e}")
            embed = EmbedFormatter.create_error_embed(
                "重新加载失败",
                f"发生错误：{str(e)}",
                user_name=interaction.user.display_name
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    """设置Cog"""
    await bot.add_cog(QAHandlerCog(bot))
