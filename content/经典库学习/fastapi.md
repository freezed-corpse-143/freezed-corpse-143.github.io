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

只要处理程序中没有任何阻塞 I/O 调用