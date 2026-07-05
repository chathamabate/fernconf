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

if [[ -t 1 ]]; then
    # Regular colors
    BLACK='\033[0;30m'
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    MAGENTA='\033[0;35m'
    CYAN='\033[0;36m'
    WHITE='\033[0;37m'
    
    # Bright colors
    BRIGHT_BLACK='\033[0;90m'   # Gray
    BRIGHT_RED='\033[0;91m'
    BRIGHT_GREEN='\033[0;92m'
    BRIGHT_YELLOW='\033[0;93m'
    BRIGHT_BLUE='\033[0;94m'
    BRIGHT_MAGENTA='\033[0;95m'
    BRIGHT_CYAN='\033[0;96m'
    BRIGHT_WHITE='\033[0;97m'

    BOLD='\033[1m'
    RESET='\033[0m'
else
    # All variables empty if not a TTY
    BLACK=''
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    MAGENTA=''
    CYAN=''
    WHITE=''
    
    # Bright colors
    BRIGHT_BLACK=''   
    BRIGHT_RED=''
    BRIGHT_GREEN=''
    BRIGHT_YELLOW=''
    BRIGHT_BLUE=''
    BRIGHT_MAGENTA=''
    BRIGHT_CYAN=''
    BRIGHT_WHITE=''

    BOLD=''
    RESET=''
fi

gt=$(git rev-parse --show-toplevel)
st_dir=$gt/shell_tests
tool=$st_dir/SimpleTool.py
good_config=$st_dir/good_config.json
bad_config=$st_dir/bad_config.json

build_dir=$st_dir/build

rm -rf $build_dir # Make sure this guy doesn't already exist!
mkdir -p $build_dir

expect_succeed() {
    echo -e "Trying    : ${BOLD}$1${RESET} ${BRIGHT_BLACK}(Should Succeed)${RESET}"
    shift
    echo -e "Executing : ${BRIGHT_BLACK}$*${RESET}"

    echo -n -e "${RED}"
    $*
    local result=$?
    echo -n -e "${RESET}"

    if ! [ $result -eq 0 ]; then
        echo -e "${RED}FAILURE${RESET}"
        exit 1
    fi
    return 0
}

expect_fail() {
    echo -e "Trying    : ${BOLD}$1${RESET} ${BRIGHT_BLACK}(Should Fail)${RESET}"
    shift
    echo -e "Executing : ${BRIGHT_BLACK}$*${RESET}"

    ($*) > /dev/null

    if [ $? -eq 0 ]; then
        echo -e "${RED}FAILURE${RESET}"
        exit 1
    fi
    return 0
}

expect_succeed "Basic Validate" python $tool $good_config
expect_fail "Basic Fail" python $tool $bad_config

echo -e "\n${BOLD}SUCCESS${RESET} ${BRIGHT_BLACK}(Cleaning Up)${RESET}"

# Cleanup at end on success!
rm -rf $build_dir
