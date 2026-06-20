from __future__ import annotations
from abc import ABC, abstractmethod
import re
from typing import Any, override, cast
from result import Ok, Err, Result

type FCValue = int | bool | str | list[FCValue] | dict[str, FCValue]


FC_ID_PATTERN: re.Pattern = re.compile("[A-Za-z_][A-Za-zZ0-9_]*")
""" 
A regex pattern which is used often in fernconf to confirm various IDs/Keys follow a 
reasonable format.
"""


def fcv_of(value: Any) -> Result[FCValue, str]:
    """
    The purpose of this function is to "construct" a FCValue from an any typed value.
    You may source a value from something which cannot be typechecked before runtime.
    (For, example a JSON file)

    This file creates a deep copy of `value` on success.
    """
    match value:
        case int() | bool() | str():
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
        
