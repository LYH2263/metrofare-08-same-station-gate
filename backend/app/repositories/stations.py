import sqlite3

from app.codes import normalize_code


def list_all(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM stations ORDER BY code").fetchall()]


def get_by_code(conn: sqlite3.Connection, code: str) -> dict | None:
    row = conn.execute("SELECT * FROM stations WHERE code=?", (code,)).fetchone()
    return dict(row) if row else None


def map_normalized(conn: sqlite3.Connection) -> dict[str, dict]:
    """返回 {规范化编码: 站点行}，用于按规范化后的编码识别站点。"""
    mapping: dict[str, dict] = {}
    for r in conn.execute("SELECT * FROM stations").fetchall():
        norm = normalize_code(r["code"])
        mapping.setdefault(norm, dict(r))
    return mapping
