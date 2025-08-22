"""
API错误监控测试脚本
用于测试API错误记录和管理员通知功能
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict
from unittest.mock import AsyncMock, MagicMock

# 设置基本日志
logging.basicConfig(level=logging.INFO)

async def test_api_error_monitor():
    """测试API错误监控功能"""
    print("🧪 开始测试API错误监控功能...")
    
    try:
        # 模拟机器人实例
        mock_bot = MagicMock()
        mock_bot.fetch_user = AsyncMock()
        
        # 模拟管理员用户
        mock_admin = MagicMock()
        mock_admin.display_name = "TestAdmin"
        mock_admin.send = AsyncMock()
        mock_bot.fetch_user.return_value = mock_admin
        
        # 导入并初始化错误监控器
        from utils.api_error_monitor import APIErrorMonitor
        monitor = APIErrorMonitor(mock_bot)
        
        print("✅ API错误监控器创建成功")
        
        # 测试错误分类
        print("\n🔍 测试错误严重程度分类...")
        
        test_cases = [
            ("connection_error", "Connection refused", "critical"),
            ("api_error", "HTTP 500 Internal Server Error", "critical"),
            ("api_error", "HTTP 401 Unauthorized", "high"),
            ("api_error", "HTTP 400 Bad Request", "high"),
            ("parse_error", "JSON decode error", "medium"),
            ("unknown_error", "Something went wrong", "low"),
        ]
        
        for error_type, error_msg, expected_severity in test_cases:
            actual_severity = monitor.classify_error_severity(error_type, error_msg)
            status = "✅" if actual_severity == expected_severity else "❌"
            print(f"{status} {error_type} -> {actual_severity} (期望: {expected_severity})")
        
        # 测试错误记录
        print("\n📝 测试错误记录功能...")
        
        # 记录几个测试错误
        test_errors = [
            {
                "error_type": "connection_error",
                "error_message": "Connection timeout to API server",
                "endpoint": "https://api.example.com",
                "user_id": 123456789
            },
            {
                "error_type": "auth_error", 
                "error_message": "Invalid API key",
                "endpoint": "https://api.example.com",
                "user_id": 987654321
            },
            {
                "error_type": "rate_limit",
                "error_message": "Too many requests",
                "endpoint": "https://api.example.com",
                "user_id": 123456789
            }
        ]
        
        for error_data in test_errors:
            await monitor.record_api_error(**error_data)
            print(f"✅ 已记录错误: {error_data['error_type']}")
        
        # 测试统计功能
        print("\n📊 测试统计功能...")
        
        stats = await monitor.get_error_statistics()
        print(f"总错误数: {stats.get('total_errors', 0)}")
        print(f"最近1小时错误数: {stats.get('last_hour', {}).get('count', 0)}")
        print(f"最近24小时错误数: {stats.get('last_day', {}).get('count', 0)}")
        
        if stats.get('most_common_errors'):
            print("最常见错误:")
            for error_key, count in list(stats['most_common_errors'].items())[:3]:
                print(f"  • {error_key}: {count}次")
        
        print("\n🎉 API错误监控功能测试完成！")
        return True
        
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("请确保在discord_qa_bot目录中运行此脚本")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_database_functions():
    """测试数据库相关功能"""
    print("\n🗄️ 测试数据库功能...")
    
    try:
        from database import database
        
        # 初始化数据库
        await database.initialize()
        print("✅ 数据库初始化成功")
        
        # 测试API错误记录
        error_id = await database.log_api_error(
            error_type="test_error",
            error_message="这是一个测试错误",
            severity="medium",
            endpoint="https://test.api.com",
            user_id=123456789,
            additional_info={"test": True, "timestamp": str(datetime.now())}
        )
        
        print(f"✅ API错误记录成功，ID: {error_id}")
        
        # 测试获取错误统计
        stats = await database.get_api_error_statistics(hours=24)
        print(f"✅ 获取错误统计成功: {stats.get('total_errors', 0)} 个错误")
        
        # 测试管理员通知记录
        notification_id = await database.log_admin_notification(
            notification_type="test",
            content="这是一个测试通知",
            title="测试通知",
            severity="low",
            recipients_count=1,
            successful_sends=1
        )
        
        print(f"✅ 管理员通知记录成功，ID: {notification_id}")
        
        # 测试获取通知历史
        notifications = await database.get_admin_notification_history(limit=5)
        print(f"✅ 获取通知历史成功: {len(notifications)} 条记录")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🚀 开始API错误监控系统测试")
    print("=" * 50)
    
    # 测试数据库功能
    db_success = await test_database_functions()
    
    # 测试错误监控器
    monitor_success = await test_api_error_monitor()
    
    print("\n" + "=" * 50)
    print("📋 测试结果总结:")
    print(f"数据库功能: {'✅ 通过' if db_success else '❌ 失败'}")
    print(f"错误监控器: {'✅ 通过' if monitor_success else '❌ 失败'}")
    
    if db_success and monitor_success:
        print("\n🎉 所有测试通过！API错误监控系统已就绪。")
        print("\n💡 提示:")
        print("• 启动机器人后，可以使用 /api-errors 查看错误统计")
        print("• 使用 /test-notification 测试管理员通知")
        print("• 使用 /system-status 查看系统状态")
        return True
    else:
        print("\n❌ 部分测试失败，请检查配置和代码。")
        return False

if __name__ == "__main__":
    import sys
    import os
    from pathlib import Path
    
    # 添加项目根目录到Python路径
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    # 设置环境变量以便测试
    if not os.getenv('DISCORD_TOKEN'):
        os.environ['DISCORD_TOKEN'] = 'test_token'
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
