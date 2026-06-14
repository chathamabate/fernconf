from abc import ABCMeta, abstractmethod
from enum import Enum
import re
from typing import ClassVar

class Property(metaclass=ABCMeta):
    NAME_PATTERN: ClassVar[re.Pattern] = re.compile("name")

    def __init__(self, name: str):
        if not Property.NAME_PATTERN.fullmatch(name):
            raise Exception(f"Invalid name given \"{name}\"")

        self.name = name

