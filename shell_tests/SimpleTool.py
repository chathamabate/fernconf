from fernconf.FCValue import *
from fernconf.FCTranslator import *
from fernconf.FCSchema import *
from fernconf.FCTooling import *

simple_schema = FCSchemaStruct([
    ("area_name", FCS_STR),
    ("cities", FCSchemaStrictList(
        FCSchemaStruct([
            ("location", FCS_STR),
            ("population", FCS_INT.with_extra_checks(
                not_empty=lambda pop: Ok(None) if cast(int, pop) > 0 else Err("value must be positive non-zero")
            ))
        ])
    ))
])

if __name__ == "__main__":
    run_fernconf(simple_schema, clang=FCT_CLANG)


