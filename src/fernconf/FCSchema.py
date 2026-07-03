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

    def __init__(self):
        pass

    def description(self) -> list[str]:
        """
        A Schema can specify a description. 

        This is NOT reflected in the output definitions in any way!

        This should return a pointer to a NEW list! Unlike FCValue's, this is just a normal
        mutable python list!
        """
        return []

    def with_description(self, desc: list[str]) -> FCSchema:
        return FCSchemaWithDescription(self, desc)

    def with_comment(self, comment: list[str]) -> FCSchema:
        """
        Adding a comment is *like* adding a description, however this is only seen in output
        definitions.
        """
        return FCSchemaWithComment(self, comment)

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

    def with_extra_checks(self, **checks: Callable[[FCValue], Result[None, str]]) -> FCSchema:
        return FCSchemaWithExtraChecks(self, **checks)

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

class FCSchemaWrapper(FCSchema):
    """
    This is meant to be used as a base class for FCSchema which simply wrap a pre-existing
    concrete schema.
    """
    def __init__(self, inner: FCSchema):
        self.inner = inner

    @override
    def description(self) -> list[str]:
        return self.inner.description()

    @override
    def default(self) -> Result[FCValue, str]:
        return self.inner.default()

    @override
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        return self.inner.validate(value)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return self.inner.translate(prefix, value, translator)

#
# Essential Composites
#

class FCSchemaWithDescription(FCSchemaWrapper):
    def __init__(self, inner: FCSchema, desc: list[str]):
        super().__init__(inner)

        if len(desc) == 0:
            raise Exception("Description cannot be empty!")

        self.desc = desc[:]

    @override
    def description(self) -> list[str]:
        output_desc = self.desc[:]
        inner_desc = super().description()
        if len(inner_desc) > 0:
            output_desc += [""] + inner_desc
        return output_desc

class FCSchemaWithComment(FCSchemaWrapper):
    def __init__(self, inner: FCSchema, comment: list[str]):
        super().__init__(inner)

        if len(comment) == 0:
            raise Exception("Comment cannot be empty!")

        self.comment = comment[:]

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return translator.comment(self.comment) + self.inner.translate(prefix, value, translator)

class FCSchemaWithDefault(FCSchemaWrapper):
    def __init__(self, schema: FCSchema, default_value: FCValue):
        super().__init__(schema) 

        valid_default = schema.validate(default_value)
        if valid_default.is_err():
            raise Exception(f"Default value failed self validation: {valid_default.unwrap_err()}")

        # Remember, `self.default_value` may contain more than what is provided in 
        # `default_value`. `schema.validate` may populate it with unspecified fields!
        self.default_value = valid_default.unwrap() 
    
    @override
    def default(self) -> Result[FCValue, str]:
        return Ok(self.default_value)

class FCSchemaWithExtraChecks(FCSchemaWrapper):
    """
    This composite schema is meant for easy extension of provided schema types without
    the need of creating a whole new class!
    """

    def __init__(self, schema: FCSchema, **checks: Callable[[FCValue], Result[None, str]]):
        """
        If `schema` has a default value, it will be checked here in this constructor.
        An exception will be raised if the default value does not conform to the 
        extra checks.
        """
        super().__init__(schema)

        if len(checks) == 0:
            raise Exception("An FCSchemaWithExtraChecks must have at least 1 check")
        
        self.checks = checks

        dv_res = schema.default()
        if dv_res.is_ok(): # We only check default, if the wrapped schema even has a default!
            dv = dv_res.unwrap()
            for check_name, check in self.checks.items():
                check_res = check(dv)
                if check_res.is_err():
                    raise Exception(f"Default value failed check \"{check_name}\": {check_res.unwrap_err()}")
    @override
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        res = super().validate(value)

        # Always perform extra checks AFTER initial validation!
        if res.is_ok():
            v = res.unwrap()
            for check_name, check in self.checks.items():
                check_res = check(v)
                if check_res.is_err():
                    return Err(f"Value failed check \"{check_name}\": {check_res.unwrap_err()}")

        return res

#
# Primitive types
#

class FCSchemaBool(FCSchema):
    @override
    def description(self) -> list[str]:
        return ["BOOL"]

    @override 
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        if not isinstance(value, bool):
            return Err(f"Given value is not of type bool")

        return Ok(value)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return translator.definition(prefix, cast(bool, value))

FCS_BOOL: FCSchema = FCSchemaBool()

class FCSchemaInt(FCSchema):
    @override
    def description(self) -> list[str]:
        return ["INTEGER"]

    @override 
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        if not isinstance(value, int):
            return Err(f"Given value is not of type int")

        # Given `value` is a valid FCValue, there is no need to do 64-bit bounds checking here!

        return Ok(value)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return translator.definition(prefix, cast(int, value))

FCS_INT: FCSchema = FCSchemaInt()

