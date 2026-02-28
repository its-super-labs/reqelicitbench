#!/bin/bash
# 运行 ReqElicitGym 评估脚本（运行全部测试样本）
#
# 使用方法：
#   1. 设置环境变量（推荐）：
#      export OPENAI_API_KEY="your-api-key"
#      export OPENAI_BASE_URL="https://api.chatanywhere.tech/v1"
#      ./run_reqelicitgym_all.sh
#
#   2. 通过命令行参数传递：
#      ./run_reqelicitgym_all.sh --api-key "your-key" --base-url "your-url"
#
#   3. 传递其他参数：
#      ./run_reqelicitgym_all.sh --interviewer-model "model-name" --gym-model "gpt-5.2" --verbose
#
#   4. 查看所有可用参数：
#      ./run_reqelicitgym_all.sh --help

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# ========= 配置区域（请根据实际情况修改） =========
# API 配置（如果未设置环境变量，可以在这里设置）
# export OPENAI_API_KEY="your-api-key-here"
# export OPENAI_BASE_URL="https://api.chatanywhere.tech/v1"

# 可选：为 judge/user 单独配置（如果不设置，将使用 OPENAI_API_KEY）
# export JUDGE_API_KEY="your-judge-api-key"
# export USER_API_KEY="your-user-api-key"
# export JUDGE_BASE_URL="your-judge-base-url"
# export USER_BASE_URL="your-user-base-url"

# ========= 默认参数 =========
# 如果不想通过命令行传递参数，可以在这里设置默认值
DEFAULT_INTERVIEWER_MODEL="Pro/deepseek-ai/DeepSeek-V3.2"
DEFAULT_GYM_MODEL="gpt-5.2"
DEFAULT_DATA_PATH="ReqElicitGym/data/test.json"

# ========= 检查环境变量 =========
if [ -z "$OPENAI_API_KEY" ]; then
    echo "警告: 未设置 OPENAI_API_KEY 环境变量"
    echo "请设置环境变量或使用 --api-key 参数"
    echo ""
fi

# ========= 构建 Python 命令 =========
# 直接传递所有参数给 Python 脚本（Python 脚本内部有默认值处理）
PYTHON_CMD="python3 run_reqelicitgym.py"

# ========= 运行脚本 =========
echo "=========================================="
echo "运行 ReqElicitGym 评估脚本"
echo "=========================================="
echo "工作目录: $SCRIPT_DIR"
if [ "$#" -gt 0 ]; then
    echo "传递的参数: $*"
    PYTHON_CMD="$PYTHON_CMD $*"
else
    echo "使用默认参数（可在脚本中修改或通过命令行传递）"
fi
echo ""

# 执行 Python 脚本
$PYTHON_CMD

# 检查退出状态
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "脚本执行成功！"
    echo "=========================================="
else
    echo ""
    echo "=========================================="
    echo "脚本执行失败，退出码: $EXIT_CODE"
    echo "=========================================="
    exit $EXIT_CODE
fi
