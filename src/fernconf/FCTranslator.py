from __future__ import annotations

from fernconf.FCValue import FCValue, FC_ID_PATTERN
from abc import ABC, abstractmethod
from typing import Any, override, cast
from result import Ok, Err, Result

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
    def comment(self, message: list[str]) -> list[str]:
        """
        Create a comment in the target format.
        Each element in `message` represents a single line of the comment message.
        Returns a list of the lines of the created comment.
        Neither input nor output lines should have newline characters!
        """
        pass

    def _definition_str(self, value_name: str, value: str) -> list[str]:
        return []

    def _definition_bool(self, value_name: str, value: bool) -> list[str]:
        return []

    def _definition_int(self, value_name: str, value: int) -> list[str]:
        return []

    def definition(self, value_name: str, value: str | bool | int) -> list[str]:
        """
        Create a definition in the target format!

        If `value_name` does not follow FC_ID_PATTERN, an exception will be thrown.
        
        Note that `value_name` must appear EXACTLY as is in the output definition.
        """
        if not FC_ID_PATTERN.fullmatch(value_name):
            # Note that this does not return a result. If we make it here, the implementor
            # made a mistake (not the user). 
            raise Exception(f"value name did not follow FC ID regex format: \"{value_name}\"")

        match value:
            case str():
                return self._definition_str(value_name, value)

            case bool():
                return self._definition_bool(value_name, value)

            case int():
                return self._definition_int(value_name, value)
                
            case _:
                raise Exception(f"Can't define given value \"{value_name}\", unexpected type")


class FCTranslatorCLang(FCTranslator):
    @override
    def comment(self, message: list[str]) -> list[str]:
        return ["/*"] + [" * " + line for line in message] + [" */"]

    @override
    def _definition_str(self, value_name: str, value: str) -> list[str]:
        return [f"#define {value_name} \"{value}\""]

    @override
    def _definition_bool(self, value_name: str, value: bool) -> list[str]:
        return [("" if value else "// ") + f"#define {value_name}"]

    @override
    def _definition_int(self, value_name: str, value: int) -> list[str]:
        if value < 0:
            neg_suffix = "LL" if value < -0x8000_0000 else "L"
            return [f"#define {value_name} ({str(value)}{neg_suffix})"]
        
        pos_suffix = "ULL" if value > 0xFFFF_FFFF else "UL"
        return [f"#define {value_name} (0x{value:X}{pos_suffix})"]

FCT_CLANG = FCTranslatorCLang()

class FCTranslatorLD32(FCTranslator):
    """
    This is kinda unique, this if for linker scirpts of 32-bit binaries.
    It uses C preprocessor directives though, declaring actual integer style variables in 
    linkerscripts will create a symbol in the binary! 

    The intention that the user of this will invoke the C preprocessor on their linker script
    (which should #include the output of this translator)
    """

    @override
    def comment(self, message: list[str]) -> list[str]:
        return ["/*"] + [" * " + line for line in message] + [" */"]

    @override
    def _definition_int(self, value_name: str, value: int) -> list[str]:
        if value < 0 or 0xFFFF_FFFF < value:
            return []

        # We only translate integer values which could be valid memory addresses!
        # No other values should ever be referenceable in a linker script!
        return [f"#define {value_name} (0x{value:X})"]

FCT_LD32 = FCTranslatorLD32()

class FCTranslatorMake(FCTranslator):
    @override
    def comment(self, message: list[str]) -> list[str]:
        return ["#  " + line for line in message]

    @override
    def _definition_str(self, value_name: str, value: str) -> list[str]:
        return [f"{value_name}:={value}"]

    @override
    def _definition_bool(self, value_name: str, value: bool) -> list[str]:
        return [f"{value_name}:={'y' if value else 'n'}"] # y/n in Make!

    @override
    def _definition_int(self, value_name: str, value: int) -> list[str]:
        if value < 0:
            return [f"{value}:={str(value)}"]

        return [f"{value_name}:=0x{value:X}"]

FCT_MAKE = FCTranslatorMake()

