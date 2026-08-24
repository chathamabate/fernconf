from fernconf.FCValue import *
from fernconf.FCCheck import *
from result import Ok, Err, Result
import pytest

class TestFCCheck:
    def test_fcc_b(self) -> None:
        fcv = fcv_of({
            "p": {
                "r": True,
                "q": False
            }
        }).unwrap()

        assert fcc_b("p.r")(fcv).is_ok()
        assert fcc_b("p.q")(fcv).is_err()

    def test_fcc_not(self) -> None:
        fcv = fcv_of({
            "p": [True, False]
        }).unwrap()

        assert fcc_not(fcc_b("p.0"))(fcv).is_err()
        assert fcc_not(fcc_b("p.1"))(fcv).is_ok()

    def test_fcc_and(self) -> None:
        fcv = fcv_of({
            "p": True,
            "r": False,
            "s": True
        }).unwrap()

        assert fcc_and(fcc_b("p"), fcc_b("s"))(fcv).is_ok()
        assert fcc_and(fcc_b("p"), fcc_b("r"), fcc_b("s"))(fcv).is_err()
        assert fcc_and(fcc_b("r"))(fcv).is_err()
        assert fcc_and(fcc_b("s"))(fcv).is_ok()

    def test_fcc_or(self) -> None:
        fcv = fcv_of([
            True, False, True
        ]).unwrap()

        assert fcc_or(fcc_b("0"))(fcv).is_ok()
        assert fcc_or(fcc_b("0"), fcc_b("1"))(fcv).is_ok()
        assert fcc_or(fcc_b("0"), fcc_b("1"), fcc_b("2"))(fcv).is_ok()
        assert fcc_or(fcc_b("1"))(fcv).is_err()
        assert fcc_or(fcc_not(fcc_b("0")), fcc_b("1"))(fcv).is_err()
