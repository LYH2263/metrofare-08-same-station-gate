import pytest
from fastapi import HTTPException

from app.errors import QuotePersistenceError, SameStationError, UnknownStationError
from app.routers import quote as quote_router
from app.schemas.quote import QuoteRequest
from app.services.metro_service import MetroService

from conftest import count_runs


# ---------- 服务层 ----------

def test_same_station_does_not_write(db):
    before = count_runs(db)
    with pytest.raises(SameStationError):
        MetroService().quote("A1", " A1 ", persist=True)
    assert count_runs(db) == before


def test_two_consecutive_same_station_attempts_zero_increment(db):
    """连续两次同站写入尝试后,记录条数零增量。"""
    before = count_runs(db)
    for s, e in [("a1", "A1"), ("　A1　", "A1")]:
        with pytest.raises(SameStationError):
            MetroService().quote(s, e, persist=True)
    assert count_runs(db) == before


def test_unknown_station_different_error_and_no_write(db):
    """未知站拒绝与同站拒绝必须是不同的错误,且不写记录。"""
    before = count_runs(db)
    with pytest.raises(UnknownStationError):
        MetroService().quote("A1", "ZZ9", persist=True)
    assert count_runs(db) == before


def test_unknown_vs_same_are_distinct_error_types():
    assert issubclass(SameStationError, Exception)
    assert issubclass(UnknownStationError, Exception)
    assert SameStationError is not UnknownStationError


def test_valid_quote_writes_one(db):
    before = count_runs(db)
    out = MetroService().quote("A1", "B2", persist=True)
    assert out["reachable"] is True
    assert out["fare"] == 4.0 and out["hops"] == 3
    assert out["run_id"] is not None
    assert count_runs(db) == before + 1


def test_reversed_valid_pair_issues_ticket(db):
    """对调合法起终点必须能出票。"""
    fwd = MetroService().quote("A1", "B2", persist=True)
    rev = MetroService().quote("B2", "A1", persist=True)
    assert fwd["run_id"] and rev["run_id"]
    assert (fwd["hops"], fwd["fare"]) == (rev["hops"], rev["fare"])


def test_existing_records_not_rewritten_by_rejection(db):
    """拒绝请求不得改写既有记录。"""
    rows_before = [dict(r) for r in db.execute("SELECT * FROM calc_runs ORDER BY id").fetchall()]
    with pytest.raises(SameStationError):
        MetroService().quote("A1", "A1", persist=True)
    with pytest.raises(UnknownStationError):
        MetroService().quote("ZZ1", "ZZ2", persist=True)
    rows_after = [dict(r) for r in db.execute("SELECT * FROM calc_runs ORDER BY id").fetchall()]
    assert rows_after == rows_before


def test_unreachable_does_not_write(db):
    before = count_runs(db)
    # C1 与主网不连通。
    db.execute("INSERT INTO stations(code,name) VALUES ('C1','孤岛')")
    db.commit()
    out = MetroService().quote("A1", "C1", persist=True)
    assert out["reachable"] is False
    assert count_runs(db) == before


def test_read_failure_does_not_increase_records(db, monkeypatch):
    """只读阶段失败时不得新增记录。"""
    before = count_runs(db)
    from app.repositories import edges as edges_repo

    def boom(conn):
        raise RuntimeError("read failed")

    monkeypatch.setattr(edges_repo, "list_pairs", boom)
    with pytest.raises(RuntimeError):
        MetroService().quote("A1", "B2", persist=True)
    assert count_runs(db) == before


def test_write_failure_does_not_increase_records(db, monkeypatch):
    """写入阶段失败时不得新增记录(回滚)。"""
    before = count_runs(db)
    from app.repositories import runs as runs_repo

    def boom(conn, kind, payload, result):
        raise RuntimeError("write failed")

    monkeypatch.setattr(runs_repo, "insert", boom)
    with pytest.raises(QuotePersistenceError):
        MetroService().quote("A1", "B2", persist=True)
    assert count_runs(db) == before


def test_case_and_space_normalization_quotes_correctly(db):
    """合法站点即使带空白/大小写差异也按规范化后的编码出票。"""
    out = MetroService().quote(" a1 ", "　b2", persist=False)
    assert out["start"] == "A1" and out["end"] == "B2"
    assert out["reachable"] is True


# ---------- 路由层(HTTP 错误区分) ----------

def test_api_same_station_422_names_both_codes(db):
    with pytest.raises(HTTPException) as ei:
        quote_router.post_quote(QuoteRequest(start="A1", end=" a1", persist=True))
    exc = ei.value
    assert exc.status_code == 422
    assert exc.detail["error"] == "same_station"
    assert exc.detail["start"] == "A1"
    assert exc.detail["end"] == " a1"
    assert exc.detail["canonical"] == "A1"


def test_api_unknown_station_is_different_http_error(db):
    with pytest.raises(HTTPException) as ei:
        quote_router.post_quote(QuoteRequest(start="A1", end="ZZ9", persist=True))
    exc = ei.value
    assert exc.status_code == 404
    assert exc.detail["error"] == "unknown_station"
    assert exc.status_code != 422


def test_api_valid_pair_returns_fare_card(db):
    out = quote_router.post_quote(QuoteRequest(start="B2", end="A1", persist=True))
    assert out["reachable"] is True and out["run_id"] is not None
