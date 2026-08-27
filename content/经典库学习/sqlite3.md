python 内置，免安装

# 连接数据库

```python
import sqlite3

con = sqlite3.connect("tutorial.db")
```

默认打开当前目录下的 tutorial.db 文件，如果不存在则会创建一个。

# 创建一个游标

```python
cur = con.cursor()
```

# 执行语句

```python
cur.execute("CREATE TABLE movie(title, year, score)")

res = cur.execute("SELECT name FROM sqlite_master")
res.fetchone()
```


# 插入数据

```python
cur.execute("""
    INSERT INTO movie VALUES
        ('Monty Python and the Holy Grail', 1975, 8.2),
        ('And Now for Something Completely Different', 1971, 7.5)
""")

con.commit()
```