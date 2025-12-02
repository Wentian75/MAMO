#!/bin/bash

# Quick Setup Test Script
# Verifies all prerequisites before running full pipeline

set -e

echo "================================================================"
echo "  MAMO Testing Setup Verification"
echo "================================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

# 1. Check Ollama server
echo -n "Checking Ollama server... "
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    echo "  Start with: ollama serve"
    ERRORS=$((ERRORS + 1))
fi

# 2. Check model
echo -n "Checking model orlm-qwen3-8b... "
if ollama list 2>/dev/null | grep -q "orlm-qwen3-8b"; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    echo "  Deploy with: cd /Users/jiawei/Downloads/Project/OR/my-orlm/ && python3 deploy_ollama.py"
    ERRORS=$((ERRORS + 1))
fi

# 3. Check Python dependencies
echo -n "Checking Python dependencies... "
python3 -c "import requests; import tqdm" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ Missing${NC}"
    echo "  Install with: pip install requests tqdm"
    ERRORS=$((ERRORS + 1))
fi

# 4. Check coptpy
echo -n "Checking coptpy... "
python3 -c "from coptpy import *" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Installed${NC}"
else
    echo -e "${YELLOW}⚠ Not found${NC}"
    echo "  Install with: pip install coptpy==7.0.5"
    echo "  Note: May require license"
fi

# 5. Check data files
echo -n "Checking data files... "
EASY_LP="/Users/jiawei/Downloads/Project/MaMo_test/Mamo/data/optimization/Easy_LP/mamo_easy_lp.jsonl"
COMPLEX_LP="/Users/jiawei/Downloads/Project/MaMo_test/Mamo/data/optimization/Complex_LP/mamo_complex_lp.jsonl"

if [ -f "$EASY_LP" ] && [ -f "$COMPLEX_LP" ]; then
    EASY_COUNT=$(wc -l < "$EASY_LP" | tr -d ' ')
    COMPLEX_COUNT=$(wc -l < "$COMPLEX_LP" | tr -d ' ')
    echo -e "${GREEN}✓ Found (${EASY_COUNT} Easy + ${COMPLEX_COUNT} Complex)${NC}"
else
    echo -e "${RED}✗ Missing${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 6. Test Ollama inference (if server is running)
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -n "Testing Ollama inference... "

    RESPONSE=$(curl -s http://localhost:11434/api/generate -d '{
        "model": "orlm-qwen3-8b",
        "prompt": "Test",
        "stream": false,
        "options": {"num_predict": 10}
    }' 2>&1)

    if echo "$RESPONSE" | grep -q "response"; then
        echo -e "${GREEN}✓ Working${NC}"
    else
        echo -e "${RED}✗ Failed${NC}"
        echo "  Response: $RESPONSE"
        ERRORS=$((ERRORS + 1))
    fi
fi

echo ""
echo "================================================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "You're ready to run the pipeline:"
    echo "  ./run_pipeline.sh"
    echo ""
    echo "Or test with a small subset first:"
    echo "  # Create test subset (first 5 problems)"
    echo "  head -n 5 ../../data/optimization/Easy_LP/mamo_easy_lp.jsonl > /tmp/test_subset.jsonl"
    echo ""
    echo "  # Run test"
    echo "  python3 1.prepare_query_optimization.py --easy_lp /tmp/test_subset.jsonl -o /tmp/test_queries.jsonl"
    echo "  python3 2.run_model_ollama.py -i /tmp/test_queries.jsonl -o /tmp/test_code"
    echo "  python3 3.run_code_comp_optimization.py -c /tmp/test_code -o /tmp/test_results --easy_lp /tmp/test_subset.jsonl"
    echo ""
else
    echo -e "${RED}✗ ${ERRORS} error(s) found${NC}"
    echo "Please fix the issues above before running the pipeline."
fi
echo "================================================================"
