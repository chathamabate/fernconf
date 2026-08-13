from __future__ import annotations

from fernconf.FCValue import *
from fernconf.FCTranslator import FCTranslator

from abc import ABC, abstractmethod
from typing import Any, override, cast, Callable
from result import Ok, Err, Result, do

class FCSchema(ABC):
    """
    An FCSchema is way of confirming an FCValue conforms to certain custom rules!
    """
    def __init__(self):
        pass

    def with_comment(self, comment: list[str]) -> FCSchema:
        """
        Adding a comment is *like* adding a description, however this is only seen in output
        definitions.
        """
        return FCSchemaWithComment(self, comment)

    def with_translates(self, *extra_translates: Callable[[str, FCValue, FCTranslator], list[str]] ) -> FCSchema:
        """
        This is for adding an extra translation step to a schema!
        """
        return FCSchemaWithExtraTranslates(self, *extra_translates)

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

    def const(self, value: FCValue) -> FCSchema:
        validated_value_result = self.validate(value)

        if validated_value_result.is_err():
            raise Exception(f"Invalid constant value: {validated_value_result.unwrap_err()}")

        validated_value = validated_value_result.unwrap()
        return self.with_extra_checks(
            check_const=lambda v: Ok(None) if v == validated_value else Err(f"Constant expected: {validated_value}")
        )

    def const_any(self, value: Any) -> FCSchema:
        value_result = fcv_of(value)
        if value_result.is_err():
            raise Exception(f"Constant value is not FCValue: {value_result.unwrap_err()}")

        return self.const(value_result.unwrap())

    def one_of(self, *values: FCValue) -> FCSchema:
        validated_value_results = [self.validate(v) for v in values]

        for index, vvr in enumerate(validated_value_results):
            if vvr.is_err():
                raise Exception(f"Invalid choice {index}: {vvr.unwrap_err()}")

        validated_values = [vvr.unwrap() for vvr in validated_value_results]
        return self.with_extra_checks(
            check_one_of=lambda v: Ok(None) if v in validated_values else Err(f"Value not one of: {validated_values}")
        )

    def one_of_any(self, *values: Any):
        fcv_results = [fcv_of(v) for v in values]

        for index, fcvr in enumerate(fcv_results):
            if fcvr.is_err():
                raise Exception(f"Non-FCValue choise {index}: {fcvr.unwrap_err()}")

        fcvs = [fcvr.unwrap() for fcvr in fcv_results]
        return self.one_of(*fcvs)

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

class FCSchemaWithComment(FCSchemaWrapper):
    def __init__(self, inner: FCSchema, comment: list[str]):
        super().__init__(inner)

        if len(comment) == 0:
            raise Exception("Comment cannot be empty!")

        self.comment = comment[:]

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return translator.comment(self.comment) + self.inner.translate(prefix, value, translator)

class FCSchemaWithExtraTranslates(FCSchemaWrapper):
    def __init__(self, inner: FCSchema, *extra_translates: Callable[[str, FCValue, FCTranslator], list[str]]):
        super().__init__(inner)

        if len(extra_translates) == 0:
            raise Exception("Extra translates cannot be empty")

        self.extra_translates = extra_translates

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        output = self.inner.translate(prefix, value, translator)

        for et in self.extra_translates:
            output += et(prefix, value, translator)

        return output

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
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        match value:
            case int():
                # Given `value` is a valid FCValue. 
                # There is no need to do 64-bit bounds checking here!
                return Ok(value)

            case str():
                try:
                    iv = int(value, 16)

                    # `iv` can be any integer value at this point, must do bounds check!
                    return fcv_int_check_result(iv)
                except ValueError:
                    return Err(f"String could not be parsed as hex \"{value}\"")

            case _:
                return Err(f"Given value cannot be interpreted as an int")

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return translator.definition(prefix, cast(int, value))

FCS_INT: FCSchema = FCSchemaInt()

class FCSchemaStr(FCSchema):
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

class FCSchemaStrictDict(FCSchema):
    """
    A strict dict is just like a strict list above, just a dictionary value is accepted instead!
    All values must conform to the given element schema!
    """
    def __init__(self, ele_schema: FCSchema):
        self.ele_schema = ele_schema

    @override 
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        if not isinstance(value, dict):
            return Err("Given value is not of type dict")

        dict_value = cast(dict[str, FCValue], value)

        new_value = {}
        for k, v in dict_value.items():
            new_v = self.ele_schema.validate(v)
            if new_v.is_err():
                return new_v.map_err(lambda msg: f"Error @ key \"{k}\": {msg}")
            new_value[k] = new_v.unwrap()

        return Ok(new_value)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        output_lines = []
        dict_value = cast(dict[str, FCValue], value)

        for k, v in dict_value.items():
            output_lines += self.ele_schema.translate(prefix + "_" + k, v, translator)

        return output_lines


