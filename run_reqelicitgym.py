"""
运行 ReqElicitGym 评估脚本（运行全部测试样本）

该脚本：
1. 从测试数据中加载所有任务（不再只取前3个）
2. 创建 ReqElicitGym 环境
3. 构建 interviewer（待评估的模型）
4. 运行所有任务并自动记录、评估
5. 保存评估结果和对话过程文件（包含方差和按 application_type 分类的统计）
"""

import os
import json
import sys
import argparse

# 添加当前目录到 Python 路径，以便导入 ReqElicitGym
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 使用正常的导入方式
from ReqElicitGym.config import ReqElicitGymConfig
from ReqElicitGym.env import ReqElicitGym
from ReqElicitGym.interviewer import Interviewer


def build_parser():
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(description="运行 ReqElicitGym 评估脚本（运行全部测试样本）")
    parser.add_argument("--api-key", type=str, default=None, help="API Key，也可用 OPENAI_API_KEY 环境变量")
    parser.add_argument("--base-url", type=str, default=None, help="API Base URL，也可用 OPENAI_BASE_URL 环境变量")
    parser.add_argument("--interviewer-model", type=str, default=None, help="Interviewer 使用的 LLM 模型")
    parser.add_argument("--gym-model", type=str, default="gpt-5.2", help="GYM（judge + user）使用的 LLM 模型，默认 gpt-5.2")
    parser.add_argument("--use-thinking", action="store_true", help="是否开启 thinking 模式（会调用带 enable_thinking 的接口）")
    parser.add_argument("--extra-body", type=str, default=None, help='Interviewer API extra_body JSON，例如 \'{"enable_thinking": true}\' 或 \'{"thinking": {"type": "enabled"}}\'')
    parser.add_argument("--data-path", type=str, default=None, help="测试数据文件路径，默认 ReqElicitGym/data/test.json")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    return parser


