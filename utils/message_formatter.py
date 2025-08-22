"""
消息格式化模块
处理Discord嵌入式消息的美化和格式化
"""

import discord
from datetime import datetime
from typing import List, Optional, Dict, Any
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
        image_analyzed: bool = False
    ) -> discord.Embed:
        """
        创建AI回复的嵌入式消息
        
        Args:
            question: 用户问题
            answer: AI回答
            user_name: 提问用户名称
            response_time: 响应时间（秒）
            image_analyzed: 是否分析了图像
        
        Returns:
            格式化的Discord嵌入消息
        """
        
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
        
        # 添加回答字段
        if len(answer) > 1024:
            # 如果回答太长，分成多个字段
            chunks = [answer[i:i+1000] for i in range(0, len(answer), 1000)]
            for i, chunk in enumerate(chunks[:3]):  # 最多显示3个块
                embed.add_field(
                    name=f"{EmbedFormatter.EMOJIS[MessageType.INFO]} 解答 {f'({i+1}/{len(chunks)})' if len(chunks) > 1 else ''}",
                    value=chunk,
                    inline=False
                )
            
            if len(chunks) > 3:
                embed.add_field(
                    name="📝 回复过长", 
                    value="完整回复请查看上方内容，如需更多帮助请继续提问。",
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
            """,
            inline=False
        )
        
        embed.add_field(
            name="💬 使用方法",
            value="""
**斜杠命令:**
• `/ask [问题]` - 询问SillyTavern相关问题
• `/diagnose` - 上传截图进行错误分析
• `/help-st` - 显示此帮助信息

**自动触发:**
• 发送包含相关关键词的消息会自动触发回复
• 支持图像分析，直接发送错误截图即可
            """,
            inline=False
        )
        
        embed.add_field(
            name="🔧 支持的问题类型",
            value="""
• API连接问题 (OpenAI, Claude, Gemini等)
• 角色卡导入和使用
• 聊天设置和参数调整
• 插件和扩展功能
• 性能优化建议
• 错误排除和故障修复
            """,
            inline=False
        )
        
        embed.set_footer(text="提示: 直接 @我 或发送包含关键词的消息也能触发回复！")
        
        return embed
    
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
