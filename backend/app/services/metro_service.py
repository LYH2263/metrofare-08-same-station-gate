from app.db import connect
from app.engines.codes import normalize_code
from app.engines.route_quote import quote_route
from app.errors import QuotePersistenceError, SameStationError, UnknownStationError
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
        # 规范化:去掉空白(含全角空格)、统一大小写后再比较。
        raw_start, raw_end = start, end
        start = normalize_code(start)
        end = normalize_code(end)

        # 同站进出闸:拒绝。不计算站数(绝不出现零站途经)、不出价、不写记录。
        if start == end:
            raise SameStationError(raw_start, raw_end, start)

        # 未知站点:与同站拒绝是两种不同的错误。
        missing = [c for c in (start, end) if stations_repo.find_by_normalized(self._conn, c) is None]
        if missing:
            raise UnknownStationError(missing)

        # 以下均为只读操作;任何失败直接抛出,此时尚未写入任何记录。
        edges = edges_repo.list_pairs(self._conn)
        rules = rules_repo.as_calc_rules(self._conn)
        result = quote_route(edges, start, end, rules)

        run_id = None
        if persist and result.get("reachable"):
            try:
                run_id = runs_repo.insert(
                    self._conn, "quote", {"start": start, "end": end}, result
                )
            except Exception as exc:
                # 写入失败:回滚,不留任何半截记录。
                self._conn.rollback()
                raise QuotePersistenceError(str(exc)) from exc
        return {"run_id": run_id, **result}

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
