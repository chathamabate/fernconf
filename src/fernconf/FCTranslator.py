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

    @abstractmethod
    def _definition(self, value_name: str, value: str | bool | int) -> list[str]:
        pass

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

        return self._definition(value_name, value)


class FCTranslatorCLang(FCTranslator):
    @override
    def comment(self, message: list[str]) -> list[str]:
        return ["/*"] + [" * " + line for line in message] + [" */"]

    @override
    def _definition(self, value_name: str, value: str | bool | int) -> list[str]:
        match value:
            case str():
                return [f"#define {value_name} \"{value}\""]
            case bool():
                return [("" if value else "// ") + f"#define {value_name}"]
            case int():
                if value < 0:
                    neg_suffix = "LL" if value < -0x8000_0000 else "L"
                    return [f"#define {value_name} ({str(value)}{neg_suffix})"]
                
                pos_suffix = "ULL" if value > 0xFFFF_FFFF else "UL"
                return [f"#define {value_name} (0x{value:X}{pos_suffix})"]
                
            case _:
                raise Exception(f"Can't define given value \"{value_name}\"")

FCT_CLANG = FCTranslatorCLang()

class FCTranslatorMake(FCTranslator):
    @override
    def comment(self, message: list[str]) -> list[str]:
        return ["#  " + line for line in message]

    @override
    def _definition(self, value_name: str, value: str | bool | int) -> list[str]:
        match value:
            case str():
                return [f"{value_name}:={value}"]
            case bool():
                return [f"{value_name}:={'y' if value else 'n'}"] # y/n in Make!
            case int():
                if value < 0:
                    return [f"{value}:={str(value)}"]

                return [f"{value_name}:=0x{value:X}"]
                
            case _:
                raise Exception(f"Can't define given value \"{value_name}\"")

FCT_MAKE = FCTranslatorMake()
