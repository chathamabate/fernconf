from fernconf.FCValue import *
from fernconf.FCTranslator import *

def try_FCTranslator(translator: FCTranslator) -> None:
    """
    It's hard to truly test what a translator is supposed to print out.
    This function just tries running `comment` and `definition` with differnet values 
    to confirm there is no major error!
    """
    translator.comment([], True)
    translator.comment([], False)
    translator.comment(["hello"], True)
    translator.comment(["hello"], False)
    translator.comment(["hello", "", "goodbye"], True)
    translator.comment(["hello", "", "goodbye"], False)

    translator.definition("val1", "hello", None)
    translator.definition("val2", 12389, ["line1", "line2"])
    translator.definition("val2", True, [])

def test_clang_translator():
    try_FCTranslator(FCT_CLANG)
