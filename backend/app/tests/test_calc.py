import pytest

from app.engines.fare_rules import fare_for_hops
from app.engines.graph_bfs import shortest_hops
from app.engines.route_quote import quote_route
from app.errors import SameStationError

EDGES = [("A1", "A2"), ("A2", "A3"), ("A2", "B1"), ("B1", "B2")]
RULES = [{"max_hops": 2, "price": 3.0}, {"max_hops": 4, "price": 4.0}, {"max_hops": None, "price": 6.0}]


def test_hops_a1_a3():
    assert shortest_hops(EDGES, "A1", "A3") == 2


def test_hops_a1_b2():
    assert shortest_hops(EDGES, "A1", "B2") == 3


def test_fare_by_hops():
    assert fare_for_hops(2, RULES) == 3.0
    assert fare_for_hops(3, RULES) == 4.0
    assert fare_for_hops(10, RULES) == 6.0


def test_quote():
    q = quote_route(EDGES, "A1", "B2", RULES)
    assert q["hops"] == 3 and q["fare"] == 4.0


def test_same_station_rejected_and_names_both_codes():
    """同站进出闸必须拒绝,错误里点名两个编码,且绝不返回零站途经。"""
    with pytest.raises(SameStationError) as ei:
        quote_route(EDGES, "A1", "A1", RULES)
    err = ei.value
    assert err.start == "A1"
    assert err.end == "A1"
    assert err.code == "A1"


@pytest.mark.parametrize(
    "start,end",
    [
        (" A1", "A1"),          # 前导空白
        ("A1 ", "A1"),          # 尾部空白
        ("a1", "A1"),           # 大小写不同
        ("A1", "a1"),
        ("　a1", "A1　"),         # 全角空格
        ("\tA1", "A\r\n1"),     # 制表符/换行
        ("  a1 \t", "　A1　"),    # 混合
    ],
)
def test_same_station_after_normalization(start, end):
    """去空白(含全角)、忽略大小写后编码相同的,一律按同站拒绝。"""
    with pytest.raises(SameStationError) as ei:
        quote_route(EDGES, start, end, RULES)
    assert ei.value.code == "A1"


def test_reversed_valid_pair_still_quoted():
    """对调合法起终点必须能出票,票价一致。"""
    fwd = quote_route(EDGES, "A1", "B2", RULES)
    rev = quote_route(EDGES, "B2", "A1", RULES)
    assert fwd["reachable"] and rev["reachable"]
    assert (fwd["hops"], fwd["fare"]) == (rev["hops"], rev["fare"])


def test_same_station_never_returns_zero_hops():
    """同站请求不会产生 hops=0 的可达结果,而是直接拒绝。"""
    with pytest.raises(SameStationError):
        quote_route(EDGES, "a1", " A1 ", RULES)
