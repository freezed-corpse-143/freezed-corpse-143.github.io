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

新增 `src/app/api/notes.py`

```python
from app.api import crud
from app.api.models import NoteDB, NoteSchema
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post("/", response_model=NoteDB, status_code=201)
async def create_note(payload: NoteSchema):
	note_id = await crud.post(payload)
	response_object = {
		"id": note_id,
		"title": payload.title,
		"description": payload.description,
	}
	return respone_object
```

新增 `src/app/api/crud.py`

```python
from app.api.models import NoteSchema
from app.db import notes, database

async def post(payload: NoteSchema):
	query = notes.insert().values(
		title=payload.title,
		description=payload.description
	)
	return await database.execute(query=query)
```

更新 `src/app/api/models.py`

```python
from pydantic import BaseModel

class NoteSchema(BaseModel):
	title: str
	description: str
	
class NoteDB(NoteSchema):
	id: int
```

更新 main.py

```python
from app.api import notes

app.include_router(notes, prefix="/notes", tags=["notes"])
```

测试模块，新增 `src/tests/test_notes.py`

```python
import json
import pytest
from app.api import crud

def test_create_note(test_app, monkeypatch):
	test_request_payload = {
		"title": "something",
		"description": "something else"
	}
	
	test_response_payload = {
		"id": 1,
		"title": "something",
		"description": "something else"
	}
	
	async def mock_post(payload):
		return 1
	
	monkeypatch.setattr(crud, "post", mock_post)
	
	response = test_app.post(
		"/notes/",
		data=json.dumps(test_request_payload)
	)
	
	assert response.status_code == 201
	assert response.json() == test_response_payload
	
def test_create_note_invalid_json(test_app):
	response = test_app.post(
		"/notes/",
		data=json.dumps({"title": "something"})
	)
	assert response.status_code == 422
```

# GET 路由

## GET 一个

更新 `src/app/api/notes.py`

```python
@router.get("/{id}/", response_model=NoteDB)
async def read_note(id: int):
	note = await crud.get(id)
	if not note:
		raise HTTPException(
			status_code=404,
			detail="Note not found"
		)
	return note
```

更新 `src/app/api/crud.py`

```python
async def get(id: int):
	query = notes.select().where(id == notes.c.id)
	return await database.fetch_one(query=query)
```

## GET 所有

更新 `src/app/api/notes.py`

```python
@router.get("/", response_model=List[NoteDB])
async def read_all_notes():
	return await crud.get_all()
```

更新 `src/app/api/crud.py`

```python
async def get_all():
	query = notes.select()
	return await database.fetch_all(query=query)
```

# PUT 路由

更新 `src/app/api/notes.py`

```python
@router.put("/{id}/", response_model=NoteDB)
async def update_note(id: int, payload: NoteSchema):
	note = await crud.get(id)
	if not note:
		raise HTTPException(
			status_code=404,
			detail="Note not found"
		)
	
	note_id = await crud.put(id payload)
	
	response_object = {
		"id": note_id,
		"title": payload.title,
		"description": payload.description,
	}
	return response_object
```

更新 `src/app/api/crud.py`

```python
async def put(id: int, payload: NoteSchema):
	query = (
		notes
		.update()
		.where(id == notes.c.id)
		.values(title=payload.title, description=payload.description)
		.returning(note.c.id)
	)
	return await database.execute(query=query)
```


# DELETE 路由

更新 `src/app/api/notes.py`

```python
@router.delete("/{id}/", response_model=NoteDB)
async def delete_note(id: int):
	note = await crud.get(id)
	if not note:
		raise HTTPException(
			status_code=404,
			detail="Note not found"
		)
	
	await crud.delete(id)
	
	return note
```

更新 `src/app/api/crud.py`

```python
async def delete(id: int):
	query = notes.delete().where(id == notes.c.id)
	return await database.execute(query=query)
```

# 配置跨域访问

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
	"http://localhost:3000",   # 例如：React 开发服务器
	"http://localhost:8080",   # 例如：Vue 开发服务器
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # 允许的源列表
    allow_credentials=True,     # 是否允许携带 Cookie
    allow_methods=["*"],        # 允许所有 HTTP 方法 (GET, POST, PUT, etc.)
    allow_headers=["*"],        # 允许所有请求头
)
```