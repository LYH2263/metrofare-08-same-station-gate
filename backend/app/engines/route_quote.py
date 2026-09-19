from app.engines.codes import normalize_code
from app.engines.fare_rules import fare_for_hops
from app.engines.graph_bfs import shortest_hops
from app.errors import SameStationError


def quote_route(edges: list[tuple[str, str]], start: str, end: str, rules: list[dict]) -> dict:
    raw_start, raw_end = start, end
    start = normalize_code(start)
    end = normalize_code(end)
    if start == end:
        # 同站进出闸:拒绝,绝不返回零站途经/零元票价。
        raise SameStationError(raw_start, raw_end, start)
    hops = shortest_hops(edges, start, end)
    if hops is None:
        return {"start": start, "end": end, "hops": None, "fare": None, "reachable": False}
    fare = fare_for_hops(hops, rules)
    return {"start": start, "end": end, "hops": hops, "fare": fare, "reachable": True}
