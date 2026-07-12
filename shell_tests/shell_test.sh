#!/bin/bash

# To run this script, make sure you are in a python virtual environment with
# fernconf installed!
#
# This just makes sure the command line interface more or less works.
# This is NOT a rigorous test of schema validation/translation logic.
# For that, see src/tests.
#
# Also, this test operates under the assumption that output is only printed on error!
# Which currently is the case for `run_fernconf`

gt=$(git rev-parse --show-toplevel)
st_dir=$gt/shell_tests
tool=$st_dir/SimpleTool.py
good_config=$st_dir/good_config.json
bad_config=$st_dir/bad_config.json

example_srcs_dir=$st_dir/example_srcs
build_dir=$st_dir/build

. $st_dir/shell_test_helpers.sh

rm -rf $build_dir # Make sure this guy doesn't already exist!
mkdir -p $build_dir

# Ok, now actual tests! Pretty minimal, but whatever.

test_header "Validate Correct Value"
expect_succeed python $tool $good_config
echo

test_header "Validate and Translate"
expect_succeed python $tool -f gcc -o $build_dir/out.h $good_config
expect_succeed test -f $build_dir/out.h # here we really just want to make sure a file was created.
expect_succeed rm $build_dir/out.h
echo

test_header "Validate Incorrect Value"
expect_fail python $tool $bad_config
echo

test_header "Bad Args"
expect_fail python $tool # No file given!
expect_fail python $tool ./non-existent-file.json # File doesn't exist
expect_fail python $tool -f bad_translator $good_config
echo

test_header "Test GCC Output"
expect_succeed python $tool -f gcc -o $build_dir/gcc_out.h $good_config
expect_succeed gcc $example_srcs_dir/example.c -I$build_dir -o $build_dir/gcc_out
expect_succeed rm $build_dir/gcc_out.h $build_dir/gcc_out
echo

test_header "Test GAS Output"
expect_succeed python $tool -f gas -o $build_dir/gas_out.h $good_config
expect_succeed gcc $example_srcs_dir/example.S -I$build_dir -o $build_dir/gas_out -c
expect_succeed rm $build_dir/gas_out.h $build_dir/gas_out
echo

test_header "Test Make Output"
expect_succeed python $tool -f make -o $build_dir/make_out.mk $good_config
expect_succeed make -f $example_srcs_dir/example.mk -I$build_dir
expect_succeed rm $build_dir/make_out.mk
echo

echo -e "${BOLD}SUCCESS${RESET} ${BRIGHT_BLACK}(Cleaning Up)${RESET}"

# Cleanup at end on success!
rm -rf $build_dir
