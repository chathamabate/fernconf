from fernconf.FCValue import *
from fernconf.FCCheck import *
from result import Ok, Err, Result
import pytest

class TestFCCheck:

    # I decided to jazz things by constructing a new fc value for each test.
    # I could've just had one nice big dict defined up here, but whatever.

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

        with pytest.raises(Exception):
            fcc_and()


    def test_fcc_or(self) -> None:
        fcv = fcv_of([
            True, False, True
        ]).unwrap()

        assert fcc_or(fcc_b("0"))(fcv).is_ok()
        assert fcc_or(fcc_b("0"), fcc_b("1"))(fcv).is_ok()
        assert fcc_or(fcc_b("0"), fcc_b("1"), fcc_b("2"))(fcv).is_ok()
        assert fcc_or(fcc_b("1"))(fcv).is_err()
        assert fcc_or(fcc_not(fcc_b("0")), fcc_b("1"))(fcv).is_err()

        with pytest.raises(Exception):
            fcc_or()

    def test_fcc_xor(self) -> None:
        fcv = fcv_of({
            "p": {
                "r": [True, False]
            }
        }).unwrap()

        assert fcc_xor(fcc_b("p.r.0"))(fcv).is_ok()
        assert fcc_xor(fcc_b("p.r.0"), fcc_b("p.r.1"))(fcv).is_ok()
        assert fcc_xor(fcc_b("p.r.0"), fcc_b("p.r.1"), fcc_b("p.r.1"))(fcv).is_ok()

        assert fcc_xor(fcc_b("p.r.0"), fcc_b("p.r.0"))(fcv).is_err()
        assert fcc_xor(fcc_b("p.r.1"), fcc_b("p.r.1"))(fcv).is_err()

        with pytest.raises(Exception):
            fcc_xor()

    def test_fcc_if(self) -> None:
        fcv = fcv_of([True, False]).unwrap()

        assert fcc_if(fcc_b("0"), fcc_b("0"))(fcv).is_ok()
        assert fcc_if(fcc_b("0"), fcc_b("1"))(fcv).is_err()
        assert fcc_if(fcc_b("1"), fcc_b("0"))(fcv).is_ok()
        assert fcc_if(fcc_b("1"), fcc_b("1"))(fcv).is_ok()

    def test_fcc_big_expr(self) -> None:
        fcv = fcv_of({
            "p": {
                "p": False,
                "r": True
            },
            "r": [
                {
                    "p": False,
                    "n": 10
                },
                {
                    "p": True,
                    "n": 5
                }
            ]
        }).unwrap()

        assert fcc_and(
            fcc_or(fcc_b("r.0.p"), fcc_b("r.1.p")),
            fcc_not(fcc_b("p.p"))
        )(fcv).is_ok()

        assert fcc_if(
            fcc_not(lambda v: Ok(None) if fcv_getp_int(fcv, "r.1.n") % 2 == 0 else Err([])),
            fcc_xor(fcc_b("p.p"), fcc_b("p.r"))
        )(fcv).is_ok()

        assert fcc_xor(
            fcc_if(fcc_b("p.p"), fcc_b("p.p")),
            fcc_and(fcc_b("r.0.p")),
            fcc_or(fcc_b("r.1.p"))
        )(fcv).is_err()
        
