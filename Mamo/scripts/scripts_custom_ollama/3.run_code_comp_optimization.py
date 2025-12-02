#!/usr/bin/env python3
"""
Evaluate generated optimization code
Executes Python code and compares results with ground truth
"""

import subprocess
import sys
import json
import argparse
import re
import math
from pathlib import Path
from tqdm import tqdm
import logging
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def execute_python_code(file_path, timeout=300):
    """
    Execute Python file and capture output

    Args:
        file_path: Path to Python file
        timeout: Timeout in seconds

    Returns:
        Tuple of (output, error)
    """
    try:
        result = subprocess.run(
            [sys.executable, str(file_path)],
            text=True,
            capture_output=True,
            check=True,
            timeout=timeout
        )
        return result.stdout.strip(), None
    except subprocess.TimeoutExpired as e:
        error_message = f"Timeout after {e.timeout} seconds"
    except subprocess.CalledProcessError as e:
        error_message = f"Execution error (return code {e.returncode}): {e.stderr.strip()}"
    except Exception as e:
        error_message = f"General error: {str(e)}"

    return None, error_message


def extract_objective_value(output):
    """
    Extract objective value from code output

    Args:
        output: stdout from code execution

    Returns:
        Float objective value or None
    """
    if not output:
        return None

    try:
        # Try to parse last line as float
        lines = output.strip().split('\n')
        last_line = lines[-1].strip()
        return float(last_line)
    except (ValueError, IndexError):
        pass

    # Try regex patterns for common optimizer output
    patterns = [
        r"Optimal objective[:\s]+([0-9.e+-]+)",
        r"Objective value[:\s]+([0-9.e+-]+)",
        r"Obj[:\s]+([0-9.e+-]+)",
        r"objval[:\s]+([0-9.e+-]+)",
        r"objVal[:\s]+([0-9.e+-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue

    return None


def comp(output, standard_answer):
    """
    Compare with relative tolerance

    Args:
        output: Generated answer
        standard_answer: Ground truth

    Returns:
        1 if match, 0 otherwise
    """
    dif = abs(float(output) - float(standard_answer))
    if float(standard_answer) == 0:
        rate = dif * 1e-4
    else:
        rate = dif / float(standard_answer)
    if abs(rate) <= 1e-4:
        return 1
    else:
        return 0


def compare_output_with_standard(output, standard_answer):
    """
    Compare output with standard answer using tolerance

    Tolerance: relative error <= 1e-4 OR absolute difference < 1

    Args:
        output: Generated answer
        standard_answer: Ground truth

    Returns:
        True if match, False otherwise
    """
    # Check if the output is a valid float
    try:
        float_output = float(output)
    except (ValueError, TypeError):
        return False

    # Scale by decimal places and check absolute difference
    if '.' in str(standard_answer):
        digit = len(str(standard_answer).split('.')[1])
        if digit <= 2:
            digit = 2
        s_ans = float(standard_answer) * 10 ** digit
        ans = float_output * 10 ** digit
        return (abs(ans - s_ans) < 1 or comp(output, standard_answer))
    else:
        digit = 2
        s_ans = float(standard_answer) * 10 ** digit
        ans = float_output * 10 ** digit
        return (abs(ans - s_ans) < 1 or comp(output, standard_answer))


def handle_error(file_path, output_folder, error_type="execution"):
    """
    Copy error file to error folder

    Args:
        file_path: Path to file with error
        output_folder: Base output folder
        error_type: Type of error (execution, parse, wrong_answer, timeout)
    """
    error_path = output_folder / f"{error_type}_errors"
    error_path.mkdir(exist_ok=True)
    try:
        shutil.copy(file_path, error_path / file_path.name)
    except Exception as e:
        logging.error(f"Failed to copy {file_path.name} to {error_path}: {e}")


def load_standard_answers(jsonl_paths):
    """
    Load standard answers from JSONL files

    Args:
        jsonl_paths: List of paths to JSONL files

    Returns:
        Dict mapping id to (answer, type)
    """
    answers = {}
    for path in jsonl_paths:
        if not path:
            continue
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                answers[data['id']] = {
                    'answer': data['Answer'],
                    'type': data.get('Type', 'unknown')
                }
    return answers


def process_files(code_dir, output_folder, standard_answers):
    """
    Process all generated code files

    Args:
        code_dir: Directory with generated Python files
        output_folder: Output directory for results
        standard_answers: Dict of ground truth answers

    Returns:
        Dict with evaluation metrics
    """
    code_dir = Path(code_dir)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    # Initialize counters
    correct_count = 0
    execution_failed = 0
    parse_failed = 0
    wrong_answer = 0
    timeout_count = 0
    total_count = len(list(code_dir.glob("*.py")))

    # Track by category
    category_stats = {
        'easy_lp': {'correct': 0, 'total': 0},
        'complex_lp': {'correct': 0, 'total': 0}
    }

    results = []

    # Process each file
    for file_path in tqdm(list(code_dir.glob("*.py")), desc="Evaluating code"):
        file_id = int(file_path.stem.split('_')[-1])

        # Get standard answer
        std_data = standard_answers.get(file_id)
        if std_data is None:
            logging.warning(f"No standard answer for {file_path.name}")
            continue

        std_answer = std_data['answer']
        problem_type = std_data['type']

        # Track category totals
        if problem_type in category_stats:
            category_stats[problem_type]['total'] += 1

        # Execute code
        output, error = execute_python_code(file_path, timeout=300)

        if error:
            # Execution failed
            if "Timeout" in error:
                timeout_count += 1
                handle_error(file_path, output_folder, "timeout")
                status = "timeout"
            else:
                execution_failed += 1
                handle_error(file_path, output_folder, "execution")
                status = "execution_error"

            results.append({
                "id": file_id,
                "status": status,
                "error": error,
                "expected": std_answer,
                "type": problem_type
            })
            continue

        # Extract objective value
        obj_value = extract_objective_value(output)

        if obj_value is None:
            # Could not parse objective
            parse_failed += 1
            handle_error(file_path, output_folder, "parse")
            results.append({
                "id": file_id,
                "status": "parse_error",
                "output": output[:500],  # Truncate long output
                "expected": std_answer,
                "type": problem_type
            })
            continue

        # Compare with standard answer
        is_correct = compare_output_with_standard(obj_value, std_answer)

        if is_correct:
            correct_count += 1
            if problem_type in category_stats:
                category_stats[problem_type]['correct'] += 1
            results.append({
                "id": file_id,
                "status": "correct",
                "output": obj_value,
                "expected": std_answer,
                "type": problem_type
            })
        else:
            wrong_answer += 1
            handle_error(file_path, output_folder, "wrong_answer")
            results.append({
                "id": file_id,
                "status": "wrong_answer",
                "output": obj_value,
                "expected": std_answer,
                "diff": abs(float(obj_value) - float(std_answer)),
                "type": problem_type
            })

    # Save detailed results
    results_path = output_folder / "evaluation_results.jsonl"
    with open(results_path, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    # Calculate metrics
    executed_count = total_count - execution_failed - timeout_count

    summary = {
        "total": total_count,
        "correct": correct_count,
        "execution_failed": execution_failed,
        "parse_failed": parse_failed,
        "wrong_answer": wrong_answer,
        "timeout": timeout_count,
        "accuracy": correct_count / total_count if total_count > 0 else 0,
        "executable_rate": executed_count / total_count if total_count > 0 else 0
    }

    # Add category-specific metrics
    for cat_name, cat_data in category_stats.items():
        if cat_data['total'] > 0:
            summary[f"{cat_name}_accuracy"] = cat_data['correct'] / cat_data['total']
            summary[f"{cat_name}_total"] = cat_data['total']
            summary[f"{cat_name}_correct"] = cat_data['correct']

    # Save summary
    summary_path = output_folder / "accuracy.jsonl"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(summary, ensure_ascii=False) + '\n')

    return summary


def main(args):
    """Main processing function"""
    # Load standard answers
    logging.info("Loading standard answers...")
    jsonl_paths = [args.easy_lp, args.complex_lp]
    standard_answers = load_standard_answers(jsonl_paths)
    logging.info(f"✓ Loaded {len(standard_answers)} standard answers")

    # Process files
    logging.info(f"Processing generated code from {args.code_dir}...")
    summary = process_files(args.code_dir, args.output_dir, standard_answers)

    # Print results
    logging.info("\n" + "=" * 60)
    logging.info("EVALUATION RESULTS")
    logging.info("=" * 60)
    logging.info(f"Total problems:      {summary['total']}")
    logging.info(f"Correct:             {summary['correct']} ({summary['accuracy']:.2%})")
    logging.info(f"Execution failed:    {summary['execution_failed']}")
    logging.info(f"Parse failed:        {summary['parse_failed']}")
    logging.info(f"Wrong answer:        {summary['wrong_answer']}")
    logging.info(f"Timeout:             {summary['timeout']}")
    logging.info(f"Executable rate:     {summary['executable_rate']:.2%}")

    # Category breakdown
    if 'easy_lp_accuracy' in summary:
        logging.info(f"\nEasy LP:             {summary['easy_lp_correct']}/{summary['easy_lp_total']} ({summary['easy_lp_accuracy']:.2%})")
    if 'complex_lp_accuracy' in summary:
        logging.info(f"Complex LP:          {summary['complex_lp_correct']}/{summary['complex_lp_total']} ({summary['complex_lp_accuracy']:.2%})")

    logging.info("=" * 60)
    logging.info(f"\n✓ Results saved to: {args.output_dir}")
    logging.info(f"  - Summary: {args.output_dir}/accuracy.jsonl")
    logging.info(f"  - Details: {args.output_dir}/evaluation_results.jsonl")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Evaluate generated optimization code"
    )
    parser.add_argument(
        '-c', '--code_dir',
        type=str,
        required=True,
        help="Directory with generated Python files"
    )
    parser.add_argument(
        '-o', '--output_dir',
        type=str,
        required=True,
        help="Output directory for evaluation results"
    )
    parser.add_argument(
        '--easy_lp',
        type=str,
        help="Path to Easy LP JSONL file with ground truth"
    )
    parser.add_argument(
        '--complex_lp',
        type=str,
        help="Path to Complex LP JSONL file with ground truth"
    )

    args = parser.parse_args()

    if not args.easy_lp and not args.complex_lp:
        parser.error("At least one of --easy_lp or --complex_lp must be specified")

    main(args)
