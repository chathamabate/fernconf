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
        # Like "with comment" it's kinda hard to test this without knowing exactly how
        # descriptions are concatenated. So, here we just make sure calling `descritpion()`
        # doesn't throw some exception.
        s = FCS_STR
        s.description()

        s = s.with_description(["A desc"])
        s.description()

        s = s.with_description(["A desc", "again"])
        s.description()

    def test_with_comment(self) -> None:
        # It's kinda difficult to really test with comment, so we just make sure translate
        # doesn't explode.
        s = FCS_STR.with_comment(["hello"])
        s.translate("MY_VAL", "hello", FCT_CLANG)

        s = s.with_comment(["anotha"])
        s.translate("MY_VAL", "aye yo", FCT_CLANG)

    def test_with_default(self) -> None:
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

        s = s.with_extra_checks(even_check=lambda v: Ok(None) if cast(int, v) % 2 == 0 else Err("Must be even"))
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

class TestStandardComposites:
    def test_schema_strict_list(self) -> None:
        s = FCSchemaStrictList(FCS_INT.with_description(["A normal int"])).with_description(["An array"])
        assert s.validate_any([]) == Ok([])
        assert s.validate_any([1, 2, 3]) == Ok([1, 2, 3])
        assert s.validate_any([1, 2, "hello"]).is_err()

        # Just make sure a simple translate/describe doesn't explode.
        val_res = s.validate_any([1, 2, 5])
        assert val_res.is_ok()
        s.translate("MY_ARR", val_res.unwrap(), FCT_CLANG)
        s.description()

        with pytest.raises(Exception):
            FCSchemaStrictList(FCS_INT, 10, 1)

        s = FCSchemaStrictList(FCS_INT, 3, 5)
        assert s.validate_any([1, 2]).is_err()
        assert s.validate_any([1, 2, 3]) == Ok([1, 2, 3])
        assert s.validate_any([1, 2, 3, 4]) == Ok([1, 2, 3, 4])
        assert s.validate_any([1, 2, 3, 4, 5]) == Ok([1, 2, 3, 4, 5])
        assert s.validate_any([1, 2, 3, 4, 5, 6]).is_err()

        s = FCSchemaStrictList(FCS_STR, 1, 1)
        assert s.validate_any([]).is_err()
        assert s.validate_any(["H"]) == Ok(["H"])
        assert s.validate_any(["H", "T"]).is_err()

        s = FCSchemaStrictList(FCS_STR, 1, 0)
        assert s.validate_any([]).is_err()
        assert s.validate_any(["H"]) == Ok(["H"])
        assert s.validate_any(["H", "T"]) == Ok(["H", "T"])

    def test_schema_struct(self) -> None:
        # A struct schema must have 1 or more fields.
        with pytest.raises(Exception):
            FCSchemaStruct([])

        with pytest.raises(Exception):
            FCSchemaStruct([
                ("  ", FCS_INT) # Invalid field name.
            ])

        with pytest.raises(Exception):
            FCSchemaStruct([
                ("a", FCS_INT),
                ("a", FCS_INT) # Repeat field name.
            ])

        s = FCSchemaStruct([
            ("name", FCS_STR.with_description(["Person name"])),
            ("age", FCS_INT.with_default_any(20).with_description(["Person Age"]))
        ]).with_description(["A person"])
        
        # List style struct values.
        assert s.validate_any(["bob", 12]) == Ok({"name": "bob", "age": 12})
        assert s.validate_any(["bob"]) == Ok({"name": "bob", "age": 20})
        assert s.validate_any([]).is_err() # No default name!
        assert s.default().is_err()

        assert s.validate_any([1]).is_err()
        assert s.validate_any(["bob", "smith"]).is_err()
        assert s.validate_any([10, 10]).is_err()

        # Dict style struct values.
        assert s.validate_any({"name": "bob", "age": 70}) == Ok({"name": "bob", "age": 70})
        assert s.validate_any({"name": "bob"}) == Ok({"name": "bob", "age": 20})
        assert s.validate_any({}).is_err()

        assert s.validate_any({"name": 12}).is_err()
        
        rv = s.validate_any(["bob", 16])
        assert rv.is_ok()
        s.translate("", rv.unwrap(), FCT_CLANG) # Simple translate check!
        s.description()

        # Let's just test out a full default, why not!
        s = FCSchemaStruct([
            ("v", FCS_INT.with_default_any(1)),
            ("p", FCS_INT.with_default_any(2)),
            ("r", FCS_INT.with_default_any(3))
        ])

        assert s.default() == Ok({"v": 1, "p": 2, "r": 3})

class TestBigComposites:
    """
    Kinda just misc tests with big ass schema.
    """
    def test_big_schema0(self) -> None:
        s = FCSchemaStruct([
            ("area_name", FCS_STR),
            ("cities", FCSchemaStrictList(
                FCSchemaStruct([
                    ("location", FCS_STR),
                    ("population", FCS_INT.with_extra_checks(
                        not_empty=lambda pop: Ok(None) if cast(int, pop) > 0 else Err("value must be positive non-zero")
                    ))
                ])
            ))
        ]).with_description(["A record describing a certain area"])

        rv = s.validate_any({
            "area_name": "New Jersey",
            "cities": [
                ["SmithVille", 1000],
                ["ML", 4000],
                {"location": "Boonton", "population": 5000},
            ]
        }) 

        assert rv == Ok({
            "area_name": "New Jersey",
            "cities": [
                {"location": "SmithVille", "population": 1000},
                {"location": "ML", "population": 4000},
                {"location": "Boonton", "population": 5000},
            ]
        })
        s.translate("FC", rv.unwrap(), FCT_CLANG)

        assert s.default().is_err()
        assert s.validate_any(["Cali", []]) == Ok({
            "area_name": "Cali",
            "cities": []
        })

        assert s.validate_any(["Mexico", [["MC", -1]]]).is_err()

    def test_big_schema1(self) -> None:
        sr = FCSchemaStrictList(FCS_INT, 2, 2).with_extra_checks(
            range_check=lambda v: Ok(None) if cast(list[int], v)[0] <= cast(list[int], v)[1] else Err("invalid bounds")
        ).with_default_any([0, 0])

        s = FCSchemaStruct([
            ("x_intervals", FCSchemaStrictList(sr).with_default_any([])),
            ("y_intervals", FCSchemaStrictList(sr).with_default_any([]))
        ])

        assert s.default() == Ok({
            "x_intervals": [],
            "y_intervals": []
        })

        assert s.validate_any([
            [[]],
        ]).is_err()

        assert s.validate_any([
            [[1, 2]],
        ]) == Ok({
            "x_intervals": [[1, 2]],
            "y_intervals": []
        })

        assert s.validate_any([
            [[1, 3]],
            [[2, 3], [4, 5], [6, 5]]
        ]).is_err()

        rv = s.validate_any({
            "x_intervals": [],
            "y_intervals": [[1, 2]]
        }) 

        assert rv == Ok({
            "x_intervals": [],
            "y_intervals": [[1, 2]]
        })
        s.translate("FC", rv.unwrap(), FCT_CLANG)


