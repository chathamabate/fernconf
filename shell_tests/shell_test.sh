#!/bin/bash

# To run this script, make sure you are in a python virtual environment with
# fernconf installed!
#
# This just makes sure the command line interface more or less works.
# This is NOT a rigorous test of schema validation/translation logic.
# For that, see src/tests.

set -e

gt=$(git rev-parse --show-toplevel)
st_dir=$gt/shell_tests
tool=$st_dir/SimpleTool.py
good_config=$st_dir/good_config.json
bad_config=$st_dir/bad_config.json

build_dir=$st_dir/build

rm -rf $build_dir # Make sure this guy doesn't already exist!
mkdir -p $build_dir

expect_succeed() {
    ($*) || (echo "FAIL" && return 1)
    return 0
}

expect_fail() {
    ($* > /dev/null) && echo "FAIL (UNEXPECTED SUCCESS)" && return 1
    return 0
}

echo "Basic Validate"
expect_succeed python $tool $good_config

echo "Basic Fail"
expect_fail python $tool $bad_config

# Cleanup at end on success!
rm -rf $build_dir

echo "SUCCESS"
