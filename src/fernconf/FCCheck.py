from __future__ import annotations
from fernconf.FCValue import *
from typing import Callable

type FCCheck = Callable[[FCValue], Result[None, list[str]]]
"""
An FCCheck is used to confirm an FCValue adheres to some
arbitrary condition(s)

A return value of Ok(None) means the check passed.
A return value of Err(<msg>) means a check failed with the given
error lines!
"""

def fcc_and(**checks: FCCheck) -> FCCheck:
    def _check(fcv: FCValue) -> Result[None, list[str]]:
        err_msg = []
        success = True

        for check_name, check in checks.items():
            cr = check(fcv)

            if cr.is_err():
                success = False
                err_msg += prepend_and_tab(
                    [f"Check \"{check_name}\" failed"],
                    cr.unwrap_err()
                )

        return Ok(None) if success else Err(err_msg)

    return _check

def fcc_or(**checks: FCCheck) -> FCCheck:
    def _check(fcv: FCValue) -> Result[None, list[str]]:
        for check_name, check in checks.items():
            cr = check(fcv)
            if cr.is_err():
                return Err(prepend_and_tab(
                    ["Or check must pass at least one of the following"],
                    list(checks.keys())
                ))
        return Ok(None)

    return _check

