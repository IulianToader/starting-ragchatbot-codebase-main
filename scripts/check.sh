#!/bin/bash
# Run code quality checks: formatting and tests
# Usage: ./scripts/check.sh [--fix]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

FIX_MODE=false
if [ "$1" = "--fix" ]; then
    FIX_MODE=true
fi

echo -e "${BLUE}=== Code Quality Checks ===${NC}"
echo ""

# 1. Black formatting
echo -e "${BLUE}[1/2] Checking code formatting (black)...${NC}"
if [ "$FIX_MODE" = true ]; then
    uv run black .
    echo -e "${GREEN}  Formatting applied.${NC}"
else
    if uv run black --check . 2>&1; then
        echo -e "${GREEN}  Formatting OK.${NC}"
    else
        echo -e "${RED}  Formatting issues found. Run './scripts/check.sh --fix' to auto-format.${NC}"
        exit 1
    fi
fi
echo ""

# 2. Tests
echo -e "${BLUE}[2/2] Running tests (pytest)...${NC}"
if uv run pytest; then
    echo -e "${GREEN}  Tests passed.${NC}"
else
    echo -e "${RED}  Tests failed.${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=== All checks passed ===${NC}"
