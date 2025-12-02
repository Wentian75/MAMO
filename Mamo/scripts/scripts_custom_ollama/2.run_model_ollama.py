#!/usr/bin/env python3
"""
Run inference using Ollama model
Generates Python code for optimization problems
"""

import json
import argparse
import requests
import time
import re
from pathlib import Path
from tqdm import tqdm
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class OllamaModel:
    """Ollama model interface using HTTP API"""

    def __init__(self, model_name="orlm-qwen3-8b", base_url="http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.api_url = f"{self.base_url}/api/generate"

    def check_server(self):
        """Check if Ollama server is running"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Ollama server not accessible: {e}")
            return False

    def call(self, prompt, max_retries=3, timeout=600):
        """
        Call Ollama API to generate code

        Args:
            prompt: Input prompt
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds

        Returns:
            Generated code string
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 40,
                "num_ctx": 8192,
                "num_predict": 4096,
                "stop": ["<EOR>"]
            }
        }

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    timeout=timeout
                )
                response.raise_for_status()
                result = response.json()

                # Extract generated text
                generated_text = result.get("response", "")

                # Clean the output
                cleaned_code = self.clean_code(generated_text)

                return cleaned_code

            except requests.exceptions.Timeout:
                logging.warning(f"Attempt {attempt + 1}/{max_retries}: Request timeout")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise Exception("Max retries exceeded: Request timeout")

            except requests.exceptions.RequestException as e:
                logging.warning(f"Attempt {attempt + 1}/{max_retries}: Request failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise Exception(f"Max retries exceeded: {e}")

            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                raise

        raise Exception("Failed to generate code after all retries")

    @staticmethod
    def clean_code(code):
        """
        Clean generated code by removing markdown fences and tokens

        Args:
            code: Raw generated code

        Returns:
            Cleaned code string
        """
        # Remove markdown code fences
        code = re.sub(r'```python\s*\n', '', code)
        code = re.sub(r'```\s*\n?', '', code)

        # Remove <EOR> token
        code = code.replace('<EOR>', '')

        # Remove any leading/trailing whitespace
        code = code.strip()

        return code


def read_jsonl_file(path):
    """Read JSONL file"""
    data = []
    with open(path, 'r', encoding='utf-8') as file:
        for line in file:
            data.append(json.loads(line))
    return data


def write_error_log(error_data, output_dir):
    """Write error log to JSONL"""
    error_path = Path(output_dir) / "inference_errors.jsonl"
    error_path.parent.mkdir(parents=True, exist_ok=True)

    with open(error_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(error_data, ensure_ascii=False) + '\n')


def main(args):
    """Main processing function"""
    # Initialize model
    model = OllamaModel(model_name=args.model_name)

    # Check server
    logging.info("Checking Ollama server...")
    if not model.check_server():
        logging.error("Ollama server is not running!")
        logging.error("Please start the server with: ollama serve")
        return

    logging.info(f"✓ Ollama server is running")
    logging.info(f"✓ Using model: {args.model_name}")

    # Read input queries
    logging.info(f"Reading queries from {args.input}")
    input_data = read_jsonl_file(args.input)
    logging.info(f"✓ Loaded {len(input_data)} queries")

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each query
    success_count = 0
    error_count = 0

    for item in tqdm(input_data, desc="Generating code"):
        item_id = item['id']
        query = item['query']

        try:
            # Generate code
            generated_code = model.call(query, timeout=args.timeout)

            # Save to file
            output_path = output_dir / f"opt_code_{item_id}.py"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(generated_code)

            success_count += 1

        except Exception as e:
            error_count += 1
            logging.error(f"Error processing item {item_id}: {e}")

            # Log error
            write_error_log({
                "id": item_id,
                "error": str(e),
                "query": query[:200]  # Log first 200 chars of query
            }, args.output_dir)

            # Create placeholder file with error comment
            error_output_path = output_dir / f"opt_code_{item_id}.py"
            with open(error_output_path, 'w', encoding='utf-8') as f:
                f.write(f"# Error generating code: {e}\n")
                f.write(f"# This is a placeholder file\n")

    # Print summary
    logging.info("\n" + "=" * 60)
    logging.info(f"✓ Generation complete!")
    logging.info(f"  Success: {success_count}/{len(input_data)}")
    logging.info(f"  Errors: {error_count}/{len(input_data)}")
    logging.info(f"  Output directory: {output_dir}")
    logging.info("=" * 60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Generate optimization code using Ollama model"
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        required=True,
        help="Path to input JSONL file with queries"
    )
    parser.add_argument(
        '-o', '--output_dir',
        type=str,
        required=True,
        help="Directory to save generated Python files"
    )
    parser.add_argument(
        '--model_name',
        type=str,
        default="orlm-qwen3-8b",
        help="Ollama model name (default: orlm-qwen3-8b)"
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=600,
        help="Request timeout in seconds (default: 600)"
    )

    args = parser.parse_args()
    main(args)
