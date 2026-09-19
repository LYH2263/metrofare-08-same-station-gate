import sqlite3

from app.codes import normalize_code
from app.db import connect
from app.engines.route_quote import quote_route
from app.errors import PersistError, QuoteError, ReadError, SameStationError, UnknownStationError
from app.repositories import edges as edges_repo
from app.repositories import fare_rules as rules_repo
from app.repositories import runs as runs_repo
from app.repositories import settings as settings_repo
from app.repositories import stations as stations_repo


class MetroService:
    def __init__(self):
        self._conn = connect()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def stations(self):
        return stations_repo.list_all(self._conn)

    def station(self, code: str):
        return stations_repo.get_by_code(self._conn, code)

    def edges(self):
        return [{"a": a, "b": b} for a, b in edges_repo.list_pairs(self._conn)]

    def fare_rules(self):
        return rules_repo.list_ordered(self._conn)

    def settings(self):
        return settings_repo.get_map(self._conn)

    def quote(self, start: str, end: str, persist: bool):
        raw_start, raw_end = start, end
        norm_start = normalize_code(start)
        norm_end = normalize_code(end)

        # 同站进出闸：编码相同，或去空白（含全角空格）、NFKC、大写规范化后相同。
        # 先于未知站判断，且与未知站使用不同错误；绝不计算零站途经、绝不写记录。
        if norm_start == norm_end:
            raise SameStationError(raw_start, raw_end, norm_start)

        # 读线网数据（只读）。读取失败必须回滚且不产生任何记录。
        try:
            station_map = stations_repo.map_normalized(self._conn)
            missing = [
                raw for norm, raw in ((norm_start, raw_start), (norm_end, raw_end))
                if norm not in station_map
            ]
            if missing:
                # 未知站拒绝：与同站拒绝是不同的错误（404 unknown_station）。
                raise UnknownStationError(missing)

            canonical_start = station_map[norm_start]["code"]
            canonical_end = station_map[norm_end]["code"]
            edges = [
                (normalize_code(a), normalize_code(b))
                for a, b in edges_repo.list_pairs(self._conn)
            ]
            rules = rules_repo.as_calc_rules(self._conn)
        except QuoteError:
            raise
        except (sqlite3.Error, OSError) as exc:  # 只读失败：不留记录
            self._safe_rollback()
            raise ReadError("读取线网数据失败，已中止试算且不写入记录。") from exc

        # 合法的不同站：仍按最短路计费（图无向，对调起终点同样可出票）。
        result = quote_route(edges, norm_start, norm_end, rules)
        result["start"] = canonical_start
        result["end"] = canonical_end

        run_id = None
        if persist and result.get("reachable"):
            run_id = self._persist_run(canonical_start, canonical_end, result)
        return {"run_id": run_id, **result}

    def _persist_run(self, start: str, end: str, result: dict) -> int:
        try:
            return runs_repo.insert(
                self._conn, "quote", {"start": start, "end": end}, result
            )
        except (sqlite3.Error, OSError) as exc:
            # 写入失败：回滚，不增加记录；既有记录不会被改写。
            self._safe_rollback()
            raise PersistError("试算结果写入失败，已回滚且未增加记录。") from exc

    def _safe_rollback(self):
        try:
            self._conn.rollback()
        except (sqlite3.Error, OSError):
            pass

    def history(self, limit=50):
        return runs_repo.list_recent(self._conn, limit)

    def dashboard(self):
        st = stations_repo.list_all(self._conn)
        clean = [s for s in st if "种子" not in s["name"]]
        dirty = [s for s in st if "种子" in s["name"]]
        return {
            "station_count": len(st),
            "edge_count": len(edges_repo.list_pairs(self._conn)),
            "clean_stations": len(clean),
            "dirty_stations": len(dirty),
        }
