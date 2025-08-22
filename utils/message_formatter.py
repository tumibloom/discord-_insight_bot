"""
消息格式化模块
处理Discord嵌入式消息的美化和格式化
"""

import discord
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum

class MessageType(Enum):
    """消息类型枚举"""
    SUCCESS = "success"
    ERROR = "error" 
    WARNING = "warning"
    INFO = "info"
    QUESTION = "question"
    SOLUTION = "solution"

class EmbedFormatter:
    """嵌入式消息格式化器"""
    
    # 颜色配置
    COLORS = {
        MessageType.SUCCESS: 0x00ff00,    # 绿色
        MessageType.ERROR: 0xff0000,      # 红色  
        MessageType.WARNING: 0xffa500,    # 橙色
        MessageType.INFO: 0x0099ff,       # 蓝色
        MessageType.QUESTION: 0x9932cc,   # 紫色
        MessageType.SOLUTION: 0x32cd32,   # 草绿色
    }
    
    # 表情符号配置
    EMOJIS = {
        MessageType.SUCCESS: "✅",
        MessageType.ERROR: "❌",
        MessageType.WARNING: "⚠️", 
        MessageType.INFO: "ℹ️",
        MessageType.QUESTION: "❓",
        MessageType.SOLUTION: "💡",
    }
    
    @staticmethod
    def create_ai_response_embed(
        question: str,
        answer: str,
        user_name: str,
        response_time: float = None,
        image_analyzed: bool = False,
        compact_mode: bool = False
    ) -> discord.Embed:
        """
        创建AI回复的嵌入式消息
        
        Args:
            question: 用户问题
            answer: AI回答
            user_name: 提问用户名称
            response_time: 响应时间（秒）
            image_analyzed: 是否分析了图像
            compact_mode: 是否使用紧凑模式
        
        Returns:
            格式化的Discord嵌入消息
        """
        
        if compact_mode:
            # 紧凑模式：只显示核心信息
            embed = discord.Embed(
                title=f"💡 SillyTavern 解答",
                color=EmbedFormatter.COLORS[MessageType.SOLUTION],
                timestamp=datetime.utcnow()
            )
            
            # 简化显示，不分页，直接截取
            answer_preview = answer[:800]  # 适当增加到800字符
            if len(answer) > 800:
                answer_preview += "\n\n💬 *回答较长，使用 /ask 命令查看完整解答*"
            
            embed.add_field(
                name=f"❓ {question[:100]}{'...' if len(question) > 100 else ''}",
                value=answer_preview,
                inline=False
            )
            
            # 简化的页脚
            footer_text = f"为 {user_name} 解答"
            if image_analyzed:
                footer_text += " · 📷 图片已分析"
            if response_time:
                footer_text += f" · ⚡ {response_time:.1f}s"
                
            embed.set_footer(text=footer_text)
            
            return embed
        
        # 原有的详细模式保持不变
        embed = discord.Embed(
            title=f"{EmbedFormatter.EMOJIS[MessageType.SOLUTION]} SillyTavern 智能助手",
            description=f"为 **{user_name}** 提供的解答",
            color=EmbedFormatter.COLORS[MessageType.SOLUTION],
            timestamp=datetime.utcnow()
        )
        
        # 添加问题字段
        embed.add_field(
            name=f"{EmbedFormatter.EMOJIS[MessageType.QUESTION]} 问题",
            value=f"```\n{question[:500]}{'...' if len(question) > 500 else ''}\n```",
            inline=False
        )
        
        # 添加回答字段 - 使用分页显示
        if len(answer) > 1024:
            # 创建分页视图
            pages = EmbedFormatter._create_answer_pages(answer)
            
            # 显示第一页
            embed.add_field(
                name=f"{EmbedFormatter.EMOJIS[MessageType.INFO]} 解答 (第1页/共{len(pages)}页)",
                value=pages[0],
                inline=False
            )
            
            if len(pages) > 1:
                embed.add_field(
                    name="� 导航提示",
                    value=f"这是一个包含 {len(pages)} 页的回答。点击下方按钮查看其他页面。",
                    inline=False
                )
        else:
            embed.add_field(
                name=f"{EmbedFormatter.EMOJIS[MessageType.INFO]} 解答",
                value=answer,
                inline=False
            )
        
        # 添加额外信息
        footer_text = "SillyTavern QA Bot"
        if response_time:
            footer_text += f" • 响应时间: {response_time:.2f}s"
        if image_analyzed:
            footer_text += " • 已分析图像"
            
        embed.set_footer(text=footer_text)
        
        return embed
    
    @staticmethod
    def create_error_embed(
        error_message: str,
        title: str = "发生错误",
        user_name: str = None
    ) -> discord.Embed:
        """创建错误消息嵌入"""
        
        embed = discord.Embed(
            title=f"{EmbedFormatter.EMOJIS[MessageType.ERROR]} {title}",
            description=error_message,
            color=EmbedFormatter.COLORS[MessageType.ERROR],
            timestamp=datetime.utcnow()
        )
        
        if user_name:
            embed.set_footer(text=f"用户: {user_name}")
        
        return embed
    
    @staticmethod
    def create_success_embed(
        message: str,
        title: str = "操作成功",
        user_name: str = None
    ) -> discord.Embed:
        """创建成功消息嵌入"""
        
        embed = discord.Embed(
            title=f"{EmbedFormatter.EMOJIS[MessageType.SUCCESS]} {title}",
            description=message,
            color=EmbedFormatter.COLORS[MessageType.SUCCESS],
            timestamp=datetime.utcnow()
        )
        
        if user_name:
            embed.set_footer(text=f"用户: {user_name}")
        
        return embed
    
    @staticmethod
    def create_help_embed() -> discord.Embed:
        """创建帮助信息嵌入"""
        
        embed = discord.Embed(
            title=f"{EmbedFormatter.EMOJIS[MessageType.INFO]} SillyTavern 问答机器人帮助",
            description="我是专门为SillyTavern用户提供技术支持的AI助手！",
            color=EmbedFormatter.COLORS[MessageType.INFO],
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="🎯 主要功能",
            value="""
• **智能问答**: 回答SillyTavern相关问题
• **错误诊断**: 分析错误截图和日志
• **配置指导**: 提供详细的设置说明
• **故障排除**: 帮助解决各种技术问题
            """.strip(),
            inline=False
        )
        
        embed.add_field(
            name="💬 使用方法",
            value="""
**斜杠命令:**
`/ask [问题]` - 询问SillyTavern相关问题
`/diagnose` - 上传截图进行错误分析
`/help-st` - 显示此帮助信息
`/search_kb [关键词]` - 搜索知识库

**自动触发:**
• 发送包含相关关键词的消息会自动触发回复
• 支持图像分析，直接发送错误截图即可
            """.strip(),
            inline=False
        )
        
        embed.set_footer(text="使用 /help-detail 查看详细帮助 • 提示: 直接发送包含关键词的消息也能触发回复！")
        
        return embed
    
    @staticmethod 
    def create_detailed_help_pages() -> List[str]:
        """创建详细帮助信息的分页内容"""
        pages = []
        
        # 第一页：基础功能
        page1 = """**🎯 主要功能介绍**

• **智能问答**: 基于AI技术回答SillyTavern相关问题
• **错误诊断**: 分析错误截图，识别问题并提供解决方案
• **配置指导**: 提供API设置、参数调优等详细说明
• **故障排除**: 针对常见问题提供快速修复方案
• **知识库搜索**: 查询内置的问题解答数据库

**� 智能特性**
• 自动识别关键词并触发回复
• 支持图片+文本综合分析
• 多页面回答支持，处理长回复
• 上下文理解，提供针对性建议"""

        # 第二页：命令详解
        page2 = """**💬 详细命令说明**

**📝 问答命令**
• `/ask <问题>` - 向AI询问任何SillyTavern相关问题
• `/diagnose <图片> [描述]` - 上传错误截图进行分析

**🔍 知识库命令**
• `/search_kb <关键词>` - 搜索内置知识库
• `/error_help <错误代码>` - 获取特定错误的解决方案
• `/quick_fix <问题类型>` - 获取常见问题的快速修复方案

**ℹ️ 信息命令**
• `/help-st` - 显示基础帮助信息
• `/help-detail` - 显示此详细帮助"""

        # 第三页：自动触发
        page3 = """**🤖 自动触发功能**

**📢 关键词触发**
当您的消息包含以下关键词时，机器人会自动回复：
• sillytavern, tavern, st
• openai, claude, gemini
• api, token, connection
• error, 错误, 报错, bug
• config, setting, 配置, 设置
• character card, 角色卡

**🖼️ 智能图片分析**
• 自动检测错误截图
• 结合文本描述进行综合分析
• 支持配置界面、错误弹窗等各类图片

**⚡ 即时反馈**
• 检测到触发后立即显示占位消息
• 实时更新处理进度"""

        # 第四页：支持范围
        page4 = """**🔧 支持的问题类型**

**🔗 API连接问题**
• OpenAI API密钥配置和错误
• Claude API设置和限制问题  
• Gemini/Google AI配置
• 自定义API端点设置
• 连接超时和网络问题

**👤 角色和聊天**
• 角色卡导入和格式问题
• 聊天记录管理
• 上下文长度限制
• 角色行为调试

**⚙️ 配置和优化**
• 参数调优建议
• 性能优化方案  
• 插件和扩展配置
• UI界面设置"""

        # 第五页：使用技巧
        page5 = """**💡 使用技巧和注意事项**

**📋 提问技巧**
• 描述具体问题现象和错误信息
• 提供相关的配置信息
• 上传清晰的错误截图
• 说明使用的API服务商和版本

**🎯 获得最佳答案**
• 一次只问一个问题，避免混杂
• 提供足够的上下文信息
• 尝试多个关键词搜索知识库
• 查看分页回答的完整内容

**⚠️ 注意事项**
• 不要分享API密钥等敏感信息
• 机器人回复会在90秒后自动删除
• 管理员命令需要特殊权限
• 遇到问题可联系服务器管理员"""

        pages = [page1, page2, page3, page4, page5]
        return pages
    
    @staticmethod
    def create_status_embed(
        ai_status: str,
        uptime: str,
        processed_questions: int,
        avg_response_time: float = None
    ) -> discord.Embed:
        """创建状态信息嵌入"""
        
        embed = discord.Embed(
            title=f"{EmbedFormatter.EMOJIS[MessageType.INFO]} 机器人状态",
            color=EmbedFormatter.COLORS[MessageType.INFO],
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="🤖 AI状态", value=ai_status, inline=True)
        embed.add_field(name="⏱️ 运行时间", value=uptime, inline=True)
        embed.add_field(name="📊 处理问题", value=f"{processed_questions} 个", inline=True)
        
        if avg_response_time:
            embed.add_field(
                name="⚡ 平均响应时间", 
                value=f"{avg_response_time:.2f}s", 
                inline=True
            )
        
        return embed
    
    @staticmethod
    def create_thinking_embed(user_name: str) -> discord.Embed:
        """创建思考中的临时嵌入"""
        
        embed = discord.Embed(
            title="🤔 正在思考中...",
            description=f"正在为 **{user_name}** 分析问题，请稍候...",
            color=EmbedFormatter.COLORS[MessageType.INFO]
        )
        
        return embed
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 1000) -> str:
        """截断文本到指定长度"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    @staticmethod
    def format_code_block(code: str, language: str = "") -> str:
        """格式化代码块"""
        return f"```{language}\n{code}\n```"
    
    @staticmethod
    def format_inline_code(code: str) -> str:
        """格式化行内代码"""
        return f"`{code}`"
    
    @staticmethod
    def _create_answer_pages(answer: str, page_size: int = 1000) -> List[str]:
        """
        将长答案分割成多个页面
        
        Args:
            answer: 原始答案
            page_size: 每页最大字符数
            
        Returns:
            分页后的答案列表
        """
        if len(answer) <= page_size:
            return [answer]
        
        pages = []
        current_page = ""
        
        # 按段落分割
        paragraphs = answer.split('\n\n')
        
        for paragraph in paragraphs:
            # 如果当前段落加上现有页面内容超过页面大小
            if len(current_page) + len(paragraph) + 2 > page_size:
                if current_page:  # 如果当前页面不为空，保存它
                    pages.append(current_page.strip())
                    current_page = paragraph + '\n\n'
                else:  # 如果单个段落就超过页面大小，强制分割
                    # 将长段落按字符强制分割
                    while len(paragraph) > page_size:
                        split_point = page_size - 10  # 留一点余量
                        pages.append(paragraph[:split_point] + "...")
                        paragraph = "..." + paragraph[split_point:]
                    current_page = paragraph + '\n\n'
            else:
                current_page += paragraph + '\n\n'
        
        # 添加最后一页
        if current_page.strip():
            pages.append(current_page.strip())
        
        return pages if pages else [answer[:page_size]]
    
    @staticmethod
    async def auto_delete_message(message: discord.Message, delay: int = 90):
        """
        自动删除消息
        
        Args:
            message: 要删除的Discord消息对象
            delay: 延迟删除的秒数，默认90秒
        """
        try:
            await asyncio.sleep(delay)
            # 普通消息都可以尝试删除，私密消息不会传递到这里
            await message.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            # 消息可能已被删除或没有权限删除
            pass
    
    @staticmethod
    async def send_with_auto_delete(
        target: Union[discord.TextChannel, discord.Interaction],
        embed: discord.Embed = None,
        content: str = None,
        ephemeral: bool = False,
        delete_after: int = 90
    ) -> Optional[discord.Message]:
        """
        发送消息并设置自动删除
        
        Args:
            target: 目标频道或交互对象
            embed: 嵌入式消息
            content: 文本内容
            ephemeral: 是否为私密消息（仅发送者可见）
            delete_after: 删除延迟秒数
            
        Returns:
            发送的消息对象（如果是ephemeral则为None）
        """
        try:
            if isinstance(target, discord.Interaction):
                # 处理斜杠命令交互
                if not target.response.is_done():
                    await target.response.send_message(
                        content=content,
                        embed=embed,
                        ephemeral=ephemeral
                    )
                    if ephemeral:
                        return None  # 私密消息无法获取消息对象
                    message = await target.original_response()
                else:
                    message = await target.followup.send(
                        content=content,
                        embed=embed,
                        ephemeral=ephemeral,
                        wait=True
                    )
            else:
                # 处理普通频道消息
                message = await target.send(content=content, embed=embed)
            
            # 如果不是私密消息且设置了自动删除，启动删除任务
            if not ephemeral and delete_after > 0 and message:
                asyncio.create_task(EmbedFormatter.auto_delete_message(message, delete_after))
            
            return message
            
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"发送消息失败: {e}")
            return None
