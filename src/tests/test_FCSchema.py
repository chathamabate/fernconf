from fernconf.FCValue import *
from fernconf.FCTranslator import *
from fernconf.FCSchema import *
import pytest

class TestSimpleSchema:
    def test_schema_bool(self) -> None:
        bs = FCSchemaBool()
        assert bs.validate_any(0.324).is_err()
        assert bs.validate_any(True) == Ok(True)
        assert bs.validate_any(False) == Ok(False)

        # Again, for translate, we just make sure no exceptions are thrown!
        v_res = bs.validate_any(True)
        assert v_res.is_ok()
        bs.translate("BOOL", v_res.unwrap(), FCT_CLANG)

    def test_schema_int(self) -> None:
        s = FCSchemaInt()
        assert s.validate_any(1) == Ok(1)
        assert s.validate_any(1.2).is_err()
        assert s.validate_any(-100) == Ok(-100)
        assert s.validate_any("hello").is_err()

        v_res = s.validate_any(10)
        assert v_res.is_ok()
        s.translate("INT", v_res.unwrap(), FCT_CLANG)

    def test_schema_str(self) -> None:
        s = FCSchemaStr()
        assert s.validate_any("Hello") == Ok("Hello")
        assert s.validate_any(2.3).is_err()
        assert s.validate_any(-100).is_err()
        assert s.validate_any("") == Ok("")

        v_res = s.validate_any("strval")
        assert v_res.is_ok()
        s.translate("STR", v_res.unwrap(), FCT_CLANG)
