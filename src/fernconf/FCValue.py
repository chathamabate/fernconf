from __future__ import annotations
from abc import ABC, abstractmethod
import re
from typing import Any, override, cast
from result import Ok, Err, Result

FC_ID_PATTERN: re.Pattern = re.compile("[A-Za-z_][A-Za-zZ0-9_]*")
""" 
A regex pattern which is used often in fernconf to confirm various IDs/Keys follow a 
reasonable format.
"""

type FCValue = int | bool | str | list[FCValue] | dict[str, FCValue]
"""
While not able to be expressed in this type defintion, FCValue integers must NEVER
exceed 64-bits.

This is enforced when creating an FCValue using `fcv_of` below.

Additionally, once you have an FCValue, it should be treated as IMMUTABLE!!!
Always use `fcv_of`below when creating new FCValues!
"""

def fcv_int_check_result(value: int) -> Result[int, str]:
    """
    Confirm that an integer can fit into either a 64-bit signed integer, or a 64-bit 
    unsigned integer!
    """
    if value < -0x8000_0000_0000_0000:
        return Err(f"Given value exceeds 64-bit negative bound {str(value)}")

    if value >= 0x1_0000_0000_0000_0000:
        return Err(f"Given value exceends 64-bit unsigned positive bound {str(value)}")

    return Ok(value)


def fcv_int_check(value: int) -> None:
    """
    Same as `fcv_int_check_result`, but raises an actual exception instead.
    """
    res = fcv_int_check_result(value)
    
    if res.is_err():
        raise Exception(res.err())


def fcv_of(value: Any) -> Result[FCValue, str]:
    """
    The purpose of this function is to "construct" a FCValue from an any typed value.
    You may source a value from something which cannot be typechecked before runtime.
    (For, example a JSON file)

    This file creates a deep copy of `value` on success.

    NOTE: This functions enforces GLOBALLY REQUIRED CONSTRAINTS which cannot be expressed
    in a simple python type definition. When creating a FCValue, this funtion must
    ALWAYS BE USED!
    """
    match value:
        case int():
            return fcv_int_check_result(value)

        case bool() | str():
            return Ok(value)
        case list():
            new_list: list[FCValue] = []
            for i, v in enumerate(value):
                match fcv_of(v):
                    case Ok(new_val):
                        new_list.append(new_val)
                    case Err(msg):
                        return Err(f"[{i}] {msg}")
            return Ok(new_list)
        case dict():
            new_dict: dict[str, FCValue] = {}
            for k, v in value.items():
                if not isinstance(k, str):
                    return Err("dict values must only have string keys")

                if not FC_ID_PATTERN.fullmatch(k):
                    return Err(f"dict key name does not conform to FCValue regex: \"{k}\"")

                match fcv_of(v):
                    case Ok(new_val):
                        new_dict[k] = new_val
                    case Err(msg):
                        return Err(f"[{k}] {msg}")

            return Ok(new_dict)
        case _:
            return Err("FCValues must conform to typedef: int | bool | str | list[FCValue] | dict[str, FCValue]")
        
