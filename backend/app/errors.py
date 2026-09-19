class QuoteError(Exception):
    """询价拒绝的基类。"""


class SameStationError(QuoteError):
    """同站进出闸:起点与终点规范化后编码相同。"""

    def __init__(self, start: str, end: str, code: str):
        self.start = start
        self.end = end
        self.code = code
        super().__init__(f"same station: {start!r} == {end!r} (canonical {code!r})")


class UnknownStationError(QuoteError):
    """未知站点:编码在站点表中不存在。"""

    def __init__(self, codes: list[str]):
        self.codes = codes
        super().__init__(f"unknown station code(s): {codes!r}")


class QuotePersistenceError(QuoteError):
    """询价结果写入失败。"""