def main():
    """主函数：运行 ReqElicitGym-v8 评估（运行全部任务）"""
    args = build_parser().parse_args()
    
    # ========= 默认配置区域 =========
    DEFAULTS = {
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "base_url": os.environ.get("OPENAI_BASE_URL") or "https://api.chatanywhere.tech/v1",
        "interviewer_model": "Pro/deepseek-ai/DeepSeek-V3.2",
        "gym_model": "gpt-5.2",
        "use_thinking": False,
        "data_path": "ReqElicitGym/data/test.json",
        "verbose": True,
    }
    
    # ========= 从命令行参数或环境变量获取配置 =========
    api_key = args.api_key or DEFAULTS["api_key"]
    base_url = args.base_url or DEFAULTS["base_url"]
    interviewer_model = args.interviewer_model or DEFAULTS["interviewer_model"]
    gym_model = args.gym_model or DEFAULTS["gym_model"]
    use_thinking = args.use_thinking or DEFAULTS["use_thinking"]
    data_path = args.data_path or DEFAULTS["data_path"]
    verbose = args.verbose or DEFAULTS["verbose"]
    extra_body = json.loads(args.extra_body) if args.extra_body else None
    
    # 统一使用同一套 API key 和 base URL
    # 如需对 judge/user 再细分 key，可以继续用 JUDGE_API_KEY / USER_API_KEY 覆盖
    judge_api_key = os.getenv("JUDGE_API_KEY", api_key)
    user_api_key = os.getenv("USER_API_KEY", api_key)
    judge_base_url = os.getenv("JUDGE_BASE_URL", base_url)
    user_base_url = os.getenv("USER_BASE_URL", base_url)
    
    if not api_key:
        print("错误: 请设置 OPENAI_API_KEY 环境变量或使用 --api-key 参数")
        sys.exit(1)

    # 检查数据文件
    if not os.path.exists(data_path):
        print(f"错误: 找不到文件 {data_path}")
        print("请确保数据文件存在")
        sys.exit(1)

    # 简单打印一下任务数量，方便确认
    try:
        print(f"\n正在加载数据文件: {data_path}")
        with open(data_path, "r", encoding="utf-8") as f:
            all_tasks = json.load(f)
        total_tasks_in_file = len(all_tasks)
        print(f"数据文件包含 {total_tasks_in_file} 个任务，将对全部任务进行评估")
    except Exception as e:
        print(f"错误: 无法加载数据文件: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # 配置结果文件路径
    llm = interviewer_model  # interviewer 使用的模型

    # 构建结果目录
    result_dir = "metrics_result"
    conversation_dir = "conversation_result"

    # 确保目录存在
    os.makedirs(result_dir, exist_ok=True)
    os.makedirs(conversation_dir, exist_ok=True)

    llm_name = llm.split("/")[-1]
    # 构建完整的文件路径（用 all 标识是全量测试）
    evaluation_result_path = f"{result_dir}/{llm_name}_{'thinking' if use_thinking else 'no_thinking'}_all.json"
    conversation_result_path = f"{conversation_dir}/{llm_name}_{'thinking' if use_thinking else 'no_thinking'}_all.json"

    # 创建配置
    config = ReqElicitGymConfig(
        data_path=data_path,  # 直接使用全量数据文件
        # Judge 配置（用于判断 interviewer 的动作）
        judge_api_key=judge_api_key,
        judge_base_url=judge_base_url,
        judge_model_name=gym_model,
        judge_temperature=0.0,
        judge_max_tokens=4096,
        judge_timeout=30.0,
        judge_extra_body=None,
        # 模拟用户配置
        user_api_key=user_api_key,
        user_base_url=user_base_url,
        user_model_name=gym_model,
        user_temperature=0.7,
        user_max_tokens=4096,
        user_timeout=30.0,
        user_extra_body=None,
        # 用户回答质量
        user_answer_quality="high",  # 可以是 "high", "medium", 或 "low"
        # 环境设置
        max_steps=20,
        verbose=verbose,
        # 配置结果文件路径
        evaluation_result_path=evaluation_result_path,
        conversation_result_path=conversation_result_path,
    )

    # 创建环境
    print("\n正在创建环境...")
    try:
        env = ReqElicitGym(config)
    except Exception as e:
        print(f"错误: 创建环境失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # 重置任务索引：__init__ 中 reset() 已消耗 task_0，需重置以便 run_all_tasks 从 task_0 开始
    env.current_task_index = 0

    # 构建 interviewer（在外部构建，不依赖环境配置）
    # 如果开启 thinking，需要更大的 max_tokens
    interviewer_max_tokens = 8192 if use_thinking else 4096
    interviewer = Interviewer(
        api_key=api_key,
        base_url=base_url,
        model_name=llm,  # 使用上面配置的模型名称
        temperature=0.0,
        max_tokens=interviewer_max_tokens,
        # timeout=30.0,
        timeout=60.0, # kimi2.5的timeout是60秒
        use_thinking=use_thinking,
        extra_body=extra_body,
    )
    print(f"Interviewer 已创建: {interviewer}")

    # 运行所有任务（环境会自动记录对话和计算评估指标）
    print("\n" + "=" * 60)
    print("开始运行全量评估实验...")
    print("=" * 60)
    results = env.run_all_tasks(interviewer)

    # 保存评估结果文件（包含方差和按 application_type 分类的统计）
    # 如果不传 file_path 参数或传入 None，会使用 config 中配置的路径
    try:
        env.save_evaluation_results(file_path=None, interviewer_model_name=interviewer.model_name)
        print(f"\n评估结果已保存到: {config.evaluation_result_path}")
    except Exception as e:
        print(f"保存评估结果时出错: {e}")
        import traceback

        traceback.print_exc()

    # 保存对话过程文件（包含每轮的 elicitation_ratio）
    # 如果不传 file_path 参数或传入 None，会使用 config 中配置的路径
    try:
        env.save_conversation_results(file_path=None)
        print(f"对话过程已保存到: {config.conversation_result_path}")
    except Exception as e:
        print(f"保存对话过程时出错: {e}")
        import traceback

        traceback.print_exc()

    # 打印总结
    print("\n" + "=" * 60)
    print("所有任务完成！")
    print("=" * 60)
    conversation_results = results.get("conversation_results", [])
    if conversation_results:
        print(f"总任务数: {len(conversation_results)}")
        avg_turns = sum(r.get("total_turns", 0) for r in conversation_results) / len(conversation_results)
        print(f"平均对话轮数: {avg_turns:.1f}")

    # 打印评估指标总结
    overall_metrics = results.get("overall_metrics", {})
    if overall_metrics:
        print(f"\n评估指标总结:")
        print(f"  总测试样本数: {overall_metrics.get('total_tasks', 0)}")
        print(f"  总隐式需求数: {overall_metrics.get('total_requirements_all_tasks', 0)}")
        print(f"  总获取数: {overall_metrics.get('total_elicited_all_tasks', 0)}")
        print(f"\n平均指标（基于测试样本平均）:")
        print(f"  平均获取比例: {overall_metrics.get('elicitation_ratio', 0.0):.2%}")
        print(f"  平均 TKQR: {overall_metrics.get('tkqr', 0.0):.4f}")
        print(f"  平均 ORA: {overall_metrics.get('ora', 0.0):.4f}")
        print(f"\n方差:")
        print(f"  获取比例方差: {overall_metrics.get('variance_elicitation_ratio', 0.0):.6f}")
        print(f"  TKQR 方差: {overall_metrics.get('variance_tkqr', 0.0):.6f}")
        print(f"  ORA 方差: {overall_metrics.get('variance_ora', 0.0):.6f}")
        print(f"\n总体比例（基于总计数）:")
        print(f"  总获取比例: {overall_metrics.get('elicitation_ratio_from_totals', 0.0):.2%}")

        # 打印按 application_type 分类的统计
        app_type_stats = overall_metrics.get("application_type_statistics", {})
        if app_type_stats:
            print(f"\n按应用类型统计:")
            print(f"{'Application Type':<40} {'任务数':<10} {'平均获取比例':<15} {'平均TKQR':<12} {'平均ORA':<12}")
            print("-" * 100)
            for app_type in sorted(app_type_stats.keys()):
                stats = app_type_stats[app_type]
                print(
                    f"{app_type:<40} {stats['num_tasks']:<10} "
                    f"{stats['average_elicitation_ratio']:>13.2%} "
                    f"{stats['average_tkqr']:>10.4f} "
                    f"{stats['average_ora']:>10.4f}"
                )

    return results

if __name__ == "__main__":
    main()

