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
	
agent = create_agent(model="google_genai:gemini-3.6-flash", tools=[search])
```

## 系统提示

设定代理处理任务的方式。系统提示参数接受字符串或数字SystemMessage。对于运行时动态提示，请使用中间件。

```python
agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=tools,
    system_prompt="You are a helpful assistant. Be concise and accurate.",
)
```

## 结构化输出

使用代理返回经过验证的模式response_format=。有关策略和示例，请参阅结构化输出。

```python
from pydantic import BaseModel
from langchain.agents import create_agent


class Answer(BaseModel):
    summary: str
    confidence: float


agent = create_agent(model="google_genai:gemini-3.6-flash", tools=tools, response_format=Answer)
result = agent.invoke({"messages": [{"role": "user", "content": "Summarize AI trends"}]})
result["structured_response"]  # Answer(summary=..., confidence=...)
```

## 代理状态

每个代理都通过类型化的字典来管理其执行上下文AgentState，该字典保存当前的对话历史记录以及您的工具和中间件需要的任何自定义字段。

```python
from langchain.agents import AgentState, create_agent


class MyState(AgentState):
    user_id: str
    call_count: int


agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[],
    state_schema=MyState,
)
```


## 调用

你可以通过消息调用代理。在后台，该消息会将更新传递给代理State。所有代理的状态中都包含一系列消息；要调用代理，请传递一条新消息以及一个参数thread_id，以便代理可以持久化并恢复对话历史记录：

```python
from langchain.agents import create_agent
from langchain_core.utils.uuid import uuid7
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[],
    checkpointer=InMemorySaver(),
)

config = {"configurable": {"thread_id": str(uuid7())}}

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
    config=config,
)

# A follow-up turn on the same conversation: reuse the same thread_id to keep history
result = agent.invoke(
    {"messages": [{"role": "user", "content": "What about tomorrow?"}]},
    config=config,
)
```

如果您还需要将每次运行的配置（例如用户 ID、API 密钥或功能标志）传递给工具和中间件，请将其作为 `context` 参数传递 `config`。使用 `<filename>` 定义该数据的结构 `context_schema`，并通过以下方式访问它 `runtime.context`：

```python
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain_core.utils.uuid import uuid7
from langgraph.checkpoint.memory import InMemorySaver


@dataclass
class Context:
    user_id: str


agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[],
    context_schema=Context,
    checkpointer=InMemorySaver(),
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
    config={"configurable": {"thread_id": str(uuid7())}},
    context=Context(user_id="user-123"),
)
```

## 流式输出

`invoke` 运行结束后返回最终响应。如果代理执行多个工具调用，用户通常需要在完成之前获取进度更新。使用流式传输可以实时显示中间消息和工具活动。

```python
from langchain.messages import AIMessage, HumanMessage


stream = agent.stream_events(
    {"messages": [{"role": "user", "content": "Search for AI news and summarize the findings"}]},
    version="v3",
)
for snapshot in stream.values:
    # Each snapshot contains the full state at that point
    latest_message = snapshot["messages"][-1]
    if latest_message.content:
        if isinstance(latest_message, HumanMessage):
            print(f"User: {latest_message.content}")
        elif isinstance(latest_message, AIMessage):
            print(f"Agent: {latest_message.content}")
    elif latest_message.tool_calls:
        print(f"Calling tools: {[tc['name'] for tc in latest_message.tool_calls]}")
```

## 执行环境

当智能体能够执行操作而不仅仅是生成文本时，它们就显得尤为有用。执行环境为智能体提供了一个工作空间：它可以调用的工具、用于跨回合读写文件的文件系统，以及用于运行脚本或 shell 命令的代码执行空间。

```python
from langchain.agents import create_agent
from deepagents.backends import StateBackend
from deepagents.middleware import FilesystemMiddleware

agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[search],
    middleware=[FilesystemMiddleware(backend=StateBackend())],
)
```

## 上下文管理

每次模型调用都有一个固定的上下文窗口。随着代理的运行，该窗口会不断累积历史记录、工具结果和中间步骤。摘要功能会在溢出之前压缩历史记录；内存会在启动时加载持久指令，以便知识能够在会话之间传递；技能会按需调用领域知识，而不是预先加载所有内容。

```python
from deepagents.backends import StateBackend
from deepagents.middleware import FilesystemMiddleware, MemoryMiddleware, SkillsMiddleware, SummarizationMiddleware

