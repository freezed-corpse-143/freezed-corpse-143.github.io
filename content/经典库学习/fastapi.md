> 官方文档： https://fastapi-tutorial.readthedocs.io/en/latest/

# 安装

```
uv pip install fastapi
```

# 项目结构

```
fastapi 
	├── docker-compose.yml 
	└── src 
		├── Dockerfile 
		├── app 
		│ 	├── __init__.py 
		│	└── main.py 
		└── requirements.txt
```


在 main.py 文件中创建一个 FastAPI 实例并设置一个检查路由

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/ping")
def pong():
	return {"ping": "pong!"}
```

# 测试设置

项目结构

```
fastapi 
	├── docker-compose.yml 
	└── src 
		├── Dockerfile 
		├── app 
		│ 	├── __init__.py 
		│ 	└── main.py 
		├── requirements.txt 
		└── tests 
			├── __init__.py 
			├── conftest.py 
			└── test_main.py
```

test_main.py 文件

```python
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ping():
	response = client.get("/ping")
	assert response.status_code == 200
	assert response.json() == {"ping": "pong!" }
```

requirements.txt 中添加

```
pytest==5.4.1
requests==2.23.0
```

conftest.py 中

```python
import pytest
from starlette.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def test_app():
	client = TestClient(app)
	yield client
```

# 异步处理

只要处理程序中没有任何阻塞 I/O 调用，只要添加 async 关键字

比如 main.py

```python
@app.get("/ping")
async def pong():
	return {"ping": "pong!"}
```

# API 路由

比如，新建 `src/app/api/ping.py`

```python
from fastapi

router = APIRouter()

@router.get("/ping")
async def pong():
	return {"ping": "pong!"}
```

修改 `main.py`

```python
from fastapi import FastAPI
from app.api import ping

app = FastAPI()

app.include_router(ping.router)
```

# 数据库连接

安装 databases 库，增加 `src/app/db.py`

```python
import os
from databases import Database

DATABASE_URL = os.getenv("DATABASE_URL")

database = Database(DATABASE_URL)
```

修改 main.py

```python
from fastapi import FastAPI
from app.api import notes, ping
from app.db import engine, metadata, database

metadata.create_all(engine)

app = FastAPI()

@app.on_event("startup")
async def startup():
	await database.connect()
	
@app.on_event("shutdown")
async def shutdown():
	await database.disconnect()
	
app.include_router(ping.router)
```
# SQLAlchemy 模型

修改 `src/app/db.py`

```python
from sqlalchemy import (Column, DateTime, Integer, MetaData, String, Table, create_engine)
from sqlalchemy.sql import func

engine = create_engine(DATABASE_URL)
metadata = MetaData()
notes = Table (
	"notes",
	metadata,
	Column("id", Integer, primary_key=True),
	Column("title", String(50)),
	Column("description", String(50)),
	Column("created_data", DateTime, default=fun.now(), nullable=False),
)
```

# Pydantic 模型

增加 `src/app/api/models.py`

```python
from pydantic import BaseModel

class NoteSchema(BaseModel):
	title: str
	description: str
```

# Post 路由

