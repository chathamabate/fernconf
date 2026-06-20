from fernconf.FCValue import FCValue, FC_ID_PATTERN

from __future__ import annotations
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
