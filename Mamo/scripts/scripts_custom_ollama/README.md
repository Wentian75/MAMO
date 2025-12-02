# Custom Ollama Model Testing for MAMO Benchmark

This directory contains scripts to test your custom `orlm-qwen3-8b` model on the MAMO benchmark optimization problems.

## Overview

The pipeline evaluates your model on **863 optimization problems** (652 Easy LP + 211 Complex LP) by:
1. Formatting problems with your custom prompt template
2. Generating Python code using Ollama
3. Executing the code and comparing results with ground truth

## Prerequisites

### 1. Ollama Server

Ensure Ollama is installed and running:

```bash
# Check if Ollama is installed
ollama --version

# Start the Ollama server (in a separate terminal)
ollama serve

# Verify your model is available
ollama list | grep orlm-qwen3-8b
```

If the model is not listed, deploy it:
```bash
cd /Users/jiawei/Downloads/Project/OR/my-orlm/
python3 deploy_ollama.py
```

### 2. Python Dependencies

Install required packages:

```bash
pip install requests tqdm
```

### 3. Optimization Solver

Your model generates code using `coptpy`. Ensure it's installed:

```bash
pip install coptpy==7.0.5
```

**Note:** coptpy may require a license. Verify it works:
```bash
python3 -c "from coptpy import *; env = Envr(); print('coptpy OK')"
```

If you prefer Gurobi instead, install it and modify the prompt template in `1.prepare_query_optimization.py` to use `gurobipy`.

## Quick Start

### Option 1: Run Full Pipeline (Recommended)

```bash
cd /Users/jiawei/Downloads/Project/MaMo_test/Mamo/scripts/scripts_custom_ollama
./run_pipeline.sh
```

This will:
1. Prepare all 863 queries
2. Generate code for all problems (may take several hours)
3. Evaluate all generated code
4. Display summary results

### Option 2: Run Steps Individually

#### Step 1: Prepare Queries

```bash
python3 1.prepare_query_optimization.py \
    --easy_lp ../../data/optimization/Easy_LP/mamo_easy_lp.jsonl \
    --complex_lp ../../data/optimization/Complex_LP/mamo_complex_lp.jsonl \
    --output /Users/jiawei/Downloads/Project/MaMo_test/results/orlm-qwen3-8b/queries_optimization.jsonl
```

#### Step 2: Generate Code

```bash
python3 2.run_model_ollama.py \
    --input /Users/jiawei/Downloads/Project/MaMo_test/results/orlm-qwen3-8b/queries_optimization.jsonl \
    --output_dir /Users/jiawei/Downloads/Project/MaMo_test/results/orlm-qwen3-8b/generated_code \
    --model_name orlm-qwen3-8b
```

#### Step 3: Evaluate Code

```bash
python3 3.run_code_comp_optimization.py \
    --code_dir /Users/jiawei/Downloads/Project/MaMo_test/results/orlm-qwen3-8b/generated_code \
    --output_dir /Users/jiawei/Downloads/Project/MaMo_test/results/orlm-qwen3-8b/evaluation \
    --easy_lp ../../data/optimization/Easy_LP/mamo_easy_lp.jsonl \
    --complex_lp ../../data/optimization/Complex_LP/mamo_complex_lp.jsonl
```

## Testing with a Small Subset

To test the pipeline on a small subset (recommended first):

```bash
# 1. Create a test subset (e.g., first 10 problems)
head -n 10 ../../data/optimization/Easy_LP/mamo_easy_lp.jsonl > /tmp/test_easy_lp.jsonl

# 2. Run pipeline on subset
python3 1.prepare_query_optimization.py \
    --easy_lp /tmp/test_easy_lp.jsonl \
    --output /tmp/test_queries.jsonl

python3 2.run_model_ollama.py \
    --input /tmp/test_queries.jsonl \
    --output_dir /tmp/test_code \
    --model_name orlm-qwen3-8b

python3 3.run_code_comp_optimization.py \
    --code_dir /tmp/test_code \
    --output_dir /tmp/test_evaluation \
    --easy_lp /tmp/test_easy_lp.jsonl

# 3. Check results
cat /tmp/test_evaluation/accuracy.jsonl
```

## Output Structure

Results are saved in `/Users/jiawei/Downloads/Project/MaMo_test/results/orlm-qwen3-8b/`:

