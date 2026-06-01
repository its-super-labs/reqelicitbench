"""
Run the ReqElicitGym evaluation script (runs all test samples).

This script:
1. Loads all tasks from the test data (no longer limited to the first 3)
2. Creates the ReqElicitGym environment
3. Builds an interviewer (the model under evaluation)
4. Runs all tasks with automatic recording and evaluation
5. Saves evaluation results and conversation records (including variance and per-application_type statistics)
"""

import os
import json
import sys
import argparse

# Add the current directory to the Python path so ReqElicitGym can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Standard imports
from ReqElicitGym.config import ReqElicitGymConfig
from ReqElicitGym.env import ReqElicitGym
from ReqElicitGym.interviewer import Interviewer


def build_parser():
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(description="Run the ReqElicitGym evaluation script (all test samples)")
    parser.add_argument("--api-key", type=str, default=None, help="API key; can also be set via OPENAI_API_KEY env var")
    parser.add_argument("--base-url", type=str, default=None, help="API base URL; can also be set via OPENAI_BASE_URL env var")
    parser.add_argument("--interviewer-model", type=str, default=None, help="LLM model to use for the interviewer")
    parser.add_argument("--gym-model", type=str, default="gpt-5.2", help="LLM model for the GYM (judge + user); default gpt-5.2")
    parser.add_argument("--use-thinking", action="store_true", help="Enable thinking mode (calls the API with enable_thinking)")
    parser.add_argument("--extra-body", type=str, default=None, help='Interviewer API extra_body JSON, e.g. \'{"enable_thinking": true}\' or \'{"thinking": {"type": "enabled"}}\'')
    parser.add_argument("--data-path", type=str, default=None, help="Path to test data file; default ReqElicitGym/data/test.json")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def main():
    """Main function: run the ReqElicitGym evaluation (all tasks)."""
    args = build_parser().parse_args()
    
    # ========= Default configuration =========
    DEFAULTS = {
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "base_url": os.environ.get("OPENAI_BASE_URL") or "https://api.chatanywhere.tech/v1",
        "interviewer_model": "Pro/deepseek-ai/DeepSeek-V3.2",
        "gym_model": "gpt-5.2",
        "use_thinking": False,
        "data_path": "ReqElicitGym/data/test.json",
        "verbose": True,
    }
    
    # ========= Resolve configuration from CLI args or environment variables =========
    api_key = args.api_key or DEFAULTS["api_key"]
    base_url = args.base_url or DEFAULTS["base_url"]
    interviewer_model = args.interviewer_model or DEFAULTS["interviewer_model"]
    gym_model = args.gym_model or DEFAULTS["gym_model"]
    use_thinking = args.use_thinking or DEFAULTS["use_thinking"]
    data_path = args.data_path or DEFAULTS["data_path"]
    verbose = args.verbose or DEFAULTS["verbose"]
    extra_body = json.loads(args.extra_body) if args.extra_body else None
    
    # Use the same API key and base URL for all components by default.
    # Override with JUDGE_API_KEY / USER_API_KEY if separate keys are needed.
    judge_api_key = os.getenv("JUDGE_API_KEY", api_key)
    user_api_key = os.getenv("USER_API_KEY", api_key)
    judge_base_url = os.getenv("JUDGE_BASE_URL", base_url)
    user_base_url = os.getenv("USER_BASE_URL", base_url)
    
    if not api_key:
        print("Error: please set the OPENAI_API_KEY environment variable or use --api-key")
        sys.exit(1)

    # Check data file
    if not os.path.exists(data_path):
        print(f"Error: file not found: {data_path}")
        print("Please ensure the data file exists")
        sys.exit(1)

    # Print task count for confirmation
    try:
        print(f"\nLoading data file: {data_path}")
        with open(data_path, "r", encoding="utf-8") as f:
            all_tasks = json.load(f)
        total_tasks_in_file = len(all_tasks)
        print(f"Data file contains {total_tasks_in_file} tasks — all will be evaluated")
    except Exception as e:
        print(f"Error: unable to load data file: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Configure result file paths
    llm = interviewer_model  # model used by the interviewer

    # Build result directories
    result_dir = "metrics_result"
    conversation_dir = "conversation_result"

    # Ensure directories exist
    os.makedirs(result_dir, exist_ok=True)
    os.makedirs(conversation_dir, exist_ok=True)

    llm_name = llm.split("/")[-1]

    # Derive thinking label from actual config rather than just the flag.
    # Models like Gemini 3.5 Flash think by default, so "no_thinking" is misleading
    # when no explicit disable was passed.
    def get_thinking_label(use_thinking, extra_body):
        if use_thinking:
            return "thinking"
        if extra_body:
            if extra_body.get("thinking_config", {}).get("thinking_budget") == 0:
                return "no_thinking"
            if extra_body.get("thinking", {}).get("type") == "disabled":
                return "no_thinking"
            if extra_body.get("enable_thinking") is False:
                return "no_thinking"
        return "default"

    thinking_label = get_thinking_label(use_thinking, extra_body)
    evaluation_result_path = f"{result_dir}/{llm_name}_{thinking_label}_all.json"
    conversation_result_path = f"{conversation_dir}/{llm_name}_{thinking_label}_all.json"

    # Create configuration
    config = ReqElicitGymConfig(
        data_path=data_path,  # Use the full data file directly
        # Judge configuration (used to assess interviewer actions)
        judge_api_key=judge_api_key,
        judge_base_url=judge_base_url,
        judge_model_name=gym_model,
        judge_temperature=0.0,
        judge_max_tokens=4096,
        judge_timeout=30.0,
        judge_extra_body=None,
        # Simulated user configuration
        user_api_key=user_api_key,
        user_base_url=user_base_url,
        user_model_name=gym_model,
        user_temperature=0.7,
        user_max_tokens=4096,
        user_timeout=30.0,
        user_extra_body=None,
        # User answer quality
        user_answer_quality="high",  # can be "high", "medium", or "low"
        # Environment settings
        max_steps=20,
        verbose=verbose,
        # Result file paths
        evaluation_result_path=evaluation_result_path,
        conversation_result_path=conversation_result_path,
    )

    # Create environment
    print("\nCreating environment...")
    try:
        env = ReqElicitGym(config)
    except Exception as e:
        print(f"Error: failed to create environment: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Reset task index: reset() in __init__ consumes task_0, so reset here so run_all_tasks starts from task_0
    env.current_task_index = 0

    # Build interviewer (constructed externally, independent of env config)
    # Use a larger max_tokens when thinking mode is enabled
    interviewer_max_tokens = 8192 if use_thinking else 4096
    interviewer = Interviewer(
        api_key=api_key,
        base_url=base_url,
        model_name=llm,  # use the model name configured above
        temperature=0.0,
        max_tokens=interviewer_max_tokens,
        # timeout=30.0,
        timeout=60.0, # kimi2.5 requires a 60-second timeout
        use_thinking=use_thinking,
        extra_body=extra_body,
    )
    print(f"Interviewer created: {interviewer}")

    # Run all tasks (the environment automatically records conversations and computes metrics)
    print("\n" + "=" * 60)
    print("Starting full evaluation run...")
    print("=" * 60)
    results = env.run_all_tasks(interviewer)

    # Save evaluation results (includes variance and per-application_type statistics)
    # Passing file_path=None uses the path configured in config
    try:
        env.save_evaluation_results(file_path=None, interviewer_model_name=interviewer.model_name)
        print(f"\nEvaluation results saved to: {config.evaluation_result_path}")
    except Exception as e:
        print(f"Error saving evaluation results: {e}")
        import traceback

        traceback.print_exc()

    # Save conversation records (includes per-turn elicitation_ratio)
    # Passing file_path=None uses the path configured in config
    try:
        env.save_conversation_results(file_path=None)
        print(f"Conversation records saved to: {config.conversation_result_path}")
    except Exception as e:
        print(f"Error saving conversation records: {e}")
        import traceback

        traceback.print_exc()

    # Print summary
    print("\n" + "=" * 60)
    print("All tasks complete!")
    print("=" * 60)
    conversation_results = results.get("conversation_results", [])
    if conversation_results:
        print(f"Total tasks: {len(conversation_results)}")
        avg_turns = sum(r.get("total_turns", 0) for r in conversation_results) / len(conversation_results)
        print(f"Average conversation turns: {avg_turns:.1f}")

    # Print evaluation metrics summary
    overall_metrics = results.get("overall_metrics", {})
    if overall_metrics:
        print(f"\nEvaluation metrics summary:")
        print(f"  Total test samples: {overall_metrics.get('total_tasks', 0)}")
        print(f"  Total implicit requirements: {overall_metrics.get('total_requirements_all_tasks', 0)}")
        print(f"  Total elicited: {overall_metrics.get('total_elicited_all_tasks', 0)}")
        print(f"\nAverage metrics (mean across test samples):")
        print(f"  Average elicitation ratio: {overall_metrics.get('elicitation_ratio', 0.0):.2%}")
        print(f"  Average TKQR: {overall_metrics.get('tkqr', 0.0):.4f}")
        print(f"  Average ORA: {overall_metrics.get('ora', 0.0):.4f}")
        print(f"\nVariances:")
        print(f"  Elicitation ratio variance: {overall_metrics.get('variance_elicitation_ratio', 0.0):.6f}")
        print(f"  TKQR variance: {overall_metrics.get('variance_tkqr', 0.0):.6f}")
        print(f"  ORA variance: {overall_metrics.get('variance_ora', 0.0):.6f}")
        print(f"\nOverall ratio (based on total counts):")
        print(f"  Total elicitation ratio: {overall_metrics.get('elicitation_ratio_from_totals', 0.0):.2%}")

        # Print statistics by application type
        app_type_stats = overall_metrics.get("application_type_statistics", {})
        if app_type_stats:
            print(f"\nStatistics by application type:")
            print(f"{'Application Type':<40} {'Tasks':<10} {'Avg Elicitation':<15} {'Avg TKQR':<12} {'Avg ORA':<12}")
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

