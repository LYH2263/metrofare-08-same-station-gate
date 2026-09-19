import unicodedata


def normalize_code(code) -> str:
    """规范化站点编码：NFKC（全角→半角）、去掉所有空白（含全角空格）、转大写。"""
    if code is None:
        return ""
    folded = unicodedata.normalize("NFKC", str(code))
    # str.split() 会按 Unicode 空白切分，覆盖空格、制表符、U+3000 全角空格、U+00A0 等。
    return "".join(folded.split()).upper()
