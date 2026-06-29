from fernconf.FCValue import *
from fernconf.FCTranslator import *
from fernconf.FCSchema import *
import pytest

class TestSimpleSchema:
    def test_schema_bool(self) -> None:
        bs = FCS_BOOL
        assert bs.validate_any(0.324).is_err()
        assert bs.validate_any(True) == Ok(True)
        assert bs.validate_any(False) == Ok(False)

        # Again, for translate, we just make sure no exceptions are thrown!
        v_res = bs.validate_any(True)
        assert v_res.is_ok()
        bs.translate("BOOL", v_res.unwrap(), FCT_CLANG)

    def test_schema_int(self) -> None:
        s = FCS_INT
        assert s.validate_any(1) == Ok(1)
        assert s.validate_any(1.2).is_err()
        assert s.validate_any(-100) == Ok(-100)
        assert s.validate_any("hello").is_err()

        v_res = s.validate_any(10)
        assert v_res.is_ok()
        s.translate("INT", v_res.unwrap(), FCT_CLANG)

    def test_schema_str(self) -> None:
        s = FCS_STR
        assert s.validate_any("Hello") == Ok("Hello")
        assert s.validate_any(2.3).is_err()
        assert s.validate_any(-100).is_err()
        assert s.validate_any("") == Ok("")

        v_res = s.validate_any("strval")
        assert v_res.is_ok()
        s.translate("STR", v_res.unwrap(), FCT_CLANG)

class TestSimpleComposites:
    """
    This test isn't that rigorous for the "with" endpoints.
    These will be tested more with the standard composites test.
    """

    def test_with_description(self) -> None:
        s = FCS_BOOL
        assert s.description() == []

        desc1 = ["line1", "line2"]
        desc2 = ["line3"]

        s = s.with_description(desc1)
        assert s.description() == desc1
        assert s.validate_any(True) == Ok(True)

        s = s.with_description(desc2)
        assert s.description() == desc2 + [""] + desc1

        with pytest.raises(Exception):
            s.with_description([])

    def test_with_comment(self) -> None:
        s = FCS_INT
        assert s.default().is_err()

        s = s.with_default_any(1)
        assert s.default() == Ok(1)

        s = s.with_default_any(2)
        assert s.default() == Ok(2)

        with pytest.raises(Exception):
            s.with_default_any(1.23)

        with pytest.raises(Exception):
            s.with_default_any("343")

    def test_with_extra_checks(self) -> None:
        s = FCS_INT
        assert s.validate_any(1) == Ok(1)

        s = s.with_extra_checks(even_check=lambda v: Ok(None) if v % 2 == 0 else Err("Must be even"))
        assert s.validate_any(1).is_err()

        with pytest.raises(Exception):
            s.with_default_any(1)

        s = s.with_default_any(2)
        with pytest.raises(Exception):
            s.with_extra_checks(not_two=lambda v: Ok(None) if v != 2 else Err("Cannot be two"))

        s = s.with_extra_checks(
            not_four=lambda v: Ok(None) if v != 4 else Err("Cannot be four"),
            not_six=lambda v: Ok(None) if v != 6 else Err("Cannot be six") 
        )

        assert s.validate_any("Hello").is_err()
        assert s.validate_any(1).is_err() # Old checks should still apply.
        assert s.validate_any(4).is_err()
        assert s.validate_any(6).is_err()

        with pytest.raises(Exception):
            s.with_default_any(1)

        with pytest.raises(Exception):
            s.with_default_any(6)

        assert s.validate_any(8) == Ok(8)

