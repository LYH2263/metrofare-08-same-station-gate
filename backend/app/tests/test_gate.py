import sqlite3

import pytest

from app.errors import (
    PersistError,
    ReadError,
    SameStationError,
    UnknownStationError,
)
from app.engines.route_quote import quote_route
from app.services.metro_service import MetroService


# ---------- 同站进出闸：service 层 ----------

def test_same_station_exact_rejected(service, run_count):
    before = run_count()
    with pytest.raises(SameStationError) as ei:
        service.quote("A1", "A1", persist=True)
    # 点名两个编码
    assert ei.value.payload["start"] == "A1"
    assert ei.value.payload["end"] == "A1"
    assert ei.value.payload["normalized"] == "A1"
    assert run_count() == before  # 不写记录


def test_same_station_normalized_variants_rejected(service, run_count):
    # 空白 / 全角空格 / 大小写 / 全角字符不同，规范化后相同 => 同站
    cases = [("A1", " a1"), ("a 1", "A1"), ("Ａ１", "a1"), ("　A1　", "a1\t")]
    before = run_count()
    for s, e in cases:
        with pytest.raises(SameStationError):
            service.quote(s, e, persist=True)
    assert run_count() == before  # 连续多次同站写入尝试仍零增量


def test_two_consecutive_same_station_writes_zero_increment(client, run_count):
    before = run_count()
    for _ in range(2):
        r = client.post("/api/quote", json={"start": "A1", "end": " a1 ", "persist": True})
        assert r.status_code == 400
        assert r.json()["error"] == "same_station"
        body = r.json()
        # 点名两个编码
        assert body["start"] == "A1" and body["end"] == " a1 "
        # 不得给出零站途经 / 票价
        assert "hops" not in body and "fare" not in body and "run_id" not in body
    assert run_count() - before == 0  # 连续两次写入尝试后记录零增量


# ---------- 未知站：与同站不同的错误 ----------

def test_unknown_station_distinct_error(client, run_count):
    before = run_count()
    r = client.post("/api/quote", json={"start": "A1", "end": "ZZ9", "persist": True})
    assert r.status_code == 404
    assert r.json()["error"] == "unknown_station"  # 不同于 same_station(400)
    assert run_count() == before


def test_same_station_precedence_over_unknown(client):
    # 起终点都未知但规范化后相同 => 同站错误优先（400 same_station，而非 404）
    r = client.post("/api/quote", json={"start": "ZZ1", "end": " zz1 ", "persist": True})
    assert r.status_code == 400
    assert r.json()["error"] == "same_station"


def test_service_unknown_raises_type(service):
    with pytest.raises(UnknownStationError):
        service.quote("A1", "NOPE", persist=False)


# ---------- 合法不同站：最短路计费、对调可出票、规范化可用 ----------

def test_legal_different_stations_shortest_fare(client, run_count):
    before = run_count()
    r = client.post("/api/quote", json={"start": "A1", "end": "B2", "persist": True})
    assert r.status_code == 200
    data = r.json()
    assert data["reachable"] is True and data["hops"] == 3
    assert data["fare"] == 4.0 and data["run_id"] is not None
    assert run_count() - before == 1


def test_reversed_legal_trip_also_tickets(client, run_count):
    # 对调合法起终点必须能出票，且无向图最短路站数/票价一致
    before = run_count()
    r = client.post("/api/quote", json={"start": "B2", "end": "A1", "persist": True})
    assert r.status_code == 200
    data = r.json()
    assert data["reachable"] is True and data["hops"] == 3 and data["fare"] == 4.0
    assert data["run_id"] is not None
    assert run_count() - before == 1


def test_legal_trip_accepts_normalized_input(client):
    r = client.post("/api/quote", json={"start": " a1 ", "end": "ｂ２", "persist": False})
    assert r.status_code == 200
    data = r.json()
    assert data["start"] == "A1" and data["end"] == "B2"  # 返回规范编码
    assert data["hops"] == 3 and data["fare"] == 4.0


# ---------- 只读失败 / 写入失败：都不增加记录 ----------

def test_read_failure_no_record(service, run_count, monkeypatch):
    from app.repositories import stations as stations_repo
    def boom(_conn):
        raise sqlite3.OperationalError("disk I/O error")
    monkeypatch.setattr(stations_repo, "map_normalized", boom)
    before = run_count()
    with pytest.raises(ReadError):
        service.quote("A1", "B2", persist=True)
    assert run_count() == before


def test_write_failure_no_record(service, run_count, monkeypatch):
    from app.repositories import runs as runs_repo

    def boom(conn, *a, **k):
        # 真实的 SQL 写入失败：不存在的列，语句报错且未 commit。
        conn.execute("INSERT INTO calc_runs(kind, bad_col) VALUES ('quote','x')")

    monkeypatch.setattr(runs_repo, "insert", boom)
    before = run_count()
    with pytest.raises(PersistError):
        service.quote("A1", "B2", persist=True)
    assert run_count() == before  # 写入失败已回滚，零增量


# ---------- 既有记录不被改写 ----------

def test_existing_seed_run_not_rewritten(first_seed_run, run_count):
    import json
    seed_total = run_count()
    assert seed_total >= 1
    row = first_seed_run()
    assert json.loads(row["input_json"]) == {"start": "A1", "end": "A3"}
    result = json.loads(row["result_json"])
    assert result["start"] == "A1" and result["end"] == "A3"
    assert result["reachable"] is True and result["hops"] == 2


# ---------- 引擎层最后防线：不产出零站 ----------

def test_engine_refuses_zero_hop():
    with pytest.raises(SameStationError):
        quote_route([("A1", "A2")], "A1", "A1", [{"max_hops": None, "price": 1.0}])
