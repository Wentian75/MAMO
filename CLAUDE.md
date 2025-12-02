# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mamo is a Mathematical Modeling Benchmark that evaluates LLM capabilities in solving mathematical modeling problems through code generation. The benchmark consists of two main problem domains:
- **ODE (Ordinary Differential Equations)**: Problems requiring ODE modeling and solving using SciPy and SymPy
- **Optimization**: Linear programming problems requiring .lp file generation for optimization solvers

## Installation & Dependencies

Install dependencies for closed-source model API calls:
```bash
pip install -r Mamo/requirements.txt
```

For open-source models using VLLM:
```bash
pip install vllm
```

**Important**: For optimization problems, you need an optimization solver that can read .lp files (e.g., COPT). The scripts assume COPT is installed, but you can modify the code to use alternative solvers.

## Development Commands

### Running ODE Benchmarks

Navigate to the ODE scripts directory:
```bash
cd Mamo/scripts/scripts_ode/mamo_script_ode
```

**For closed-source models (API-based):**
```bash
bash 1.prepare_query_ode.sh          # Generate queries from dataset
bash 2.run_model_ode.sh              # Call LLM API to generate code
bash 3.run_code_comp_ode.sh          # Execute generated code and compare results
bash 4.fix_error_ode.sh              # Use LLM to fix errors in failed code
bash 5.rerun_code_comp_ode.sh        # Re-execute fixed code
```

**For open-source models (VLLM-based):**
```bash
bash 1.prepare_query_ode.sh          # Generate queries from dataset
bash 2.run_model_ode_open.sh         # Generate code using VLLM
bash 3.run_code_comp_ode.sh          # Execute and compare
bash 4.fix_error_ode_open.sh         # Fix errors using VLLM
bash 5.rerun_code_comp_ode.sh        # Re-execute
```

### Running Optimization Benchmarks

Navigate to the optimization scripts directory:
```bash
cd Mamo/scripts/scripts_optimization/mamo_script_optimization
```

**For closed-source models:**
```bash
bash 1.prepare_query_optimization.sh
bash 2.run_model_optimization.sh
bash 3.run_code_comp_optimization.sh
bash 4.fix_error_optimization.sh
bash 5.rerun_code_comp_optimization.sh
```

**For open-source models:**
```bash
bash 1.prepare_query_optimization.sh
bash 2.run_model_optimization_open.sh
bash 3.run_code_comp_optimization.sh
bash 4.fix_error_optimization_open.sh
bash 5.rerun_code_comp_optimization.sh
```

### Running Few-Shot Experiments

For few-shot experiments, navigate to:
- `Mamo/scripts/scripts_ode/few_shot_scripts_ode/scripts_ode/`
- `Mamo/scripts/scripts_optimization/few_shot_scripts_optimization/scripts_lp/`

The workflow is similar but requires:
1. Selecting a subset of data from the main datasets into `ode_select.jsonl` or `lp_select.jsonl`
2. Updating the `prompt_template` in `1.prepare_query_*.py` files with prompts from the `*_few_shot_prompt/` directories (0-10 shots available)

## Architecture

### Five-Stage Pipeline

The benchmark follows a consistent 5-stage evaluation pipeline:

1. **Query Preparation** (`1.prepare_query_*.py`)
   - Reads JSONL dataset files
   - Injects questions into prompt templates
   - Outputs JSONL file with queries ready for LLM

2. **Model Execution** (`2.run_model_*.py`)
   - Calls LLM APIs (OpenAI format) or VLLM servers
   - Manages API keys from `api_keys.txt`
   - Generates solution code files (Python for ODE, .lp for optimization)
   - Output files named by problem ID: `ode_code_{id}.py` or `lp_code_{id}.lp`

3. **Code Compilation & Evaluation** (`3.run_code_comp_*.py`)
   - Executes generated code with 300-second timeout
   - Compares outputs against ground truth answers
   - Calculates accuracy metrics by problem type
   - Moves failed code to `errors/` subdirectory
   - Generates `code_error.jsonl` with error messages and `accuracy.jsonl` with results

4. **Error Correction** (`4.fix_error_*.py`)
   - Reads error logs from stage 3
   - Calls LLM with error messages to generate fixed code
   - Uses error-fixing prompts that include original code + error info

5. **Re-evaluation** (`5.rerun_code_comp_*.py`)
   - Re-executes fixed code
   - Updates accuracy metrics

### Script Organization

- **`mamo_script_ode/` and `mamo_script_optimization/`**: Main benchmark scripts (0-shot)
- **`few_shot_scripts_ode/` and `few_shot_scripts_optimization/`**: Few-shot experiment scripts
- **`scripts_custom_ollama/`**: Custom scripts for Ollama integration

### Key Utilities

- **`fix_basic_error.py`**: Post-processes generated code to remove markdown formatting (```python blocks) and fix basic syntax issues
- **`3.5.select_error.py`**: Utility to filter and select specific errors for analysis

### Data Format

All datasets are in JSONL format with the following structure:
```json
{
    "id": 1,
    "Question": "problem description with LaTeX math",
    "Answer": "numerical answer as string",
    "Category": "ordinary_differential_equation" or "optimization",
    "Type": "first_order_equation" / "second_order_equation" / "system_equation" / "easy_lp" / "complex_lp"
}
```

### LLM Integration

- Uses OpenAI API format (openai==0.28.0)
- API keys stored in `api_keys.txt` (one per line)
- Randomly selects API key for load balancing
- `openai.api_base` can be customized for alternative endpoints
- Temperature defaults to 0.8

### Prompt Engineering

- **ODE prompts**: Instruct models to generate Python code using `solve_ivp`, `odeint`, or `dsolve`
- **Optimization prompts**: Instruct models to generate .lp files in CPLEX LP format
- Prompts include few-shot examples demonstrating expected output format
- Responses must be pure code without markdown formatting or explanations
- Include significant figures rounding requirements

### Error Handling & Metrics

- Code execution timeout: 300 seconds
- Numerical comparison tolerance: 1e-4 relative error
- Accuracy calculated overall and per problem type
- Error logs include problem ID and full error traceback

## Configuration Notes

Before running scripts:
1. Update `INPUT_PATH` and `OUTPUT_PATH` in .sh files
2. Ensure `api_keys.txt` contains valid API keys (for closed-source models)
3. For VLLM models, configure the VLLM server endpoint
4. For optimization problems, verify COPT or alternative solver is installed and accessible

## File Path Conventions

- Always specify paths relative to the repository root in .sh scripts
- Data files located at `Mamo/data/ode/` and `Mamo/data/optimization/`
- Generated code outputs should go to designated output directories
- Error files automatically moved to `{output_dir}/errors/`
