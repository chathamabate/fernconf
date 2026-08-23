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

    def default(self) -> Result[FCValue, list[str]]:
        """
        Here more than ever, make sure that the value returned is not changed!
        It is completely legal for a Schema to have a single default object it always returns
        a reference to!
        """
        return Err(["Given schema provides no default FCValue"])

    def with_default(self, default_value: FCValue) -> FCSchema:
        return FCSchemaWithDefault(self, default_value)

    def with_default_any(self, default_value: Any) -> FCSchema:
        default_fcv = fcv_of(default_value)
        if default_fcv.is_err():
            raise Exception(f"Default value is not a FCValue: {default_fcv.unwrap_err()}")

        return self.with_default(default_fcv.unwrap())

    def with_extra_checks(self, **checks: Callable[[FCValue], Result[None, list[str]]]) -> FCSchema:
        return FCSchemaWithExtraChecks(self, **checks)

    def const(self, value: FCValue) -> FCSchema:
        """
        This Schema will be given `value` as a default value THEN will be given
        and extra check which refuses all other values!
        """

        # Frustratingly, this function will actually validate `value` twice.
        # Once in this function, and a second time when `with_default` executes.

        validated_value_result = self.validate(value)
        if validated_value_result.is_err():
            raise Exception(f"Invalid constant value: {validated_value_result.unwrap_err()}")
        validated_value = validated_value_result.unwrap()

        # Its important to realize the default is changed BEFORE applying the
        # extra checks. This way `self`'s current default value does not cause
        # an exception to be thrown if it is not equal to value.
        #
        # NOTE: Realize, that the internal default values of `self` still exist!
        return self.with_default(value).with_extra_checks(
            check_const=lambda v: Ok(None) if v == validated_value else Err([f"Constant expected: {validated_value}"])
        )

    def const_any(self, value: Any) -> FCSchema:
        value_result = fcv_of(value)
        if value_result.is_err():
            raise Exception(f"Constant value is not FCValue: {value_result.unwrap_err()}")

        return self.const(value_result.unwrap())

    def one_of(self, *values: FCValue) -> FCSchema:
        """
        The default overriding behavior is similar to that of `const`.

        NOTE: The FIRST value given will be come the new defualt!
        For example, self.one_of("a", "b", "c") sets "a" to the new default!
        """
        if len(values) == 0:
            raise Exception("Must be given at least 1 choice for one_of")

        validated_value_results = [self.validate(v) for v in values]

        for index, vvr in enumerate(validated_value_results):
            if vvr.is_err():
                raise Exception(f"Invalid choice {index}: {vvr.unwrap_err()}")

        validated_values = [vvr.unwrap() for vvr in validated_value_results]
        return self.with_default(values[0]).with_extra_checks(
            check_one_of=lambda v: Ok(None) if v in validated_values else Err([f"Value not one of: {validated_values}"])
        )

    def one_of_any(self, *values: Any):
        fcv_results = [fcv_of(v) for v in values]

        for index, fcvr in enumerate(fcv_results):
            if fcvr.is_err():
                raise Exception(f"Non-FCValue choise {index}: {fcvr.unwrap_err()}")

        fcvs = [fcvr.unwrap() for fcvr in fcv_results]
        return self.one_of(*fcvs)

    @abstractmethod
    def validate(self, value: FCValue) -> Result[FCValue, list[str]]:
        """
        validate takes as input a FCValue and confirms that it abides by implementation 
        specific rules.

        On success it should return Ok(value | new_value).
        The idea is that given a `value` which may not be entirely complete, this function
        may decide to return a new complete value. For example, populating a struct with 
        default values for optional fields which were not provided.
        """
        pass

    def validate_any(self, value: Any) -> Result[FCValue, list[str]]:
        fcv_res = fcv_of(value)

        if fcv_res.is_err():
            return fcv_res

        return self.validate(fcv_res.unwrap())

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
    def default(self) -> Result[FCValue, list[str]]:
        return self.inner.default()

    @override
    def validate(self, value: FCValue) -> Result[FCValue, list[str]]:
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
    def default(self) -> Result[FCValue, list[str]]:
        return Ok(self.default_value)

