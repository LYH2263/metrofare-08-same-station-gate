import re
import unicodedata

_WS_RE = re.compile(r"\s+", re.UNICODE)


def normalize_code(code) -> str:
    """NFKC 后删除所有空白(含全角空格 U+3000、制表符等)并统一大写。"""
    s = unicodedata.normalize("NFKC", str(code))
    return _WS_RE.sub("", s).upper()
