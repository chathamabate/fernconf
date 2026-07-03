from __future__ import annotations

from fernconf.FCValue import *
from fernconf.FCTranslator import *
from fernconf.FCSchema import *

import argparse as ap

import pathtype as pt # type: ignore[import-untyped]

def run(schema: FCSchema, **translators: FCTranslator) -> None:
    """
    Run fernconf cli given a schema and supported translators!
    """
    p = ap.ArgumentParser(prog="FernConf", 
                          description="General purpose configuration tool intended for FernOS!")

    p.add_argument("filename", type=pt.Path(exists=True, readable=True), help="JSON file to be validated/translated")
    p.add_argument("-f", "--format", choices=list(translators.keys()), help="The translator used when outputing a config")
    p.add_argument("-o", "--output", type=pt.Path(writable_or_creatable=True), help="Path of output file")

    args = p.parse_args()


run(FCS_STR, clang=FCT_CLANG)


