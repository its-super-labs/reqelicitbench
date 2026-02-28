# ReqElicitBench（ReqElicitGym）

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Gymnasium](https://img.shields.io/badge/gymnasium-0.26%2B-green.svg)](https://gymnasium.farama.org/)

**ReqElicitBench** 是论文 **ReqElicitGym: An Evaluation Environment for Interview Competence in Conversational Requirements Elicitation** 的官方实现与基准评测代码仓库。

论文作者：Dongming Jin, Zhi Jin*, Zheng Fang, Linyu Li, Xiaotian Yang, Yuanpeng He, Xiaohong Chen（TOSEM 2025）

**语言**：[English](README.md) | [中文](README_zh.md)

## 📖 项目简介

随着大模型（LLMs）编码能力提升，自动化软件开发的瓶颈逐渐从“生成正确代码”转向“有效获取并补全用户需求”。**ReqElicitGym** 提供了一个**可交互、可自动评测、可复现**的环境，用于评估任意对话式需求获取方法（例如 LLM-based agent）的**访谈能力（interview competence）**。

本仓库包含：

- **评测数据集**：共 **101** 个网站需求获取场景，覆盖 **10** 类应用（`ReqElicitGym/data/test.json`）
- **Oracle User（模拟用户）**：基于预定义隐式需求的 LLM 模拟利益相关者
- **Task Evaluator / Judge（评测器）**：对 interviewer 的每轮动作做分类（clarify/probe/finish），并判断是否命中/获取到某条隐式需求
- **一键运行脚本**：自动保存对话过程与定量指标，支持复现实验与分析

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 支持 **OpenAI-compatible** `chat.completions` 的模型服务（需要配置 `OPENAI_API_KEY`，可选 `OPENAI_BASE_URL`）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API Key / Base URL

推荐使用环境变量：

```bash
export OPENAI_API_KEY="your-api-key"
# 可选：OpenAI-compatible 代理/网关
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

可选：给 judge / user 单独配置（不配置则复用 OPENAI_*）：

```bash
export JUDGE_API_KEY="your-judge-key"
export USER_API_KEY="your-user-key"
export JUDGE_BASE_URL="your-judge-base-url"
export USER_BASE_URL="your-user-base-url"
```

### 运行全量评测（101 个任务）

```bash
bash run_reqelicitgym.sh
```

或直接运行 Python：

```bash
python3 run_reqelicitgym.py \
  --interviewer-model "Pro/deepseek-ai/DeepSeek-V3.2" \
  --gym-model "gpt-5.2" \
  --data-path "ReqElicitGym/data/test.json"
```

开启 `thinking` 模式（适用于部分模型服务）：

```bash
python3 run_reqelicitgym.py --use-thinking
```

调试建议：复制 `test.json` 截取少量任务生成小文件，然后用 `--data-path` 指向该文件即可快速跑通流程。

## 📁 目录结构

```text
ReqElicitBench/
├── ReqElicitGym/                     # 核心环境包
│   ├── config.py                     # ReqElicitGymConfig 配置
│   ├── interviewer.py                # 被评测的 interviewer（LLM 封装）
│   ├── data/
│   │   └── test.json                 # 101 个任务（评测场景）
│   └── env/
│       ├── reqelicit_gym.py          # Gymnasium 环境 + 指标计算/聚合
│       ├── prompts.py                # judge/user 调用与评测流程
│       ├── utils.py                  # prompt 模板与解析工具
│       └── task_data.py              # 数据加载
├── run_reqelicitgym.py               # 主运行入口（全量任务）
├── run_reqelicitgym.sh               # shell 封装
├── metrics_result/                   # 输出：评测指标（JSON）
├── conversation_result/              # 输出：对话过程（JSON）
└── ReqElicitGym.pdf                  # 论文 PDF（便于查看）
```

## 🔧 主要参数说明

完整参数请运行：`python3 run_reqelicitgym.py --help`。常用参数：

- `--api-key`：API Key（或用 `OPENAI_API_KEY`）
- `--base-url`：Base URL（或用 `OPENAI_BASE_URL`）
- `--interviewer-model`：**被评测模型**（interviewer）
- `--gym-model`：**环境模型**（judge + oracle user 使用），默认 `gpt-5.2`
- `--use-thinking`：开启 interviewer 的 thinking 调用（实现通过 OpenAI-compatible `extra_body`）
- `--data-path`：数据文件路径（默认 `ReqElicitGym/data/test.json`）
- `--verbose`：输出更详细的运行日志

## 📦 数据格式（`test.json`）

每个任务是一个 JSON 对象，关键字段如下：

- `name`：系统名称
- `application_type`：应用类型（共 10 类）
- `initial_requirements`：用户的初始、欠规格化需求（对话的第一句 user utterance）
- `Implicit Requirements`：隐式需求列表，每条包含：
  - `Aspect`：`Interaction` / `Content` / `Style`
  - `RequirementText`：隐式需求文本
- `URL`：目标“完整需求”对应的用户故事列表（参考产物）

## 📊 指标与输出文件

运行结束会产出两类文件：

- `metrics_result/<llm>_<thinking|no_thinking>_all.json`
  - `overall_evaluation`：总体指标（跨任务聚合），包括：
    - **Elicitation Ratio（IRE）**：隐式需求获取比例
    - **TKQR**：Turn-discounted Key Question Rate
    - **ORA**：Optimal Round Assessment
    - `action_type_effectiveness`：不同动作类型（probe/clarify/finish/…）的有效性
    - `aspect_type_elicitation`：按 `Interaction/Content/Style` 的获取比例
    - `application_type_statistics`：按应用类型分组统计
  - `task_results`：逐任务指标

- `conversation_result/<llm>_<thinking|no_thinking>_all.json`
  - 逐任务的对话轮次记录：包含 `action_type`、是否命中隐式需求、以及每轮后的 `elicitation_ratio`

## ⚠️ 注意事项

- **接口兼容性**：本仓库使用 `openai` Python SDK 调用 **OpenAI-compatible** `chat.completions`。若你使用的服务对 “thinking” 参数要求不同，请在 `ReqElicitGym/env/prompts.py` 中调整 `extra_body`。
- **成本与时间**：全量 101 任务会对 **interviewer + judge + oracle user** 产生大量调用，耗时与花费取决于模型与网关策略。

## 📝 引用

如果你在研究中使用了本仓库，请引用.

## 📄 许可

当前仓库快照未包含 `LICENSE` 文件。如需明确使用许可或商业使用授权，请联系作者。

