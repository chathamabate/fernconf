from fernconf.FCValue import *
from result import Ok, Err, Result
import pytest

def test_fcv_int_check():
    """
    The core logic of this check is already covered by test_fcv_of_int.
    This just confirms a true exception is raised when expected. 
    """
    with pytest.raises(Exception):
        fcv_int_check(-0x1_0000_0000_0000_0000)
    fcv_int_check_result(0)

class TestFCValue:
    def test_fcv_of_int(self):
        assert fcv_of(1) == Ok(1)
        assert fcv_of(2) == Ok(2)
        assert fcv_of(0) == Ok(0)
        assert fcv_of(-2) == Ok(-2)
        assert fcv_of(0x8000_0000_0000_0000) == Ok(0x8000_0000_0000_0000)
        assert fcv_of(-0x8000_0000_0000_0000) == Ok(-0x8000_0000_0000_0000)
        assert fcv_of(0xFFFF_FFFF_FFFF_FFFF) == Ok(0xFFFF_FFFF_FFFF_FFFF)
        assert fcv_of(0x1_0000_0000_0000_0000).is_err()
        assert fcv_of(-0x8000_0000_0000_0001).is_err()

    def test_fcv_of_bool(self):
        assert fcv_of(True) == Ok(True)
        assert fcv_of(False) == Ok(False)

    def test_fcv_of_str(self):
        assert fcv_of("hello") == Ok("hello")
        assert fcv_of("") == Ok("")

    def test_fcv_of_list(self):
        assert fcv_of([1, 2, 3]) == Ok([1, 2, 3])
        assert fcv_of(["hello"]) == Ok(["hello"])
        assert fcv_of([]) == Ok([])
        assert fcv_of([[1, 2, 3], ["hello"]]) == Ok([[1, 2, 3], ["hello"]])
        assert fcv_of([True, 1, "h"]) == Ok([True, 1, "h"])
        assert fcv_of([1, 1.5]).is_err()

    def test_fcv_of_dict(self):
        assert fcv_of({"a": 1}) == Ok({"a": 1})
        assert fcv_of({"ab": 2, "c": "name", "d": True}) == Ok({"ab": 2, "c": "name", "d": True})
        assert fcv_of({"prop": [1, 2, 3], "prop2": {"a": True}}) == Ok({"prop": [1, 2, 3], "prop2": {"a": True}})
        assert fcv_of({}) == fcv_of({})
        assert fcv_of({" ": 1}).is_err()
        assert fcv_of({"a": 1.2}).is_err()

    def test_fcv_of_bad(self):
        assert fcv_of(3.4).is_err()

