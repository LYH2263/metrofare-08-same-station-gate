from app.codes import normalize_code


def test_exact_and_empty():
    assert normalize_code("A1") == "A1"
    assert normalize_code("") == ""
    assert normalize_code(None) == ""


def test_whitespace_stripped():
    assert normalize_code(" A1") == "A1"
    assert normalize_code("A1 ") == "A1"
    assert normalize_code(" A 1 ") == "A1"   # 内部空白也移除
    assert normalize_code("A\t1") == "A1"


def test_full_width_space_and_chars():
    assert normalize_code("　A1　") == "A1"          # U+3000 全角空格
    assert normalize_code("Ａ１") == "A1"            # 全角字母数字 NFKC
    assert normalize_code("　ａ１") == "A1"          # 全角空格 + 全角小写


def test_case_folded():
    assert normalize_code("a1") == "A1"
    assert normalize_code("  b2 ") == "B2"


def test_same_after_normalization():
    variants = ["A1", " a1", "a 1", "Ａ１", "　a1　", "A1\t"]
    norms = {normalize_code(v) for v in variants}
    assert norms == {"A1"}
