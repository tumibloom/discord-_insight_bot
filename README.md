# Discord SillyTavern 问答机器人

一个专门为SillyTavern用户提供智能问答和故障排除的Discord机器人，基于Google Gemini 2.5 Flash模型。

## ✨ 功能特性

### 🤖 AI集成模块
- 支持Gemini 2.5 Flash模型
- 自定义OpenAI兼容接口支持
- 智能请求管理和错误处理
- 专业的SillyTavern知识训练

### 📝 消息监听与处理
- **被动监听**: 关键词自动触发回复
- **主动触发**: 完整的斜杠命令支持
- 智能消息分类和预处理
- 支持多轮对话上下文

### 🖼️ 图像识别功能
- 截图错误自动分析
- 配置文件智能识别
- 多模态问题诊断
- 支持PNG、JPG、GIF等格式

### 💬 回复系统
- 美观的嵌入式消息格式
- 步骤化解决方案展示
- 相关资源自动链接
- 响应时间统计显示

### 📚 知识库管理
- SillyTavern专业知识库
- 常见问题FAQ自动匹配
- 错误代码数据库
- 快速修复指南

## 🛠️ 安装部署

### 环境要求
- Python 3.8+
- Discord.py 2.3.0+
- Google Generative AI SDK

### 快速开始

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd discord_qa_bot
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入必要配置
   ```

4. **运行测试**
   ```bash
   python test_modules.py
   ```

5. **启动机器人**
   ```bash
   python main.py
   # 或者使用启动脚本（Windows）
   start.bat
   ```

### 配置说明

编辑 `.env` 文件配置以下必要参数：

```env
# Discord机器人Token（必需）
DISCORD_TOKEN=your_discord_bot_token_here

# Gemini API密钥（必需）
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp

# 管理员用户ID
ADMIN_USERS=123456789012345678,987654321098765432

# 功能开关
AUTO_REPLY_ENABLED=true
KEYWORD_TRIGGER_ENABLED=true

# 监听频道（留空监听所有频道）
MONITOR_CHANNELS=

# 其他设置
LOG_LEVEL=INFO
DATABASE_PATH=qa_bot.db
```

## 📖 使用说明

### 斜杠命令

- `/ask [问题]` - 询问SillyTavern相关问题
- `/diagnose [图片] [描述]` - 分析错误截图
- `/help-st` - 显示帮助信息
- `/search_kb [关键词]` - 搜索知识库内容
- `/error_help [错误代码]` - 获取错误解决方案
- `/quick_fix [问题类型]` - 获取快速修复指南

### 管理员命令

- `/status` - 显示机器人状态
- `/reload_cog [模块名]` - 重新加载功能模块
- `/cleanup_db [天数]` - 清理数据库记录
- `/user_stats [用户]` - 查看用户统计
- `/recent_questions` - 查看最近问题
- `/system_info` - 显示系统信息

### 自动触发

机器人会自动监听包含以下关键词的消息：
- sillytavern, silly tavern, st
- api error, 连接失败, connection failed
- character card, 角色卡, tavern
- openai, claude, gemini, token
- error, 错误, 报错, bug
- config, setting, 配置, 设置

### 图像分析

直接发送包含以下内容的消息和截图即可自动触发分析：
- "help", "帮助", "求助"
- "error", "错误", "报错"
- "problem", "问题"
- "看看", "分析", "诊断"

## 🏗️ 项目结构

```
discord_qa_bot/
├── main.py                     # 主程序入口
├── bot.py                      # 机器人核心类
├── config.py                   # 配置管理
├── database.py                 # 数据库管理
├── requirements.txt            # 依赖包列表
├── .env.example               # 环境变量示例
├── test_modules.py            # 模块测试脚本
├── start.bat                  # Windows启动脚本
├── cogs/                      # 功能模块
│   ├── ai_integration.py      # AI集成
│   ├── qa_handler.py          # 问答处理
│   ├── knowledge_base.py      # 知识库管理
│   └── admin.py               # 管理功能
├── utils/                     # 工具模块
│   ├── logger.py              # 日志系统
│   ├── ai_client.py           # AI客户端
│   └── message_formatter.py   # 消息格式化
├── data/                      # 数据文件
│   └── knowledge_base.json    # 知识库数据
└── logs/                      # 日志目录
```

## 📊 功能展示

### 智能问答
- 专业的SillyTavern技术支持
- 上下文理解能力
- 多语言支持（中英文）
- 实时响应时间统计

### 错误诊断
- 自动识别错误类型
- 提供详细解决步骤
- 相关资源链接推荐
- 配置建议优化

### 数据分析
- 用户使用统计
- 问题类型分析
- 响应性能监控
- 系统资源监控

## 🔧 开发说明

### 添加新功能模块

1. 在 `cogs/` 目录创建新的Cog文件
2. 继承 `commands.Cog` 类
3. 实现所需的命令和事件处理器
4. 在 `bot.py` 中注册新模块

### 扩展知识库

编辑 `data/knowledge_base.json` 文件，添加：
- 新的问题分类
- 错误代码定义
- 快速修复指南
- 资源链接

### 自定义AI提示词

在 `utils/ai_client.py` 中修改 `_prepare_sillytavern_prompt` 方法。

## 🐛 故障排除

### 常见问题

1. **模块导入错误**
   - 检查Python环境和依赖包安装
   - 确认项目根目录在Python路径中

2. **配置加载失败**
   - 验证 `.env` 文件格式和编码
   - 检查必要的环境变量是否设置

3. **数据库连接错误**
   - 确认数据库文件路径权限
   - 检查磁盘空间是否充足

4. **API调用失败**
   - 验证API密钥有效性
   - 检查网络连接和防火墙设置

### 获取帮助

- 运行 `python test_modules.py` 进行系统检测
- 查看 `logs/` 目录下的日志文件
- 检查Discord开发者控制台的错误信息

## � 更新日志

### v1.0.0 (2024-08-22)
- ✨ 初始版本发布
- 🤖 集成Gemini 2.5 Flash AI模型
- 💬 实现智能问答系统
- �️ 添加图像分析功能
- 📚 构建SillyTavern知识库
- 🛡️ 完善错误处理和日志系统

## 📄 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

**注意**: 使用前请确保已正确配置Discord机器人Token和Gemini API密钥。