```
results/orlm-qwen3-8b/
├── queries_optimization.jsonl              # 863 formatted prompts
├── generated_code/                         # 863 Python files
│   ├── opt_code_1.py
│   ├── opt_code_2.py
│   └── ...
└── evaluation/
    ├── accuracy.jsonl                      # Summary metrics
    ├── evaluation_results.jsonl            # Per-problem results
    ├── execution_errors/                   # Code that failed to run
    ├── parse_errors/                       # Cannot extract objective
    ├── wrong_answer/                       # Incorrect results
    └── timeout/                            # Timeout files
```

## Understanding Results

### Summary Metrics (accuracy.jsonl)

```json
{
  "total": 863,
  "correct": 245,
  "execution_failed": 123,
  "parse_failed": 45,
  "wrong_answer": 450,
  "timeout": 0,
  "accuracy": 0.284,
  "executable_rate": 0.857,
  "easy_lp_accuracy": 0.312,
  "easy_lp_total": 652,
  "easy_lp_correct": 203,
  "complex_lp_accuracy": 0.199,
  "complex_lp_total": 211,
  "complex_lp_correct": 42
}
```

**Key Metrics:**
- **Accuracy**: Percentage of correct answers (target: 15-35% for 8B model)
- **Executable Rate**: Percentage of code that runs without errors
- **Category Breakdown**: Separate accuracy for Easy vs Complex LP

### Expected Performance

Based on MAMO benchmark paper:
- **GPT-4**: 60-80% accuracy
- **Llama-70B**: 30-50% accuracy
- **7B-13B models**: 10-30% accuracy

Your fine-tuned 8B model should target **20-40% accuracy** on optimization problems.

## Troubleshooting

### 1. Ollama Server Not Running

```
Error: Ollama server is not running!
```

**Solution:**
```bash
# Start server in background
ollama serve &

# Or in a separate terminal
ollama serve
```

### 2. Model Not Found

```
Error: Model 'orlm-qwen3-8b' not found!
```

**Solution:**
```bash
cd /Users/jiawei/Downloads/Project/OR/my-orlm/
python3 deploy_ollama.py
```

### 3. coptpy License Error

```
Error: COPT license not found
```

**Solution:**
- Obtain a coptpy license (academic, trial, or commercial)
- Or switch to Gurobi by modifying the prompt template

### 4. Generated Code Doesn't Print Objective

If many files end up in `parse_errors/`, the model might not be printing the objective value.

**Solution:**
Check a few generated files manually:
```bash
cat /Users/jiawei/Downloads/Project/MaMo_test/results/orlm-qwen3-8b/generated_code/opt_code_1.py
```

If the code doesn't print the objective, you may need to:
- Adjust the prompt template in `1.prepare_query_optimization.py`
- Add post-processing to append print statements

### 5. Slow Inference

Inference may take several hours for all 863 problems.

**Tips:**
- Use a smaller subset first (see "Testing with a Small Subset" above)
- Adjust timeout in `2.run_model_ollama.py` (default: 600s per problem)
- Run overnight for full evaluation

## Customization

### Modify Prompt Template

Edit `1.prepare_query_optimization.py`, line 10-19 (PROMPT_TEMPLATE).

### Change Inference Parameters

Edit `2.run_model_ollama.py`, lines 48-56:
```python
"options": {
    "temperature": 0.2,      # Lower = more deterministic
    "top_p": 0.95,
    "top_k": 40,
    "num_ctx": 8192,         # Context window
    "num_predict": 4096,     # Max tokens to generate
}
```

### Adjust Timeout

Edit `3.run_code_comp_optimization.py`, line 236:
```python
output, error = execute_python_code(file_path, timeout=300)  # 5 minutes
```

## Next Steps

After running the full evaluation:

1. **Analyze Results**: Check `evaluation_results.jsonl` for per-problem details
2. **Inspect Errors**: Look at files in error folders to identify patterns
3. **Iterate**: Adjust prompts or model parameters based on findings
4. **Compare**: Compare your results with MAMO paper benchmarks

## Support

For issues specific to:
- **MAMO benchmark**: See main MAMO README
- **Ollama**: https://ollama.com/
- **coptpy**: https://www.copt.com/

## License

See main MAMO project license.
