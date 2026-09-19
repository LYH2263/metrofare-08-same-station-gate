import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest  # noqa: E402

from app import seed  # noqa: E402
from app.db import connect  # noqa: E402


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """每个测试使用全新的种子数据库(种子库自带 1 条历史记录)。"""
    db_path = tmp_path / "test.db"
    import app.db as db_mod

    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    seed.init_db()
    conn = connect()
    yield conn
    conn.close()


def count_runs(conn) -> int:
    return conn.execute("SELECT COUNT(*) c FROM calc_runs").fetchone()["c"]
