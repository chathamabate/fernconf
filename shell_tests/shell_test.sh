#!/bin/bash

# To run this script, make sure you are in a python virtual environment with
# fernconf installed!

set -e

gt=$(git rev-parse --show-toplevel)

python $gt/shell_tests/SimpleTool.py
! echo "hello"
