"""
AI集成Cog
处理与Gemini 2.5 Flash的交互和OpenAI兼容接口
"""

import asyncio
import time
import traceback
from typing import Optional, Union
from io import BytesIO

import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image

from utils.logger import get_logger
from utils.ai_client import ai_client
from utils.message_formatter import EmbedFormatter, MessageType
from database import database
from config import config

logger = get_logger(__name__)

class AIIntegrationCog(commands.Cog, name="AI集成"):
    """AI集成功能模块"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_logger(self.__class__.__name__)
        self.request_count = 0
        self.total_response_time = 0.0
        
    async def cog_load(self):
        """Cog加载时的初始化"""
        self.logger.info("AI集成模块已加载")
    
    async def cog_unload(self):
        """Cog卸载时的清理"""
        await ai_client.close()
        self.logger.info("AI集成模块已卸载")
    
    @app_commands.command(name="ask", description="向AI询问SillyTavern相关问题")
    @app_commands.describe(question="你想问的问题")
    async def ask_question(self, interaction: discord.Interaction, question: str):
        """处理用户的问答请求"""
        await self._handle_question(
            interaction=interaction,
            question=question,
            user=interaction.user,
            channel=interaction.channel
        )
    
    @app_commands.command(name="diagnose", description="分析错误截图或配置")
    @app_commands.describe(
        image="上传截图或配置文件图片",
        description="描述遇到的问题（可选）"
    )
    async def diagnose_image(
        self, 
        interaction: discord.Interaction, 
        image: discord.Attachment, 
        description: str = ""
    ):
        """处理图像分析请求"""
        await self._handle_image_analysis(
            interaction=interaction,
            attachment=image,
            description=description,
            user=interaction.user,
            channel=interaction.channel
        )
    
    @app_commands.command(name="help-st", description="显示SillyTavern帮助信息")
    async def help_sillytavern(self, interaction: discord.Interaction):
        """显示帮助信息"""
        embed = EmbedFormatter.create_help_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _handle_question(
        self,
        interaction: discord.Interaction = None,
        question: str = "",
        user: discord.User = None,
        channel: discord.TextChannel = None,
        message: discord.Message = None
    ):
        """
        统一的问题处理方法
        
        Args:
            interaction: Discord交互对象（斜杠命令）
            question: 用户问题
            user: 提问用户
            channel: 发送频道
            message: 原始消息（关键词触发时）
        """
        start_time = time.time()
        
        try:
            # 发送初始响应
            if interaction:
                thinking_embed = EmbedFormatter.create_thinking_embed(user.display_name)
                await interaction.response.send_message(embed=thinking_embed)
            
            # 生成AI回复
            ai_response = await ai_client.generate_response(question)
            
            if not ai_response:
                error_embed = EmbedFormatter.create_error_embed(
                    "AI服务暂时不可用，请稍后再试。",
                    title="服务不可用",
                    user_name=user.display_name
                )
                
                if interaction:
                    await interaction.edit_original_response(embed=error_embed)
                else:
                    await channel.send(embed=error_embed)
                return
            
            # 计算响应时间
            response_time = time.time() - start_time
            self.request_count += 1
            self.total_response_time += response_time
            
            # 创建回复嵌入
            response_embed = EmbedFormatter.create_ai_response_embed(
                question=question,
                answer=ai_response,
                user_name=user.display_name,
                response_time=response_time,
                image_analyzed=False
            )
            
            # 发送回复
            if interaction:
                await interaction.edit_original_response(embed=response_embed)
            else:
                # 关键词触发时，回复原消息
                if message:
                    await message.reply(embed=response_embed)
                else:
                    await channel.send(embed=response_embed)
            
            # 记录到数据库
            await database.record_qa(
                user_id=user.id,
                user_name=user.display_name,
                channel_id=channel.id,
                guild_id=channel.guild.id if channel.guild else None,
                question=question,
                answer=ai_response,
                has_image=False,
                response_time=response_time
            )
            
            self.logger.info(f"成功处理用户 {user.display_name} 的问题，响应时间: {response_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"处理问题时发生错误: {e}")
            
            error_embed = EmbedFormatter.create_error_embed(
                f"处理您的问题时遇到了错误: {str(e)}",
                title="处理错误",
                user_name=user.display_name
            )
            
            try:
                if interaction:
                    await interaction.edit_original_response(embed=error_embed)
                else:
                    await channel.send(embed=error_embed)
            except:
                pass  # 如果发送错误消息也失败了，就不再尝试
            
            # 记录错误到数据库
            await database.log_error(
                error_type="question_processing",
                error_message=str(e),
                user_id=user.id,
                channel_id=channel.id,
                traceback=traceback.format_exc()
            )
    
    async def _handle_image_analysis(
        self,
        interaction: discord.Interaction = None,
        attachment: discord.Attachment = None,
        description: str = "",
        user: discord.User = None,
        channel: discord.TextChannel = None,
        message: discord.Message = None
    ):
        """
        统一的图像分析处理方法
        
        Args:
            interaction: Discord交互对象
            attachment: 图像附件
            description: 问题描述
            user: 用户
            channel: 频道
            message: 原始消息
        """
        start_time = time.time()
        
        try:
            # 检查附件类型
            if not attachment.content_type or not attachment.content_type.startswith('image/'):
                error_embed = EmbedFormatter.create_error_embed(
                    "请上传有效的图片文件！支持的格式: PNG, JPG, JPEG, GIF",
                    title="文件格式错误",
                    user_name=user.display_name
                )
                
                if interaction:
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    await channel.send(embed=error_embed)
                return
            
            # 检查文件大小 (20MB限制)
            if attachment.size > 20 * 1024 * 1024:
                error_embed = EmbedFormatter.create_error_embed(
                    "图片文件过大，请上传小于20MB的图片。",
                    title="文件过大",
                    user_name=user.display_name
                )
                
                if interaction:
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    await channel.send(embed=error_embed)
                return
            
            # 发送初始响应
            if interaction:
                thinking_embed = EmbedFormatter.create_thinking_embed(user.display_name)
                thinking_embed.add_field(
                    name="📸 正在分析图片",
                    value="请稍候，我正在分析您的截图...",
                    inline=False
                )
                await interaction.response.send_message(embed=thinking_embed)
            
            # 下载并处理图片
            image_data = await attachment.read()
            image = Image.open(BytesIO(image_data))
            
            # 构建分析问题
            analysis_question = description if description else "请分析这张SillyTavern相关的截图，说明可能的问题和解决方案。"
            
            # 调用AI分析
            ai_response = await ai_client.analyze_image(image, analysis_question)
            
            if not ai_response:
                error_embed = EmbedFormatter.create_error_embed(
                    "图像分析服务暂时不可用，请稍后再试。",
                    title="分析失败",
                    user_name=user.display_name
                )
                
                if interaction:
                    await interaction.edit_original_response(embed=error_embed)
                else:
                    await channel.send(embed=error_embed)
                return
            
            # 计算响应时间
            response_time = time.time() - start_time
            self.request_count += 1
            self.total_response_time += response_time
            
            # 创建回复嵌入
            response_embed = EmbedFormatter.create_ai_response_embed(
                question=f"图像分析: {analysis_question}",
                answer=ai_response,
                user_name=user.display_name,
                response_time=response_time,
                image_analyzed=True
            )
            
            # 添加原图片缩略图
            response_embed.set_thumbnail(url=attachment.url)
            
            # 发送回复
            if interaction:
                await interaction.edit_original_response(embed=response_embed)
            else:
                if message:
                    await message.reply(embed=response_embed)
                else:
                    await channel.send(embed=response_embed)
            
            # 记录到数据库
            await database.record_qa(
                user_id=user.id,
                user_name=user.display_name,
                channel_id=channel.id,
                guild_id=channel.guild.id if channel.guild else None,
                question=f"图像分析: {analysis_question}",
                answer=ai_response,
                has_image=True,
                response_time=response_time
            )
            
            self.logger.info(f"成功分析用户 {user.display_name} 的图片，响应时间: {response_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"图像分析时发生错误: {e}")
            
            error_embed = EmbedFormatter.create_error_embed(
                f"分析图片时遇到了错误: {str(e)}",
                title="分析错误",
                user_name=user.display_name
            )
            
            try:
                if interaction:
                    await interaction.edit_original_response(embed=error_embed)
                else:
                    await channel.send(embed=error_embed)
            except:
                pass
            
            # 记录错误到数据库
            await database.log_error(
                error_type="image_analysis",
                error_message=str(e),
                user_id=user.id,
                channel_id=channel.id,
                traceback=traceback.format_exc()
            )
    
    def get_stats(self) -> dict:
        """获取AI模块统计信息"""
        avg_response_time = (
            self.total_response_time / self.request_count 
            if self.request_count > 0 else 0
        )
        
        return {
            'request_count': self.request_count,
            'avg_response_time': avg_response_time,
            'total_response_time': self.total_response_time
        }

async def setup(bot: commands.Bot):
    """设置Cog"""
    await bot.add_cog(AIIntegrationCog(bot))
