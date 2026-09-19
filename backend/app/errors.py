class QuoteError(Exception):
    """询价业务错误基类，携带 HTTP 状态码与结构化 payload。"""

    status_code = 400
    error = "quote_error"

    def __init__(self, message: str, payload: dict | None = None):
        super().__init__(message)
        self.message = message
        self.payload = payload or {"error": self.error, "message": message}


class SameStationError(QuoteError):
    """同站进出闸：起终点规范化后编码相同。"""

    status_code = 400
    error = "same_station"

    def __init__(self, start: str, end: str, normalized: str | None = None):
        code = normalized if normalized is not None else start
        message = (
            f"同站进出闸被拒绝：起点“{start}”与终点“{end}”规范化后均为“{code}”，"
            "不能发售零站车票。"
        )
        super().__init__(
            message,
            {
                "error": self.error,
                "message": message,
                "start": start,
                "end": end,
                "normalized": code,
            },
        )


class UnknownStationError(QuoteError):
    """未知站点：编码在线网中不存在，与同站拒绝区分（404 vs 400）。"""

    status_code = 404
    error = "unknown_station"

    def __init__(self, unknown: list[str] | str):
        codes = unknown if isinstance(unknown, list) else [unknown]
        message = "未知站点编码，无法试算：" + "、".join(f"“{c}”" for c in codes)
        super().__init__(
            message,
            {"error": self.error, "message": message, "unknown": codes},
        )


class ReadError(QuoteError):
    """只读失败：读取线网数据失败，不进行计费、不写入记录。"""

    status_code = 500
    error = "read_failed"


class PersistError(QuoteError):
    """试算记录写入失败（已回滚，不增加记录）。"""

    status_code = 500
    error = "persist_failed"
