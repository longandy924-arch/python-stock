#!/bin/bash
source config/env.sh


cd "$PROJECT_ROOT"

$PYTHON_BIN scripts/update_v52_market_result.py

