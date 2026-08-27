
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

