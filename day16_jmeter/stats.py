# -*- coding: utf-8 -*-
"""从 JTL 算吞吐量 / 百分位 / 错误率（JMeter 命令行 summary 不给百分位）

用法（在 day16_jmeter 目录下）：
    ..\\.venv\\Scripts\\python.exe stats.py r5.jtl r50.jtl r100.jtl
    或直接 python stats.py r5.jtl

⚠️ 注意：JMeter 对已存在的 jtl 是【追加】不是覆盖。
   同一天跑两遍，样本数会翻倍、表里混两次的数据。
   每轮开跑前先删： del *.jtl
"""
import re
import sys


def stats(path):
    txt = open(path, encoding="utf-8", errors="ignore").read()

    rows = []          # (ts, 耗时ms)
    err = 0
    for m in re.finditer(r'<httpSample[^>]*? t="(\d+)"[^>]*? ts="(\d+)"[^>]*? s="(true|false)"', txt):
        rows.append((int(m.group(2)), int(m.group(1))))
        if m.group(3) == "false":
            err += 1

    if not rows:
        print("%-8s 无数据（文件是空的，或 jmx 里没写结果）" % path)
        return

    rows.sort()
    n = len(rows)
    ts = sorted(d for _, d in rows)
    span = (rows[-1][0] - rows[0][0]) / 1000.0

    def p(q):
        return ts[min(n - 1, int(round(n * q)))]

    tps = n / span if span > 0 else 0.0
    print("%-9s 样本 %4d | 平均 %5dms | 中位 %5dms | 90%% %5dms | 95%% %5dms | 最大 %5dms | 吞吐 %5.1f/s | 错误 %d (%.1f%%)"
          % (path, n, sum(ts) / n, p(0.5), p(0.9), p(0.95), ts[-1], tps, err, 100.0 * err / n))


if __name__ == "__main__":
    args = sys.argv[1:] or ["r5.jtl", "r50.jtl", "r100.jtl"]
    for f in args:
        stats(f)
