"""
AI客户端模块
统一管理AI模型调用，支持Gemini 2.5 Flash和OpenAI兼容接口
"""

import asyncio
import aiohttp
import base64
from io import BytesIO
from typing import Dict, List, Optional, Union, Any
from PIL import Image
import google.generativeai as genai

from utils.logger import get_logger
from config import config

logger = get_logger(__name__)

class AIClient:
    """AI客户端统一接口"""
    
    def __init__(self):
        self.gemini_client = None
        self.session = None
        self._setup_clients()
    
    def _setup_clients(self):
        """初始化AI客户端"""
        gemini_available = False
        custom_api_available = False
        
        try:
            # 检查自定义API配置
            if config.CUSTOM_API_ENDPOINT and config.CUSTOM_API_KEY:
                custom_api_available = True
                logger.info(f"自定义API配置已启用: {config.CUSTOM_API_ENDPOINT}")
                logger.info(f"自定义API模型: {config.CUSTOM_API_MODEL}")
            
            # 检查Gemini配置
            if config.GEMINI_API_KEY:
                genai.configure(api_key=config.GEMINI_API_KEY)
                self.gemini_client = genai.GenerativeModel(config.GEMINI_MODEL)
                gemini_available = True
                logger.info(f"Gemini客户端初始化成功，模型: {config.GEMINI_MODEL}")
            
            # 根据配置情况提供相应的信息
            if custom_api_available and gemini_available:
                logger.info("✅ 检测到多个AI配置，优先使用自定义API")
            elif custom_api_available:
                logger.info("✅ 使用自定义API作为AI服务提供商")
            elif gemini_available:
                logger.info("✅ 使用Gemini作为AI服务提供商")
            else:
                logger.warning("⚠️ 未检测到任何AI配置！请配置GEMINI_API_KEY或自定义API设置")
                logger.warning("   自定义API需要: CUSTOM_API_ENDPOINT, CUSTOM_API_KEY, CUSTOM_API_MODEL")
                logger.warning("   Gemini需要: GEMINI_API_KEY")
                
        except Exception as e:
            logger.error(f"初始化AI客户端失败: {e}")
    
    def get_available_apis(self) -> Dict[str, bool]:
        """获取可用的API状态"""
        return {
            'custom_api': bool(config.CUSTOM_API_ENDPOINT and config.CUSTOM_API_KEY),
            'gemini': bool(config.GEMINI_API_KEY and self.gemini_client),
            'has_any_api': bool(
                (config.CUSTOM_API_ENDPOINT and config.CUSTOM_API_KEY) or 
                (config.GEMINI_API_KEY and self.gemini_client)
            )
        }
    
    async def get_session(self) -> aiohttp.ClientSession:
        """获取或创建HTTP会话"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=config.REQUEST_TIMEOUT)
            )
        return self.session
    
    async def close(self):
        """关闭HTTP会话"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _prepare_sillytavern_prompt(self, user_question: str, context: Optional[str] = None) -> str:
        """准备SillyTavern专用的AI提示词"""
        base_prompt = """你是一个专业的SillyTavern技术支持助手。请根据用户的问题提供准确、详细的解决方案。

SillyTavern是一个用于AI聊天的前端界面，常见问题包括：
- API连接问题 (OpenAI, Claude, Gemini等)
- 角色卡导入和配置
- 聊天设置和参数调整
- 插件和扩展使用
- 性能优化和故障排除

请用中文回复，提供具体的操作步骤，必要时包含代码示例或配置参数。

用户问题: {question}"""

        if context:
            base_prompt += f"\n\n相关上下文: {context}"
        
        return base_prompt.format(question=user_question)
    
    async def generate_response(
        self, 
        prompt: str, 
        image: Optional[Union[Image.Image, bytes]] = None,
        max_tokens: int = None,
        temperature: float = None
    ) -> Optional[str]:
        """
        生成AI回复
        
        Args:
            prompt: 用户输入的问题
            image: 可选的图像数据
            max_tokens: 最大token数
            temperature: 温度参数
        
        Returns:
            AI生成的回复文本
        """
        try:
            # 准备SillyTavern专用提示词
            full_prompt = self._prepare_sillytavern_prompt(prompt)
            
            # 优先使用自定义API (OpenAI兼容)
            if config.CUSTOM_API_ENDPOINT and config.CUSTOM_API_KEY:
                return await self._generate_with_custom_api(full_prompt, image, max_tokens, temperature)
            
            # 备用选择：使用Gemini
            if self.gemini_client:
                return await self._generate_with_gemini(full_prompt, image, max_tokens, temperature)
            
            logger.error("没有可用的AI客户端配置")
            return "抱歉，AI服务暂时不可用，请联系管理员检查配置。"
            
        except Exception as e:
            logger.error(f"生成AI回复时发生错误: {e}")
            return "抱歉，处理您的问题时遇到了技术问题，请稍后再试。"
    
    async def _generate_with_gemini(
        self, 
        prompt: str, 
        image: Optional[Union[Image.Image, bytes]] = None,
        max_tokens: int = None,
        temperature: float = None
    ) -> str:
        """使用Gemini生成回复"""
        try:
            # 准备输入内容
            content = [prompt]
            
            # 如果有图像，添加到输入中
            if image:
                if isinstance(image, bytes):
                    # 从字节数据创建PIL Image
                    image_obj = Image.open(BytesIO(image))
                else:
                    image_obj = image
                content.append(image_obj)
            
            # 配置生成参数
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens or config.MAX_TOKENS,
                temperature=temperature or config.TEMPERATURE,
            )
            
            # 生成回复
            response = await asyncio.to_thread(
                self.gemini_client.generate_content,
                content,
                generation_config=generation_config
            )
            
            if response.text:
                logger.info("Gemini回复生成成功")
                return response.text
            else:
                logger.warning("Gemini返回了空回复")
                return "抱歉，我无法理解您的问题，请尝试重新表述。"
                
        except Exception as e:
            logger.error(f"Gemini生成回复失败: {e}")
            raise
    
    async def _generate_with_custom_api(
        self, 
        prompt: str, 
        image: Optional[Union[Image.Image, bytes]] = None,
        max_tokens: int = None,
        temperature: float = None
    ) -> str:
        """使用自定义API生成回复"""
        try:
            session = await self.get_session()
            
            # 准备消息
            messages = [{"role": "user", "content": prompt}]
            
            # 如果有图像，添加到消息中
            if image:
                # 转换图像为base64
                if isinstance(image, Image.Image):
                    img_buffer = BytesIO()
                    image.save(img_buffer, format='PNG')
                    img_data = img_buffer.getvalue()
                else:
                    img_data = image
                
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                
                # 根据API格式调整消息结构
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                        }
                    ]
                }]
            
            # API请求数据
            data = {
                "model": config.CUSTOM_API_MODEL,  # 使用配置的模型名称
                "messages": messages,
                "max_tokens": max_tokens or config.MAX_TOKENS,
                "temperature": temperature or config.TEMPERATURE,
            }
            
            headers = {
                "Authorization": f"Bearer {config.CUSTOM_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # 发送请求
            async with session.post(
                f"{config.CUSTOM_API_ENDPOINT}/chat/completions",
                json=data,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]
                    logger.info("自定义API回复生成成功")
                    return content
                else:
                    error_text = await response.text()
                    logger.error(f"自定义API请求失败: {response.status}, {error_text}")
                    raise Exception(f"API请求失败: {response.status}")
                    
        except Exception as e:
            logger.error(f"自定义API生成回复失败: {e}")
            raise
    
    async def analyze_image(self, image: Union[Image.Image, bytes], question: str = "") -> str:
        """
        分析图像内容
        
        Args:
            image: 图像数据
            question: 关于图像的问题
        
        Returns:
            分析结果
        """
        try:
            analysis_prompt = f"""请分析这张图片，特别关注SillyTavern相关的内容：
- 如果是错误截图，请说明错误类型和可能的解决方案
- 如果是配置界面，请指出配置要点
- 如果是聊天界面，请分析可能的问题

{f"用户问题: {question}" if question else ""}

请提供详细的分析和建议。"""
            
            return await self.generate_response(analysis_prompt, image)
            
        except Exception as e:
            logger.error(f"图像分析失败: {e}")
            return "抱歉，无法分析这张图片，请确保图片格式正确且清晰可见。"

# 全局AI客户端实例
ai_client = AIClient()
