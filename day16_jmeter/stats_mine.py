# -*- coding: utf-8 -*-
"""只统计某一次压测的数据（jtl 是追加写入，跑过两遍就会混在一起）

用法：
    ..\\.venv\\Scripts\\python.exe stats_mine.py r5.jtl r50.jtl r100.jtl --since 15:50
    （--since 换成你那次开跑的时分；不写就统计全部）

原理：JMeter 每条 sample 都带 ts（epoch 毫秒），按时分切一刀就行。
"""
import datetime
import re
import sys


def stats(path, cut_ms=0):
    txt = open(path, encoding="utf-8", errors="ignore").read()

    rows, err = [], 0
    for m in re.finditer(r'<httpSample[^>]*? t="(\d+)"[^>]*? ts="(\d+)"[^>]*? s="(true|false)"', txt):
        t = int(m.group(2))
        if t < cut_ms:
            continue
        rows.append((t, int(m.group(1))))
        if m.group(3) == "false":
            err += 1

    if not rows:
        print("%-9s 该时间段无数据" % path)
        return

    rows.sort()
    n = len(rows)
    ts = sorted(d for _, d in rows)
    span = (rows[-1][0] - rows[0][0]) / 1000.0
    tps = n / span if span > 0 else 0.0

    def p(q):
        return ts[min(n - 1, int(round(n * q)))]

    hh = datetime.datetime.fromtimestamp(rows[0][0] / 1000).strftime("%H:%M:%S")
    print("%-9s 样本 %4d | 平均 %5dms | 中位 %5dms | 90%% %5dms | 95%% %5dms | 最大 %5dms | 吞吐 %5.1f/s | 错误 %d (%.1f%%)  [起 %s]"
          % (path, n, sum(ts) / n, p(0.5), p(0.9), p(0.95), ts[-1], tps, err, 100.0 * err / n, hh))


if __name__ == "__main__":
    argv = sys.argv[1:]
    cut = 0
    if "--since" in argv:
        i = argv.index("--since")
        hh, mm = argv[i + 1].split(":")[:2]
        today = datetime.date.today()
        cut = int(datetime.datetime(today.year, today.month, today.day, int(hh), int(mm)).timestamp() * 1000)
        argv = argv[:i] + argv[i + 2:]
    for f in (argv or ["r5.jtl", "r50.jtl", "r100.jtl"]):
        stats(f, cut)
