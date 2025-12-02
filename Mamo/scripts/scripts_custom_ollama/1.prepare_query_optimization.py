#!/usr/bin/env python3
"""
Prepare optimization queries for custom Ollama model
Adapts prompts for Gurobi/coptpy Python code generation
"""

import json
import argparse
from pathlib import Path
from tqdm import tqdm

# Custom prompt template adapted from deploy_ollama.py
# Modified to explicitly request Python code that prints the objective value
PROMPT_TEMPLATE = """Below is an operations research question. Build a mathematical model and corresponding python code using `gurobipy` that appropriately addresses the question.

IMPORTANT: Your code must print ONLY the final objective value as a number on the last line.

# Question:
{question}

# Response:
(Write the final answer only. Do not include chain-of-thought. End your response with the exact token <EOR> on its own line.)
"""


def generate_query(data, prompt):
    """Generate query from data using prompt template"""
    return prompt.format(question=data["Question"])


def read_jsonl_file(path):
    """Read JSONL file and return list of records"""
    data = []
    with open(path, 'r', encoding='utf-8') as file:
        for line in file:
            data.append(json.loads(line))
    return data


def write_jsonl_file(data, output_path):
    """Write list of records to JSONL file"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as file:
        for item in data:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")


def main(args):
    """Main processing function"""
    output_data = []

    # Process Easy LP problems
    if args.easy_lp:
        print(f"Reading Easy LP problems from {args.easy_lp}")
        easy_data = read_jsonl_file(args.easy_lp)
        print(f"  Loaded {len(easy_data)} Easy LP problems")

        for item in tqdm(easy_data, desc="Processing Easy LP"):
            query = generate_query(item, PROMPT_TEMPLATE)
            output_data.append({
                "id": item['id'],
                "query": query,
                "answer": item['Answer'],
                "type": item.get('Type', 'easy_lp'),
                "category": item.get('Category', 'optimization')
            })

    # Process Complex LP problems
    if args.complex_lp:
        print(f"Reading Complex LP problems from {args.complex_lp}")
        complex_data = read_jsonl_file(args.complex_lp)
        print(f"  Loaded {len(complex_data)} Complex LP problems")

        for item in tqdm(complex_data, desc="Processing Complex LP"):
            query = generate_query(item, PROMPT_TEMPLATE)
            output_data.append({
                "id": item['id'],
                "query": query,
                "answer": item['Answer'],
                "type": item.get('Type', 'complex_lp'),
                "category": item.get('Category', 'optimization')
            })

    # Write output
    write_jsonl_file(output_data, args.output)
    print(f"\n✓ Generated {len(output_data)} queries")
    print(f"✓ Output written to {args.output}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Generate optimization queries for custom Ollama model"
    )
    parser.add_argument(
        '--easy_lp',
        type=str,
        help="Path to Easy LP JSONL file"
    )
    parser.add_argument(
        '--complex_lp',
        type=str,
        help="Path to Complex LP JSONL file"
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        required=True,
        help="Path to output JSONL file"
    )

    args = parser.parse_args()

    if not args.easy_lp and not args.complex_lp:
        parser.error("At least one of --easy_lp or --complex_lp must be specified")

    main(args)
