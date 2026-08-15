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

# NOTE: The below helpers are really just to help with static type checking.
# If this module didn't use mypy, these functions wouldn't be necessary.

def fcv_get(val: FCValue, *p: str | int) -> FCValue:
    """
    This a helper for traversing an FCValue via fields and indeces which are guaranteed to exist!

    See that this does not return a Result. If a component of `p` doesn't exist, there are no 
    safeguards. An exception will be thrown.

    The purpose of this function really is to prevent the need for elaborate cast expressions.

    NOTE: If a component of `p` is a string, it is assumed a dictionary is being indexed.
    If a component of `p` is an integer, it is assumed a list is being indexed!
    """
    v = val

    for c in p:
        if isinstance(c, int):
            v = cast(list[FCValue], v)[c]
        else:
            if c == "":
                raise Exception("Empty path component found")

            v = cast(dict[str, FCValue], v)[c]
        
    return v

def fcv_get_int(val: FCValue, *p: str | int) -> int:
    return cast(int, fcv_get(val, *p))

def fcv_get_bool(val: FCValue, *p: str | int) -> bool:
    return cast(bool, fcv_get(val, *p))

def fcv_get_str(val: FCValue, *p: str | int) -> str:
    return cast(str, fcv_get(val, *p))

def fcv_get_list(val: FCValue, *p: str | int) -> list[FCValue]:
    return cast(list[FCValue], fcv_get(val, *p))

def fcv_get_dict(val: FCValue, *p: str | int) -> dict[str, FCValue]:
    return cast(dict[str, FCValue], fcv_get(val, *p))

def fcv_getp(val: FCValue, p_str: str) -> FCValue:
    """
    `fcv_getp` is identical to `fcv_get`, it just first translates a string
    into a list of path components.

    This is done by splitting on ".".
    Then, if any path component starts with a digit, it is converted to an integer.
    """
    p: list[str | int] = cast(list[str | int], p_str.split("."))

    for i in range(len(p)):
        c = cast(str, p[i]) # all elements of p start as strings.

        if len(c):
            raise Exception(f"Empty path component found in path \"{p}\"")

        if ord("0") <= ord(c[0]) and ord(c[0]) <= ord("9"):
            p[i] = int(c) 

    return fcv_get(val, *p)

def fcv_getp_bool(val: FCValue, p_str: str) -> bool:
    return cast(bool, fcv_getp(val, p_str))

def fcv_getp_str(val: FCValue, p_str: str) -> str:
    return cast(str, fcv_getp(val, p_str))

def fcv_getp_list(val: FCValue, p_str: str) -> list[FCValue]:
    return cast(list[FCValue], fcv_getp(val, p_str))

def fcv_getp_dict(val: FCValue, p_str: str) -> dict[str, FCValue]:
    return cast(dict[str, FCValue], fcv_getp(val, p_str))
