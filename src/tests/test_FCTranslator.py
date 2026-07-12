from fernconf.FCValue import *
from fernconf.FCTranslator import *

def try_FCTranslator(translator: FCTranslator) -> None:
    """
    It's hard to truly test what a translator is supposed to print out.
    This function just tries running `comment` and `definition` with differnet values 
    to confirm there is no major error!
    """
    translator.comment([])
    translator.comment(["hello"])
    translator.comment(["hello", "", "goodbye"])

    translator.definition("val1", "hello")
    translator.definition("val2", 12389)
    translator.definition("val2", True)

def test_gcc_translator():
    try_FCTranslator(FCT_GCC)

def test_gas_translator():
    try_FCTranslator(FCT_GAS)

def test_ld_translator():
    try_FCTranslator(FCT_LD32)

def test_make_translator():
    try_FCTranslator(FCT_MAKE)
