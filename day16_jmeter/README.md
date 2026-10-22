# Day16 · JMeter 压测练习（下单接口）

本地 mock 服务 + JMeter 脚本，用来跑一次完整的性能测试并定位瓶颈。

## 文件

| 文件 | 作用 |
| --- | --- |
| `mock_orders.py` | 被测服务：下单接口 `POST /orders`，内含一段 20ms 的**串行临界区**（模拟生成单号 / 扣库存），所以能压出瓶颈 |
| `users.csv` | 正常压测数据（20 个用户 + 金额），期望错误率 0 |
| `users_mixed.csv` | 脏数据（金额 0 / 负数 / 字母、空用户名、超上限），用来验证断言真的会响 |
| `orders_load.jmx` | JMeter 脚本：线程组 + CSV 参数化 + HTTP 请求 + 两条断言 |
| `stats.py` | 从 JTL 算平均 / 中位 / 90% / 95% / 最大 / **吞吐量** / 错误率 |
| `stats_mine.py` | 同上，但可按 `--since HH:MM` 只算某一次跑（jtl 是追加写入，跑两遍会混） |

## 怎么跑

需要 JDK（本机 `D:\Java\jdk-21.0.12.1+1`）与 JMeter（`D:\apache-jmeter-5.6.3`）。

```bash
# 1. 起靶子（另开一个终端，压测期间不要关）
python mock_orders.py

# 2. 每轮开跑前先删旧结果 —— jtl 是【追加】不是覆盖，不删样本数会翻倍
del *.jtl

# 3. 跑三档并发（在本目录下执行，CSV 是相对路径）
jmeter -n -t orders_load.jmx -Jthreads=5   -Jramp=2  -Jloops=20 -Jjtl=r5.jtl
jmeter -n -t orders_load.jmx -Jthreads=50  -Jramp=10 -Jloops=20 -Jjtl=r50.jtl
jmeter -n -t orders_load.jmx -Jthreads=100 -Jramp=10 -Jloops=10 -Jjtl=r100.jtl

# 4. 算百分位（命令行 summary 不给 90% 线）
#    .venv 在仓库根目录，不在 day16_jmeter 里 → python.exe 要用 ..\ 上去
..\.venv\Scripts\python.exe stats.py r5.jtl r50.jtl r100.jtl

# 5. 脏数据场景：验证断言在工作
jmeter -n -t orders_load.jmx -Jthreads=10 -Jramp=2 -Jloops=5 -Jcsv=users_mixed.csv -Jjtl=rmix.jtl
..\.venv\Scripts\python.exe stats.py rmix.jtl
```

Windows 下若 `jmeter` 不在 PATH，用全路径 `D:\apache-jmeter-5.6.3\bin\jmeter`。
**PowerShell 调 `jmeter.bat` 时 `-J` 参数必须加引号**：`"-Jjtl=r50.jtl"`，否则会被拆成 `-Jjtl` + `.jtl`，报 `Unknown arg: .jtl`。

## 实测结果（2026-10-22）

| 并发 | 样本 | 平均 | 90% 线 | 最大 | 吞吐量 | 错误率 |
| --- | --- | --- | --- | --- | --- | --- |
| 5 | 100 | 40 ms | 42 ms | 62 ms | 41.3 /s | 0% |
| 50 | 1000 | 526 ms | 779 ms | 819 ms | 48.4 /s | 0% |
| 100 | 1000 | 998 ms | 1521 ms | 1594 ms | 48.4 /s | 0% |
| 10（脏数据） | 50 | 24 ms | 33 ms | 53 ms | 25.6 /s | 26% |

### 自己复跑一遍的结果（15:52 那次，用 `stats_mine.py --since 15:50` 切出来）

| 并发 | 样本 | 平均 | 中位 | 90% 线 | 95% 线 | 最大 | 吞吐量 | 错误率 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 100 | 45 ms | 40 ms | 61 ms | 64 ms | 76 ms | 43.9 /s | 0% |
| 50 | 1000 | 529 ms | 577 ms | 797 ms | 800 ms | 820 ms | 48.8 /s | 0% |
| 100 | 1000 | 1006 ms | 1088 ms | 1537 ms | 1556 ms | 1619 ms | 49.3 /s | 0% |

两次跑几乎一模一样 —— 说明这个瓶颈是**稳定可复现**的，不是一次偶发。
注意 50 → 100：吞吐量 48.8 → 49.3（涨 1%，等于没涨），平均响应时间 529 → 1006 ms（翻一倍）。

**拐点结论：** 并发 50 → 100，吞吐量卡在 **48.4 /s 一动不动**，响应时间翻倍（526ms → 998ms）。
瓶颈 = 那段 20ms 的串行临界区：理论上限 `1 / 0.02 = 50 /s`，实测 48.4，几乎打满。

**脏数据那次更重要：** 错误率 26%、平均响应 24ms（比正常场景还快）—— 因为非法请求在第一道校验就被打回，
根本没进真正的处理。没有断言的话，这次跑会显示成一次「又快又稳」的好结果。

## 诚实边界

- 被测服务是**本机 mock**，不是真实系统；绝对值没有参考价值，方法才有。
- 施压机与被测服务在**同一台机器**，JMeter 自身也占资源；真实项目要分开部署。
- 只压了**单个接口**，真实场景需要做混合场景（多接口按比例）。