backend = StateBackend()
model = "google_genai:gemini-3.6-flash"

agent = create_agent(
    model=model,
    tools=[search],
    middleware=[
        FilesystemMiddleware(backend=backend),
        SummarizationMiddleware(model=model, backend=backend),
        MemoryMiddleware(backend=backend, sources=["./AGENTS.md"]),
        SkillsMiddleware(backend=backend, sources=["./skills/"]),
    ],
)
```

## 计划与授权

复杂任务通常超出单个上下文窗口的处理能力。委托机制允许主代理将工作分解成多个部分，交给在各自独立上下文中运行的子代理，从而使主代理能够专注于协调而非执行。工作可以并行运行；主代理的上下文保持清晰。

```python
from deepagents.backends import StateBackend
from deepagents.middleware import FilesystemMiddleware
from deepagents.middleware.subagents import SubAgentMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain.tools import tool


@tool
def search(query: str) -> str:
    """Search for a query and return a short summary."""
    return f"Search results for: {query}"


backend = StateBackend()

agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[search],
    middleware=[
        FilesystemMiddleware(backend=backend),
        TodoListMiddleware(),
        SubAgentMiddleware(
            backend=backend,
            subagents=[
                {
                    "name": "researcher",
                    "description": "Searches and returns a structured summary.",
                    "system_prompt": "Use the search tool to research the question and summarize key points.",
                    "tools": [search],
                    "model": "anthropic:claude-sonnet-4-6",
                    "middleware": [],
                }
            ],
        ),
    ],
)
```

## 调用特定智能体

可以选择为智能体使用标识符。

```python
agent = create_agent(model="google_genai:gemini-3.6-flash", tools=tools, name="research_assistant")
```

## 容错性

生产环境中的代理会遇到一些在开发环境中很少出现的故障：速率限制、模型超时、瞬态 API 错误。容错中间件会在基础设施层面处理这些问题，因此您的工具和业务逻辑无需在每个调用周围编写 try/catch 语句。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
from langchain.tools import tool


@tool
def search(query: str) -> str:
    """Search for a query and return a short summary."""
    return f"Search results for: {query}"


agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[search],
    middleware=[
        ModelRetryMiddleware(max_retries=3),
        ToolRetryMiddleware(max_retries=2),
    ],
)
```

## 护栏

有些策略不能仅仅停留在提示信息中——无论模型如何运行，它们都需要确定性地执行。防护机制会在数据流经代理循环时进行拦截，在工具结果到达模型上下文之前应用合规性规则或内容策略。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware
from langchain.tools import tool


@tool
def search(query: str) -> str:
    """Search for a query and return a short summary."""
    return f"Search results for: {query}"


agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[search],
    middleware=[PIIMiddleware("email")],
)
```

## 转向

完全自主并非总是合适的。通过“引导”机制，您可以在特定的决策点（例如执行破坏性写入、耗时的 API 调用或任何需要判断的操作之前）安排人工干预，而无需重构您的代理。代理会暂停并等待；人工进行批准、编辑或拒绝；然后继续执行。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.tools import tool


@tool
def search(query: str) -> str:
    """Search for a query and return a short summary."""
    return f"Search results for: {query}"


agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[search],
    middleware=[HumanInTheLoopMiddleware(interrupt_on={"write_file": True})],
)
```

# 工具

工具扩展了[代理](/oss/python/langchain/agents)的能力——让它们获取实时数据、执行代码、查询外部数据库，并在真实世界中采取行动。

在底层，工具是具有明确定义输入和输出的可调用函数，它们会被传递给[聊天模型](/oss/python/langchain/models)。模型根据对话上下文决定何时调用工具，以及提供什么输入参数。

