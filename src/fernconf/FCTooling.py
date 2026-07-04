from __future__ import annotations

from typing import NoReturn

from fernconf.FCValue import *
from fernconf.FCTranslator import *
from fernconf.FCSchema import *

import argparse as ap
import json

import pathtype as pt # type: ignore[import-untyped]
import pathlib as pl

def run(schema: FCSchema, prefix: str="FC", **translators: FCTranslator) -> NoReturn:
    """
    Run fernconf cli given a schema and supported translators!
    """
    p = ap.ArgumentParser(prog="FernConf", 
                          description="General purpose configuration tool intended for FernOS!")

    p.add_argument("filename", type=pt.Path(exists=True, readable=True), help="JSON file to be validated/translated")
    p.add_argument("-f", "--format", choices=list(translators.keys()), help="The translator used when outputing a config")
    p.add_argument("-o", "--output", type=pt.Path(writable_or_creatable=True), default=pl.Path("./a.out"), help="Path of output file")

    args = p.parse_args()
    
    fn = args.filename # Gauranteed to exist.
    
    data = {}
    try:
        with open(fn, "r") as f:
            data = json.load(f)
    except:
        print(f"Failed to parse input file {fn}") 
        exit(1)

    fcv_res = fcv_of(data)

    if fcv_res.is_err():
        print(f"Failed to validate input file {fn}")
        print(fcv_res.unwrap_err())
        exit(1)

    fcv = fcv_res.unwrap()

    if args.format is not None:
        t = translators[args.format]
        lines = schema.translate(prefix, fcv, t)
        args.output.write_text("\n".join(lines))

    exit(0)
