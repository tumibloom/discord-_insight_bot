"""
管理功能Cog
提供机器人管理、状态监控和系统维护功能
"""

import asyncio
import psutil
import platform
import time
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord.ext import commands, tasks
from discord import app_commands

from utils.logger import get_logger
from utils.message_formatter import EmbedFormatter, MessageType
from database import database
from config import config

logger = get_logger(__name__)

class AdminCog(commands.Cog, name="管理功能"):
    """管理功能模块"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_logger(self.__class__.__name__)
        self.start_time = datetime.now()
        
        # 启动定期任务
        self.cleanup_task.start()
        self.system_monitor.start()
    
    async def cog_unload(self):
        """Cog卸载时停止任务"""
        self.cleanup_task.cancel()
        self.system_monitor.cancel()
    
    def cog_check(self, ctx):
        """检查命令权限"""
        return config.is_admin_user(ctx.author.id)
    
    @app_commands.command(name="status", description="显示机器人状态信息")
    async def status(self, interaction: discord.Interaction):
        """显示机器人状态"""
        if not config.is_admin_user(interaction.user.id):
            await interaction.response.send_message("❌ 您没有权限使用此命令", ephemeral=True)
            return
        
        # 获取系统信息
        uptime = datetime.now() - self.start_time
        uptime_str = self._format_uptime(uptime)
        
        # 获取AI模块统计
        ai_cog = self.bot.get_cog("AI集成")
        ai_stats = ai_cog.get_stats() if ai_cog else {}
        
        # 获取数据库统计
        db_stats = await database.get_system_stats()
        
        # 创建状态嵌入
        embed = EmbedFormatter.create_status_embed(
            ai_status="✅ 正常运行" if ai_cog else "❌ 未加载",
            uptime=uptime_str,
            processed_questions=db_stats.get('total_questions', 0),
            avg_response_time=ai_stats.get('avg_response_time')
        )
        
        # 添加系统信息
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        embed.add_field(
            name="💻 系统资源",
            value=f"CPU: {cpu_percent:.1f}%\n"
                  f"内存: {memory.percent:.1f}%\n"
                  f"可用内存: {memory.available / 1024 / 1024 / 1024:.1f}GB",
            inline=True
        )
        
        embed.add_field(
            name="📊 今日统计",
            value=f"问题数: {db_stats.get('today_questions', 0)}\n"
                  f"图片分析: {db_stats.get('total_images', 0)}\n"
                  f"活跃用户: {db_stats.get('total_users', 0)}",
            inline=True
        )
        
        # 添加配置信息
        embed.add_field(
            name="⚙️ 配置状态",
            value=f"自动回复: {'✅' if config.AUTO_REPLY_ENABLED else '❌'}\n"
                  f"关键词触发: {'✅' if config.KEYWORD_TRIGGER_ENABLED else '❌'}\n"
                  f"监控频道: {len(config.MONITOR_CHANNELS) if config.MONITOR_CHANNELS else '全部'}",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="reload_cog", description="重新加载指定的Cog模块")
    @app_commands.describe(cog_name="要重新加载的Cog名称")
    async def reload_cog(self, interaction: discord.Interaction, cog_name: str):
        """重新加载Cog模块"""
        if not config.is_admin_user(interaction.user.id):
            await interaction.response.send_message("❌ 您没有权限使用此命令", ephemeral=True)
            return
        
        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            
            embed = EmbedFormatter.create_success_embed(
                f"✅ Cog模块 `{cog_name}` 重新加载成功",
                user_name=interaction.user.display_name
            )
            
            self.logger.info(f"管理员 {interaction.user.display_name} 重新加载了Cog: {cog_name}")
            
        except commands.ExtensionNotFound:
            embed = EmbedFormatter.create_error_embed(
                f"❌ 找不到Cog模块: `{cog_name}`",
                user_name=interaction.user.display_name
            )
        except Exception as e:
            embed = EmbedFormatter.create_error_embed(
                f"❌ 重新加载Cog失败: {str(e)}",
                user_name=interaction.user.display_name
            )
            self.logger.error(f"重新加载Cog {cog_name} 失败: {e}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="cleanup_db", description="清理旧的数据库记录")
    @app_commands.describe(days="保留多少天的记录（默认30天）")
    async def cleanup_database(self, interaction: discord.Interaction, days: int = 30):
        """清理数据库"""
        if not config.is_admin_user(interaction.user.id):
            await interaction.response.send_message("❌ 您没有权限使用此命令", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            await database.cleanup_old_records(days)
            
            embed = EmbedFormatter.create_success_embed(
                f"✅ 数据库清理完成，已删除 {days} 天前的记录",
                user_name=interaction.user.display_name
            )
            
            self.logger.info(f"管理员 {interaction.user.display_name} 执行了数据库清理")
            
        except Exception as e:
            embed = EmbedFormatter.create_error_embed(
                f"❌ 数据库清理失败: {str(e)}",
                user_name=interaction.user.display_name
            )
            self.logger.error(f"数据库清理失败: {e}")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="user_stats", description="查看用户的使用统计")
    @app_commands.describe(user="要查看的用户")
    async def user_stats(self, interaction: discord.Interaction, user: discord.User):
        """查看用户统计"""
        if not config.is_admin_user(interaction.user.id):
            await interaction.response.send_message("❌ 您没有权限使用此命令", ephemeral=True)
            return
        
        stats = await database.get_user_stats(user.id)
        
        if not stats:
            embed = EmbedFormatter.create_error_embed(
                f"❌ 没有找到用户 {user.display_name} 的使用记录",
                user_name=interaction.user.display_name
            )
        else:
            embed = discord.Embed(
                title=f"📊 用户统计 - {user.display_name}",
                color=EmbedFormatter.COLORS[MessageType.INFO]
            )
            
            embed.add_field(name="总问题数", value=stats['total_questions'], inline=True)
            embed.add_field(name="图片分析", value=stats['total_images'], inline=True)
            embed.add_field(
                name="平均响应时间", 
                value=f"{stats['avg_response_time']:.2f}s", 
                inline=True
            )
            
            if stats['first_question_at']:
                first_time = datetime.fromisoformat(stats['first_question_at'])
                embed.add_field(
                    name="首次提问", 
                    value=first_time.strftime("%Y-%m-%d %H:%M"), 
                    inline=True
                )
            
            if stats['last_question_at']:
                last_time = datetime.fromisoformat(stats['last_question_at'])
                embed.add_field(
                    name="最近提问", 
                    value=last_time.strftime("%Y-%m-%d %H:%M"), 
                    inline=True
                )
            
            embed.set_thumbnail(url=user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="recent_questions", description="查看最近的问题记录")
    @app_commands.describe(
        limit="显示数量（默认10）",
        hours="时间范围小时数（默认24小时）"
    )
    async def recent_questions(
        self, 
        interaction: discord.Interaction, 
        limit: int = 10, 
        hours: int = 24
    ):
        """查看最近的问题"""
        if not config.is_admin_user(interaction.user.id):
            await interaction.response.send_message("❌ 您没有权限使用此命令", ephemeral=True)
            return
        
        questions = await database.get_recent_questions(limit, hours)
        
        if not questions:
            embed = EmbedFormatter.create_error_embed(
                f"❌ 最近 {hours} 小时内没有问题记录",
                user_name=interaction.user.display_name
            )
        else:
            embed = discord.Embed(
                title=f"📋 最近 {hours} 小时的问题记录",
                description=f"共显示 {len(questions)} 条记录",
                color=EmbedFormatter.COLORS[MessageType.INFO]
            )
            
            for i, q in enumerate(questions, 1):
                question_preview = q['question'][:100] + ("..." if len(q['question']) > 100 else "")
                
                created_time = datetime.fromisoformat(q['created_at'])
                time_str = created_time.strftime("%m-%d %H:%M")
                
                field_name = f"{i}. {q['user_name']} ({time_str})"
                field_value = f"**Q**: {question_preview}\n"
                
                if q['has_image']:
                    field_value += "🖼️ 包含图片分析\n"
                
                if q['response_time']:
                    field_value += f"⏱️ 响应时间: {q['response_time']:.2f}s"
                
                embed.add_field(name=field_name, value=field_value, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="system_info", description="显示系统详细信息")
    async def system_info(self, interaction: discord.Interaction):
        """显示系统信息"""
        if not config.is_admin_user(interaction.user.id):
            await interaction.response.send_message("❌ 您没有权限使用此命令", ephemeral=True)
            return
        
        # 获取系统信息
        system_info = {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
        }
        
        # 获取内存信息
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        embed = discord.Embed(
            title="💻 系统详细信息",
            color=EmbedFormatter.COLORS[MessageType.INFO]
        )
        
        embed.add_field(
            name="🖥️ 系统",
            value=f"操作系统: {system_info['platform']} {system_info['platform_release']}\n"
                  f"架构: {system_info['architecture']}\n"
                  f"Python: {system_info['python_version']}",
            inline=True
        )
        
        embed.add_field(
            name="💾 内存",
            value=f"总计: {memory.total / 1024**3:.1f}GB\n"
                  f"使用: {memory.used / 1024**3:.1f}GB ({memory.percent:.1f}%)\n"
                  f"可用: {memory.available / 1024**3:.1f}GB",
            inline=True
        )
        
        embed.add_field(
            name="💿 磁盘",
            value=f"总计: {disk.total / 1024**3:.1f}GB\n"
                  f"使用: {disk.used / 1024**3:.1f}GB ({disk.percent:.1f}%)\n"
                  f"可用: {disk.free / 1024**3:.1f}GB",
            inline=True
        )
        
        # Discord.py信息
        embed.add_field(
            name="🤖 Discord信息",
            value=f"延迟: {self.bot.latency * 1000:.1f}ms\n"
                  f"服务器数: {len(self.bot.guilds)}\n"
                  f"用户数: {len(self.bot.users)}",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @tasks.loop(hours=24)
    async def cleanup_task(self):
        """定期清理任务"""
        try:
            await database.cleanup_old_records(days=30)
            self.logger.info("定期数据库清理完成")
        except Exception as e:
            self.logger.error(f"定期清理任务失败: {e}")
    
    @tasks.loop(minutes=30)
    async def system_monitor(self):
        """系统监控任务"""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 如果资源使用过高，记录警告
            if memory.percent > 90 or cpu_percent > 90:
                self.logger.warning(
                    f"系统资源使用过高 - CPU: {cpu_percent:.1f}%, 内存: {memory.percent:.1f}%"
                )
                
                # 可以在这里添加通知管理员的逻辑
                
        except Exception as e:
            self.logger.error(f"系统监控任务失败: {e}")
    
    @cleanup_task.before_loop
    async def before_cleanup(self):
        """等待机器人就绪"""
        await self.bot.wait_until_ready()
    
    @system_monitor.before_loop
    async def before_monitor(self):
        """等待机器人就绪"""
        await self.bot.wait_until_ready()
    
    def _format_uptime(self, uptime: timedelta) -> str:
        """格式化运行时间"""
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}天 {hours}小时 {minutes}分钟"
        elif hours > 0:
            return f"{hours}小时 {minutes}分钟"
        else:
            return f"{minutes}分钟"

async def setup(bot: commands.Bot):
    """设置Cog"""
    await bot.add_cog(AdminCog(bot))
