> 官方文档： https://docs.langchain.com/oss/python/langchain/overview

# 安装

```bash
uv pip install langchain-openai
```
# 创建代理

```bash
from langchain.agents import create_agent

def get_weather(city: str) -> str:
	return f"It's always sunny in {city}"
	
agent = create_agent(
	model="openai:gpt-5.5",
	tools=[get_weather],
	system_prompt="You are a helpful assisant",
)

result = agent.invoke(
	{
		"messages": [
			{
				"role": "user",
				"content": "What's the weather in San Francisco?"
			}
		]
	}
)

print(result["messages"][-1].content_blocks)
```

## 模型

```python
from langchain.agents import create_agent

agent = create_agent(
	model = "google_genai:gemini-3.6-flash",
	tools=tools
)
```

## 工具

```python
from langchain.agents import create_agent
from langchain.tools import tool

@tool
def search(query: str) -> str:
	return f"Result for: {query}"
	
agent = 
```

