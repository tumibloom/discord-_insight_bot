"""
API错误监控模块
监控API调用错误并通知管理员
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from collections import defaultdict, deque

import discord
from discord.ext import commands, tasks

from utils.logger import get_logger
from database import database
from config import config

logger = get_logger(__name__)

class APIErrorMonitor:
    """API错误监控器"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_logger(self.__class__.__name__)
        
        # 错误统计
        self.error_counts = defaultdict(int)  # 错误类型计数
        self.recent_errors = deque(maxlen=100)  # 最近的错误记录
        self.notified_errors: Set[str] = set()  # 已通知的错误（避免重复通知）
        
        # 错误阈值配置
        self.error_thresholds = {
            'critical': 1,  # 关键错误，立即通知
            'high': 3,     # 高频错误，3次后通知
            'medium': 5,   # 中等错误，5次后通知
            'low': 10      # 低级错误，10次后通知
        }
        
        # 通知冷却时间（避免频繁通知）
        self.notification_cooldown = 300  # 5分钟
        self.last_notifications: Dict[str, datetime] = {}
        
    def classify_error_severity(self, error_type: str, error_message: str) -> str:
        """根据错误类型和消息分类错误严重程度"""
        error_lower = error_message.lower()
        
        # 关键错误 - 立即通知
        if any(keyword in error_lower for keyword in [
            'connection refused', 'connection timeout', 'network unreachable',
            '500', '502', '503', '504',  # 服务器错误
            'authentication failed', 'unauthorized', 'invalid api key',
            'quota exceeded', 'rate limit exceeded',
            'service unavailable', 'internal server error'
        ]):
            return 'critical'
        
        # 高频错误
        if any(keyword in error_lower for keyword in [
            '400', 'bad request', 'invalid request',
            '401', '403', 'forbidden',
            '429', 'too many requests'
        ]):
            return 'high'
        
        # 中等错误
        if any(keyword in error_lower for keyword in [
            'timeout', 'connection error',
            'json decode', 'parse error',
            'context length', 'content filter'
        ]):
            return 'medium'
        
        # 其他为低级错误
        return 'low'
    
    async def record_api_error(
        self, 
        error_type: str, 
        error_message: str, 
        endpoint: Optional[str] = None,
        user_id: Optional[int] = None,
        additional_info: Optional[Dict] = None
    ):
        """记录API错误"""
        try:
            # 创建错误记录
            error_record = {
                'timestamp': datetime.now(),
                'error_type': error_type,
                'error_message': error_message,
                'endpoint': endpoint,
                'user_id': user_id,
                'additional_info': additional_info or {}
            }
            
            # 添加到最近错误队列
            self.recent_errors.append(error_record)
            
            # 更新错误计数
            error_key = f"{error_type}:{error_message[:50]}"  # 限制长度避免内存问题
            self.error_counts[error_key] += 1
            
            # 分类错误严重程度
            severity = self.classify_error_severity(error_type, error_message)
            
            # 记录到数据库
            await database.log_api_error(
                error_type=error_type,
                error_message=error_message,
                severity=severity,
                endpoint=endpoint,
                user_id=user_id,
                additional_info=additional_info
            )
            
            # 检查是否需要通知管理员
            await self._check_notification_threshold(error_key, severity, error_record)
            
            self.logger.warning(
                f"API错误记录: {error_type} - {error_message[:100]}..."
                f" (严重程度: {severity}, 计数: {self.error_counts[error_key]})"
            )
            
        except Exception as e:
            self.logger.error(f"记录API错误时发生异常: {e}")
    
    async def _check_notification_threshold(self, error_key: str, severity: str, error_record: Dict):
        """检查是否达到通知阈值"""
        try:
            current_count = self.error_counts[error_key]
            threshold = self.error_thresholds.get(severity, 10)
            
            # 检查是否达到阈值
            should_notify = False
            
            if severity == 'critical':
                # 关键错误立即通知
                should_notify = True
            elif current_count >= threshold:
                # 达到阈值通知
                should_notify = True
            
            if should_notify:
                # 检查通知冷却时间
                now = datetime.now()
                last_notification = self.last_notifications.get(error_key)
                
                if (last_notification is None or 
                    (now - last_notification).seconds >= self.notification_cooldown):
                    
                    await self._send_admin_notification(error_key, severity, error_record, current_count)
                    self.last_notifications[error_key] = now
                else:
                    self.logger.debug(f"错误 {error_key} 在冷却期内，跳过通知")
            
        except Exception as e:
            self.logger.error(f"检查通知阈值时发生异常: {e}")
    
    async def _send_admin_notification(self, error_key: str, severity: str, error_record: Dict, count: int):
        """发送管理员通知"""
        try:
            # 获取所有管理员ID（包括环境变量配置的和数据库中的）
            admin_ids = set(config.ADMIN_USERS)  # 环境变量管理员
            
            # 从数据库获取管理员
            try:
                db_admins = await database.get_admin_users(active_only=True)
                for admin in db_admins:
                    admin_ids.add(admin['user_id'])
            except Exception as e:
                self.logger.warning(f"获取数据库管理员列表失败: {e}")
            
            if not admin_ids:
                self.logger.warning("未配置管理员用户，无法发送通知")
                return 0, 0
            
            # 创建错误通知嵌入消息
            embed = await self._create_error_notification_embed(error_record, severity, count)
            
            # 向所有管理员发送私信
            successful_notifications = 0
            failed_notifications = 0
            
            for admin_id in admin_ids:
                try:
                    admin_user = await self.bot.fetch_user(admin_id)
                    if admin_user:
                        await admin_user.send(embed=embed)
                        successful_notifications += 1
                        self.logger.info(f"已向管理员 {admin_user.display_name} 发送API错误通知")
                        
                        # 更新数据库中管理员的最后活动时间
                        try:
                            await database.update_admin_activity(admin_id)
                        except:
                            pass  # 如果不是数据库管理员，忽略错误
                        
                except discord.HTTPException as e:
                    failed_notifications += 1
                    self.logger.warning(f"向管理员 {admin_id} 发送私信失败: {e}")
                except Exception as e:
                    failed_notifications += 1
                    self.logger.error(f"获取管理员用户 {admin_id} 失败: {e}")
            
            total_admins = len(admin_ids)
            
            if successful_notifications > 0:
                self.logger.info(f"API错误通知已发送给 {successful_notifications}/{total_admins} 个管理员")
                
                # 记录通知发送
                await database.log_admin_notification(
                    notification_type="api_error",
                    title=f"API错误警告 - {severity.upper()}",
                    content=f"{error_record['error_type']}: {error_record['error_message'][:100]}",
                    severity=severity,
                    recipients_count=total_admins,
                    successful_sends=successful_notifications,
                    failed_sends=failed_notifications
                )
            else:
                self.logger.error("未能向任何管理员发送通知")
                
            return successful_notifications, total_admins
                
        except Exception as e:
            self.logger.error(f"发送管理员通知时发生异常: {e}")
            return 0, 0
    
    async def _create_error_notification_embed(self, error_record: Dict, severity: str, count: int) -> discord.Embed:
        """创建错误通知嵌入消息"""
        # 根据严重程度选择颜色
        colors = {
            'critical': 0xFF0000,  # 红色
            'high': 0xFF8C00,      # 橙色
            'medium': 0xFFD700,    # 金色
            'low': 0x87CEEB        # 天蓝色
        }
        color = colors.get(severity, 0x87CEEB)
        
        # 严重程度图标
        severity_icons = {
            'critical': '🚨',
            'high': '⚠️',
            'medium': '🟡',
            'low': '🔵'
        }
        icon = severity_icons.get(severity, '🔵')
        
        embed = discord.Embed(
            title=f"{icon} API错误监控警报",
            description=f"检测到 **{severity.upper()}** 级别的API错误",
            color=color,
            timestamp=error_record['timestamp']
        )
        
        # 基本错误信息
        embed.add_field(
            name="🔍 错误类型",
            value=f"`{error_record['error_type']}`",
            inline=True
        )
        
        embed.add_field(
            name="📊 发生次数",
            value=f"**{count}** 次",
            inline=True
        )
        
        embed.add_field(
            name="⏰ 最新发生时间",
            value=f"<t:{int(error_record['timestamp'].timestamp())}:R>",
            inline=True
        )
        
        # 错误详情
        error_msg = error_record['error_message']
        if len(error_msg) > 500:
            error_msg = error_msg[:500] + "..."
        
        embed.add_field(
            name="📝 错误详情",
            value=f"```\n{error_msg}\n```",
            inline=False
        )
        
        # API端点信息
        if error_record.get('endpoint'):
            embed.add_field(
                name="🌐 API端点",
                value=f"`{error_record['endpoint']}`",
                inline=True
            )
        
        # 用户信息
        if error_record.get('user_id'):
            try:
                user = await self.bot.fetch_user(error_record['user_id'])
                user_info = f"{user.display_name} (`{user.id}`)" if user else f"Unknown (`{error_record['user_id']}`)"
            except:
                user_info = f"Unknown (`{error_record['user_id']}`)"
            
            embed.add_field(
                name="👤 触发用户",
                value=user_info,
                inline=True
            )
        
        # 附加信息
        if error_record.get('additional_info'):
            info_text = ""
            for key, value in error_record['additional_info'].items():
                info_text += f"**{key}**: {value}\n"
            
            if info_text:
                embed.add_field(
                    name="ℹ️ 附加信息",
                    value=info_text[:500],
                    inline=False
                )
        
        # 建议操作
        suggestions = self._get_error_suggestions(error_record['error_type'], error_record['error_message'])
        if suggestions:
            embed.add_field(
                name="💡 建议操作",
                value=suggestions,
                inline=False
            )
        
        embed.set_footer(text="QA Bot API监控系统")
        
        return embed
    
    def _get_error_suggestions(self, error_type: str, error_message: str) -> str:
        """根据错误类型获取建议操作"""
        error_lower = error_message.lower()
        
        # 网络连接问题
        if any(keyword in error_lower for keyword in ['connection', 'network', 'timeout']):
            return "• 检查网络连接状态\n• 验证API端点可访问性\n• 考虑增加请求超时时间"
        
        # 认证问题
        if any(keyword in error_lower for keyword in ['auth', 'unauthorized', 'api key', 'token']):
            return "• 检查API密钥是否正确\n• 验证API密钥是否过期\n• 确认账户权限设置"
        
        # 配额限制
        if any(keyword in error_lower for keyword in ['quota', 'rate limit', 'billing']):
            return "• 检查API配额使用情况\n• 考虑升级API计划\n• 实施请求限流策略"
        
        # 服务器错误
        if any(keyword in error_lower for keyword in ['500', '502', '503', '504', 'server error']):
            return "• 等待API服务恢复\n• 考虑使用备用API端点\n• 监控官方状态页面"
        
        # 请求格式错误
        if any(keyword in error_lower for keyword in ['400', 'bad request', 'invalid']):
            return "• 检查请求参数格式\n• 验证API文档要求\n• 确认数据编码正确"
        
        return "• 查看详细日志信息\n• 参考API文档\n• 必要时联系技术支持"
    
    async def get_error_statistics(self) -> Dict:
        """获取错误统计信息"""
        try:
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            
            # 统计最近1小时和24小时的错误
            recent_hour_errors = [
                err for err in self.recent_errors 
                if err['timestamp'] >= hour_ago
            ]
            recent_day_errors = [
                err for err in self.recent_errors 
                if err['timestamp'] >= day_ago
            ]
            
            # 按类型统计
            hour_by_type = defaultdict(int)
            day_by_type = defaultdict(int)
            
            for err in recent_hour_errors:
                hour_by_type[err['error_type']] += 1
            
            for err in recent_day_errors:
                day_by_type[err['error_type']] += 1
            
            return {
                'total_errors': len(self.recent_errors),
                'last_hour': {
                    'count': len(recent_hour_errors),
                    'by_type': dict(hour_by_type)
                },
                'last_day': {
                    'count': len(recent_day_errors),
                    'by_type': dict(day_by_type)
                },
                'most_common_errors': dict(
                    sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                )
            }
            
        except Exception as e:
            self.logger.error(f"获取错误统计时发生异常: {e}")
            return {}
    
    async def send_admin_notification(
        self,
        notification_type: str,
        title: str,
        content: str,
        severity: str = "medium"
    ) -> tuple[int, int]:
        """
        发送管理员通知（公共方法）
        
        Args:
            notification_type: 通知类型（如 "test", "api_error", "system"）
            title: 通知标题
            content: 通知内容
            severity: 严重程度（critical, high, medium, low）
            
        Returns:
            tuple[successful_count, total_admins]: 成功发送数量和总管理员数量
        """
        try:
            # 获取所有管理员ID
            admin_ids = set(config.ADMIN_USERS)  # 环境变量管理员
            
            # 从数据库获取管理员
            try:
                db_admins = await database.get_admin_users(active_only=True)
                for admin in db_admins:
                    admin_ids.add(admin['user_id'])
            except Exception as e:
                self.logger.warning(f"获取数据库管理员列表失败: {e}")
            
            if not admin_ids:
                self.logger.warning("未配置管理员用户，无法发送通知")
                return 0, 0
            
            # 创建通知嵌入消息
            embed = self._create_general_notification_embed(
                notification_type=notification_type,
                title=title,
                content=content,
                severity=severity
            )
            
            # 向所有管理员发送私信
            successful_notifications = 0
            failed_notifications = 0
            
            for admin_id in admin_ids:
                try:
                    admin_user = await self.bot.fetch_user(admin_id)
                    if admin_user:
                        await admin_user.send(embed=embed)
                        successful_notifications += 1
                        self.logger.info(f"已向管理员 {admin_user.display_name} 发送通知: {title}")
                        
                        # 更新数据库中管理员的最后活动时间
                        try:
                            await database.update_admin_activity(admin_id)
                        except:
                            pass  # 如果不是数据库管理员，忽略错误
                        
                except discord.HTTPException as e:
                    failed_notifications += 1
                    self.logger.warning(f"向管理员 {admin_id} 发送私信失败: {e}")
                except Exception as e:
                    failed_notifications += 1
                    self.logger.error(f"获取管理员用户 {admin_id} 失败: {e}")
            
            total_admins = len(admin_ids)
            
            if successful_notifications > 0:
                self.logger.info(f"通知已发送给 {successful_notifications}/{total_admins} 个管理员")
                
                # 记录通知发送
                await database.log_admin_notification(
                    notification_type=notification_type,
                    title=title,
                    content=content[:500],  # 限制长度
                    severity=severity,
                    recipients_count=total_admins,
                    successful_sends=successful_notifications,
                    failed_sends=failed_notifications
                )
            else:
                self.logger.error("未能向任何管理员发送通知")
                
            return successful_notifications, total_admins
                
        except Exception as e:
            self.logger.error(f"发送管理员通知时发生异常: {e}")
            return 0, 0
    
    def _create_general_notification_embed(
        self,
        notification_type: str,
        title: str,
        content: str,
        severity: str
    ) -> discord.Embed:
        """创建通用通知嵌入消息"""
        # 严重程度配色和图标
        severity_config = {
            'critical': {'color': 0xFF0000, 'icon': '🚨'},
            'high': {'color': 0xFF8C00, 'icon': '⚠️'},
            'medium': {'color': 0xFFD700, 'icon': '🟡'},
            'low': {'color': 0x00CED1, 'icon': '🔵'}
        }
        
        config_data = severity_config.get(severity, severity_config['medium'])
        
        embed = discord.Embed(
            title=f"{config_data['icon']} {title}",
            description=content,
            color=config_data['color'],
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📋 详细信息",
            value=f"类型: **{notification_type.upper()}**\n"
                  f"严重程度: **{severity.upper()}**\n"
                  f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            inline=False
        )
        
        embed.set_footer(text="QA Bot 管理员通知系统")
        return embed

# 全局错误监控器实例
error_monitor: Optional[APIErrorMonitor] = None

def initialize_error_monitor(bot: commands.Bot):
    """初始化错误监控器"""
    global error_monitor
    error_monitor = APIErrorMonitor(bot)
    logger.info("API错误监控器已初始化")

async def record_api_error(
    error_type: str, 
    error_message: str, 
    endpoint: Optional[str] = None,
    user_id: Optional[int] = None,
    additional_info: Optional[Dict] = None
):
    """便捷函数：记录API错误"""
    if error_monitor:
        await error_monitor.record_api_error(
            error_type=error_type,
            error_message=error_message,
            endpoint=endpoint,
            user_id=user_id,
            additional_info=additional_info
        )
    else:
        logger.warning("错误监控器未初始化，无法记录API错误")
