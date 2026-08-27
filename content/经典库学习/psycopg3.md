# 安装

```bash
pip install "psycopg[binary]"   # 推荐：自带 libpq 的 C 扩展
pip install "psycopg[pool]"     # 连接池（独立包 psycopg_pool）
```

- 模块名是 `psycopg`，**没有** `psycopg3` 包。
- 纯 Python 版 `pip install psycopg` 慢，生产用 `[binary]` 或 `[c]`。

# 连接

```python
import psycopg

conn = psycopg.connect("dbname=test user=postgres")
conn = psycopg.connect(host="localhost", port=5432, dbname="test",
                       user="postgres", password="secret")
```

- `connect()` 返回未进入上下文的连接；不传关键字就支持 libpq DSN 字符串。
- 常用参数：`autocommit=True`、`row_factory=dict_row`、`prepare_threshold`、`isolation_level`。
- 标准用法是 `with` 块：正常退出自动 `COMMIT` + `close()`；块内抛异常则 `ROLLBACK` + `close()`：

```python
with psycopg.connect("dbname=test user=postgres") as conn:
    conn.execute("INSERT INTO t (num) VALUES (%s)", (100,))
# 退出时自动 COMMIT 并关闭
```

> 与 psycopg 2 不同：psycopg 3 的 `with conn` 会在退出时提交并**关闭连接**，不能重复进入。需要多事务复用连接时用 `conn.transaction()`。


# 数据定义 DDL

直接 `execute()`，`execute()` 返回 cursor，可链式操作：

```python
with psycopg.connect(...) as conn:
    conn.execute("""
        CREATE TABLE test (
            id serial PRIMARY KEY,
            num integer,
            data text)
        """)
```

- 表名/列名等**标识符**不能走 `%s` 参数，要用 `psycopg.sql` 动态拼接：

```python
from psycopg import sql

conn.execute(
    sql.SQL("INSERT INTO {} VALUES (%s)").format(sql.Identifier("numbers")),
    (10,))
```

- `CREATE DATABASE`、`VACUUM` 等不能跑在事务里的语句，需要 `autocommit=True` 的连接。

# 数据操纵

```python
# 占位符一律 %s（位置）或 %(name)s（命名），值作为第二个参数传入
cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)", (100, "abc'def"))
cur.execute("INSERT INTO t VALUES (%(id)s, %(name)s)",
            {"id": 10, "name": "O'Reilly"})

# 批量
cur.executemany("INSERT INTO test (num) VALUES (%s)", [(33,), (66,), (99,)])

# 查询：fetchone / fetchmany / fetchall / 直接迭代
cur.execute("SELECT * FROM test")
cur.fetchone()              # 元组
for record in cur.execute("SELECT id, num FROM test"):
    print(record)

# 快捷写法：conn.execute() 返回 cursor，execute() 返回 self 可链式
record = conn.execute("SELECT now()").fetchone()[0]
```

安全要点：
- **禁止**用 `%` 或 `+` 拼值进 SQL（SQL 注入）。`cur.execute("... VALUES (%s)" % (10,))` 是错的。
- 单参数也必须是序列：`("bar",)` 或 `["bar"]`。
- 占位符不要加引号 `'%s'`；类型不区分 `%d` / `%f`，统一 `%s`。
- 查询中的字面 `%` 写成 `%%`。
- 二进制结果：`cur.execute(..., binary=True)`，或 `conn.cursor(binary=True)`；二进制模式不能多语句。

行工厂（row_factory），默认返回元组：

```python
from psycopg.rows import dict_row, namedtuple_row, class_row

conn = psycopg.connect(..., row_factory=dict_row)   # 结果变 dict
cur = conn.cursor(row_factory=class_row(Person))    # 结果变 dataclass
```

# 事务管理

**默认每次操作自动开事务**（隐式 BEGIN），必须显式 `commit()` / `rollback()`：

```python
conn = psycopg.connect()

cur.execute("SELECT count(*) FROM my_table")   # 隐式 BEGIN，事务开始
cur.execute("INSERT INTO data VALUES (%s)", ("Hello",))

conn.commit()    # 持久化
# 或 conn.rollback() 丢弃；出错后必须 rollback() 才能继续用该连接
```

- 出错后同连接继续执行会报 `InFailedSqlTransaction`，先 `rollback()`。
- 长连接注意避免 "idle in transaction"（持有锁、表膨胀），尽早结束事务或开 autocommit。

**autocommit**：`psycopg.connect(autocommit=True)` — 每条语句立即生效，不隐式开事务。

**推荐组合**（文档认可的资深做法）：`with connect(...)` 连接块 + `autocommit=True` + 需要原子性处用 `conn.transaction()`：

```python
with psycopg.connect(autocommit=True) as conn:
    with conn.transaction():      # 进入时 BEGIN，正常退出 COMMIT，异常退出 ROLLBACK
        conn.execute("INSERT INTO data VALUES (%s)", ("Hello",))
        conn.execute("INSERT INTO times VALUES (now())")
```

**嵌套事务**：`conn.transaction()` 嵌套时内层用 SAVEPOINT，内层失败只回滚内层；`raise psycopg.Rollback` 可显式回滚到指定块。

事务特性：`conn.isolation_level`（READ COMMITTED 等）、`conn.read_only`、`conn.deferrable`；SERIALIZABLE 下要处理 `SerializationFailure` 重试。3.3 起 `Transaction.status` 可查事务最终状态（COMMITTED / ROLLED_BACK_WITH_ERROR 等）。

# 特色功能

**COPY 高效导入导出**（比 INSERT 快很多）：

```python
# 行式写入
with conn.cursor().copy("COPY sample (col1, col2, col3) FROM STDIN") as copy:
    for record in [(10, 20, "hello"), (40, None, "world")]:
        copy.write_row(record)

# 块式搬表
with conn1.cursor().copy("COPY src TO STDOUT (FORMAT BINARY)") as c1, \
     conn2.cursor().copy("COPY tgt FROM STDIN (FORMAT BINARY)") as c2:
    for data in c1:
        c2.write(data)
```

COPY 后仍需 commit（非 autocommit）。

**连接池**（`psycopg_pool`）：

```python
from psycopg_pool import ConnectionPool

with ConnectionPool("dbname=test", min_size=1, max_size=4) as pool:
    with pool.connection() as conn:    # 退出时提交/回滚并归还连接
        conn.execute("SELECT 1")
```

**异步**（`AsyncConnection` / `AsyncCursor`，需 `async with await`）：

```python
async with await psycopg.AsyncConnection.connect("dbname=test") as aconn:
    async with aconn.cursor() as acur:
        await acur.execute("SELECT * FROM test")
        async for record in acur:
            print(record)
```

线程模型：**Connection 线程安全**（多线程可共享，同连接共享同一事务），**Cursor 不线程安全**；连接不能跨进程（fork 后重建）。

**预编译语句**：同一查询执行超过 `prepare_threshold`（默认 5）次自动 PREPARE；`execute(..., prepare=True/False)` 可强制/禁用；PgBouncer 场景注意兼容性（或设 `prepare_threshold=None`）。

**Pipeline 模式**（低延迟场景批量发送，一次网络往返）：

```python
with conn.pipeline():
    conn.execute("INSERT INTO mytable VALUES (%s)", ["hello"])
    conn.execute("SELECT data FROM mytable WHERE id = %s", [1])
```

注意：pipeline 是实验特性；不支持 COPY、ServerCursor、多语句；`executemany()` 内部已自动用 pipeline。

**LISTEN/NOTIFY**：`conn.execute("LISTEN chan")` + `conn.notifies()` 生成器接收（建议 autocommit）。
