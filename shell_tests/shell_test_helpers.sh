#!/bin/bash

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

fail() {
    echo -e "${RED}FAILURE${RESET}"
    exit 1
}

test_header() {
    echo -e "Test        : ${BOLD}$1${RESET}"
}

expect_succeed() {
    echo -e "Expect Pass : ${BRIGHT_BLACK}$*${RESET}"

    echo -n -e "${RED}"
    $*
    local result=$?
    echo -n -e "${RESET}"

    if ! [ $result -eq 0 ]; then
        fail
    fi
    return 0
}

expect_fail() {
    echo -e "Expect ${BRIGHT_BLACK}Fail${RESET} : ${BRIGHT_BLACK}$*${RESET}"

    (($*) 2>&1) > /dev/null

    if [ $? -eq 0 ]; then
        echo -e "${RED}Command unexpectedly succeeded${RESET}"
        fail
    fi
    return 0
}
