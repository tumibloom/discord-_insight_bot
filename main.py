"""
Discord SillyTavern 问答机器人
主程序入口文件
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.logger import setup_logger
from bot import DiscordQABot

def main():
    """主程序入口"""
    
    # 设置日志
    logger = setup_logger(
        name="main",
        level="INFO",
        log_file="logs/discord_qa_bot.log"
    )
    
    logger.info("=" * 50)
    logger.info("Discord SillyTavern 问答机器人启动中...")
    logger.info("=" * 50)
    
    try:
        # 检查必要的环境变量
        if not os.getenv('DISCORD_TOKEN'):
            logger.error("❌ DISCORD_TOKEN 环境变量未设置")
            logger.error("请复制 .env.example 为 .env 并配置必要的环境变量")
            sys.exit(1)
        
        # 检查AI配置 - 至少需要配置一种AI服务
        has_gemini = bool(os.getenv('GEMINI_API_KEY'))
        has_custom_api = bool(os.getenv('CUSTOM_API_ENDPOINT') and os.getenv('CUSTOM_API_KEY'))
        
        if not has_gemini and not has_custom_api:
            logger.error("❌ 未检测到任何AI服务配置")
            logger.error("请配置以下任一AI服务:")
            logger.error("• Gemini API: 设置 GEMINI_API_KEY")
            logger.error("• 自定义API: 设置 CUSTOM_API_ENDPOINT, CUSTOM_API_KEY, CUSTOM_API_MODEL")
            sys.exit(1)
        
        if has_custom_api:
            logger.info("✅ 检测到自定义API配置")
        if has_gemini:
            logger.info("✅ 检测到Gemini API配置")
        
        # 创建并启动机器人
        bot = DiscordQABot()
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("用户中断，程序退出")
    except Exception as e:
        logger.error(f"程序运行失败: {e}")
        sys.exit(1)
    finally:
        logger.info("程序已退出")

if __name__ == "__main__":
    main()
