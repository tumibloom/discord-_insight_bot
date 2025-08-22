"""
分页视图模块
处理Discord消息的分页交互
"""

import discord
from typing import List, Optional
from datetime import datetime, timedelta

from utils.message_formatter import EmbedFormatter, MessageType

class PaginationView(discord.ui.View):
    """分页视图类"""
    
    def __init__(
        self, 
        pages: List[str], 
        question: str,
        user_name: str,
        response_time: float = None,
        image_analyzed: bool = False,
        timeout: float = 300.0  # 5分钟超时
    ):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.question = question
        self.user_name = user_name
        self.response_time = response_time
        self.image_analyzed = image_analyzed
        self.current_page = 0
        self.max_pages = len(pages)
        
        # 如果只有一页，不显示按钮
        if self.max_pages <= 1:
            self.clear_items()
    
    def create_embed(self) -> discord.Embed:
        """创建当前页面的嵌入消息"""
        embed = discord.Embed(
            title=f"{EmbedFormatter.EMOJIS[MessageType.SOLUTION]} SillyTavern 智能助手",
            description=f"为 **{self.user_name}** 提供的解答",
            color=EmbedFormatter.COLORS[MessageType.SOLUTION],
            timestamp=datetime.utcnow()
        )
        
        # 添加问题字段
        embed.add_field(
            name=f"{EmbedFormatter.EMOJIS[MessageType.QUESTION]} 问题",
            value=f"```\n{self.question[:500]}{'...' if len(self.question) > 500 else ''}\n```",
            inline=False
        )
        
        # 添加当前页面的回答
        page_title = f"{EmbedFormatter.EMOJIS[MessageType.INFO]} 解答"
        if self.max_pages > 1:
            page_title += f" (第{self.current_page + 1}页/共{self.max_pages}页)"
            
        embed.add_field(
            name=page_title,
            value=self.pages[self.current_page],
            inline=False
        )
        
        # 添加页脚信息
        footer_text = "SillyTavern QA Bot"
        if self.response_time:
            footer_text += f" • 响应时间: {self.response_time:.2f}s"
        if self.image_analyzed:
            footer_text += " • 已分析图像"
        if self.max_pages > 1:
            footer_text += f" • 第{self.current_page + 1}/{self.max_pages}页"
            
        embed.set_footer(text=footer_text)
        
        return embed
    
    def update_buttons(self):
        """更新按钮状态"""
        if self.max_pages <= 1:
            return
            
        # 更新按钮的启用状态
        self.first_page.disabled = (self.current_page == 0)
        self.previous_page.disabled = (self.current_page == 0)
        self.next_page.disabled = (self.current_page == self.max_pages - 1)
        self.last_page.disabled = (self.current_page == self.max_pages - 1)
    
    @discord.ui.button(label='⏪', style=discord.ButtonStyle.gray, disabled=True)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """跳转到第一页"""
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
    
    @discord.ui.button(label='◀️', style=discord.ButtonStyle.blurple, disabled=True)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
    
    @discord.ui.button(label='🗑️', style=discord.ButtonStyle.red)
    async def delete_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        """删除消息"""
        await interaction.response.defer()
        try:
            await interaction.delete_original_response()
        except discord.NotFound:
            pass  # 消息已被删除
    
    @discord.ui.button(label='▶️', style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """下一页"""
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
    
    @discord.ui.button(label='⏩', style=discord.ButtonStyle.gray)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """跳转到最后一页"""
        self.current_page = self.max_pages - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
    
    async def on_timeout(self):
        """超时处理"""
        # 禁用所有按钮
        for item in self.children:
            item.disabled = True
