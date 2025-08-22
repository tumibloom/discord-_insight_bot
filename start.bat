@echo off
echo Discord SillyTavern 问答机器人启动脚本
echo ====================================

REM 检查.env文件是否存在
if not exist .env (
    echo 错误: .env 配置文件不存在
    echo 请复制 .env.example 为 .env 并配置必要的环境变量
    pause
    exit /b 1
)

REM 激活conda环境（如果需要）
call conda activate mybot 2>nul

REM 启动机器人
echo 正在启动机器人...
python main.py

pause
