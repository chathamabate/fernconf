from fernconf.FCValue import FCValue, FC_ID_PATTERN
from fernconf.FCTranslator import FCTranslator

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, override, cast
from result import Ok, Err, Result

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

    """
    NOTE: It is very important to realize the differences in how type checking should be 
    handled in the above two abstract endpoints.

    For `validate`, we are given a value at runtime who's type we know nothing about.
    It is expected, that this value will sometimes abide by our schema, and sometimes not.
    Type checks in `validate`, should thus be dynamic and runtime safe. If we get a `list`,
    but we are expecting an `int`, an `Err` object should be returned with a descriptive
    message. A rigorous `validate` implementation will likley include `match` statements and/or
    `isinstance` calls for dynamic type checking.

    `translate` on the other hand should be written with the understanding that at runtime it
    will only ever be called with a value which passed `validate`. Here we can just assume
    that the given value abides by our schema. We would only expect the use of `cast` in 
    these functions to ensure static type checking passes. A type related runtime error
    here would signal an error in the schema, not an error in user input!
    """


class FCSchemaBool(FCSchema):
    @override 
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        if not isinstance(value, bool):
            return Err(f"Given value is not of type bool")

        return Ok(value)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return translator.definition(prefix, cast(bool, value), [self.desc] if self.desc is not None else None)

class FCSchemaInt(FCSchema):
    @override 
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        if not isinstance(value, int):
            return Err(f"Given value is not of type int")

        return Ok(value)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return translator.definition(prefix, cast(int, value), [self.desc] if self.desc is not None else None)

class FCSchemaStr(FCSchema):
    @override 
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        if not isinstance(value, str):
            return Err(f"Given value is not of type str")

        return Ok(value)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return translator.definition(prefix, cast(str, value), [self.desc] if self.desc is not None else None)

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
        output_lines = []

        if self.desc is not None:
            output_lines += [self.desc]

        list_value = cast(list[FCValue], value)
        for i in range(len(list_value)):
            output_lines += self.ele_schema.translate(prefix + str(i), list_value[i], translator)

        return output_lines
