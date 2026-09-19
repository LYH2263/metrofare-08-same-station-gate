from fastapi import APIRouter, HTTPException

from app.errors import QuotePersistenceError, SameStationError, UnknownStationError
from app.schemas.quote import QuoteRequest
from app.services.metro_service import MetroService

router = APIRouter(tags=["quote"])


@router.post("/quote")
def post_quote(body: QuoteRequest):
    try:
        with MetroService() as s:
            return s.quote(body.start, body.end, body.persist)
    except SameStationError as exc:
        # 同站进出闸:422,明确点名两个编码。
        raise HTTPException(
            status_code=422,
            detail={
                "error": "same_station",
                "message": f"起点与终点为同一站({exc.code}),同站进出闸被拒绝",
                "start": exc.start,
                "end": exc.end,
                "canonical": exc.code,
            },
        )
    except UnknownStationError as exc:
        # 未知站点:与同站拒绝不同的错误类型。
        raise HTTPException(
            status_code=404,
            detail={
                "error": "unknown_station",
                "message": f"未知站点编码: {', '.join(exc.codes)}",
                "codes": exc.codes,
            },
        )
    except QuotePersistenceError as exc:
        raise HTTPException(status_code=500, detail={"error": "persist_failed", "message": str(exc)})
