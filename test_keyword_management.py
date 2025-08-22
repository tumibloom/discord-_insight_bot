#!/usr/bin/env python3
"""
动态关键词管理功能测试脚本

这个脚本演示了如何通过数据库API来管理正则关键词
在实际使用中，应该通过Discord斜杠命令来操作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from database import database
from utils.logger import get_logger

logger = get_logger("keyword_test")

async def test_keyword_management():
    """测试关键词管理功能"""
    
    print("🚀 开始测试动态关键词管理功能...")
    
    # 初始化数据库
    await database.initialize()
    
    print("\n1. 添加测试关键词...")
    
    # 添加一些测试关键词
    test_keywords = [
        {
            "pattern": r"chatgpt.*error",
            "description": "ChatGPT相关错误"
        },
        {
            "pattern": r"stable\s*diffusion.*问题",
            "description": "Stable Diffusion问题"
        },
        {
            "pattern": r"api.*limit.*exceeded",
            "description": "API限制超出错误"
        },
        {
            "pattern": r"测试.*机器人.*响应",
            "description": "测试机器人响应的关键词"
        }
    ]
    
    for kw in test_keywords:
        success = await database.add_regex_keyword(
            kw["pattern"], 
            kw["description"], 
            created_by=12345  # 模拟用户ID
        )
        print(f"  {'✅' if success else '❌'} {kw['pattern']} - {kw['description']}")
    
    print("\n2. 查看所有关键词...")
    keywords = await database.get_regex_keywords(enabled_only=False)
    print(f"共有 {len(keywords)} 个关键词:")
    
    for kw in keywords:
        status = "启用" if kw['enabled'] else "禁用"
        print(f"  - [{status}] {kw['pattern']} ({kw.get('description', '无描述')})")
    
    print("\n3. 测试关键词切换...")
    if keywords:
        test_pattern = keywords[0]['pattern']
        new_state = await database.toggle_regex_keyword(test_pattern)
        print(f"  关键词 '{test_pattern}' 状态切换为: {'启用' if new_state else '禁用'}")
    
    print("\n4. 测试触发计数...")
    if keywords:
        test_pattern = keywords[0]['pattern']
        print(f"  为关键词 '{test_pattern}' 增加触发计数...")
        await database.increment_keyword_trigger(test_pattern)
        await database.increment_keyword_trigger(test_pattern)
        await database.increment_keyword_trigger(test_pattern)
        
        # 重新获取关键词查看计数
        updated_keywords = await database.get_regex_keywords(enabled_only=False)
        for kw in updated_keywords:
            if kw['pattern'] == test_pattern:
                print(f"  触发计数: {kw['trigger_count']}")
                break
    
    print("\n5. 测试删除关键词...")
    if len(keywords) > 1:
        test_pattern = keywords[1]['pattern']
        success = await database.remove_regex_keyword(test_pattern)
        print(f"  {'✅' if success else '❌'} 删除关键词: {test_pattern}")
    
    print("\n6. 最终关键词列表:")
    final_keywords = await database.get_regex_keywords(enabled_only=False)
    for kw in final_keywords:
        status = "✅启用" if kw['enabled'] else "❌禁用"
        trigger_count = kw.get('trigger_count', 0)
        print(f"  {status} `{kw['pattern']}`")
        print(f"    描述: {kw.get('description', '无')}")
        print(f"    触发次数: {trigger_count}")
        print(f"    创建时间: {kw['created_at']}")
        print()
    
    print("✅ 测试完成！")
    print("\n🎯 使用说明:")
    print("1. 在Discord中使用 `/keyword-add` 添加新的正则关键词")
    print("2. 使用 `/keyword-list` 查看所有关键词")
    print("3. 使用 `/keyword-toggle` 启用/禁用关键词")
    print("4. 使用 `/keyword-remove` 删除关键词")
    print("5. 使用 `/keyword-reload` 重新加载关键词（管理员）")

if __name__ == "__main__":
    asyncio.run(test_keyword_management())
