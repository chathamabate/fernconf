from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
import re
from typing import Any, override, Callable
from result import Ok, Err, Result

type FCValue = int | bool | str | list[FCValue] | dict[str, FCValue]

FC_ID_PATTERN: re.Pattern = re.compile("[A-Za-z_][A-Za-zZ0-9_]*")
""" 
A regex pattern which is used often in fernconf to confirm various IDs/Keys follow a 
reasonable format.
"""

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

                if not FC_ID_PATTERN.fullmatch(k):
                    return Err(f"dict key name does not conform to FCValue regex: \"{k}\"")

                match of(v):
                    case Ok(new_val):
                        new_dict[k] = new_val
                    case Err(msg):
                        return Err(f"[{k}] {msg}")

            return Ok(new_dict)
        case _:
            return Err("FCValues must conform to typedef: int | bool | str | dict[str, FCValue]")

class FCTranslator(ABC):
    """
    An FCTranslator is used to output shallow information to a specific target format.

    Notice that `definition` takes `str | bool | int` as its input value and not an FCValue.
    FCTranslator is meant to be somewhat separate to the FCValue/FCSchema paradigm. 

    This need only know how to translate very simple values! It is up to the Schema to 
    define what primitive values to actually define given a potentially large composite
    FCValue.
    """

    @abstractmethod
    def comment(self, message: list[str], docstring: bool=False) -> list[str]:
        """
        Create a comment in the target format.
        Each element in `message` represents a single line of the comment message.
        Returns a list of the lines of the created comment.
        Neither input nor output lines should have newline characters!
        """
        pass

    @abstractmethod
    def _definition(self, value_name: str, value: str | bool | int) -> list[str]:
        pass

    def definition(self, value_name: str, value: str | bool | int, docstring: list[str] | None=None) -> list[str]:
        """
        Create a definition in the target format!

        If `value_name` does not follow FC_ID_PATTERN, an exception will be thrown.
        
        Note that `value_name` must appear EXACTLY as is in the output definition.
        `docstring` should be a list of the lines of the docstring (with NO NEWLINE CHARACTERS).
        The returned string can also span multiple lines!
        """
        if not FC_ID_PATTERN.fullmatch(value_name):
            # Note that this does not return a result. If we make it here, the implementor
            # made a mistake (not the user). 
            raise Exception(f"value name did not follow FC ID regex format: \"{value_name}\"")

        def_lines = []
        if docstring is not None:
            def_lines += self.comment(docstring, True)

        return def_lines + self._definition(value_name, value)
        
class FCSchema(ABC):
    """
    An FCSchema is way of confirming an FCValue conforms to certain custom rules!
    """

    def __init__(self, desc: str=""):
        self.desc = desc

    @abstractmethod
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        """
        validate takes as input a FCValue and confirms that it abides by implementation 
        specific rules. On success it should always return Ok(value).
        """
        pass

# I guess, I don't totally understand the best way to 
# Maybe like a definition callable is given??
# With no

# Ok, and what about like idk... output creation??
# Isn't that important too?
# shouldn't that also be reuseable??
# The point of the schema is to prove that certain constraints are met!
# And maybe also to spit out a default value?
# Later, what, we pass is a value and a schema?? And like that does some sort of print
# behavior, isn't that bad design?

class RangeSchema(FCSchema):
    @override 
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        # Ok, well now what??
        # Maybe a static type check schema??
        # I mean, Can't these be listed and shit?
        # There is no list schema... I feel like that would be cool too imo.
        return Err("noop")

# Ok, so we can get our FCValue...
# What else do we need here... and FCSchema?
# And what even is an FCSchema?
# Ok, so now what?

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