class FCSchemaWithExtraChecks(FCSchemaWrapper):
    """
    This composite schema is meant for easy extension of provided schema types without
    the need of creating a whole new class!
    """

    @staticmethod
    def perform_checks(value: FCValue, **checks: Callable[[FCValue], Result[None, list[str]]]) -> Result[None, list[str]]:
        """
        Helper for performing a set of named checks on an FCValue!

        NOTE: Even in error case, this will perform ALL checks. The intention is to give as 
        detailed an error message as possible!
        """
        
        success = True
        err_msg = []

        for check_name, check in checks.items():
            result = check(value)

            if result.is_err():
                success = False
                err_msg += prepend_and_tab(
                    [f"Error @ check \"{check_name}\""],
                    result.unwrap_err()
                )
        
        return Ok(None) if success else Err(err_msg)

    def __init__(self, schema: FCSchema, **checks: Callable[[FCValue], Result[None, list[str]]]):
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
            dv_check_res = FCSchemaWithExtraChecks.perform_checks(dv, **checks)

            if dv_check_res.is_err():
                raise Exception("\n".join(
                    prepend_and_tab(["Default value failed checks"],
                        dv_check_res.unwrap_err()
                    )
                ))

    @override
    def validate(self, value: FCValue) -> Result[FCValue, list[str]]:
        res = super().validate(value)
        
        if res.is_err():
            return res

        # Always perform extra checks AFTER initial validation!
        v = res.unwrap()
        
        check_res = FCSchemaWithExtraChecks.perform_checks(v, **self.checks)
        return check_res.map(lambda n: Ok(v))

#
# Primitive types
#

class FCSchemaBool(FCSchema):
    @override 
    def validate(self, value: FCValue) -> Result[FCValue, list[str]]:
        if not isinstance(value, bool):
            return Err([f"Given value is not of type bool"])

        return Ok(value)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return translator.definition(prefix, cast(bool, value))

FCS_BOOL: FCSchema = FCSchemaBool()

class FCSchemaInt(FCSchema):
    @override 
    def validate(self, value: FCValue) -> Result[FCValue, list[str]]:
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
                    return Err([f"String could not be parsed as hex \"{value}\""])

            case _:
                return Err([f"Given value cannot be interpreted as an int"])

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        return translator.definition(prefix, cast(int, value))

FCS_INT: FCSchema = FCSchemaInt()

class FCSchemaStr(FCSchema):
    @override 
    def validate(self, value: FCValue) -> Result[FCValue, list[str]]:
        if not isinstance(value, str):
            return Err([f"Given value is not of type str"])

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
    def validate(self, value: FCValue) -> Result[FCValue, list[str]]:
        if not isinstance(value, list):
            return Err([f"Given value is not of type list"])
        
        list_value = cast(list[FCValue], value)
        ele_count = len(list_value)

        if ele_count < self.min_eles:
            return Err([f"Given list has too few elements"])

        if ele_count > self.max_eles and self.max_eles != 0:
            return Err([f"Given list has too many elements"])
        
        new_value = []
        err_msg = []
        success = True

        for i in range(ele_count):
            child_res = self.ele_schema.validate(list_value[i])
            if child_res.is_err():
                success = False
                err_msg += prepend_and_tab(
                    [f"StrictList Error @ index {str(i)}"],
                    child_res.unwrap_err()
                )

            # We only add to new_value if there's a chance it will be returned.
            # If success if False, we have already hit an error, and this is impossible.
            elif success: 
                new_value.append(child_res.unwrap())

        return Ok(new_value) if success else Err(err_msg)

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
    def validate(self, value: FCValue) -> Result[FCValue, list[str]]:
        if not isinstance(value, dict):
            return Err(["Given value is not of type dict"])

        dict_value = cast(dict[str, FCValue], value)

        new_value = {}
        err_msg = []
        success = True

        for k, v in dict_value.items():
            new_v = self.ele_schema.validate(v)
            if new_v.is_err():
                success = False
                err_msg += prepend_and_tab(
                    [f"StrictDict Error @ key \"{k}\""],
                    err_msg.unwrap_err()
                )
            elif success:
                new_value[k] = new_v.unwrap()

        return Ok(new_value) if success else Err(err_msg)

    @override
    def translate(self, prefix: str, value: FCValue, translator: FCTranslator) -> list[str]:
        output_lines = []
        dict_value = cast(dict[str, FCValue], value)

        for k, v in dict_value.items():
            output_lines += self.ele_schema.translate(prefix + "_" + k, v, translator)

        return output_lines