class FCSchemaStruct(FCSchema):
    def __init__(self, fields: list[tuple[str, FCSchema]], 
                 **derived: tuple[FCSchema, Callable[[FCValue], FCValue]]):
        """
        A Struct is just an ordered list of named values.

        The struct schema actually allows two different ways of specifying a struct.
        A) as an ordered list of values.
        B) as an object mapping field names to values. 

        In both cases, missing values will be attempted to be filled in with defaults.
        The dict representation is always what is returned from validate!

        "derived fields" can be specified with kwargs. This is allows for fields to be added to
        the struct during validation as a function of the original value.
        Describing the validation process is a little confusing, your best off just looking at
        the validate function below to see the steps taken.
        """
        if len(fields) == 0:
            raise Exception("An FCSchemaStruct cannot be empty!")
        
        self.field_order = [field[0] for field in fields]
        self.fields_dict: dict[str, FCSchema] = {}
        self.derived_dict = derived

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

        # For derived fields, we need to both confirm valid field names, and also, potentially
        # add to the default value!
        for field, (schema, func) in derived.items():
            # This may be redundant because we are using kwargs, but whatever.
            if not FC_ID_PATTERN.fullmatch(field):
                raise Exception(f"FCSchemaStruct derived field name is invalid \"{field}\"")

            if field in self.fields_dict:
                raise Exception(f"FCSchemaStruct derived field name already exists \"{field}\"")

        # NOTE: For adding to the default value, we don't actually use the derived schema default
        # values. We instead simulate the validation process on the currently constructed default.
        # That is, we pass the default into the given lambda for each derived field!
        if self.default_result.is_ok():
            dv = self.default_result.unwrap()

            derived_fvs = {}
            for field, (schema, func) in derived.items():
                dfv_res = schema.validate(func(dv))

                # If a derived value is failed to be created for the given default,
                # this is an error with the schema, and thus warrants an exception!
                if not dfv_res.is_ok():
                    raise Exception(f"FCSchemaStruct has bad derived field lambda \"{field}\"")

                derived_fvs[field] = dfv_res.unwrap()

            # Don't modify the actual default value until the end!
            dv |= derived_fvs

    @override
    def default(self) -> Result[FCValue, str]:
        return self.default_result 

    def _validate_list(self, value: list[FCValue]) -> Result[dict[str, FCValue], str]:
        """
        Here given values must be in the same order as `self.fields`.
        If fields are missing at the end, they'll be attempted to be filled in with defaults.

        DOES NOT ADD DERIVED FIELDS
        """
        if len(value) > len(self.field_order):
            return Err(f"Too many fields provided: {len(value)} (expected={len(self.field_order)})")
 
        new_value = {}
        for i in range(len(value)):
            field_name = self.field_order[i]
            schema = self.fields_dict[field_name]
            field_res = schema.validate(value[i])

            if field_res.is_err():
                return Err(f"Failure @ field \"{field_name}\": {field_res.unwrap_err()}")

            new_value[field_name] = field_res.unwrap()

        for i in range(len(value), len(self.field_order)):
            field_name = self.field_order[i]
            schema = self.fields_dict[field_name]
            dv_res = schema.default()

            if dv_res.is_err():
                return Err(f"Field {field_name} must be specified")

            new_value[field_name] = dv_res.unwrap()

        return Ok(new_value)

    def _validate_dict(self, value: dict[str, FCValue]) -> Result[dict[str, FCValue], str]:
        """
        Here we just make sure all requred values are present and valid.
        Missing fields being populated with defaults.

        DOES NOT ADD DERIVED FIELDS
        """
        new_value = {}
        for name, field_value in value.items():
            if name not in self.fields_dict:
                return Err(f"Field {name} is unknown")
            field_res = self.fields_dict[name].validate(field_value)

            if field_res.is_err():
                return Err(f"Failure @ field \"{name}\": {field_res.unwrap_err()}")

            new_value[name] = field_res.unwrap()

        # Now for defaults.
        for name, schema in self.fields_dict.items():
            if name not in new_value:
                dv_res = schema.default()

                if dv_res.is_err():
                    return Err(f"Failure @ field \"{name}\": {dv_res.unwrap_err()}")

                new_value[name] = dv_res.unwrap()

        return Ok(new_value)

    @override 
    def validate(self, value: FCValue) -> Result[FCValue, str]:
        """
        While both list or dict FCValues are accepted by this function, only a dict is ever 
        returned!
        """
        valid_res = None
        match value:
            case list():
                valid_res = self._validate_list(cast(list[FCValue], value))
            case dict():
                valid_res = self._validate_dict(cast(dict[str, FCValue], value))
            case _:
                return Err("Struct must either be specified as a list or dict")

        if valid_res.is_err():
            return valid_res

        valid_value = valid_res.unwrap()

        # Now for derived fields!
        derived_values: dict[str, FCValue] = {}
        for field, (schema, func) in self.derived_dict.items():
            dfv_res = schema.validate(func(valid_value))

            # NOTE: There was a time where I maintained the condition that if initial fields
            # are valid, derived fields must also be valid. This if statement actually used to
            # to raise an exception! The idea being that the schema designer should prevent
            # the derived value from ever failing validation!
            #
            # In theory this was cool, but ultimately lead to kinda confusing extras checks needed
            # on the initial fields to guarantee valid derived fields.
            if not dfv_res.is_ok():
                return dfv_res.map_err(lambda msg: f"Error @ derived field \"{field}\": {msg}")

            derived_values[field] = dfv_res.unwrap()

        # NOTE: It is ok to modify this value as I personally know that _validate_list and 
        # _validate_dict construct entirely new dictionaries during validation.
        # It is impossible the `valid_value` dict to have any references outside of this
        # very function!
        valid_value |= derived_values

        return Ok(valid_value)

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

        for name, (schema, _) in self.derived_dict.items():
            lines += schema.translate(prefix + "_" + name, dict_val[name], translator)

        return lines

