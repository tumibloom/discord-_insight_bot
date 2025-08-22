"""
管理员控制面板 - 统一的管理界面
提供直观的按钮式操作界面，整合所有管理员功能
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List, Dict
import asyncio
from datetime import datetime, timedelta

from utils.logger import get_logger
from utils.message_formatter import EmbedFormatter, MessageType
from database import database
from config import config

class AdminPanelView(discord.ui.View):
    """管理员面板主视图"""
    
    def __init__(self, user_id: int, logger):
        super().__init__(timeout=300)  # 5分钟超时
        self.user_id = user_id
        self.logger = logger
    
    @discord.ui.button(label="🔧 系统状态", style=discord.ButtonStyle.primary, row=0)
    async def system_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        """系统状态查看"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        # 获取系统状态
        embed = await self._create_system_status_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="👥 用户管理", style=discord.ButtonStyle.secondary, row=0)
    async def user_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        """用户管理面板"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        # 检查是否为超级管理员
        is_super_admin = config.is_super_admin(interaction.user.id)
        
        view = UserManagementView(self.user_id, is_super_admin, self.logger)
        embed = await self._create_user_management_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="📊 数据统计", style=discord.ButtonStyle.secondary, row=0)
    async def data_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """数据统计面板"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        view = DataStatsView(self.user_id, self.logger)
        embed = await self._create_data_stats_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🔔 通知管理", style=discord.ButtonStyle.secondary, row=1)
    async def notification_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        """通知管理面板"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        view = NotificationView(self.user_id, self.logger)
        embed = await self._create_notification_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🛠️ 系统维护", style=discord.ButtonStyle.danger, row=1)
    async def system_maintenance(self, interaction: discord.Interaction, button: discord.ui.Button):
        """系统维护面板"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        view = MaintenanceView(self.user_id, self.logger)
        embed = await self._create_maintenance_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="❌ 关闭面板", style=discord.ButtonStyle.danger, row=1)
    async def close_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """关闭面板"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="✅ 管理员面板已关闭",
            description="感谢您使用管理员面板！",
            color=0x95A5A6,
            timestamp=datetime.now()
        )
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def on_timeout(self):
        """面板超时处理"""
        try:
            embed = discord.Embed(
                title="⏰ 管理员面板已超时",
                description="面板已自动关闭，请重新打开",
                color=0x95A5A6
            )
            await self.message.edit(embed=embed, view=None)
        except:
            pass
    
    async def _create_system_status_embed(self) -> discord.Embed:
        """创建系统状态嵌入"""
        embed = discord.Embed(
            title="🔧 系统状态总览",
            color=0x3498DB,
            timestamp=datetime.now()
        )
        
        try:
            # 获取数据库统计
            db_stats = await database.get_system_stats()
            
            # 机器人基本信息
            embed.add_field(
                name="🤖 机器人状态",
                value=f"在线状态: ✅ 正常运行\n"
                      f"服务器数: **计算中...**\n"
                      f"用户数: **计算中...**",
                inline=True
            )
            
            # 今日统计
            embed.add_field(
                name="📈 今日数据",
                value=f"问题数: **{db_stats.get('today_questions', 0)}**\n"
                      f"活跃用户: **{db_stats.get('active_users', 0)}**\n"
                      f"图片分析: **{db_stats.get('today_images', 0)}**",
                inline=True
            )
            
            # 系统配置
            embed.add_field(
                name="⚙️ 系统配置",
                value=f"管理员数: **{len(config.get_all_admin_ids())}**\n"
                      f"自动回复: **{'✅' if config.AUTO_REPLY_ENABLED else '❌'}**\n"
                      f"关键词触发: **{'✅' if config.KEYWORD_TRIGGER_ENABLED else '❌'}**",
                inline=True
            )
            
        except Exception as e:
            embed.add_field(
                name="⚠️ 错误",
                value=f"获取系统信息时发生错误: {str(e)[:100]}",
                inline=False
            )
        
        return embed
    
    async def _create_user_management_embed(self) -> discord.Embed:
        """创建用户管理嵌入"""
        embed = discord.Embed(
            title="👥 用户管理面板",
            description="管理管理员用户和权限设置",
            color=0x9B59B6,
            timestamp=datetime.now()
        )
        
        # 获取管理员列表
        try:
            admin_users = await database.get_admin_users()
            admin_count = len(admin_users)
            super_admin_count = len(config.ADMIN_USERS)
            
            embed.add_field(
                name="👑 超级管理员",
                value=f"环境变量配置: **{super_admin_count}** 名",
                inline=True
            )
            
            embed.add_field(
                name="🛡️ 普通管理员",
                value=f"数据库配置: **{admin_count}** 名",
                inline=True
            )
            
            if admin_users:
                recent_admins = admin_users[:3]  # 显示最近3个
                admin_list = "\n".join([
                    f"• {admin['display_name']} ({admin['permissions']})"
                    for admin in recent_admins
                ])
                
                embed.add_field(
                    name="📋 最近管理员",
                    value=admin_list,
                    inline=False
                )
        except Exception as e:
            embed.add_field(
                name="⚠️ 错误",
                value=f"获取用户信息失败: {str(e)[:100]}",
                inline=False
            )
        
        return embed
    
    async def _create_data_stats_embed(self) -> discord.Embed:
        """创建数据统计嵌入"""
        embed = discord.Embed(
            title="📊 数据统计面板",
            description="查看系统使用统计和分析数据",
            color=0xE74C3C,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📈 可用统计",
            value="• 用户使用统计\n• 最近问题记录\n• API错误统计\n• 关键词统计",
            inline=False
        )
        
        return embed
    
    async def _create_notification_embed(self) -> discord.Embed:
        """创建通知管理嵌入"""
        embed = discord.Embed(
            title="🔔 通知管理面板",
            description="管理系统通知和消息推送",
            color=0xF39C12,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🛎️ 通知功能",
            value="• 查看通知历史\n• 测试通知系统\n• 查看API错误通知",
            inline=False
        )
        
        return embed
    
    async def _create_maintenance_embed(self) -> discord.Embed:
        """创建维护面板嵌入"""
        embed = discord.Embed(
            title="🛠️ 系统维护面板",
            description="执行系统维护和管理任务",
            color=0xE67E22,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🔧 维护功能",
            value="• 清理数据库\n• 重载模块\n• 系统详细信息",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ 注意",
            value="维护操作可能影响机器人运行，请谨慎操作",
            inline=False
        )
        
        return embed


class UserManagementView(discord.ui.View):
    """用户管理子面板"""
    
    def __init__(self, user_id: int, is_super_admin: bool, logger):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.is_super_admin = is_super_admin
        self.logger = logger
        
        # 只有超级管理员才能添加/移除管理员
        if not is_super_admin:
            self.add_admin.disabled = True
            self.remove_admin.disabled = True
    
    @discord.ui.button(label="➕ 添加管理员", style=discord.ButtonStyle.success, row=0)
    async def add_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        """添加管理员"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        modal = AddAdminModal(self.logger)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="➖ 移除管理员", style=discord.ButtonStyle.danger, row=0)
    async def remove_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        """移除管理员"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        # 获取管理员列表用于选择
        try:
            admin_users = await database.get_admin_users()
            if not admin_users:
                await interaction.response.send_message("❌ 没有可移除的管理员", ephemeral=True)
                return
            
            view = RemoveAdminSelectView(self.user_id, admin_users, self.logger)
            embed = discord.Embed(
                title="➖ 选择要移除的管理员",
                description="请从下拉菜单中选择要移除的管理员",
                color=0xE74C3C
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"获取管理员列表失败: {e}")
            await interaction.response.send_message(f"❌ 操作失败: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="📋 查看管理员", style=discord.ButtonStyle.secondary, row=0)
    async def list_admins(self, interaction: discord.Interaction, button: discord.ui.Button):
        """查看管理员列表"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 获取管理员列表
            admin_users = await database.get_admin_users()
            
            embed = discord.Embed(
                title="👥 管理员列表",
                color=0x3498DB,
                timestamp=datetime.now()
            )
            
            # 超级管理员
            super_admins = [f"<@{uid}>" for uid in config.ADMIN_USERS]
            if super_admins:
                embed.add_field(
                    name="👑 超级管理员 (环境变量)",
                    value="\n".join(super_admins),
                    inline=False
                )
            
            # 数据库管理员
            if admin_users:
                admin_list = []
                for admin in admin_users:
                    status = "✅ 活跃" if admin.get('is_active', True) else "❌ 停用"
                    admin_list.append(
                        f"**{admin['display_name']}** ({admin['permissions']}) - {status}\n"
                        f"添加时间: {admin['created_at'][:10]}"
                    )
                
                embed.add_field(
                    name="🛡️ 数据库管理员",
                    value="\n\n".join(admin_list),
                    inline=False
                )
            else:
                embed.add_field(
                    name="🛡️ 数据库管理员",
                    value="暂无数据库管理员",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"查看管理员列表失败: {e}")
            await interaction.followup.send(f"❌ 操作失败: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="🔙 返回", style=discord.ButtonStyle.secondary, row=1)
    async def go_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """返回主面板"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        main_view = AdminPanelView(self.user_id, self.logger)
        embed = await self._create_main_panel_embed()
        await interaction.response.edit_message(embed=embed, view=main_view)
    
    async def _create_main_panel_embed(self) -> discord.Embed:
        """创建主面板嵌入"""
        embed = discord.Embed(
            title="🎛️ 管理员控制面板",
            description="选择您要执行的管理操作",
            color=0x2ECC71,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🔧 功能模块",
            value="• **系统状态** - 查看系统运行状态\n"
                  "• **用户管理** - 管理管理员用户\n"
                  "• **数据统计** - 查看使用统计\n"
                  "• **通知管理** - 管理系统通知\n"
                  "• **系统维护** - 执行维护任务",
            inline=False
        )
        
        return embed


class AddAdminModal(discord.ui.Modal, title="添加管理员"):
    """添加管理员模态框"""
    
    def __init__(self, logger):
        super().__init__()
        self.logger = logger
    
    user_id = discord.ui.TextInput(
        label="用户ID",
        placeholder="请输入要添加为管理员的用户ID",
        required=True,
        max_length=20
    )
    
    permissions = discord.ui.TextInput(
        label="权限级别",
        placeholder="admin 或 moderator",
        required=True,
        max_length=10,
        default="admin"
    )
    
    notes = discord.ui.TextInput(
        label="备注",
        placeholder="可选的备注信息",
        required=False,
        max_length=200
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_id.value)
            permissions = self.permissions.value.lower()
            notes = self.notes.value or None
            
            # 验证权限级别
            if permissions not in ['admin', 'moderator']:
                await interaction.response.send_message(
                    "❌ 权限级别只能是 'admin' 或 'moderator'", 
                    ephemeral=True
                )
                return
            
            # 获取用户信息
            try:
                user = await interaction.client.fetch_user(user_id)
            except:
                await interaction.response.send_message(
                    "❌ 找不到该用户，请检查用户ID是否正确", 
                    ephemeral=True
                )
                return
            
            # 添加管理员
            success = await database.add_admin_user(
                user_id=user.id,
                username=user.name,
                discriminator=user.discriminator,
                display_name=user.display_name,
                added_by=interaction.user.id,
                permissions=permissions,
                notes=notes
            )
            
            if success:
                # 如果是admin权限，添加到运行时配置
                if permissions == 'admin':
                    config.add_runtime_admin(user.id)
                
                embed = EmbedFormatter.create_success_embed(
                    f"✅ 用户 **{user.display_name}** 已成功添加为管理员\n"
                    f"权限级别: **{permissions}**\n"
                    f"备注: {notes or '无'}",
                    title="管理员添加成功",
                    user_name=interaction.user.display_name
                )
                
                self.logger.info(f"管理员 {interaction.user.display_name} 通过面板添加了新管理员: {user.display_name}")
                
            else:
                embed = EmbedFormatter.create_error_embed(
                    "添加管理员时发生错误，可能用户已经是管理员",
                    title="添加失败",
                    user_name=interaction.user.display_name
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ 用户ID必须是数字", ephemeral=True)
        except Exception as e:
            self.logger.error(f"添加管理员失败: {e}")
            await interaction.response.send_message(f"❌ 添加失败: {str(e)}", ephemeral=True)


class RemoveAdminSelectView(discord.ui.View):
    """移除管理员选择视图"""
    
    def __init__(self, user_id: int, admin_users: List[Dict], logger):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.logger = logger
        
        # 创建选择菜单选项
        options = []
        for admin in admin_users[:25]:  # Discord限制25个选项
            options.append(discord.SelectOption(
                label=admin['display_name'],
                description=f"{admin['permissions']} | 添加于 {admin['created_at'][:10]}",
                value=str(admin['user_id'])
            ))
        
        if options:
            select = AdminRemoveSelect(options, self.user_id, self.logger)
            self.add_item(select)


class AdminRemoveSelect(discord.ui.Select):
    """管理员移除选择器"""
    
    def __init__(self, options: List[discord.SelectOption], user_id: int, logger):
        super().__init__(
            placeholder="选择要移除的管理员...",
            options=options
        )
        self.user_id = user_id
        self.logger = logger
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        try:
            user_id = int(self.values[0])
            
            # 获取要移除的用户信息
            user_info = await database.get_admin_user(user_id)
            if not user_info:
                await interaction.response.send_message("❌ 找不到该管理员", ephemeral=True)
                return
            
            # 移除管理员
            success = await database.remove_admin_user(user_id)
            
            if success:
                # 从运行时配置中移除
                config.remove_runtime_admin(user_id)
                
                embed = EmbedFormatter.create_success_embed(
                    f"✅ 管理员 **{user_info['display_name']}** 已成功移除",
                    title="管理员移除成功",
                    user_name=interaction.user.display_name
                )
                
                self.logger.info(f"管理员 {interaction.user.display_name} 通过面板移除了管理员: {user_info['display_name']}")
                
            else:
                embed = EmbedFormatter.create_error_embed(
                    "移除管理员时发生错误",
                    title="移除失败",
                    user_name=interaction.user.display_name
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"移除管理员失败: {e}")
            await interaction.response.send_message(f"❌ 移除失败: {str(e)}", ephemeral=True)


class DataStatsView(discord.ui.View):
    """数据统计面板"""
    
    def __init__(self, user_id: int, logger):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.logger = logger
    
    @discord.ui.button(label="📈 用户统计", style=discord.ButtonStyle.primary, row=0)
    async def user_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """用户统计"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        # 这里可以打开用户选择器或显示用户统计模态框
        modal = UserStatsModal(self.logger)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📋 最近问题", style=discord.ButtonStyle.secondary, row=0)
    async def recent_questions(self, interaction: discord.Interaction, button: discord.ui.Button):
        """最近问题统计"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 获取最近24小时的问题
            questions = await database.get_recent_questions(limit=10, hours=24)
            
            if not questions:
                embed = EmbedFormatter.create_error_embed(
                    "最近24小时内没有问题记录",
                    title="暂无数据"
                )
            else:
                embed = discord.Embed(
                    title="📋 最近问题记录",
                    description=f"最近24小时共 **{len(questions)}** 个问题",
                    color=0x3498DB,
                    timestamp=datetime.now()
                )
                
                for i, q in enumerate(questions[:5]):  # 显示前5个
                    question_preview = q['question'][:100] + ("..." if len(q['question']) > 100 else "")
                    created_time = datetime.fromisoformat(q['created_at'])
                    time_str = created_time.strftime("%m-%d %H:%M")
                    
                    embed.add_field(
                        name=f"❓ {q['user_name']} ({time_str})",
                        value=f"{question_preview}\n"
                              f"{'🖼️ 包含图片' if q.get('has_image') else ''} "
                              f"{'⏱️ ' + str(q['response_time'])[:4] + 's' if q.get('response_time') else ''}",
                        inline=False
                    )
                
                if len(questions) > 5:
                    embed.add_field(
                        name="📊 更多数据",
                        value=f"还有 **{len(questions) - 5}** 个问题未显示",
                        inline=False
                    )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"获取最近问题失败: {e}")
            await interaction.followup.send(f"❌ 操作失败: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="⚠️ API错误", style=discord.ButtonStyle.danger, row=0)
    async def api_errors(self, interaction: discord.Interaction, button: discord.ui.Button):
        """API错误统计"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 获取API错误统计
            error_stats = await database.get_api_error_statistics(hours=24)
            
            embed = discord.Embed(
                title="⚠️ API错误统计",
                description="最近24小时的API错误情况",
                color=0xE74C3C,
                timestamp=datetime.now()
            )
            
            if error_stats and error_stats.get('total_errors', 0) > 0:
                total_errors = error_stats['total_errors']
                embed.add_field(
                    name="📊 错误总数",
                    value=f"**{total_errors}** 个错误",
                    inline=True
                )
                
                # 按类型统计错误分布
                by_type = error_stats.get('by_type', [])
                if by_type:
                    error_types = "\n".join([
                        f"• {item['type']}: **{item['total_count']}** 次"
                        for item in by_type[:5]
                    ])
                    
                    embed.add_field(
                        name="🔍 错误类型分布",
                        value=error_types,
                        inline=False
                    )
                
                # 按严重程度统计
                by_severity = error_stats.get('by_severity', [])
                if by_severity:
                    severity_stats = "\n".join([
                        f"• {item['severity'].title()}: **{item['total_count']}** 次"
                        for item in by_severity[:5]
                    ])
                    
                    embed.add_field(
                        name="⚠️ 严重程度分布",
                        value=severity_stats,
                        inline=False
                    )
            else:
                embed.add_field(
                    name="✅ 系统状态",
                    value="最近24小时内没有API错误记录",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"获取API错误统计失败: {e}")
            await interaction.followup.send(f"❌ 操作失败: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="🔙 返回", style=discord.ButtonStyle.secondary, row=1)
    async def go_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """返回主面板"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        main_view = AdminPanelView(self.user_id, self.logger)
        embed = await main_view._create_system_status_embed()  # 重用系统状态作为主面板
        main_embed = discord.Embed(
            title="🎛️ 管理员控制面板",
            description="选择您要执行的管理操作",
            color=0x2ECC71,
            timestamp=datetime.now()
        )
        
        main_embed.add_field(
            name="🔧 功能模块",
            value="• **系统状态** - 查看系统运行状态\n"
                  "• **用户管理** - 管理管理员用户\n"
                  "• **数据统计** - 查看使用统计\n"
                  "• **通知管理** - 管理系统通知\n"
                  "• **系统维护** - 执行维护任务",
            inline=False
        )
        
        await interaction.response.edit_message(embed=main_embed, view=main_view)


class UserStatsModal(discord.ui.Modal, title="用户统计查询"):
    """用户统计查询模态框"""
    
    def __init__(self, logger):
        super().__init__()
        self.logger = logger
    
    user_id = discord.ui.TextInput(
        label="用户ID",
        placeholder="请输入要查询的用户ID",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_id.value)
            
            # 获取用户信息
            try:
                user = await interaction.client.fetch_user(user_id)
            except:
                await interaction.response.send_message(
                    "❌ 找不到该用户，请检查用户ID是否正确", 
                    ephemeral=True
                )
                return
            
            # 获取用户统计
            stats = await database.get_user_stats(user_id)
            
            if not stats:
                embed = EmbedFormatter.create_error_embed(
                    f"没有找到用户 {user.display_name} 的使用记录",
                    title="暂无数据"
                )
            else:
                embed = discord.Embed(
                    title=f"📊 用户统计 - {user.display_name}",
                    color=0x3498DB,
                    timestamp=datetime.now()
                )
                
                embed.set_thumbnail(url=user.display_avatar.url)
                
                embed.add_field(
                    name="📈 使用统计",
                    value=f"总问题数: **{stats['total_questions']}**\n"
                          f"图片分析: **{stats['total_images']}**\n"
                          f"平均响应时间: **{stats['avg_response_time']:.2f}s**",
                    inline=True
                )
                
                if stats['first_question_at']:
                    first_time = datetime.fromisoformat(stats['first_question_at'])
                    embed.add_field(
                        name="⏰ 时间信息",
                        value=f"首次提问: {first_time.strftime('%Y-%m-%d %H:%M')}\n"
                              f"最近提问: {datetime.fromisoformat(stats['last_question_at']).strftime('%Y-%m-%d %H:%M') if stats['last_question_at'] else '未知'}",
                        inline=True
                    )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ 用户ID必须是数字", ephemeral=True)
        except Exception as e:
            self.logger.error(f"查询用户统计失败: {e}")
            await interaction.response.send_message(f"❌ 查询失败: {str(e)}", ephemeral=True)


class NotificationView(discord.ui.View):
    """通知管理面板"""
    
    def __init__(self, user_id: int, logger):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.logger = logger
    
    @discord.ui.button(label="📜 通知历史", style=discord.ButtonStyle.primary, row=0)
    async def notification_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        """查看通知历史"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 获取通知历史
            notifications = await database.get_admin_notification_history(limit=10)
            
            if not notifications:
                embed = EmbedFormatter.create_error_embed(
                    "暂无通知历史记录",
                    title="暂无数据"
                )
            else:
                embed = discord.Embed(
                    title="📜 管理员通知历史",
                    description=f"最近 **{len(notifications)}** 条通知记录",
                    color=0x9B59B6,
                    timestamp=datetime.now()
                )
                
                for i, notif in enumerate(notifications[:5]):
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
                        value=f"{notif['content'][:80]}{'...' if len(notif['content']) > 80 else ''}\n{status}",
                        inline=False
                    )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"获取通知历史失败: {e}")
            await interaction.followup.send(f"❌ 操作失败: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="🧪 测试通知", style=discord.ButtonStyle.success, row=0)
    async def test_notification(self, interaction: discord.Interaction, button: discord.ui.Button):
        """测试通知系统"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        modal = TestNotificationModal(self.logger)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🔙 返回", style=discord.ButtonStyle.secondary, row=1)
    async def go_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """返回主面板"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        main_view = AdminPanelView(self.user_id, self.logger)
        main_embed = discord.Embed(
            title="🎛️ 管理员控制面板",
            description="选择您要执行的管理操作",
            color=0x2ECC71,
            timestamp=datetime.now()
        )
        
        main_embed.add_field(
            name="🔧 功能模块",
            value="• **系统状态** - 查看系统运行状态\n"
                  "• **用户管理** - 管理管理员用户\n"
                  "• **数据统计** - 查看使用统计\n"
                  "• **通知管理** - 管理系统通知\n"
                  "• **系统维护** - 执行维护任务",
            inline=False
        )
        
        await interaction.response.edit_message(embed=main_embed, view=main_view)


class TestNotificationModal(discord.ui.Modal, title="测试通知"):
    """测试通知模态框"""
    
    def __init__(self, logger):
        super().__init__()
        self.logger = logger
    
    message = discord.ui.TextInput(
        label="通知消息",
        placeholder="请输入要发送的测试消息",
        required=True,
        max_length=500,
        default="这是一条测试通知消息"
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # 这里需要导入错误监控器
            from utils.api_error_monitor import error_monitor
            
            await interaction.response.defer(ephemeral=True)
            
            if error_monitor:
                success_count, total_admins = await error_monitor.send_admin_notification(
                    notification_type="test",
                    title="🧪 测试通知",
                    content=f"{self.message.value}\n\n发起人: {interaction.user.display_name}",
                    severity="low"
                )
                
                if success_count > 0:
                    embed = EmbedFormatter.create_success_embed(
                        f"✅ 测试通知已发送\n发送成功: **{success_count}**/{total_admins} 名管理员",
                        title="通知测试成功",
                        user_name=interaction.user.display_name
                    )
                else:
                    embed = EmbedFormatter.create_error_embed(
                        f"❌ 通知发送失败\n目标管理员: {total_admins} 名",
                        title="通知测试失败",
                        user_name=interaction.user.display_name
                    )
            else:
                embed = EmbedFormatter.create_error_embed(
                    "❌ 错误监控系统未初始化",
                    title="测试失败",
                    user_name=interaction.user.display_name
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"测试通知失败: {e}")
            await interaction.followup.send(f"❌ 测试失败: {str(e)}", ephemeral=True)


class MaintenanceView(discord.ui.View):
    """系统维护面板"""
    
    def __init__(self, user_id: int, logger):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.logger = logger
    
    @discord.ui.button(label="🗑️ 清理数据库", style=discord.ButtonStyle.danger, row=0)
    async def cleanup_db(self, interaction: discord.Interaction, button: discord.ui.Button):
        """清理数据库"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        # 显示确认对话框
        view = ConfirmView(self.user_id, "cleanup_db")
        embed = discord.Embed(
            title="⚠️ 确认清理数据库",
            description="此操作将删除30天前的旧记录，此操作不可逆！",
            color=0xE74C3C
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🔄 重载模块", style=discord.ButtonStyle.secondary, row=0)
    async def reload_cog(self, interaction: discord.Interaction, button: discord.ui.Button):
        """重载模块"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        modal = ReloadCogModal(self.logger)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="💻 系统详情", style=discord.ButtonStyle.primary, row=0)
    async def system_details(self, interaction: discord.Interaction, button: discord.ui.Button):
        """查看系统详细信息"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            import platform
            import psutil
            
            # 获取系统信息
            system_info = {
                'platform': platform.system(),
                'platform_release': platform.release(),
                'architecture': platform.machine(),
                'python_version': platform.python_version(),
            }
            
            # 获取资源信息
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent(interval=1)
            
            embed = discord.Embed(
                title="💻 系统详细信息",
                color=0x3498DB,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="🖥️ 系统",
                value=f"操作系统: {system_info['platform']} {system_info['platform_release']}\n"
                      f"架构: {system_info['architecture']}\n"
                      f"Python: {system_info['python_version']}",
                inline=True
            )
            
            embed.add_field(
                name="⚡ 性能",
                value=f"CPU使用率: {cpu_percent:.1f}%\n"
                      f"内存使用率: {memory.percent:.1f}%\n"
                      f"磁盘使用率: {disk.percent:.1f}%",
                inline=True
            )
            
            embed.add_field(
                name="💾 资源",
                value=f"总内存: {memory.total / 1024**3:.1f}GB\n"
                      f"可用内存: {memory.available / 1024**3:.1f}GB\n"
                      f"可用磁盘: {disk.free / 1024**3:.1f}GB",
                inline=True
            )
            
            # Discord信息
            embed.add_field(
                name="🤖 Discord信息",
                value=f"延迟: {interaction.client.latency * 1000:.1f}ms\n"
                      f"服务器数: {len(interaction.client.guilds)}\n"
                      f"用户数: {len(interaction.client.users)}",
                inline=True
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"获取系统详细信息失败: {e}")
            await interaction.followup.send(f"❌ 操作失败: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="🔙 返回", style=discord.ButtonStyle.secondary, row=1)
    async def go_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """返回主面板"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        main_view = AdminPanelView(self.user_id, self.logger)
        main_embed = discord.Embed(
            title="🎛️ 管理员控制面板",
            description="选择您要执行的管理操作",
            color=0x2ECC71,
            timestamp=datetime.now()
        )
        
        main_embed.add_field(
            name="🔧 功能模块",
            value="• **系统状态** - 查看系统运行状态\n"
                  "• **用户管理** - 管理管理员用户\n"
                  "• **数据统计** - 查看使用统计\n"
                  "• **通知管理** - 管理系统通知\n"
                  "• **系统维护** - 执行维护任务",
            inline=False
        )
        
        await interaction.response.edit_message(embed=main_embed, view=main_view)


class ConfirmView(discord.ui.View):
    """确认操作视图"""
    
    def __init__(self, user_id: int, operation: str):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.operation = operation
    
    @discord.ui.button(label="✅ 确认", style=discord.ButtonStyle.danger, row=0)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            if self.operation == "cleanup_db":
                await database.cleanup_old_records(days=30)
                embed = EmbedFormatter.create_success_embed(
                    "✅ 数据库清理完成，已删除30天前的记录",
                    title="清理成功",
                    user_name=interaction.user.display_name
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            error_embed = EmbedFormatter.create_error_embed(
                f"操作失败: {str(e)}",
                title="操作失败",
                user_name=interaction.user.display_name
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    @discord.ui.button(label="❌ 取消", style=discord.ButtonStyle.secondary, row=0)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 您无权操作此面板", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ 操作已取消",
            color=0x95A5A6
        )
        await interaction.response.edit_message(embed=embed, view=None)


class ReloadCogModal(discord.ui.Modal, title="重载模块"):
    """重载模块模态框"""
    
    def __init__(self, logger):
        super().__init__()
        self.logger = logger
    
    cog_name = discord.ui.TextInput(
        label="模块名称",
        placeholder="请输入要重载的Cog模块名称",
        required=True,
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            cog_name = self.cog_name.value
            
            # 重载Cog
            try:
                await interaction.client.reload_extension(f"cogs.{cog_name}")
                
                embed = EmbedFormatter.create_success_embed(
                    f"✅ Cog **{cog_name}** 重载成功",
                    title="重载成功",
                    user_name=interaction.user.display_name
                )
                
                self.logger.info(f"管理员 {interaction.user.display_name} 重载了Cog: {cog_name}")
                
            except commands.ExtensionNotFound:
                embed = EmbedFormatter.create_error_embed(
                    f"❌ 找不到Cog: {cog_name}",
                    title="重载失败",
                    user_name=interaction.user.display_name
                )
            except commands.ExtensionNotLoaded:
                embed = EmbedFormatter.create_error_embed(
                    f"❌ Cog {cog_name} 未加载",
                    title="重载失败",
                    user_name=interaction.user.display_name
                )
            except Exception as e:
                embed = EmbedFormatter.create_error_embed(
                    f"❌ 重载失败: {str(e)}",
                    title="重载失败",
                    user_name=interaction.user.display_name
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"重载Cog失败: {e}")
            await interaction.response.send_message(f"❌ 重载失败: {str(e)}", ephemeral=True)


class AdminPanelCog(commands.Cog):
    """管理员面板Cog"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_logger(__name__)
    
    @app_commands.command(name="admin-panel", description="打开管理员控制面板（管理员）")
    async def admin_panel(self, interaction: discord.Interaction):
        """打开管理员控制面板"""
        # 权限检查
        is_admin = await config.is_admin_user_async(interaction.user.id)
        if not is_admin:
            embed = EmbedFormatter.create_error_embed(
                "你没有权限使用此命令",
                title="权限不足",
                user_name=interaction.user.display_name
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # 创建主面板
            view = AdminPanelView(interaction.user.id, self.logger)
            
            embed = discord.Embed(
                title="🎛️ 管理员控制面板",
                description="欢迎使用Discord QA Bot管理员控制面板\n请选择您要执行的管理操作",
                color=0x2ECC71,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="🔧 功能模块",
                value="• **系统状态** - 查看系统运行状态和基本信息\n"
                      "• **用户管理** - 管理管理员用户和权限\n"
                      "• **数据统计** - 查看使用统计和分析数据\n"
                      "• **通知管理** - 管理系统通知和消息推送\n"
                      "• **系统维护** - 执行维护任务和系统管理",
                inline=False
            )
            
            embed.add_field(
                name="ℹ️ 使用说明",
                value="• 面板将在**5分钟**后自动关闭\n"
                      "• 所有操作都只对您可见\n"
                      "• 点击按钮即可进入对应功能模块",
                inline=False
            )
            
            embed.set_footer(
                text=f"管理员: {interaction.user.display_name} | QA Bot v2.0",
                icon_url=interaction.user.display_avatar.url
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            # 记录面板访问
            self.logger.info(f"管理员 {interaction.user.display_name} ({interaction.user.id}) 打开了管理员面板")
            
        except Exception as e:
            self.logger.error(f"打开管理员面板失败: {e}")
            error_embed = EmbedFormatter.create_error_embed(
                f"打开管理员面板时发生错误: {str(e)}",
                title="面板启动失败",
                user_name=interaction.user.display_name
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """设置Cog"""
    await bot.add_cog(AdminPanelCog(bot))