class FCSchemaStr(FCSchema):
    @override
    def description(self) -> list[str]:
        return ["STRING"]

    @override 
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        if not isinstance(value, str):
            return Err(f"Given value is not of type str")

        return Ok(value)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return translator.definition(prefix, cast(str, value))

FCS_STR: FCSchema = FCSchemaStr()

#
# Standard Composites
#

class FCSchemaStrictList(FCSchema):
    def __init__(self, ele_schema: FCSchema, min_eles: int=0, max_eles: int=0):
        """
        Check for a list of FCValues where each value follows the same schema.

        If `max_eles` is 0, there is no limit to the number of elements in the list!

        NOTE: Like bool | int | str, this has no builtin default value.
        """
        self.ele_schema = ele_schema
        self.min_eles = min_eles
        self.max_eles = max_eles

        if min_eles < 0 or max_eles < 0:
            raise Exception("element count constraints cannot be negative")

        if min_eles > max_eles and max_eles != 0:
            raise Exception(f"Invalid element count constraints ({str(min_eles)}, {str(max_eles)})")

    @override
    def description(self) -> list[str]:
        header = "list[]"
        if self.min_eles > 0:
            header += f" min_eles={self.min_eles}"
        if self.max_eles > 0:
            header += f" max_eles={self.max_eles}"

        return [header] + ["  " + line for line in self.ele_schema.description()]

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

        list_value = cast(list[FCValue], value)
        for i in range(len(list_value)):
            output_lines += self.ele_schema.translate(prefix + "_" + str(i), list_value[i], translator)

        return output_lines

class FCSchemaStruct(FCSchema):
    def __init__(self, fields: list[tuple[str, FCSchema]]):
        """
        A Struct is just an ordered list of named values.

        The struct schema actually allows two different ways of specifying a struct.
        A) as an ordered list of values.
        B) as an object mapping field names to values. 

        In both cases, missing values will be attempted to be filled in with defaults.
        The dict representation is always what is returned from validate!
        """
        if len(fields) == 0:
            raise Exception("An FCSchemaStruct cannot be empty!")
        
        self.field_order = [field[0] for field in fields]
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
    def description(self) -> list[str]:
        desc_lines = []
        for field_name, schema in self.fields_dict.items():
            desc_lines += [f"[{field_name}]"]
            desc_lines += ["  " + line for line in schema.description()]
        return desc_lines
        
    @override
    def default(self) -> Result[FCValue, str]:
        return self.default_result 

    def validate_list(self, value: list[FCValue]) -> Result[FCValue, str]:
        """
        Here given values must be in the same order as `self.fields`.
        If fields are missing at the end, they'll be attempted to be filled in with defaults.
        """
        if len(value) > len(self.field_order):
            return Err(f"Too many fields provided: {len(value)} (expected={len(self.field_order)})")
 
        new_value = {}
        for i in range(len(value)):
            field_name = self.field_order[i]
            schema = self.fields_dict[field_name]
            field_res = schema.validate(value[i])

            if field_res.is_err():
                return field_res.map_err(lambda msg: f"Failure @ field \"{field_name}\": {msg}")

            new_value[field_name] = field_res.unwrap()

        for i in range(len(value), len(self.field_order)):
            field_name = self.field_order[i]
            schema = self.fields_dict[field_name]
            dv_res = schema.default()

            if dv_res.is_err():
                return Err(f"Field {field_name} must be specified")

            new_value[field_name] = dv_res.unwrap()

        return Ok(new_value)

    def validate_dict(self, value: dict[str, FCValue]) -> Result[FCValue, str]:
        """
        Here we just make sure all requred values are present and valid.
        Missing fields being populated with defaults.
        """
        new_value = {}
        for name, field_value in value.items():
            if name not in self.fields_dict:
                return Err(f"Field {name} is unknown")
            field_res = self.fields_dict[name].validate(field_value)

            if field_res.is_err():
                return field_res.map_err(lambda msg: f"Error @ field \"{name}\": {msg}")

            new_value[name] = field_res.unwrap()

        # Now for defaults.
        for name, schema in self.fields_dict.items():
            if name not in new_value:
                dv_res = schema.default()

                if dv_res.is_err():
                    return dv_res.map_err(lambda msg: f"Error @ field \"{name}\": {msg}")

                new_value[name] = dv_res.unwrap()

        return Ok(new_value)

    @override 
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        """
        While both list or dict FCValues are accepted by this function, only a dict is ever 
        returned!
        """
        match value:
            case list():
                return self.validate_list(cast(list[FCValue], value))
            case dict():
                return self.validate_dict(cast(dict[str, FCValue], value))
            case _:
                return Err("Struct must either be specified as a list or dict")

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        """
        NOTE: as it is requred that `value` be validated before being passed into this function,
        we know with certainty that `value` is of type dict[str, FCValue].
        """
        lines = []

        dict_val = cast(dict[str, FCValue], value)
        for name, ele_schema in self.fields_dict.items():
            lines += ele_schema.translate(prefix + "_" + name, dict_val[name], translator)

        return lines

