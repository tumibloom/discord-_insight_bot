"""
测试脚本
验证各个模块是否正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_modules():
    """测试各个模块"""
    
    print("🧪 开始模块测试...")
    print("=" * 50)
    
    # 测试配置模块
    try:
        from config import config
        print("✅ 配置模块加载成功")
        print(f"   - Discord Token: {'已配置' if config.DISCORD_TOKEN != 'your_discord_bot_token_here' else '未配置'}")
        print(f"   - Gemini API Key: {'已配置' if config.GEMINI_API_KEY else '未配置'}")
        print(f"   - 管理员用户: {len(config.ADMIN_USERS)} 个")
    except Exception as e:
        print(f"❌ 配置模块加载失败: {e}")
        return False
    
    # 测试日志模块
    try:
        from utils.logger import get_logger
        logger = get_logger("test")
        logger.info("日志系统测试")
        print("✅ 日志模块工作正常")
    except Exception as e:
        print(f"❌ 日志模块失败: {e}")
        return False
    
    # 测试数据库模块
    try:
        from database import database
        await database.initialize()
        print("✅ 数据库模块初始化成功")
        
        # 测试基本操作
        stats = await database.get_system_stats()
        print(f"   - 数据库统计: {stats}")
        
    except Exception as e:
        print(f"❌ 数据库模块失败: {e}")
        return False
    
    # 测试消息格式化模块
    try:
        from utils.message_formatter import EmbedFormatter
        embed = EmbedFormatter.create_help_embed()
        print("✅ 消息格式化模块工作正常")
    except Exception as e:
        print(f"❌ 消息格式化模块失败: {e}")
        return False
    
    # 测试AI客户端模块
    try:
        from utils.ai_client import ai_client
        print("✅ AI客户端模块加载成功")
        
        # 注意：不进行实际API调用测试，避免消耗配额
        
    except Exception as e:
        print(f"❌ AI客户端模块失败: {e}")
        return False
    
    # 测试知识库模块
    try:
        from cogs.knowledge_base import KnowledgeBaseCog
        print("✅ 知识库模块加载成功")
    except Exception as e:
        print(f"❌ 知识库模块失败: {e}")
        return False
    
    print("=" * 50)
    print("🎉 所有模块测试通过！")
    print()
    print("📋 下一步操作:")
    print("1. 配置 .env 文件中的 DISCORD_TOKEN 和 GEMINI_API_KEY")
    print("2. 设置 ADMIN_USERS 为你的Discord用户ID")  
    print("3. 运行 python main.py 启动机器人")
    
    return True

def main():
    """主函数"""
    try:
        result = asyncio.run(test_modules())
        return 0 if result else 1
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
