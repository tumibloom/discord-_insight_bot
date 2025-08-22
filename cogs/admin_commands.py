"""
管理员命令Cog
提供API错误监控、系统状态和管理功能
"""

import discord
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from utils.logger import get_logger
from utils.message_formatter import EmbedFormatter
from utils.api_error_monitor import error_monitor
from database import database
from config import config

logger = get_logger(__name__)

class AdminCommandsCog(commands.Cog, name="管理员命令"):
    """管理员命令功能模块"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_logger(self.__class__.__name__)
    
    async def cog_load(self):
        """Cog加载时的初始化"""
        self.logger.info("管理员命令模块已加载")
    
    @discord.app_commands.command(name="api-errors", description="查看API错误统计（管理员）")
    async def view_api_errors(self, interaction: discord.Interaction, hours: Optional[int] = 24):
        """查看API错误统计"""
        # 权限检查
        if not config.is_admin_user(interaction.user.id):
            embed = EmbedFormatter.create_error_embed(
                "你没有权限使用此命令",
                title="权限不足",
                user_name=interaction.user.display_name
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # 延迟响应，避免超时
            await interaction.response.defer(ephemeral=True)
            
            # 获取数据库统计
            db_stats = await database.get_api_error_statistics(hours=hours)
            
            # 获取内存统计（如果错误监控器可用）
            memory_stats = {}
            if error_monitor:
                memory_stats = await error_monitor.get_error_statistics()
            
            # 创建统计报告嵌入
            embed = await self._create_error_statistics_embed(db_stats, memory_stats, hours)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"查看API错误统计失败: {e}")
            error_embed = EmbedFormatter.create_error_embed(
                f"获取错误统计时发生问题: {str(e)}",
                title="统计获取失败",
                user_name=interaction.user.display_name
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    @discord.app_commands.command(name="system-status", description="查看系统状态（管理员）")
    async def view_system_status(self, interaction: discord.Interaction):
        """查看系统状态"""
        # 权限检查
        if not config.is_admin_user(interaction.user.id):
            embed = EmbedFormatter.create_error_embed(
                "你没有权限使用此命令",
                title="权限不足",
                user_name=interaction.user.display_name
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # 延迟响应
            await interaction.response.defer(ephemeral=True)
            
            # 收集系统信息
            system_info = await self._collect_system_information()
            
            # 创建系统状态嵌入
            embed = await self._create_system_status_embed(system_info)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"查看系统状态失败: {e}")
            error_embed = EmbedFormatter.create_error_embed(
                f"获取系统状态时发生问题: {str(e)}",
                title="状态获取失败",
                user_name=interaction.user.display_name
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    @discord.app_commands.command(name="notification-history", description="查看管理员通知历史（管理员）")
    async def view_notification_history(self, interaction: discord.Interaction, limit: Optional[int] = 20):
        """查看管理员通知历史"""
        # 权限检查
        if not config.is_admin_user(interaction.user.id):
            embed = EmbedFormatter.create_error_embed(
                "你没有权限使用此命令",
                title="权限不足",
                user_name=interaction.user.display_name
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # 延迟响应
            await interaction.response.defer(ephemeral=True)
            
            # 获取通知历史
            notifications = await database.get_admin_notification_history(limit=limit)
            
            if not notifications:
                embed = EmbedFormatter.create_info_embed(
                    "暂无管理员通知记录",
                    title="通知历史",
                    user_name=interaction.user.display_name
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 创建通知历史嵌入
            embed = await self._create_notification_history_embed(notifications)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"查看通知历史失败: {e}")
            error_embed = EmbedFormatter.create_error_embed(
                f"获取通知历史时发生问题: {str(e)}",
                title="历史获取失败",
                user_name=interaction.user.display_name
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    @discord.app_commands.command(name="test-notification", description="测试管理员通知功能（管理员）")
    async def test_admin_notification(self, interaction: discord.Interaction):
        """测试管理员通知功能"""
        # 权限检查
        if not config.is_admin_user(interaction.user.id):
            embed = EmbedFormatter.create_error_embed(
                "你没有权限使用此命令",
                title="权限不足",
                user_name=interaction.user.display_name
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # 立即响应
            await interaction.response.send_message(
                "🧪 正在测试管理员通知功能，请检查您的私信...", 
                ephemeral=True
            )
            
            # 创建测试通知
            if error_monitor:
                await error_monitor._send_admin_notification(
                    error_key="test_notification",
                    severity="low",
                    error_record={
                        'timestamp': datetime.now(),
                        'error_type': 'test',
                        'error_message': '这是一个测试通知，用于验证管理员通知系统是否正常工作。',
                        'endpoint': 'test_endpoint',
                        'user_id': interaction.user.id,
                        'additional_info': {
                            'test_by': interaction.user.display_name,
                            'channel': interaction.channel.name if hasattr(interaction.channel, 'name') else 'DM'
                        }
                    },
                    count=1
                )
                
                # 记录测试
                await database.log_admin_notification(
                    notification_type="test",
                    content="管理员通知功能测试",
                    title="测试通知",
                    severity="low",
                    recipients_count=len(config.ADMIN_USERS),
                    successful_sends=len(config.ADMIN_USERS)
                )
            else:
                await interaction.followup.send(
                    "❌ 错误监控器未初始化，无法测试通知功能", 
                    ephemeral=True
                )
            
        except Exception as e:
            self.logger.error(f"测试管理员通知失败: {e}")
            await interaction.followup.send(
                f"❌ 测试通知失败: {str(e)}", 
                ephemeral=True
            )
    
    async def _create_error_statistics_embed(self, db_stats: Dict, memory_stats: Dict, hours: int) -> discord.Embed:
        """创建错误统计嵌入消息"""
        embed = discord.Embed(
            title="📊 API错误统计报告",
            description=f"最近 **{hours} 小时** 的API错误统计信息",
            color=0x3498DB,
            timestamp=datetime.now()
        )
        
        # 数据库统计
        if db_stats:
            embed.add_field(
                name="📈 总体统计",
                value=f"错误记录数: **{db_stats.get('total_errors', 0)}**",
                inline=True
            )
            
            # 按类型统计
            if db_stats.get('by_type'):
                type_text = ""
                for item in db_stats['by_type'][:5]:  # 只显示前5个
                    type_text += f"• {item['type']}: {item['records']}条 ({item['total_count']}次)\n"
                
                if type_text:
                    embed.add_field(
                        name="🏷️ 按类型统计",
                        value=type_text[:1000],
                        inline=False
                    )
            
            # 按严重程度统计
            if db_stats.get('by_severity'):
                severity_text = ""
                severity_icons = {'critical': '🚨', 'high': '⚠️', 'medium': '🟡', 'low': '🔵'}
                
                for item in db_stats['by_severity']:
                    icon = severity_icons.get(item['severity'], '🔵')
                    severity_text += f"{icon} {item['severity'].upper()}: {item['records']}条\n"
                
                if severity_text:
                    embed.add_field(
                        name="📊 按严重程度统计",
                        value=severity_text,
                        inline=True
                    )
            
            # 最近的错误
            if db_stats.get('recent_errors'):
                recent_text = ""
                for error in db_stats['recent_errors'][:3]:  # 只显示最近3个
                    recent_text += f"• **{error['type']}**: {error['message'][:50]}...\n"
                
                if recent_text:
                    embed.add_field(
                        name="🕐 最近错误",
                        value=recent_text,
                        inline=False
                    )
        
        # 内存统计（如果可用）
        if memory_stats:
            if memory_stats.get('last_hour', {}).get('count', 0) > 0:
                embed.add_field(
                    name="⚡ 实时统计",
                    value=f"最近1小时: **{memory_stats['last_hour']['count']}** 个错误",
                    inline=True
                )
        
        embed.set_footer(text="QA Bot 错误监控系统")
        return embed
    
    async def _collect_system_information(self) -> Dict:
        """收集系统信息"""
        info = {}
        
        try:
            # AI客户端状态
            from utils.ai_client import ai_client
            info['ai_status'] = ai_client.get_available_apis()
            
            # 机器人状态
            info['bot_status'] = {
                'latency': round(self.bot.latency * 1000, 2),
                'guilds': len(self.bot.guilds),
                'users': len(self.bot.users),
                'channels': sum(len(guild.channels) for guild in self.bot.guilds)
            }
            
            # 配置状态
            info['config_status'] = {
                'admin_users': len(config.ADMIN_USERS),
                'monitor_channels': len(config.MONITOR_CHANNELS) if config.MONITOR_CHANNELS else "全部频道",
                'auto_reply_enabled': config.AUTO_REPLY_ENABLED,
                'keyword_trigger_enabled': config.KEYWORD_TRIGGER_ENABLED
            }
            
            # 错误监控状态
            info['monitor_status'] = {
                'initialized': error_monitor is not None,
                'recent_errors': len(error_monitor.recent_errors) if error_monitor else 0,
                'error_types': len(error_monitor.error_counts) if error_monitor else 0
            }
            
        except Exception as e:
            self.logger.error(f"收集系统信息时出错: {e}")
            info['error'] = str(e)
        
        return info
    
    async def _create_system_status_embed(self, system_info: Dict) -> discord.Embed:
        """创建系统状态嵌入消息"""
        embed = discord.Embed(
            title="🖥️ 系统状态报告",
            description="QA Bot 当前系统状态概览",
            color=0x2ECC71,
            timestamp=datetime.now()
        )
        
        # AI客户端状态
        if 'ai_status' in system_info:
            ai_status = system_info['ai_status']
            ai_text = ""
            if ai_status.get('custom_api'):
                ai_text += "✅ 自定义API: 可用\n"
            else:
                ai_text += "❌ 自定义API: 不可用\n"
                
            if ai_status.get('gemini'):
                ai_text += "✅ Gemini: 可用\n"
            else:
                ai_text += "❌ Gemini: 不可用\n"
            
            embed.add_field(
                name="🤖 AI服务状态",
                value=ai_text,
                inline=True
            )
        
        # 机器人状态
        if 'bot_status' in system_info:
            bot_status = system_info['bot_status']
            bot_text = f"延迟: **{bot_status['latency']}ms**\n"
            bot_text += f"服务器: **{bot_status['guilds']}**\n"
            bot_text += f"用户: **{bot_status['users']}**\n"
            bot_text += f"频道: **{bot_status['channels']}**"
            
            embed.add_field(
                name="📡 连接状态",
                value=bot_text,
                inline=True
            )
        
        # 功能配置状态
        if 'config_status' in system_info:
            config_status = system_info['config_status']
            config_text = f"管理员: **{config_status['admin_users']}** 人\n"
            config_text += f"监控频道: **{config_status['monitor_channels']}**\n"
            config_text += f"自动回复: **{'启用' if config_status['auto_reply_enabled'] else '禁用'}**\n"
            config_text += f"关键词触发: **{'启用' if config_status['keyword_trigger_enabled'] else '禁用'}**"
            
            embed.add_field(
                name="⚙️ 功能配置",
                value=config_text,
                inline=False
            )
        
        # 错误监控状态
        if 'monitor_status' in system_info:
            monitor_status = system_info['monitor_status']
            monitor_text = f"监控器: **{'已启用' if monitor_status['initialized'] else '未启用'}**\n"
            monitor_text += f"最近错误: **{monitor_status['recent_errors']}** 条\n"
            monitor_text += f"错误类型: **{monitor_status['error_types']}** 种"
            
            embed.add_field(
                name="🔍 错误监控",
                value=monitor_text,
                inline=True
            )
        
        # 错误信息
        if 'error' in system_info:
            embed.add_field(
                name="❌ 收集状态时出错",
                value=f"```\n{system_info['error']}\n```",
                inline=False
            )
            embed.color = 0xE74C3C
        
        embed.set_footer(text="QA Bot 系统监控")
        return embed
    
    async def _create_notification_history_embed(self, notifications: List[Dict]) -> discord.Embed:
        """创建通知历史嵌入消息"""
        embed = discord.Embed(
            title="📜 管理员通知历史",
            description=f"最近 **{len(notifications)}** 条通知记录",
            color=0x9B59B6,
            timestamp=datetime.now()
        )
        
        for i, notif in enumerate(notifications[:10]):  # 最多显示10条
            # 严重程度图标
            severity_icons = {
                'critical': '🚨',
                'high': '⚠️', 
                'medium': '🟡',
                'low': '🔵'
            }
            icon = severity_icons.get(notif['severity'], '🔵')
            
            # 发送状态
            if notif['successful_sends'] > 0:
                status = f"✅ {notif['successful_sends']}/{notif['recipients_count']}"
            else:
                status = "❌ 发送失败"
            
            embed.add_field(
                name=f"{icon} {notif['type'].upper()} - {notif['created_at'][:16]}",
                value=f"{notif['content'][:100]}{'...' if len(notif['content']) > 100 else ''}\n{status}",
                inline=False
            )
        
        if len(notifications) > 10:
            embed.add_field(
                name="📊 更多记录",
                value=f"还有 **{len(notifications) - 10}** 条记录未显示",
                inline=False
            )
        
        embed.set_footer(text="QA Bot 通知系统")
        return embed

async def setup(bot: commands.Bot):
    """设置Cog"""
    await bot.add_cog(AdminCommandsCog(bot))
