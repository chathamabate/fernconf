from __future__ import annotations
from abc import ABCMeta, abstractmethod
from enum import Enum
import re
from typing import ClassVar, Any
from result import Ok, Err, Result

type FCValue = int | bool | str | dict[str, FCValue]

FCVALUE_KEY_PATTERN: re.Pattern = re.compile("[A-Za-z_][A-Za-zZ0-9_]*")

def of(value: Any) -> Result[FCValue, str]:
    """
    The purpose of this function is to "construct" a FCValue from an any typed value.
    You may source a value from something which cannot be typechecked before runtime.
    (For, example a JSON file)

    This file creates a deep copy of `value` on success.
    """
    match value:
        case int() | bool() | str():
            return Ok(value)
        case dict():
            new_dict: dict[str, FCValue] = {}
            for k, v in value.items():
                if not isinstance(k, str):
                    return Err("dict values must only have string keys")

                if not FCVALUE_KEY_PATTERN.fullmatch(k):
                    return Err(f"dict key name does not conform to FCValue regex: \"{k}\"")

                match of(v):
                    case Ok(new_val):
                        new_dict[k] = new_val
                    case Err(msg):
                        return Err(f"[{k}] {msg}")

            return Ok(new_dict)
        case _:
            return Err("FCValues must conform to typedef: int | bool | str | dict[str, FCValue]")



#class FCValue(metaclass=ABCMeta):
#    @staticmethod
#    def of(value: Any) -> FCValue | None:
#        match value:
#            case int():
#                return FCValueInt(value)
#            case bool():
#                return FCValueBool(value)
#            case str():
#                return FCValueStr(value)
#            case dict():
#                new_dict: dict[str, FCValue] = {}
#                for k, v in value.items():
#                    if not isinstance(k, str):
#                        return None
#
#                    new_val = FCValue.of(v)
#                    if new_val is None:
#                        return None
#
#                    new_dict[k] = new_val
#
#                return FCValueObj(new_dict)
#            case _:
#                return None
#        
#class FCValueInt(FCValue):
#    def __init__(self, value: int):
#        self.value = value
#
#    def __str__(self) -> str:
#        return str(self.value)
#
#class FCValueBool(FCValue):
#    def __init__(self, value: bool):
#        self.value = value
#
#    def __str__(self) -> str:
#        return str(self.value)
#
#class FCValueStr(FCValue):
#    def __init__(self, value: str):
#        self.value = value
#
#    def __str__(self) -> str:
#        return str(self.value)
#
#class FCValueObj(FCValue):
#    def __init__(self, value: dict[str, FCValue]):
#        self.value = value
#
#    def __str__(self) -> str:
#        return "{" + ", ".join([f"\"{k}\": {str(v)}"   for k, v in self.value.items()]) + "}"

# IDK, are there even benefits to this design above tbh??
# I don't even really know at this point?
# Honestly, I don't even really know??
# Well, I guess there are constraints and such?
# What does a schema even do?? It validates??
# Based on defined rules???
# Yeah, I guess that's really the whole point?

# Lit that this actually works!
# print(FCValue.of({"a": 1, "b": {"c": 3}}))
# So this is a fern config object ^ 
# Which in theory can be parsed directly from JSON?
# Ehhh, we may want a parse function as is imo...


#class Property(metaclass=ABCMeta):
#    NAME_PATTERN: ClassVar[re.Pattern] = re.compile("[A-Z_][A-Z0-9_]*")
#
#    def __init__(self, name: str):
#        if not Property.NAME_PATTERN.fullmatch(name):
#            raise Exception(f"Invalid name given \"{name}\"")
#
#        self.name = name
#
#class PropertyString(Property):
#    def __init__(self, name: str, value: str):
#        super().__init__(name)
#
#        # By default, string properties apply no regex at all!
#        # Even an empty stirng is technically valid.
#        self.value = value
#
#class PropertyInteger(Property):
#    def __init__(self, name: str, value: int):
#        super().__init__(name)
#        self.value = value;
#
## I mean, shouldn't a config really be a dictionary for fast lookup?
## Ever thought of that one?
#
#class PropertyBoolean(Property):
#    def __init__()
