"""数据库校验（可选依赖 pymysql）：接口断言之外的数据落库校验。

用法:
    db = DB({"host": ..., "port": 3306, "user": ..., "password": ..., "database": ...})
    row = db.query_one("SELECT status FROM orders WHERE order_no=%s", ("SO123",))
"""
from __future__ import annotations

from core.logging.logger import log_redacted


class DB:
    def __init__(self, conf: dict, autocommit: bool = True):
        try:
            import pymysql
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("未安装 pymysql，请执行: pip install pymysql") from e

        self._conn = pymysql.connect(
            host=conf.get("host", "127.0.0.1"),
            port=int(conf.get("port", 3306)),
            user=conf.get("user", "root"),
            password=conf.get("password", ""),
            database=conf.get("database"),
            charset=conf.get("charset", "utf8mb4"),
            autocommit=autocommit,
            cursorclass=pymysql.cursors.DictCursor,
        )
        log_redacted("DB 已连接", conf)

    def query_one(self, sql: str, params: tuple | None = None) -> dict | None:
        with self._conn.cursor() as cur:
            cur.execute(sql, params or ())
            row = cur.fetchone()
        return row

    def query_all(self, sql: str, params: tuple | None = None) -> list[dict]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()

    def close(self):
        self._conn.close()
