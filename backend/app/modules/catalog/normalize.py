import re

_CODE_JUNK = re.compile(r"[\s\-_./\\]+")
_NAME_JUNK = re.compile(r"[\s\-_.]+")


def normalize_code(code: str) -> str:
    """'HU-66', 'hu 66', 'HU.66' -> 'HU66'. Letters/suffixes are kept: HU66P != HU66."""
    return _CODE_JUNK.sub("", code).upper()


def normalize_brand(name: str) -> str:
    """'Key-Line', 'keyline', 'KEY LINE' -> 'keyline'."""
    return _NAME_JUNK.sub("", name).casefold()
