from app.engines.fare_rules import fare_for_hops
from app.engines.graph_bfs import shortest_hops
from app.errors import SameStationError


def quote_route(edges: list[tuple[str, str]], start: str, end: str, rules: list[dict]) -> dict:
    # 同站进出闸在引擎层同样拒绝：绝不产出 hops=0 / 票价，绝不调用方据此写记录。
    # service 层在规范化后已先行拦截，这里是最后一道防线。
    if start == end:
        raise SameStationError(start, end, start)
    hops = shortest_hops(edges, start, end)
    if hops is None:
        return {"start": start, "end": end, "hops": None, "fare": None, "reachable": False}
    fare = fare_for_hops(hops, rules)
    return {"start": start, "end": end, "hops": hops, "fare": fare, "reachable": True}
