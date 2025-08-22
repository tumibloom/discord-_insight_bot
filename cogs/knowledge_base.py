"""
知识库管理Cog
管理SillyTavern相关的知识库和常见问题解答
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any

import discord
from discord.ext import commands
from discord import app_commands

from utils.logger import get_logger
from utils.message_formatter import EmbedFormatter, MessageType
from database import database
from config import config

logger = get_logger(__name__)

class KnowledgeBaseCog(commands.Cog, name="知识库"):
    """知识库管理功能模块"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_logger(self.__class__.__name__)
        self.knowledge_base: Dict[str, Any] = {}
        self.knowledge_file = Path("data/knowledge_base.json")
        
        # 加载知识库
        asyncio.create_task(self.load_knowledge_base())
    
    async def cog_load(self):
        """Cog加载时的初始化"""
        self.logger.info("知识库模块已加载")
    
    async def load_knowledge_base(self):
        """加载知识库数据"""
        try:
            if self.knowledge_file.exists():
                with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                    self.knowledge_base = json.load(f)
                self.logger.info(f"已加载知识库，包含 {len(self.knowledge_base.get('categories', {}))} 个分类")
            else:
                self.logger.warning("知识库文件不存在，使用空知识库")
                self.knowledge_base = {}
        except Exception as e:
            self.logger.error(f"加载知识库失败: {e}")
            self.knowledge_base = {}
    
    async def save_knowledge_base(self):
        """保存知识库数据"""
        try:
            # 确保数据目录存在
            self.knowledge_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_base, f, ensure_ascii=False, indent=2)
            self.logger.info("知识库已保存")
        except Exception as e:
            self.logger.error(f"保存知识库失败: {e}")
    
    @app_commands.command(name="search_kb", description="搜索知识库内容")
    @app_commands.describe(query="搜索关键词")
    async def search_knowledge_base(self, interaction: discord.Interaction, query: str):
        """搜索知识库"""
        await interaction.response.defer()
        
        try:
            results = await self._search_knowledge(query)
            
            if not results:
                embed = EmbedFormatter.create_error_embed(
                    f"没有找到与 '{query}' 相关的知识库内容",
                    title="搜索结果为空",
                    user_name=interaction.user.display_name
                )
            else:
                embed = discord.Embed(
                    title=f"🔍 知识库搜索结果",
                    description=f"关键词: **{query}**",
                    color=EmbedFormatter.COLORS[MessageType.INFO]
                )
                
                for i, result in enumerate(results[:5], 1):  # 最多显示5个结果
                    embed.add_field(
                        name=f"{i}. {result['title']}",
                        value=result['description'][:200] + ("..." if len(result['description']) > 200 else ""),
                        inline=False
                    )
                
                if len(results) > 5:
                    embed.set_footer(text=f"还有 {len(results) - 5} 个相关结果...")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"搜索知识库失败: {e}")
            embed = EmbedFormatter.create_error_embed(
                f"搜索时发生错误: {str(e)}",
                title="搜索错误",
                user_name=interaction.user.display_name
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="error_help", description="获取特定错误代码的帮助")
    @app_commands.describe(error_code="错误代码或关键词")
    async def error_help(self, interaction: discord.Interaction, error_code: str):
        """获取错误代码帮助"""
        await interaction.response.defer()
        
        try:
            error_info = await self._get_error_help(error_code)
            
            if not error_info:
                embed = EmbedFormatter.create_error_embed(
                    f"没有找到错误代码 '{error_code}' 的相关信息",
                    title="错误代码未知",
                    user_name=interaction.user.display_name
                )
            else:
                embed = discord.Embed(
                    title=f"🔧 错误解决方案: {error_info['name']}",
                    description=error_info['description'],
                    color=EmbedFormatter.COLORS[MessageType.SOLUTION]
                )
                
                solutions_text = "\n".join([f"• {solution}" for solution in error_info['solutions']])
                embed.add_field(
                    name="💡 解决方案",
                    value=solutions_text,
                    inline=False
                )
                
                embed.set_footer(text=f"错误代码: {error_code}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"获取错误帮助失败: {e}")
            embed = EmbedFormatter.create_error_embed(
                f"获取错误信息时发生问题: {str(e)}",
                title="查询错误",
                user_name=interaction.user.display_name
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="quick_fix", description="获取常见问题的快速解决方案")
    @app_commands.describe(issue="问题类型")
    @app_commands.choices(issue=[
        app_commands.Choice(name="清理缓存", value="clear_cache"),
        app_commands.Choice(name="重置设置", value="reset_settings"),
        app_commands.Choice(name="检查日志", value="check_logs"),
    ])
    async def quick_fix(self, interaction: discord.Interaction, issue: str):
        """快速修复指南"""
        await interaction.response.defer()
        
        try:
            fix_info = self.knowledge_base.get('quick_fixes', {}).get(issue)
            
            if not fix_info:
                embed = EmbedFormatter.create_error_embed(
                    f"没有找到 '{issue}' 的快速解决方案",
                    title="解决方案不存在",
                    user_name=interaction.user.display_name
                )
            else:
                embed = discord.Embed(
                    title=f"⚡ 快速修复: {fix_info['name']}",
                    description=fix_info['description'],
                    color=EmbedFormatter.COLORS[MessageType.SOLUTION]
                )
                
                steps_text = "\n".join([f"{i}. {step}" for i, step in enumerate(fix_info['steps'], 1)])
                embed.add_field(
                    name="📋 操作步骤",
                    value=steps_text,
                    inline=False
                )
                
                embed.add_field(
                    name="⚠️ 注意事项",
                    value="请按顺序执行步骤，如问题仍未解决请寻求进一步帮助。",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"获取快速修复失败: {e}")
            embed = EmbedFormatter.create_error_embed(
                f"获取解决方案时发生错误: {str(e)}",
                title="查询错误",
                user_name=interaction.user.display_name
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="kb_stats", description="显示知识库统计信息")
    async def knowledge_base_stats(self, interaction: discord.Interaction):
        """显示知识库统计信息"""
        if not config.is_admin_user(interaction.user.id):
            await interaction.response.send_message("❌ 您没有权限使用此命令", ephemeral=True)
            return
        
        try:
            categories_count = len(self.knowledge_base.get('categories', {}))
            error_codes_count = len(self.knowledge_base.get('error_codes', {}))
            quick_fixes_count = len(self.knowledge_base.get('quick_fixes', {}))
            resources_count = len(self.knowledge_base.get('resources', {}))
            
            embed = discord.Embed(
                title="📊 知识库统计信息",
                color=EmbedFormatter.COLORS[MessageType.INFO]
            )
            
            embed.add_field(name="问题分类", value=categories_count, inline=True)
            embed.add_field(name="错误代码", value=error_codes_count, inline=True)
            embed.add_field(name="快速修复", value=quick_fixes_count, inline=True)
            embed.add_field(name="资源链接", value=resources_count, inline=True)
            
            # 添加最近更新时间
            if self.knowledge_file.exists():
                import os
                mtime = os.path.getmtime(self.knowledge_file)
                from datetime import datetime
                update_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                embed.add_field(name="最后更新", value=update_time, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"获取知识库统计失败: {e}")
            embed = EmbedFormatter.create_error_embed(
                f"获取统计信息失败: {str(e)}",
                title="统计错误",
                user_name=interaction.user.display_name
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _search_knowledge(self, query: str) -> List[Dict[str, str]]:
        """搜索知识库内容"""
        results = []
        query_lower = query.lower()
        
        # 搜索分类
        for category_id, category_info in self.knowledge_base.get('categories', {}).items():
            if (query_lower in category_info['name'].lower() or
                any(keyword.lower() in query_lower for keyword in category_info.get('keywords', []))):
                results.append({
                    'title': f"分类: {category_info['name']}",
                    'description': f"常见解决方案: {', '.join(category_info.get('common_solutions', [])[:3])}"
                })
        
        # 搜索错误代码
        for error_code, error_info in self.knowledge_base.get('error_codes', {}).items():
            if (query_lower in error_code.lower() or
                query_lower in error_info['name'].lower() or
                query_lower in error_info['description'].lower()):
                results.append({
                    'title': f"错误代码: {error_code} - {error_info['name']}",
                    'description': error_info['description']
                })
        
        # 搜索快速修复
        for fix_id, fix_info in self.knowledge_base.get('quick_fixes', {}).items():
            if (query_lower in fix_info['name'].lower() or
                query_lower in fix_info['description'].lower()):
                results.append({
                    'title': f"快速修复: {fix_info['name']}",
                    'description': fix_info['description']
                })
        
        return results
    
    async def _get_error_help(self, error_code: str) -> Optional[Dict[str, Any]]:
        """获取特定错误的帮助信息"""
        error_codes = self.knowledge_base.get('error_codes', {})
        
        # 直接匹配
        if error_code in error_codes:
            return error_codes[error_code]
        
        # 模糊匹配
        for code, info in error_codes.items():
            if (error_code.lower() in code.lower() or
                error_code.lower() in info['name'].lower()):
                return info
        
        return None
    
    def get_category_solutions(self, keywords: List[str]) -> List[str]:
        """根据关键词获取分类解决方案"""
        solutions = []
        
        for category_id, category_info in self.knowledge_base.get('categories', {}).items():
            category_keywords = [kw.lower() for kw in category_info.get('keywords', [])]
            
            # 检查是否有关键词匹配
            if any(keyword.lower() in category_keywords for keyword in keywords):
                solutions.extend(category_info.get('common_solutions', []))
        
        return list(set(solutions))  # 去重
    
    def get_resources(self) -> Dict[str, str]:
        """获取资源链接"""
        return self.knowledge_base.get('resources', {})

async def setup(bot: commands.Bot):
    """设置Cog"""
    await bot.add_cog(KnowledgeBaseCog(bot))