class FCSchemaStruct(FCSchema):

    @staticmethod
    def _fill_in_list(fvs: list[FCValue], fields: list[tuple[str, FCSchema]]) -> Result[dict[str, FCValue], list[str]]:
        """
        Helper method, given a list of value and a list of fields which should exist, 
        validate given fields and fill in missing fields, and return as a dictionary!

        NOTE: this function is private as it does not validate that field names in 'fields' are
        valid!
        """

        if len(fvs) > len(fields):
            return Err([f"Given {len(fvs)} fields, but expected <= {len(fields)}"])

        new_value = {}
        err_msg = []
        success = True

        for i, given_value in enumerate(fvs):
            field_name, field_schema = fields[i]
            rv = field_schema.validate(given_value) 
            if rv.is_err():
                success = False
                err_msg += prepend_and_tab(
                    [f"Error validating struct field \"{field_name}\""],
                    rv.unwrap_err()
                )
            elif success:
                new_value[field_name] = rv.unwrap()

        # Ok, now try to add defaults of fields not given
        for i in range(len(fvs), len(fields)):
            field_name, field_schema = fields[i]
            rv = field_schema.default()
            if rv.is_err():
                success = False
                err_msg += [f"Require field not specified \"{field_name}\""]
            elif success: 
                new_value[field_name] = rv.unwrap()

        return Ok(new_value) if success else Err(err_msg)


    @staticmethod
    def _fill_in_dict(fvs: dict[str, FCValue], fields: dict[str, FCSchema]) -> Result[dict[str, FCValue], list[str]]:
        """
        Helper method, given a dictionary of values, and a dictionary of fields validate given
        fields and filli n missing fields.

        (Realize this doesn't need a list of fields, as order is not needed in this case)
        
        Private as field name regex match is not applied to `fields`.

        DOES NOT modify `fvs`, returns a new dictionary!
        """

        new_value = {}
        err_msg = []
        success = True

        for field_name, field_value in fvs.items():
            if field_name not in fields:
                success = False
                err_msg += [f"Unknown field provided \"{field_name}\""]
            else:
                field_schema = fields[field_name]
                rv = field_schema.validate(field_value)
                if rv.is_err():
                    success = False
                    err_msg += prepend_and_tab(
                        [f"Error validating struct field \"{field_name}\""],
                        rv.unwrap_err()
                    )
                elif success:
                    new_value[field_name] = rv.unwrap()

        # Ok, now for unprovided fields
        for field_name, field_schema in fields.items():
            if field_name not in fvs:
                rv = field_schema.default()
                if rv.is_err():
                    success = False
                    err_msg += [f"Required field not specified \"{field_name}\""]
                elif success:
                    new_value[field_name] = rv.unwrap()

        return Ok(new_value) if success else Err(err_msg)

    @staticmethod
    def _append_derived(fvs: dict[str, FCValue], derived: dict[str, tuple[FCSchema, Callable[[FCValue], FCValue]]]) -> dict[str, FCValue]:
        """
        Helper for generating and adding derived fields to a dictionary!

        This DOES NOT modify fvs!
        """
        new_derived_values = {}
        err_msg = []
        success = True

        for df_name, (df_schema, df_func) in derived.items():
            rdv = df_schema.validate(df_func(fvs))

            if rdv.is_err():
                success = False
                err_msg += prepend_and_tab(
                    [f"Error creating derived field \"{df_name}\""],
                    rdv.unwrap_err()
                )
            elif success:
                new_derived_values[df_name] = rdv.unwrap()
        
        # If a derived field fails its own schema, this is the fault of the schema creator!
        # NOT THE USER!
        if not success:
            raise Exception("\n".join(err_msg))

        return fvs | new_derived_values

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
        
        # We'll store fields in two forms just for convenience.
        self.fields_list = fields[:]
        self.fields_dict: dict[str, FCSchema] = {}

        # First confirm all field names are valid! (Creating fields dict while we go)
        for (field, schema) in self.fields_list 
            if not FC_ID_PATTERN.fullmatch(field):
                raise Exception(f"FCSchemaStruct field name is invalid \"{field}\"")
            
            if field in self.fields_dict:
                raise Exception(f"FCSchemaStruct has repeat field name \"{field}\"")

            self.fields_dict[field] = schema

        # For derived fields, we must confirm names are valid AND no repeat names!
        for field, (schema, func) in derived.items():
            # This may be redundant because we are using kwargs, but whatever.
            if not FC_ID_PATTERN.fullmatch(field):
                raise Exception(f"FCSchemaStruct derived field name is invalid \"{field}\"")

            if field in self.fields_dict:
                raise Exception(f"FCSchemaStruct derived field name already exists \"{field}\"")

        self.derived_dict = derived

        # Ok, finally, let's attempt to create a default value. (It is ok if this fails)
        # To create the default, we ask for the default value from all explicit field schema.
        # If all those schema have defaults, then the resulting value is passed to the derived
        # value functions! 
        dvr = FCSchemaStruct._fill_in_dict({}, self.fields_dict))
        if dvr.is_ok():
            dvr = Ok(FCSchemaStruct._append_derived(dvr.unwrap(), self.derived_dict))

        self.default_result = dvr

    @override
    def default(self) -> Result[FCValue, list[str]]:
        return self.default_result 

    @override 
    def validate(self, value: FCValue) -> Result[FCValue, list[str]]:
        """
        While both list or dict FCValues are accepted by this function, only a dict is ever 
        returned!
        """
        valid_res: Result[dict[str, FCValue], list[str]] = Ok({})
        match value:
            case list():
                valid_res = FCSchemaStruct._fill_in_list(value, self.fields_list)
            case dict():
                valid_res = FCSchemaStruct._fill_in_dict(value, self.fields_dict)
            case _:
                return Err(["Struct must either be specified as a list or dict"])

        return valid_res.map(lambda fvs: FCSchemaStruct._append_derived(fvs, self.derived_dict))

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
