import os
import tempfile

# 必须在导入任何 app.* 模块之前指向临时数据库（config/db 在导入期读取该变量）。
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="metrofare-pytest-")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from app.main import app
    with TestClient(app) as c:  # 触发 startup：建表 + 种子数据（含 1 条既有记录）
        yield c


@pytest.fixture
def service(client):  # 依赖 client 以确保 startup 已建表/播种
    from app.services.metro_service import MetroService
    with MetroService() as s:
        yield s


@pytest.fixture
def run_count():
    import sqlite3
    from app.db import DB_PATH

    def _count():
        conn = sqlite3.connect(DB_PATH)
        try:
            return conn.execute("SELECT COUNT(*) FROM calc_runs").fetchone()[0]
        finally:
            conn.close()
    return _count


@pytest.fixture
def first_seed_run():
    import json
    import sqlite3
    from app.db import DB_PATH

    def _row():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            r = conn.execute("SELECT * FROM calc_runs ORDER BY id ASC LIMIT 1").fetchone()
            return {"input_json": r["input_json"], "result_json": r["result_json"]}
        finally:
            conn.close()
    return _row