> 提示：关于模型如何处理工具调用，请参阅[工具调用](/oss/python/langchain/models#tool-calling)。可以使用 [LangSmith](https://smith.langchain.com) 追踪工具调用并调试错误。

## 创建工具

### 基本工具定义

创建工具最简单的方式是使用 [`@tool`](https://reference.langchain.com/python/langchain-core/tools/convert/tool) 装饰器。默认情况下，函数的 docstring 会成为工具的描述，帮助模型理解何时使用它：

```python
from langchain.tools import tool

@tool
def search_database(query: str, limit: int = 10) -> str:
    """Search the customer database for records matching the query.

    Args:
        query: Search terms to look for
        limit: Maximum number of results to return
    """
    return f"Found {limit} results for '{query}'"
```

类型提示是**必需**的，因为它们定义了工具的输入 schema。docstring 应该简洁且信息丰富，帮助模型理解工具的用途。

> 注意：**服务端工具调用**——某些聊天模型带有内置工具（网络搜索、代码解释器），这些工具在服务端执行。详见下文"服务端工具调用"。
>
> 警告：工具名称尽量使用 `snake_case`（例如 `web_search` 而不是 `Web Search`）。部分模型提供商对包含空格或特殊字符的名称会报错或直接拒绝。坚持使用字母数字、下划线和连字符有助于提高跨提供商的兼容性。

### 自定义工具属性

#### 自定义工具名称

默认情况下，工具名称取自函数名。需要更具描述性的名称时可以覆盖：

```python
@tool("web_search")  # Custom name
def search(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"

print(search.name)  # web_search
```

#### 自定义工具描述

覆盖自动生成的工具描述，为模型提供更清晰的指导：

```python
@tool("calculator", description="Performs arithmetic calculations. Use this for any math problems.")
def calc(expression: str) -> str:
    """Evaluate mathematical expressions."""
    return str(eval(expression))
```

### 高级 schema 定义

用 Pydantic 模型或 JSON schema 定义复杂输入：

Pydantic 模型：

```python
from pydantic import BaseModel, Field
from typing import Literal

class WeatherInput(BaseModel):
    """Input for weather queries."""
    location: str = Field(description="City name or coordinates")
    units: Literal["celsius", "fahrenheit"] = Field(
        default="celsius",
        description="Temperature unit preference"
    )
    include_forecast: bool = Field(
        default=False,
        description="Include 5-day forecast"
    )

@tool(args_schema=WeatherInput)
def get_weather(location: str, units: str = "celsius", include_forecast: bool = False) -> str:
    """Get current weather and optional forecast."""
    temp = 22 if units == "celsius" else 72
    result = f"Current weather in {location}: {temp} degrees {units[0].upper()}"
    if include_forecast:
        result += "\nNext 5 days: Sunny"
    return result
```

JSON Schema：

```python
weather_schema = {
    "type": "object",
    "properties": {
        "location": {"type": "string"},
        "units": {"type": "string"},
        "include_forecast": {"type": "boolean"}
    },
    "required": ["location", "units", "include_forecast"]
}

@tool(args_schema=weather_schema)
def get_weather(location: str, units: str = "celsius", include_forecast: bool = False) -> str:
    """Get current weather and optional forecast."""
    temp = 22 if units == "celsius" else 72
    result = f"Current weather in {location}: {temp} degrees {units[0].upper()}"
    if include_forecast:
        result += "\nNext 5 days: Sunny"
    return result
```

### 保留参数名

以下参数名被保留，不能用作工具参数。使用这些名称会导致运行时错误：

| 参数名 | 用途 |
| ------ | ---- |
| `config` | 保留用于在内部向工具传递 `RunnableConfig` |
| `runtime` | 保留给 `ToolRuntime` 参数（访问状态、上下文、存储） |

要访问运行时信息，请使用 [`ToolRuntime`](https://reference.langchain.com/python/langchain/tools/#langchain.tools.ToolRuntime) 参数，而不是把自己的参数命名为 `config` 或 `runtime`。如果你使用 `InjectedState`、`InjectedStore`、`get_runtime()` 或 `InjectedToolCallId`，请参阅"从旧式注入模式迁移"。

## 访问上下文

工具在能够访问运行时信息（如对话历史、用户数据和持久化记忆）时最为强大。本节介绍如何在工具内访问和更新这些信息。

工具可以通过 [`ToolRuntime`](https://reference.langchain.com/python/langchain/tools/#langchain.tools.ToolRuntime) 参数访问运行时信息，它提供：

| 组件 | 描述 | 用例 |
| ---- | ---- | ---- |
| **状态（State）** | 短期记忆——当前对话期间存在的可变数据（消息、计数器、自定义字段） | 访问对话历史、跟踪工具调用次数 |
| **上下文（Context）** | 调用时传入的不可变配置（用户 ID、会话信息） | 根据用户身份个性化响应 |
| **存储（Store）** | 长期记忆——跨对话存活的持久化数据 | 保存用户偏好、维护知识库 |
| **流写入器（Stream Writer）** | 在工具执行期间发出实时更新 | 为长时间运行的操作显示进度 |
| **执行信息（Execution Info）** | 当前执行的身份与重试信息（线程 ID、运行 ID、尝试次数） | 访问线程/运行 ID、根据重试状态调整行为 |
| **服务器信息（Server Info）** | 在 LangGraph Server 上运行时，服务器特定的元数据（assistant ID、graph ID、已认证用户） | 访问 assistant ID、graph ID 或已认证用户信息 |
| **配置（Config）** | 执行的 [`RunnableConfig`](https://reference.langchain.com/python/langchain-core/runnables/config/RunnableConfig) | 访问回调、标签和元数据 |
| **工具调用 ID** | 当前工具调用的唯一标识符 | 关联工具调用以进行日志记录和模型调用 |

### 短期记忆（状态）

状态代表对话期间存在的短期记忆，包括消息历史以及你在[图状态](/oss/python/langgraph/graph-api#state)中定义的任何自定义字段。

#### 访问状态

在工具签名中添加 `runtime: ToolRuntime` 即可访问状态。调用时，[`ToolNode`](https://reference.langchain.com/python/langgraph/agents/#langgraph.prebuilt.tool_node.ToolNode) 会自动注入该值；该参数不会出现在发送给模型的工具 schema 中。使用 `runtime.state` 读取当前对话状态：

```python
from langchain.tools import tool, ToolRuntime
from langchain.messages import HumanMessage

@tool
def get_last_user_message(runtime: ToolRuntime) -> str:
    """Get the most recent message from the user."""
    messages = runtime.state["messages"]

    # Find the last human message
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message.content

    return "No user messages found"

# Access custom state fields
@tool
def get_user_preference(
    pref_name: str,
    runtime: ToolRuntime
) -> str:
    """Get a user preference value."""
    preferences = runtime.state.get("user_preferences", {})
    return preferences.get(pref_name, "Not set")
```

> 警告：`runtime` 参数对模型是隐藏的。在上面的例子中，模型在工具 schema 中只能看到 `pref_name`。

#### 更新状态

使用 [`Command`](https://reference.langchain.com/python/langgraph/types/Command) 更新代理状态。这对于需要更新自定义状态字段的工具很有用。请在更新中包含 `ToolMessage`，这样模型才能看到工具调用的结果：

```python
from langchain.agents import AgentState
from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime, tool
from langgraph.types import Command

class CustomState(AgentState):
    user_name: str

@tool
def set_user_name(new_name: str, runtime: ToolRuntime[None, CustomState]) -> Command:
    """Set the user's name in the conversation state."""
    return Command(
        update={
            "user_name": new_name,
            "messages": [
                ToolMessage(
                    content=f"User name set to {new_name}.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )
```

> 提示：当工具更新状态变量时，请考虑为这些字段定义 [reducer](/oss/python/langgraph/graph-api#reducers)。由于 LLM 可以并行调用多个工具，当同一状态字段被并发工具调用更新时，reducer 决定了如何解决冲突。

### 上下文

上下文提供调用时传入的不可变配置数据。用于用户 ID、会话详情或对话期间不应改变的应用程序特定设置。

> 注意：`thread_id`（通过 `config={"configurable": {"thread_id": ...}}` 传入）限定*对话*的范围——消息历史和检查点；而 `context` 携带*每次运行*的数据，工具和中间件在调用时读取。生产环境中通常两者同时传入：每个对话一个稳定的 `thread_id`，每次调用一个 `context` 对象。

通过 `runtime.context` 访问上下文。将它与 `thread_id` 一起传入，使对话在回合之间保持持久：

```python
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime
from langchain_core.utils.uuid import uuid7
from langchain_openai import ChatOpenAI

USER_DATABASE = {
    "user123": {
        "name": "Alice Johnson",
        "account_type": "Premium",
        "balance": 5000,
        "email": "alice@example.com",
    },
    "user456": {
        "name": "Bob Smith",
        "account_type": "Standard",
        "balance": 1200,
        "email": "bob@example.com",
    },
}

@dataclass
class UserContext:
    user_id: str

@tool
def get_account_info(runtime: ToolRuntime[UserContext]) -> str:
    """Get the current user's account information."""
    user_id = runtime.context.user_id

    if user_id in USER_DATABASE:
        user = USER_DATABASE[user_id]
        return (
            f"Account holder: {user['name']}\n"
            f"Type: {user['account_type']}\n"
            f"Balance: ${user['balance']}"
        )
    return "User not found"

model = ChatOpenAI(model="google_genai:gemini-3.6-flash")
agent = create_agent(
    model,
    tools=[get_account_info],
    context_schema=UserContext,
    system_prompt="You are a financial assistant.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's my current balance?"}]},
    config={"configurable": {"thread_id": str(uuid7())}},
    context=UserContext(user_id="user123"),
)
```

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了 7 个相同示例，仅模型字符串不同；此处以 Google 为例，其他提供商只需替换 `model` 字符串。）

### 长期记忆（存储）

[`BaseStore`](https://reference.langchain.com/python/langchain-core/stores/BaseStore) 提供跨对话存活的持久化存储。与状态（短期记忆）不同，保存到存储中的数据在未来的会话中仍然可用。

通过 `runtime.store` 访问存储。存储使用命名空间/键（namespace/key）模式组织数据：

> 提示：生产环境请使用持久化存储实现，如 [`PostgresStore`](https://reference.langchain.com/python/langgraph/store/#langgraph.store.postgres.PostgresStore)、`MongoDBStore` 或 `RedisStore`，而不是 `InMemoryStore`。设置细节请参阅[记忆文档](/oss/python/langgraph/add-memory)。

```python
from typing import Any
from langgraph.store.memory import InMemoryStore
from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime
from langchain_openai import ChatOpenAI

# Access memory
@tool
def get_user_info(user_id: str, runtime: ToolRuntime) -> str:
    """Look up user info."""
    store = runtime.store
    user_info = store.get(("users",), user_id)
    return str(user_info.value) if user_info else "Unknown user"

# Update memory
@tool
def save_user_info(user_id: str, user_info: dict[str, Any], runtime: ToolRuntime) -> str:
    """Save user info."""
    store = runtime.store
    store.put(("users",), user_id, user_info)
    return "Successfully saved user info."

model = ChatOpenAI(model="gpt-5.5")

store = InMemoryStore()
agent = create_agent(
    model,
    tools=[get_user_info, save_user_info],
    store=store
)

# First session: save user info
agent.invoke({
    "messages": [{"role": "user", "content": "Save the following user: userid: abc123, name: Foo, age: 25, email: foo@langchain.dev"}]
})

# Second session: get user info
agent.invoke({
    "messages": [{"role": "user", "content": "Get user info for user with id 'abc123'"}]
})
# Here is the user info for user with ID "abc123":
# - Name: Foo
# - Age: 25
# - Email: foo@langchain.dev
```

# 模型

# 安装

```python
uv pip install "langchain[openai]"
```

## 初始化模型

```python
import os
from langchain.chat_models import init_chat_model

os.environ["OPENAI_API_KEY"] = "sk-..."

model = init_chat_model("gpt-5.5")

response = model.invoke("Why do parrots talk?")
```

## 传入参数

```python
model = init_chat_model(
    "claude-sonnet-4-6",
    # Kwargs passed to the model:
    temperature=0.7,
    timeout=30,
    max_tokens=1000,
    max_retries=6,  # Default; increase for unreliable networks
)
```

## 连接弹性

```python
from langchain.chat_models import init_chat_model

model = init_chat_model(
    "google_genai:gemini-3.6-flash",
    max_retries=10,  # Increase for unreliable networks (default: 6)
    timeout=120,  # Seconds; increase for slow connections
)
```

## 调用

```python
response = model.invoke("Why do parrots have colorful feathers?")
print(response)
```

## 多轮对话调用

```python
conversation = [
    {"role": "system", "content": "You are a helpful assistant that translates English to French."},
    {"role": "user", "content": "Translate: I love programming."},
    {"role": "assistant", "content": "J'adore la programmation."},
    {"role": "user", "content": "Translate: I love building applications."}
]

response = model.invoke(conversation)
print(response)  # AIMessage("J'adore créer des applications.")
```

```python
from langchain.messages import HumanMessage, AIMessage, SystemMessage

conversation = [
    SystemMessage("You are a helpful assistant that translates English to French."),
    HumanMessage("Translate: I love programming."),
    AIMessage("J'adore la programmation."),
    HumanMessage("Translate: I love building applications.")
]

response = model.invoke(conversation)
print(response)  # AIMessage("J'adore créer des applications.")
```

## 流式输出

```python

for chunk in model.stream("Why do parrots have colorful feathers?"):
    print(chunk.text, end="|", flush=True)
```

```python
full = None  # None | AIMessageChunk
for chunk in model.stream("What color is the sky?"):
    full = chunk if full is None else full + chunk
    print(full.text)

# The
# The sky
# The sky is
# The sky is typically
# The sky is typically blue
# ...

print(full.content_blocks)
# [{"type": "text", "text": "The sky is typically blue..."}]
```

## 对话批处理

```python
responses = model.batch([
    "Why do parrots have colorful feathers?",
    "How do airplanes fly?",
    "What is quantum computing?"
])
for response in responses:
    print(response)
```


```python

for response in model.batch_as_completed([
    "Why do parrots have colorful feathers?",
    "How do airplanes fly?",
    "What is quantum computing?"
]):
    print(response)
```

## 工具调用

```python
from langchain.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get the weather at a location."""
    return f"It's sunny in {location}."


model_with_tools = model.bind_tools([get_weather])

response = model_with_tools.invoke("What's the weather like in Boston?")
for tool_call in response.tool_calls:
    # View tool calls made by the model
    print(f"Tool: {tool_call['name']}")
    print(f"Args: {tool_call['args']}")
```

## 结构化输出

```python
from pydantic import BaseModel, Field

class Movie(BaseModel):
    """A movie with details."""
    title: str = Field(description="The title of the movie")
    year: int = Field(description="The year the movie was released")
    director: str = Field(description="The director of the movie")
    rating: float = Field(description="The movie's rating out of 10")

model_with_structure = model.with_structured_output(Movie)
response = model_with_structure.invoke("Provide details about the movie Inception")
print(response)  # Movie(title="Inception", year=2010, director="Christopher Nolan", rating=8.8)
```

## 多模态

```python
response = model.invoke("Create a picture of a cat")
print(response.content_blocks)
# [
#     {"type": "text", "text": "Here's a picture of a cat"},
#     {"type": "image", "base64": "...", "mime_type": "image/jpeg"},
# ]
```

## 推理

许多模型能够进行多步骤推理以得出结论。这涉及到将复杂问题分解成更小、更易于处理的步骤。

```python
for chunk in model.stream("Why do parrots have colorful feathers?"):
    reasoning_steps = [r for r in chunk.content_blocks if r["type"] == "reasoning"]
    print(reasoning_steps if reasoning_steps else chunk.text)
```

指定推理水平

```python
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(model="claude-sonnet-4-6")
response = model.invoke(
    "Why do parrots have colorful feathers?",
    reasoning_effort="high",
)
```

或者

```python
model.profile["reasoning_effort_levels"]  # e.g. ['low', 'medium', 'high']
model.profile["reasoning_effort_default"]  # e.g. 'high'
```

## 服务端工具的调用

```python
from langchain.chat_models import init_chat_model

model = init_chat_model("gpt-5.4-mini")

tool = {"type": "web_search"}
model_with_tools = model.bind_tools([tool])

response = model_with_tools.invoke("What was a positive news story from today?")
print(response.content_blocks)
```

## 模型异常

`langchain_core.exceptions` 主要的集成包会针对常见的模型故障（例如身份验证错误、速率限制和超时）引发标准异常类型。这些异常继承自 LangChain 基本类型和提供程序 SDK 自身的异常类型，因此您可以捕获其中任何一种：

```python
from langchain.chat_models import init_chat_model
from langchain_core.exceptions import ModelTimeoutError

model = init_chat_model("openai:gpt-5.6-luna", timeout=0.0001)

try:
    response = model.invoke("Hello")
except ModelTimeoutError:
    print("caught")
```

## 对数概率

`logprobs` 某些模型可以通过在初始化模型时设置参数来配置，从而返回表示给定标记可能性的标记级日志概率：

```python
model = init_chat_model(
    model="gpt-5.5",
    model_provider="openai"
).bind(logprobs=True)

response = model.invoke("Why do parrots talk?")
print(response.response_metadata["logprobs"])
```

## token 用量

```python
from langchain.chat_models import init_chat_model
from langchain_core.callbacks import UsageMetadataCallbackHandler

model_1 = init_chat_model(model="gpt-5.4-mini")
model_2 = init_chat_model(model="claude-haiku-4-5-20251001")

callback = UsageMetadataCallbackHandler()
result_1 = model_1.invoke("Hello", config={"callbacks": [callback]})
result_2 = model_2.invoke("Hello", config={"callbacks": [callback]})
print(callback.usage_metadata)
```

预期输出

```json
{
    'gpt-5.4-mini': {
        'input_tokens': 8,
        'output_tokens': 10,
        'total_tokens': 18,
        'input_token_details': {'audio': 0, 'cache_read': 0},
        'output_token_details': {'audio': 0, 'reasoning': 0}
    },
    'claude-haiku-4-5-20251001': {
        'input_tokens': 8,
        'output_tokens': 21,
        'total_tokens': 29,
        'input_token_details': {'cache_read': 0, 'cache_creation': 0}
    }
}
```

## 调用配置

```python
response = model.invoke(
    "Tell me a joke",
    config={
        "run_name": "joke_generation",      # Custom name for this run
        "tags": ["humor", "demo"],          # Tags for categorization
        "metadata": {"user_id": "123"},     # Custom metadata
        "callbacks": [my_callback_handler], # Callback handlers
    }
)
```

## 可配置模型

```python
from langchain.chat_models import init_chat_model

configurable_model = init_chat_model(temperature=0)

configurable_model.invoke(
    "what's your name",
    config={"configurable": {"model": "gpt-5-nano"}},  # Run with GPT-5-Nano
)
configurable_model.invoke(
    "what's your name",
    config={"configurable": {"model": "claude-sonnet-4-6"}},  # Run with Claude
)
```

## 动态模型

动态模型的选择是在运行时环境基于当前状态以及上下文信息。这使得复杂的路由逻辑和成本优化成为可能。

```python
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse


basic_model = ChatOpenAI(model="gpt-5.4-mini")
advanced_model = ChatOpenAI(model="gpt-5.5")

@wrap_model_call
def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
    """Choose model based on conversation complexity."""
    message_count = len(request.state["messages"])

    if message_count > 10:
        # Use an advanced model for longer conversations
        model = advanced_model
    else:
        model = basic_model

    return handler(request.override(model=model))

agent = create_agent(
    model=basic_model,  # Default model
    tools=tools,
    middleware=[dynamic_model_selection]
)
```

# 消息

## 基本用法

```python
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, AIMessage, SystemMessage

model = init_chat_model("gpt-5-nano")

system_msg = SystemMessage("You are a helpful assistant.")
human_msg = HumanMessage("Hello, how are you?")

# Use with chat models
messages = [system_msg, human_msg]
response = model.invoke(messages)  # Returns AIMessage
```

## 文本提示

文本提示是字符串——非常适合简单的生成任务，无需保留对话历史记录。

```python
response = model.invoke("Write a haiku about spring")
```

## 消息提示


或者，您可以通过提供消息对象列表，将消息列表传递给模型。

```python
from langchain.messages import SystemMessage, HumanMessage, AIMessage

messages = [
    SystemMessage("You are a poetry expert"),
    HumanMessage("Write a haiku about spring"),
    AIMessage("Cherry blossoms bloom...")
]
response = model.invoke(messages)
```

## 字典格式

```python
messages = [
    {"role": "system", "content": "You are a poetry expert"},
    {"role": "user", "content": "Write a haiku about spring"},
    {"role": "assistant", "content": "Cherry blossoms bloom..."}
]
response = model.invoke(messages)
```

## 系统消息

```python
system_msg = SystemMessage("You are a helpful coding assistant.")

messages = [
    system_msg,
    HumanMessage("How do I create a REST API?")
]
response = model.invoke(messages)
```

```python

from langchain.messages import SystemMessage, HumanMessage

system_msg = SystemMessage("""
You are a senior Python developer with expertise in web frameworks.
Always provide code examples and explain your reasoning.
Be concise but thorough in your explanations.
""")

messages = [
    system_msg,
    HumanMessage("How do I create a REST API?")
]
response = model.invoke(messages)
```

## 人类消息

文本内容

```python
response = model.invoke([
  HumanMessage("What is machine learning?")
])
```

消息元数据

```python
human_msg = HumanMessage(
    content="Hello!",
    name="alice",  # Optional: identify different users
    id="msg_123",  # Optional: unique identifier for tracing
)
```

## AI 消息

表示AIMessage模型调用的输出。它们可以包含多模态数据、工具调用和特定于提供商的元数据，您可以稍后访问这些元数据。

```python
response = model.invoke("Explain AI")
print(type(response))  # <class 'langchain.messages.AIMessage'>
```

```python
from langchain.messages import AIMessage, SystemMessage, HumanMessage

# Create an AI message manually (e.g., for conversation history)
ai_msg = AIMessage("I'd be happy to help you with that question!")

# Add to conversation history
messages = [
    SystemMessage("You are a helpful assistant"),
    HumanMessage("Can you help me?"),
    ai_msg,  # Insert as if it came from the model
    HumanMessage("Great! What's 2+2?")
]

response = model.invoke(messages)
```

## 工具调用

```python
from langchain.chat_models import init_chat_model

model = init_chat_model("gpt-5-nano")

def get_weather(location: str) -> str:
    """Get the weather at a location."""
    ...

model_with_tools = model.bind_tools([get_weather])
response = model_with_tools.invoke("What's the weather in Paris?")

for tool_call in response.tool_calls:
    print(f"Tool: {tool_call['name']}")
    print(f"Args: {tool_call['args']}")
    print(f"ID: {tool_call['id']}")
```

## token 使用

```python
from langchain.chat_models import init_chat_model

model = init_chat_model("gpt-5-nano")

response = model.invoke("Hello!")
response.usage_metadata
```

```json
{'input_tokens': 8,
 'output_tokens': 304,
 'total_tokens': 312,
 'input_token_details': {'audio': 0, 'cache_read': 0},
 'output_token_details': {'audio': 0, 'reasoning': 256}}
```

## 流式输出

```python
chunks = []
full_message = None
for chunk in model.stream("Hi"):
    chunks.append(chunk)
    print(chunk.text)
    full_message = chunk if full_message is None else full_message + chunk
```

## 工具调用的消息

```python
from langchain.messages import AIMessage
from langchain.messages import ToolMessage

# After a model makes a tool call
# (Here, we demonstrate manually creating the messages for brevity)
ai_message = AIMessage(
    content=[],
    tool_calls=[{
        "name": "get_weather",
        "args": {"location": "San Francisco"},
        "id": "call_123"
    }]
)

# Execute tool and create result message
weather_result = "Sunny, 72°F"
tool_message = ToolMessage(
    content=weather_result,
    tool_call_id="call_123"  # Must match the call ID
)

# Continue conversation
messages = [
    HumanMessage("What's the weather in San Francisco?"),
    ai_message,  # Model's tool call
    tool_message,  # Tool execution result
]
response = model.invoke(messages)  # Model processes the result
```

## 多模态输入

您可以将消息内容理解为发送到模型的数据有效载荷。消息具有一个content弱类型属性，支持字符串和无类型对象列表（例如字典）。这使得 LangChain 聊天模型能够直接支持提供者原生结构，例如多模态内容和其他数据。

```python
# From URL
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this image."},
        {"type": "image", "url": "https://example.com/path/to/image.jpg"},
    ]
}

# From base64 data
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this image."},
        {
            "type": "image",
            "base64": "AAAAIGZ0eXBtcDQyAAAAAGlzb21tcDQyAAACAGlzb2...",
            "mime_type": "image/jpeg",
        },
    ]
}

# From provider-managed File ID
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this image."},
        {"type": "image", "file_id": "file-abc123"},
    ]
}
```


## 序列化

您可以将消息序列化为普通对象进行存储，并反序列化回消息实例。这对于持久化对话历史记录和恢复会话非常有用。

```python
from langchain.messages import HumanMessage
from langchain_core.load import dumpd, load

message = HumanMessage("What is the capital of France?")

# Serialize to a plain dict
serialized = dumpd(message)

# Deserialize back to a message object
restored = load(serialized)
```

#