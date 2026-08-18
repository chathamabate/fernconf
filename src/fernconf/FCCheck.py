from __future__ import annotations

from fernconf.FCValue import *
from typing import Any, override, cast, Callable

type FCCheck = Callable[[FCValue], Result[None, list[str]]]
"""
An FCCheck simply checks a value in some way.

Ok(None) means Success, while Err(<mesg>) means Failure.
"""

# Maybe we could make error messages a little better?
# I think this would be a big improvement tbh.


type FCBoolCondition = Callable[[FCValue], bool]
"""
FCExtraCheck is great because you can return a dynamcially created error message.
Although, sometimes this is tedious.

FCBoolCondition is a simpler version supported by some of the below constructors.
True mean Success and False means Failure.
"""

# IDK Return like just the path??? Would that be good or bad???
# I don't really know tbh... something to think about for sure.
def fec_bool_opt() -> FCExtraCheck:
    pass

# Maybe an option type thing?

def fec_requires(**conditions: FCBoolCondition) -> FCExtraCheck:
    """
    This extra check will fail if any of the 
    """
    pass

# Alright, so what else? Maybe some sort of condition type thing?
