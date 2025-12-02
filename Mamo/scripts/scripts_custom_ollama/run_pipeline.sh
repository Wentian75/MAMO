#!/bin/bash

# MAMO Benchmark Testing Pipeline for Custom Ollama Model
# Evaluates orlm-qwen3-8b on optimization problems

set -e  # Exit on error

# Configuration
BASE_DIR="/Users/jiawei/Downloads/Project/MaMo_test"
SCRIPT_DIR="$BASE_DIR/Mamo/scripts/scripts_custom_ollama"
DATA_DIR="$BASE_DIR/Mamo/data/optimization"
RESULTS_DIR="$BASE_DIR/results/orlm-qwen3-8b"

MODEL_NAME="orlm-qwen3-8b"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "================================================================"
echo "  MAMO Benchmark Testing Pipeline"
echo "  Model: $MODEL_NAME"
echo "================================================================"
echo ""

# Check if Ollama server is running
echo -e "${BLUE}Checking Ollama server...${NC}"
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo -e "${RED}Error: Ollama server is not running!${NC}"
    echo "Please start the server with: ollama serve"
    exit 1
fi
echo -e "${GREEN}✓ Ollama server is running${NC}"
echo ""

# Check if model exists
echo -e "${BLUE}Checking model...${NC}"
if ! ollama list | grep -q "$MODEL_NAME"; then
    echo -e "${RED}Error: Model '$MODEL_NAME' not found!${NC}"
    echo "Please deploy the model first"
    exit 1
fi
echo -e "${GREEN}✓ Model '$MODEL_NAME' found${NC}"
echo ""

# Create results directory
mkdir -p "$RESULTS_DIR"

# Step 1: Prepare queries
echo "================================================================"
echo "  Step 1: Preparing Queries"
echo "================================================================"
python3 "$SCRIPT_DIR/1.prepare_query_optimization.py" \
    --easy_lp "$DATA_DIR/Easy_LP/mamo_easy_lp.jsonl" \
    --complex_lp "$DATA_DIR/Complex_LP/mamo_complex_lp.jsonl" \
    --output "$RESULTS_DIR/queries_optimization.jsonl"

echo ""
echo -e "${GREEN}✓ Step 1 complete${NC}"
echo ""

# Step 2: Run model inference
echo "================================================================"
echo "  Step 2: Running Model Inference"
echo "================================================================"
echo "This may take a while depending on the number of problems..."
echo ""

python3 "$SCRIPT_DIR/2.run_model_ollama.py" \
    --input "$RESULTS_DIR/queries_optimization.jsonl" \
    --output_dir "$RESULTS_DIR/generated_code" \
    --model_name "$MODEL_NAME"

echo ""
echo -e "${GREEN}✓ Step 2 complete${NC}"
echo ""

# Step 3: Evaluate generated code
echo "================================================================"
echo "  Step 3: Evaluating Generated Code"
echo "================================================================"
echo "Executing and comparing results..."
echo ""

python3 "$SCRIPT_DIR/3.run_code_comp_optimization.py" \
    --code_dir "$RESULTS_DIR/generated_code" \
    --output_dir "$RESULTS_DIR/evaluation" \
    --easy_lp "$DATA_DIR/Easy_LP/mamo_easy_lp.jsonl" \
    --complex_lp "$DATA_DIR/Complex_LP/mamo_complex_lp.jsonl"

echo ""
echo -e "${GREEN}✓ Step 3 complete${NC}"
echo ""

# Display results
echo "================================================================"
echo "  Pipeline Complete!"
echo "================================================================"
echo ""
echo "Results location: $RESULTS_DIR/evaluation/"
echo ""
echo "Key files:"
echo "  - Summary metrics:  $RESULTS_DIR/evaluation/accuracy.jsonl"
echo "  - Detailed results: $RESULTS_DIR/evaluation/evaluation_results.jsonl"
echo "  - Generated code:   $RESULTS_DIR/generated_code/"
echo ""
echo "Error folders (if any):"
echo "  - Execution errors: $RESULTS_DIR/evaluation/execution_errors/"
echo "  - Parse errors:     $RESULTS_DIR/evaluation/parse_errors/"
echo "  - Wrong answers:    $RESULTS_DIR/evaluation/wrong_answer/"
echo "  - Timeouts:         $RESULTS_DIR/evaluation/timeout/"
echo ""

# Display accuracy summary
if [ -f "$RESULTS_DIR/evaluation/accuracy.jsonl" ]; then
    echo "Quick Summary:"
    echo "================================================================"
    cat "$RESULTS_DIR/evaluation/accuracy.jsonl" | python3 -m json.tool
    echo "================================================================"
fi

echo ""
echo -e "${GREEN}✓ All done!${NC}"
