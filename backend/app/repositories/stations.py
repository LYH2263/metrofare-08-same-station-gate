import sqlite3

from app.engines.codes import normalize_code


def list_all(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM stations ORDER BY code").fetchall()]


def get_by_code(conn: sqlite3.Connection, code: str) -> dict | None:
    row = conn.execute("SELECT * FROM stations WHERE code=?", (code,)).fetchone()
    return dict(row) if row else None


def find_by_normalized(conn: sqlite3.Connection, code: str) -> dict | None:
    """按规范化编码(去空白、忽略大小写)查找站点。"""
    canonical = normalize_code(code)
    for row in conn.execute("SELECT * FROM stations").fetchall():
        if normalize_code(row["code"]) == canonical:
            return dict(row)
    return None
