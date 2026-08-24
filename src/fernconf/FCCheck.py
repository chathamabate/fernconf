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

def fcc_b(p_str: str) -> FCCheck:
    """
    This check is used when it is GUARANTEED that a boolean FCValue exists in the checked value
    at path `p_str`. It succeeds when the boolean is True and fails when it is False!
    """
    def _check(fcv: FCValue) -> Result[None, list[str]]:
        if fcv_getp_bool(fcv, p_str):
            return Ok(None)

        return Err([f"Path \"{p_str}\" evaluated to False"])

    return _check

def fcc_not(check: FCCheck) -> FCCheck:
    def _check(fcv: FCValue) -> Result[None, list[str]]:
        cr = check(fcv)
        if cr.is_ok():
            return Err(["Not expression succeeded unexplectedly"])

        return Ok(None)

    return _check


def fcc_and(*checks: FCCheck) -> FCCheck:
    def _check(fcv: FCValue) -> Result[None, list[str]]:
        err_msg = []
        success = True

        for check in checks:
            cr = check(fcv)

            if cr.is_err():
                success = False
                err_msg += cr.unwrap_err()

        return Ok(None) if success else Err(err_msg)

    return _check

def fcc_or(*checks: FCCheck) -> FCCheck:
    def _check(fcv: FCValue) -> Result[None, list[str]]:
        for check in checks:
            cr = check(fcv)
            if cr.is_ok():
                return Ok(None)

        return Err(["All Or checks failed"])

    return _check

def fcc_xor(*checks: FCCheck) -> FCCheck:
    def _check(fcv: FCValue) -> Result[None, list[str]]:
        pass_found = False
        for check in checks:
            cr = check(fcv)
            if cr.is_ok():
                if pass_found:
                    return Err(["More than one Xor condition succeeded"])
                pass_found = True

        if pass_found:
            return Ok(None)
        return Err(["No Xor conditions succeeded"])

    return _check

def fcc_if(cond: FCCheck, conseq: FCCheck) -> FCCheck:
    def _check(fcv: FCValue) -> Result[None, list[str]]:
        cond_r = cond(fcv)
        if cond_r.is_err():
            return Ok(None)

        conseq_r = conseq(fcv)
        if conseq_r.is_err():
            return Err(prepend_and_tab(
                ["Consequence failed when condition succeeded"],
                conseq_r.unwrap_err()
            ))
        return Ok(None)

    return _check

