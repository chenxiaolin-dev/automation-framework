# -*- coding: utf-8 -*-
"""Day16 压测靶子：一个带「串行临界区」的订单接口。

设计意图（面试能讲的点）：
  - 单条请求的实际工作只有 30ms（sleep 30ms 模拟业务处理）
  - 但其中 20ms 必须走一把全局锁（模拟「写同一张表 / 抢同一个库存行」）
  - 并发一高，线程全堵在这把锁上 → 响应时间被排队放大，吞吐量却涨不动
  - 这就是压测里最典型的「拐点」：并发加上去，TPS 不涨了，响应时间还在涨

启动：python mock_orders.py        （默认 8099 端口）
"""
import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8099

# 模拟「必须串行执行」的那一段（写主表 / 扣库存 / 生成单号）
_db_lock = threading.Lock()
SERIAL_MS = 0.020      # 临界区 20ms
BUSY_MS = 0.010        # 临界区之外的业务处理 10ms
ORDER_SEQ = [100000]
_seq_lock = threading.Lock()


def gen_order_id():
    with _seq_lock:
        ORDER_SEQ[0] += 1
        return ORDER_SEQ[0]


def create_order(user_id, amount):
    # ① 临界区外：参数校验（可并行）
    if not user_id:
        return None, "user_id is required"
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return None, "amount must be a number"
    if amount <= 0 or amount > 50000:
        return None, "amount out of range"

    time.sleep(BUSY_MS)  # 业务处理

    # ② 临界区：写主表 + 生成单号（必须串行）
    with _db_lock:
        time.sleep(SERIAL_MS)
        order_id = gen_order_id()
    return {"order_id": order_id, "user_id": str(user_id), "amount": amount,
            "status": "CREATED"}, None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # 压测时刷屏太多，关掉
        pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "up"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/orders":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send(400, {"error": "bad json"})
            return
        data, err = create_order(payload.get("user_id"), payload.get("amount"))
        if err:
            self._send(400, {"error": err})
            return
        self._send(201, data)


if __name__ == "__main__":
    print("mock orders 服务已启动: http://127.0.0.1:%d/orders" % PORT)
    print("临界区 %dms + 业务处理 %dms（单条下限约 %dms）"
          % (SERIAL_MS * 1000, BUSY_MS * 1000, (SERIAL_MS + BUSY_MS) * 1000))
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
