
# 建立连接 - 引擎

任何 SQLAlchemy 应用程序的开始都是一个名为 Engine 的对象。此对象充当特定数据库连接的中心来源，既提供工厂，又为这些数据库提供名为连接池的持有空间。引擎通常是为特定数据库服务器创建一次的全局对象，并使用 URL 字符串进行配置，该字符串将描述应如何连接到数据库主机或后端。

例如：

```python
from sqlalchemy import create_engine
engine = create_engine("sqlite+pysqlite:///:memeory:", echo=True)
```

# 获取连接

通过提供 Connection 对象来连接数据库。例如：

```python
from sqlalchemy import text

with engine.connect() as conn:
	result = conn.execute(text("select 'hello world'"))
	print(result.all())
```

# 提交更改

```python
with engine.connect() as conn:
	conn.execute(text("CREATE TABLE some_table(x int, y int)"))
	conn.execute(
		text("INSERT INTO some_table (x, y) VALUES (:x, :y)"),
		[{"x": 1, "y": 1}, {"x": 2, "y": 4}]
	)
	conn.commit()
```

# 使用 ORM Session 执行

```python
from sqlalchemy.orm import Session

stmt = text("SELECT x, y FROM some_table WHERE y > :y ORDER BY x, y")
with Session(engine) as session:
	result = session.execute(stmt, {"y": 6})
	for row in result:
		print(f"x: {row.x} y: {row.y}")
```

# 形式化定义元数据

```python
from sqlalchemy import Table, Column, Integer, String
user_table = Table(
    "user_account",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("name", String(30)),
    Column("fullname", String),
)
```

```python
from sqlalchemy import ForeignKey
address_table = Table(
    "address",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("user_id", ForeignKey("user_account.id"), nullable=False),
    Column("email_address", String, nullable=False),
)
```

向数据库发出 DDL

```python
from sqlalchemy import MetaData
metadata_obj = MetaData()


from sqlalchemy import Table, Column, Integer, String
user_table = Table(
    "user_account",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("name", String(30)),
    Column("fullname", String),
)

metadata_obj.create_all(engine)
```
# 通过 ORM 进行数据操作

ORM 模式下你操作的是映射类的实例，Session 负责把对象状态翻译成 SQL 并管理事务。增删改不会立即发 SQL——先在内存累积，直到 flush（手动调用，或在 commit/查询前自动触发，即 autoflush）。

## 增加

```python
squidward = User(name="squidward", fullname="Squidward Tentacles")
session.add(squidward)      # 对象进入 pending 状态，未入库
session.commit()            # flush + commit，真正写入
print(squidward.id)         # 自增主键自动回填（如 4）
```

- 主键留空由数据库自动生成，flush 后 ORM 通过 RETURNING 把新主键写回对象。
- 可用 session.add_all([obj 1, obj 2]) 一次加多个。

## 查询

```python
# 按主键获取（先查 identity map，没有才发 SELECT）
sandy = session.get(User, 2)

# 条件查询
user = session.execute(
select(User).filter_by(name="sandy")
).scalar_one()          # 恰好一行，否则抛错
users = session.execute(select(User).where(User.fullname.like("S%"))).scalars().all()
```

 - identity map：同一 Session 内同一主键只会有一个 Python 实例（session.get(User, 2) is 之前加载的对象 为 True）。

## 更新

```python
sandy = session.get(User, 2)
sandy.fullname = "Sandy Squirrel"   # 直接改属性，对象进入 dirty 状态
session.commit()                    # flush 时按主键发 UPDATE
```

 不需要显式 update() 语句——修改已加载对象的属性即可，Session 自动跟踪。

## 删除

```python
patrick = session.get(User, 3)
session.delete(patrick)     # 标记删除，flush 时才真正 DELETE
session.commit()
```

 注意：删除带外键关联的对象时，ORM 会先 SELECT 相关表（级联行为），相关行处理方式由 cascade 配置决定。

## 批量操作

 对简单大批量插入/更新/删除，可以不用构造对象，直接用 Core 风格的 insert()/update()/delete() 构造通过 Session 执行：

```python
from sqlalchemy import insert, update, delete

# 批量插入（一次传多个字典）
session.execute(insert(User), [
{"name": "squidward", "fullname": "Squidward Tentacles"},
{"name": "krabs", "fullname": "Eugene H. Krabs"},
])
session.commit()

# 条件更新 / 删除
session.execute(update(User).where(User.name == "sandy").values(fullname="Sandy Squirrel"))
session.execute(delete(User).where(User.name == "patrick"))
session.commit()
```

## 回滚与关闭

```python
session.rollback()    # 回滚事务，并让所有关联对象过期（下次访问属性时重新加载）
session.close()       # 释放连接资源、驱逐所有对象（对象变为 detached 状态）
```

 - 事务会一直开着直到 commit() / rollback() / close()。
 - close() 后访问已过期对象会抛 DetachedInstanceError；需要跨 Session 用对象时设 Session(engine, expire_on_commit=False)。
 - 推荐用上下文管理器自动关闭：

```python
with Session(engine) as session:
session.add(User(name="squidward", fullname="Squidward Tentacles"))
session.commit()
```