"""
Discord QA机器人核心类
管理机器人的生命周期、Cog加载和事件处理
"""

import asyncio
import traceback
from pathlib import Path

import discord
from discord.ext import commands

from utils.logger import get_logger
from utils.message_formatter import EmbedFormatter
from database import database
from config import config

logger = get_logger(__name__)

class DiscordQABot:
    """Discord问答机器人核心类"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        
        # 配置Discord intents
        intents = discord.Intents.default()
        intents.message_content = True  # 需要读取消息内容
        intents.messages = True
        intents.guilds = True
        intents.guild_messages = True
        
        # 创建机器人实例
        self.bot = commands.Bot(
            command_prefix=config.BOT_PREFIX,
            intents=intents,
            help_command=None,  # 使用自定义帮助命令
            case_insensitive=True
        )
        
        # 注册事件处理器
        self._setup_events()
    
    def _setup_events(self):
        """设置机器人事件处理器"""
        
        @self.bot.event
        async def on_ready():
            """机器人就绪事件"""
            self.logger.info(f"机器人已登录: {self.bot.user}")
            self.logger.info(f"机器人ID: {self.bot.user.id}")
            self.logger.info(f"连接到 {len(self.bot.guilds)} 个服务器")
            
            # 设置机器人状态
            activity = discord.Activity(
                type=discord.ActivityType.listening,
                name="SillyTavern问题 | /ask"
            )
            await self.bot.change_presence(activity=activity)
            
            # 同步斜杠命令
            try:
                synced = await self.bot.tree.sync()
                self.logger.info(f"同步了 {len(synced)} 个斜杠命令")
            except Exception as e:
                self.logger.error(f"同步斜杠命令失败: {e}")
        
        @self.bot.event
        async def on_guild_join(guild):
            """加入新服务器事件"""
            self.logger.info(f"加入了新服务器: {guild.name} (ID: {guild.id})")
            
            # 查找系统频道发送欢迎消息
            if guild.system_channel:
                try:
                    embed = EmbedFormatter.create_help_embed()
                    embed.title = "👋 感谢邀请SillyTavern问答机器人！"
                    embed.description = "我是专门为SillyTavern用户提供技术支持的AI助手。"
                    
                    await guild.system_channel.send(embed=embed)
                except:
                    pass  # 如果无权限发送消息就跳过
        
        @self.bot.event
        async def on_guild_remove(guild):
            """离开服务器事件"""
            self.logger.info(f"离开了服务器: {guild.name} (ID: {guild.id})")
        
        @self.bot.event
        async def on_command_error(ctx, error):
            """命令错误处理"""
            if isinstance(error, commands.CommandNotFound):
                return  # 忽略未知命令
            
            if isinstance(error, commands.MissingPermissions):
                embed = EmbedFormatter.create_error_embed(
                    "您没有足够的权限使用此命令。",
                    title="权限不足",
                    user_name=ctx.author.display_name
                )
                await ctx.send(embed=embed)
                return
            
            if isinstance(error, commands.BadArgument):
                embed = EmbedFormatter.create_error_embed(
                    f"命令参数错误: {str(error)}",
                    title="参数错误",
                    user_name=ctx.author.display_name
                )
                await ctx.send(embed=embed)
                return
            
            # 记录未处理的错误
            self.logger.error(f"命令错误: {error}")
            self.logger.error(traceback.format_exc())
            
            # 记录错误到数据库
            await database.log_error(
                error_type="command_error",
                error_message=str(error),
                user_id=ctx.author.id,
                channel_id=ctx.channel.id,
                traceback=traceback.format_exc()
            )
            
            embed = EmbedFormatter.create_error_embed(
                "执行命令时发生了意外错误，请稍后再试。",
                title="系统错误",
                user_name=ctx.author.display_name
            )
            await ctx.send(embed=embed)
        
        @self.bot.event
        async def on_app_command_error(interaction, error):
            """应用命令（斜杠命令）错误处理"""
            self.logger.error(f"斜杠命令错误: {error}")
            self.logger.error(traceback.format_exc())
            
            # 记录错误到数据库
            await database.log_error(
                error_type="app_command_error",
                error_message=str(error),
                user_id=interaction.user.id,
                channel_id=interaction.channel.id if interaction.channel else None,
                traceback=traceback.format_exc()
            )
            
            embed = EmbedFormatter.create_error_embed(
                f"处理命令时发生错误: {str(error)}",
                title="命令错误",
                user_name=interaction.user.display_name
            )
            
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                pass  # 如果无法发送错误消息就跳过
        
        @self.bot.event
        async def on_error(event, *args, **kwargs):
            """全局错误处理"""
            self.logger.error(f"未处理的错误在事件 {event}: {traceback.format_exc()}")
    
    async def setup_database(self):
        """设置数据库"""
        try:
            await database.initialize()
            self.logger.info("数据库初始化完成")
        except Exception as e:
            self.logger.error(f"数据库初始化失败: {e}")
            raise
    
    async def load_cogs(self):
        """加载所有Cog模块"""
        cogs_to_load = [
            'ai_integration',  # AI集成
            'qa_handler',      # 问答处理
            'knowledge_base',  # 知识库管理
            'admin',           # 管理功能
        ]
        
        loaded_count = 0
        for cog_name in cogs_to_load:
            try:
                await self.bot.load_extension(f'cogs.{cog_name}')
                self.logger.info(f"已加载Cog: {cog_name}")
                loaded_count += 1
            except Exception as e:
                self.logger.error(f"加载Cog {cog_name} 失败: {e}")
        
        self.logger.info(f"成功加载 {loaded_count}/{len(cogs_to_load)} 个Cog模块")
        
        if loaded_count == 0:
            raise Exception("没有成功加载任何Cog模块")
    
    async def start_bot(self):
        """启动机器人"""
        try:
            # 初始化数据库
            await self.setup_database()
            
            # 加载Cogs
            await self.load_cogs()
            
            # 启动机器人
            self.logger.info("正在启动Discord机器人...")
            await self.bot.start(config.DISCORD_TOKEN)
            
        except Exception as e:
            self.logger.error(f"启动机器人失败: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """清理资源"""
        try:
            # 关闭AI客户端
            from utils.ai_client import ai_client
            await ai_client.close()
            
            self.logger.info("资源清理完成")
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}")
    
    def run(self):
        """运行机器人（同步方法）"""
        try:
            asyncio.run(self.start_bot())
        except KeyboardInterrupt:
            self.logger.info("接收到中断信号，正在关闭机器人...")
        except Exception as e:
            self.logger.error(f"机器人运行失败: {e}")
            raise
