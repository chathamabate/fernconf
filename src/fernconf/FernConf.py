from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
import re
from typing import Any, override, Callable, cast
from result import Ok, Err, Result, do

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

    def __init__(self, desc: str | None=None):
        self.desc = desc

    @abstractmethod
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        """
        validate takes as input a FCValue and confirms that it abides by implementation 
        specific rules. On success it should always return Ok(value).
        """
        pass

    @abstractmethod
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        """
        Output the defined value with name prefix using `translator`.
        
        This function can assume that `value` was validated with `self.validate` before
        calling this function.
        """
        pass


class FCSchemaBool(FCSchema):
    @override 
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        if not isinstance(value, bool):
            return Err(f"Given value is not of type bool")

        return Ok(value)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return translator.definition(prefix, cast(bool, value), [self.desc] if self.desc else None)

class FCSchemaInt(FCSchema):
    @override 
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        if not isinstance(value, int):
            return Err(f"Given value is not of type int")

        return Ok(value)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return translator.definition(prefix, cast(int, value), [self.desc] if self.desc else None)

class FCSchemaStr(FCSchema):
    @override 
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        if not isinstance(value, str):
            return Err(f"Given value is not of type str")

        return Ok(value)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return translator.definition(prefix, cast(str, value), [self.desc] if self.desc else None)

class FCSchemaList(FCSchema):
    def __init__(self, ele_schema: FCSchema, min_eles: int=0, max_eles: int=0, desc: str | None=None):
        """
        Check for a list of FCValues where each value follows the same schema.

        If `max_eles` is 0, there is no limit to the number of elements in the list!
        """
        super().__init__(desc)
        self.ele_schema = ele_schema
        self.min_eles = min_eles
        self.max_eles = max_eles

        if min_eles > max_eles and max_eles != 0:
            raise Exception(f"Invalid element count constraints ({str(min_eles)}, {str(max_eles)})")

    @override 
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        if not isinstance(value, list):
            return Err(f"Given value is not of type list")
        
        list_value = list(value)
        ele_count = len(list_value)

        if ele_count < self.min_eles:
            return Err(f"Given list has too few elements")

        if ele_count > self.max_eles and self.max_eles != 0:
            return Err(f"Given list has too many elements")

        for i in range(ele_count):
            child_res = self.ele_schema.validate(list_value[i])

            if child_res.is_err():
                return child_res.map_err(lambda msg: f"Error @ index {str(i)}: {msg}")

        return Ok(value)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return []
