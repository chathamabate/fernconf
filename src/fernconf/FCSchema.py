from __future__ import annotations

from fernconf.FCValue import FCValue, FC_ID_PATTERN, fcv_of
from fernconf.FCTranslator import FCTranslator, FCTranslatorCLang

from abc import ABC, abstractmethod
from typing import Any, override, cast, Callable
from result import Ok, Err, Result, do

class FCSchema(ABC):
    """
    An FCSchema is way of confirming an FCValue conforms to certain custom rules!
    """

    def __init__(self, desc: str | None=None):
        self.desc = desc

    def default(self) -> Result[FCValue, str]:
        """
        Here more than ever, make sure that the value returned is not changed!
        It is completely legal for a Schema to have a single default object it always returns
        a reference to!
        """
        return Err("Given schema provides no default FCValue")

    def with_default(self, default_value: FCValue) -> FCSchema:
        return FCSchemaWithDefault(self, default_value)

    def with_default_any(self, default_value: Any) -> FCSchema:
        default_fcv = fcv_of(default_value)
        if default_fcv.is_err():
            raise Exception(f"Default value is not a FCValue: {default_fcv.unwrap_err()}")

        return self.with_default(default_fcv.unwrap())

    @abstractmethod
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        """
        validate takes as input a FCValue and confirms that it abides by implementation 
        specific rules.

        On success it should return Ok(value | new_value).
        The idea is that given a `value` which may not be entirely complete, this function
        may decide to return a new complete value. For example, populating a struct with 
        default values for optional fields which were not provided.
        """
        pass

    def validate_any(self, value: Any) -> Result[FCValue, str]:
        return do(
            self.validate(fcv)
            for fcv in fcv_of(value)
        )

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


class FCSchemaWithDefault(FCSchema):
    """
    At first glance the existence of this class may seem overengineered.

    Here is what my original solution kinda looked like:

    class FCSchema:
        def __init__(self, ... default_value ...):
            ...
            # Validating the default value at the end is problematic as the derrived classmethod
            # is yet to be fully initialized! self.validate may depend on fields/structures
            # set up in child class constructor!
            self.validate(default_value)

    The problem is:
        If a schema has a default value, that value must also abide by the schema itself.
        I cannot run this validation check in the super class constructor since at that point
        the derrived schema is not initialized.
        Without this class, whenever someone overrides the FCSchema base class, they'd need
        to remember to call self.validate(default_value) at the very end of their constructor!

    FCSchemaWithDefault is now given a schema when it is already entirely initialized!
    Using it to validate the given default value causes no problems!
    """

    def __init__(self, schema: FCSchema, default_value: FCValue):
        super().__init__() # We won't store our own description.

        valid_default = schema.validate(default_value)
        if valid_default.is_err():
            raise Exception(f"Default value failed self validation: {valid_default.unwrap_err()}")

        self.schema = schema

        # Remember, `self.default_value` may contain more than what is provided in 
        # `default_value`. `schema.validate` may populate it with unspecified fields!
        self.default_value = valid_default.unwrap() 
    
    @override
    def default(self) -> Result[FCValue, str]:
        return Ok(self.default_value)
    
    @override
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        return self.schema.validate(value)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return self.schema.translate(prefix, value, translator)

class FCSchemaWithExtraChecks(FSchema):
    def __init__(self, schema: FCSchema, *checks: Callable[[FCValue], Result[None, str]]):
        """
        This composite schema is meant for easy extension of provided schema types without
        the need of creating a whole new class!

        NOTE: if the wrapped schema has a default value, it'll be checked against `checks` here
        in this constructor and raise an exception on failure.
        """
        if len(checks) == 0:
            raise Exception("An FCSchemaWithExtraChecks must have at least 1 check")

        self.checks = checks

        # Should extra checks have like, IDK, names though?
        # I feel like that could be pretty cool tho tbh...
        # Yeah, I think so too, that'd be dope asf.
        # The question is, how do we know a default value is actually populated correctly?

        dv_res = schema.default()
        if dv_res.is_ok(): # We only check default, if the wrapped schema even has a default!
            dv = dv_res.unwrap()
            for check in self.checks:
                check_res = check(dv)
                if check_res.is_err():
                    raise Exception()

        pass

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

        # Given `value` is a valid FCValue, there is no need to do 64-bit bounds checking here!

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

class FCSchemaStrictList(FCSchema):
    def __init__(self, ele_schema: FCSchema, min_eles: int=0, max_eles: int=0, desc: str | None=None):
        """
        Check for a list of FCValues where each value follows the same schema.

        If `max_eles` is 0, there is no limit to the number of elements in the list!

        NOTE: Like bool | int | str, this has no builtin default value.
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
        
        list_value = cast(list[FCValue], value)
        ele_count = len(list_value)

        if ele_count < self.min_eles:
            return Err(f"Given list has too few elements")

        if ele_count > self.max_eles and self.max_eles != 0:
            return Err(f"Given list has too many elements")
        
        new_value = []
        for i in range(ele_count):
            child_res = self.ele_schema.validate(list_value[i])
            if child_res.is_err():
                return child_res.map_err(lambda msg: f"Error @ index {str(i)}: {msg}")

            new_value.append(child_res.unwrap())

        return Ok(new_value)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        output_lines = []

        if self.desc is not None:
            output_lines += translator.comment([self.desc])

        list_value = cast(list[FCValue], value)
        for i in range(len(list_value)):
            output_lines += self.ele_schema.translate(prefix + "_" + str(i), list_value[i], translator)

        return output_lines

class FCSchemaStruct(FCSchema):
    def __init__(self, fields: list[tuple[str, FCSchema]], desc: str | None=None):
        """
        A Struct is just an ordered list of named values.

        The struct schema actually allows two different ways of specifying a struct.
        A) as an order list of values.
        B) as an object mapping field names to values. 

        In both cases, missing values will be attempted to be filled in with defaults.
        The dict representation is always what is returned from validate!
        """
        if len(fields) == 0:
            raise Exception("An FCSchemaStruct cannot be empty!")
        
        self.fields = fields
        self.fields_dict: dict[str, FCSchema] = {}

        # We will try to generate a single default value here!
        self.default_result: Result[dict[str, FCValue], str] = Ok({})

        for (field, schema) in fields:
            if not FC_ID_PATTERN.fullmatch(field):
                raise Exception(f"FCSchemaStruct field name is invalid \"{field}\"")
            
            if field in self.fields_dict:
                raise Exception(f"FCSchemaStruct has repeat field name \"{field}\"")

            self.fields_dict[field] = schema

            if self.default_result.is_ok():
                field_dv = schema.default()
                if field_dv.is_ok():
                    self.default_result.unwrap()[field] = field_dv.unwrap()
                else:
                    # NOTE: That is totally ok for our struct not to have a default value!
                    self.default_result = Err(f"Struct has no default value, (\"{field}\" is required)")
        
    @override
    def default(self) -> Result[FCValue, str]:
        return self.default_result 

    @override 
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        # Uhmmmm, now what? IDEK.... Uhhhh, maybe some bullshit?
        return Err("ah")

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return []

