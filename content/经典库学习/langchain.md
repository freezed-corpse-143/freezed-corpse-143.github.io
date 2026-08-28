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

### 流写入器

在工具执行期间流式传输实时更新。这对于在长时间运行的操作中向用户提供进度反馈非常有用。

使用 `runtime.stream_writer` 发出自定义更新：

```python
from langchain.tools import tool, ToolRuntime

@tool
def get_weather(city: str, runtime: ToolRuntime) -> str:
    """Get weather for a given city."""
    writer = runtime.stream_writer

    # Stream custom updates as the tool executes
    writer(f"Looking up data for city: {city}")
    writer(f"Acquired data for city: {city}")

    return f"It's always sunny in {city}!"
```

> 注意：如果在工具内使用 `runtime.stream_writer`，该工具必须在 LangGraph 执行上下文中调用。详见[流式传输](/oss/python/langchain/streaming)。

### 执行信息

通过 `runtime.execution_info` 在工具内访问线程 ID、运行 ID 和重试状态：

```python
from langchain.tools import tool, ToolRuntime

@tool
def log_execution_context(runtime: ToolRuntime) -> str:
    """Log execution identity information."""
    info = runtime.execution_info
    print(f"Thread: {info.thread_id}, Run: {info.run_id}")
    print(f"Attempt: {info.node_attempt}")
    return "done"
```

> 注意：需要 `deepagents>=0.5.0`（或 `langgraph>=1.1.5`）。

### 服务器信息

当工具运行在 LangGraph Server 上时，通过 `runtime.server_info` 访问 assistant ID、graph ID 和已认证用户：

```python
from langchain.tools import tool, ToolRuntime

@tool
def get_assistant_scoped_data(runtime: ToolRuntime) -> str:
    """Fetch data scoped to the current assistant."""
    server = runtime.server_info
    if server is not None:
        print(f"Assistant: {server.assistant_id}, Graph: {server.graph_id}")
        if server.user is not None:
            print(f"User: {server.user.identity}")
    return "done"
```

当工具未运行在 LangGraph Server 上时（例如本地开发或测试期间），`server_info` 为 `None`。

> 注意：需要 `deepagents>=0.5.0`（或 `langgraph>=1.1.5`）。

### 从旧式注入模式迁移

旧示例使用 `InjectedState`、`InjectedStore`、`get_runtime()` 或 `InjectedToolCallId`。请改用 [`ToolRuntime`](https://reference.langchain.com/python/langchain/tools/#langchain.tools.ToolRuntime)，为状态、上下文、存储和执行元数据提供统一的显式接口。

旧模式：

```python
from langchain.tools import tool, InjectedState

@tool
def summarize(state: InjectedState) -> str:
    """Summarize the conversation."""
    messages = state["messages"]
    return f"Conversation length: {len(messages)} messages."
```

推荐模式：

```python
from langchain.tools import tool, ToolRuntime

@tool
def summarize(runtime: ToolRuntime) -> str:
    """Summarize the conversation."""
    messages = runtime.state["messages"]
    return f"Conversation length: {len(messages)} messages."
```

代理级别的迁移（例如 `create_react_agent` 和自定义状态），请参阅 [LangChain v1 迁移指南](/oss/python/migrate/langchain-v1)。

## 工具执行

在 LangChain 中，工具由代理使用（例如通过 [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent)），工具错误处理通过[中间件](/oss/python/langchain/middleware)配置。

对于 LangGraph 工作流，工具执行由 [`ToolNode`](https://reference.langchain.com/python/langgraph/agents/#langgraph.prebuilt.tool_node.ToolNode) 处理。关于图 API 的用法，包括工具如何访问当前图状态和运行作用域上下文，请参阅 [ToolNode](/oss/python/langgraph/workflows-agents#toolnode)。

### 工具返回值

可以为工具选择不同的返回值：

* 返回 `string` 用于人类可读的结果。
* 返回 `object` 用于模型需要解析的结构化结果。
* 返回带可选消息的 `Command`，用于需要写入状态时。

#### 返回字符串

当工具应为模型提供纯文本以供阅读并在下一步响应中使用时，返回字符串：

```python
from langchain.tools import tool

@tool
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"It is currently sunny in {city}."
```

行为：

* 返回值转换为 `ToolMessage`。
* 模型看到该文本并决定下一步做什么。
* 除非模型或其他工具稍后修改，否则不会改变任何代理状态字段。

适用于结果天然是人类可读文本的情况。

#### 返回对象

当工具产生模型应该检查的结构化数据时，返回对象（例如 `dict`）：

```python
from langchain.tools import tool

@tool
def get_weather_data(city: str) -> dict:
    """Get structured weather data for a city."""
    return {
        "city": city,
        "temperature_c": 22,
        "conditions": "sunny",
    }
```

行为：

* 对象被序列化并作为工具输出发送回去。
* 模型可以读取特定字段并在此基础上推理。
* 与字符串返回一样，这不会直接更新图状态。

适用于下游推理需要显式字段而非自由格式文本的情况。

#### 返回多模态内容

工具不仅限于纯文本。当模型支持多模态工具结果时，工具可以返回[标准内容块](/oss/python/langchain/messages#standard-content-blocks)，使模型在一次工具结果中收到文本、图像和其他媒体：

```python
from langchain.tools import tool

@tool
def capture_screenshot() -> list[dict]:
    """Capture a screenshot of the current page."""
    return [
        {"type": "text", "text": "Screenshot of the current page:"},
        {"type": "image", "url": "https://example.com/page.png"},
    ]
```

行为：

* 返回值转换为带多模态 `content` 的 `ToolMessage`。
* 使用 `message.content_blocks` 在工具运行后读取规范化后的块列表。
* 模型必须支持你返回的模态。返回图像、音频或视频之前，请检查你的[模型能力](/oss/python/integrations/chat)。

关于块类型和提供商特定要求，请参阅[多模态消息](/oss/python/langchain/messages#multimodal)。返回图像或混合内容的 MCP 工具也会以同样方式转换；请参阅[多模态工具内容](/oss/python/langchain/mcp#multimodal-tool-content)。

#### 返回 Command

当工具需要更新图状态（例如设置用户偏好或应用状态）时，返回 [`Command`](https://reference.langchain.com/python/langgraph/types/Command)。
当 `Command` 指向当前图时，请在更新中包含一个工具调用 ID 与当前工具调用匹配的 `ToolMessage`。
消息历史中的每个工具调用都必须有对应的 `ToolMessage`。

对 `tool_call_id` 参数使用 `runtime.tool_call_id`。`ToolNode` 强制执行此要求：如果更新中没有与工具调用匹配的 `ToolMessage`，会抛出 `ValueError`。

```python
from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime, tool
from langgraph.types import Command

@tool
def set_language(language: str, runtime: ToolRuntime) -> Command:
    """Set the preferred response language."""
    return Command(
        update={
            "preferred_language": language,
            "messages": [
                ToolMessage(
                    content=f"Language set to {language}.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )
```

行为：

* 命令通过 `update` 更新状态。
* 更新后的状态对同一次运行中的后续步骤可用。
* 对可能被并行工具调用更新的字段使用 reducer。

适用于工具不只是返回数据、还在修改代理状态的情况。

#### 直接从工具返回

在工具上设置 `return_direct` 可以短路代理循环：代理立即把工具输出返回给调用者，而不将其发回模型做进一步处理。

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了 7 个相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI

@tool(return_direct=True)
def fetch_order_status(order_id: str) -> str:
    """Fetch the current status of a customer order."""
    # In production, query your order management system here
    return f"Order {order_id} is shipped and will arrive in 2 days."

agent = create_agent(
    ChatOpenAI(model="google_genai:gemini-3.6-flash"),
    tools=[fetch_order_status],
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "What is the status of order #12345?"}]
})
# The agent returns the tool output directly without another LLM call:
# "Order 12345 is shipped and will arrive in 2 days."
```

行为：

* 工具正常执行，其输出包装在 `ToolMessage` 中。
* 代理停止循环，将工具输出作为最终响应返回，绕过任何额外的模型调用。
* **多个并行工具调用：** 当模型在一步中调用多个工具时，它们都会先执行。所有工具完成后，仅当该批次中**每个**工具都有 `return_direct=True` 时，代理才路由到 `END`。最终响应包含该步骤中调用的每个工具的 `ToolMessage` 输出。

适用于以下情况：

* 工具的输出就是完整、用户可直接使用的答案（例如返回可直接显示结果的查询）。
* 不需要额外推理时，希望避免多余的模型调用。
* 需要确定性、未经修改的输出：模型不能改写、总结或对工具结果采取行动。

> 警告：由于模型不处理工具输出，`return_direct=True` 不适合结果需要进一步推理、总结或与其他工具调用链式组合的工具。

> 警告：**混合并行调用：** 如果模型将 `return_direct=True` 工具与未设置 `return_direct=True` 的工具一起调用，代理在该步骤后**不会**退出。它会带着该批次中的所有 `ToolMessage` 路由回模型，以便模型对所有结果进行推理。只有当步骤中的每个工具调用都有 `return_direct=True` 时，`return_direct` 才会短路循环。

#### 返回 Command 与 return_direct

带有 `return_direct=True` 的工具也可以返回 [`Command`](https://reference.langchain.com/python/langgraph/types/Command)，在代理退出前更新图状态。与普通返回值不同，`Command` 不会自动转换为 `ToolMessage`。当 `Command` 指向当前图（`graph` 未设置或为 `None`）时，请在 `Command.update` 中包含与工具调用 `tool_call_id` 匹配的 `ToolMessage`。省略它会导致 `ToolNode` 抛出 `ValueError`，因为每个 `AIMessage` 工具调用都必须有对应的 `ToolMessage`。

```python
from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime, tool
from langgraph.types import Command

@tool(return_direct=True)
def fetch_and_store_order(order_id: str, runtime: ToolRuntime) -> Command:
    """Fetch order status and store it in state."""
    status = f"Order {order_id} is shipped and will arrive in 2 days."
    return Command(
        update={
            "last_order_status": status,
            # Must include a ToolMessage so the message history stays valid
            "messages": [
                ToolMessage(
                    content=status,
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )
```

若要写入父图，请设置 `graph=Command.PARENT`。这种情况下 `ToolMessage` 要求会被解除，因为执行会完全离开当前图。

### 错误处理

使用 LangChain 代理[中间件](/oss/python/langchain/middleware)处理工具错误——重试失败的工具调用或返回自定义错误消息：

（官方文档对 7 家提供商提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
from collections.abc import Callable

from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest

@wrap_tool_call
def handle_tool_errors(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage],
) -> ToolMessage:
    """Convert tool exceptions into ToolMessages the model can handle."""
    try:
        return handler(request)
    except Exception as e:
        return ToolMessage(
            content=f"Tool error: Please check your input and try again. ({e})",
            tool_call_id=request.tool_call["id"],
        )

agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[],
    middleware=[handle_tool_errors],
)
```

### 状态注入

工具通过 [`ToolRuntime`](https://reference.langchain.com/python/langchain/tools/#langchain.tools.ToolRuntime) 访问图状态。请参阅[访问上下文](#访问上下文)了解状态、上下文、存储和流式 API。

```python
from langchain.tools import tool, ToolRuntime

@tool
def get_message_count(runtime: ToolRuntime) -> str:
    """Get the number of messages in the conversation."""
    messages = runtime.state["messages"]
    return f"There are {len(messages)} messages."
```

关于从工具访问状态、上下文和长期记忆的更多细节，请参阅[访问上下文](#访问上下文)。

## 动态工具选择

使用动态工具时，代理可用的工具集在运行时被修改，而不是一开始就全部定义。并非每个工具都适合每种情况。工具太多可能会压垮模型（使上下文过载）并增加错误；太少则限制能力。动态工具选择使得可以根据认证状态、用户权限、功能标志或对话阶段调整可用工具集。

有两种方法，取决于工具是否提前已知：

### 过滤预注册工具

当所有可能的工具在代理创建时已知，你可以预注册它们，并根据状态、权限或上下文动态过滤向模型暴露哪些工具。

按状态过滤——仅在达到某些对话里程碑后启用高级工具：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@wrap_model_call
def state_based_tools(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Filter tools based on conversation State."""
    # Read from State: check if user has authenticated
    state = request.state
    is_authenticated = state.get("authenticated", False)
    message_count = len(state["messages"])

    # Only enable sensitive tools after authentication
    if not is_authenticated:
        tools = [t for t in request.tools if t.name.startswith("public_")]
        request = request.override(tools=tools)
    elif message_count < 5:
        # Limit tools early in conversation
        tools = [t for t in request.tools if t.name != "advanced_search"]
        request = request.override(tools=tools)

    return handler(request)

agent = create_agent(
    model="gpt-5.5",
    tools=[public_search, private_search, advanced_search],
    middleware=[state_based_tools]
)
```

按存储过滤——根据 Store 中的用户偏好或功能标志过滤工具：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

@wrap_model_call
def store_based_tools(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Filter tools based on Store preferences."""
    user_id = request.runtime.context.user_id

    # Read from Store: get user's enabled features
    store = request.runtime.store
    feature_flags = store.get(("features",), user_id)

    if feature_flags:
        enabled_features = feature_flags.value.get("enabled_tools", [])
        # Only include tools that are enabled for this user
        tools = [t for t in request.tools if t.name in enabled_features]
        request = request.override(tools=tools)

    return handler(request)

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, analysis_tool, export_tool],
    middleware=[store_based_tools],
    context_schema=Context,
    store=InMemoryStore()
)
```

按运行时上下文过滤——根据 Runtime Context 中的用户权限过滤工具：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@dataclass
class Context:
    user_role: str

@wrap_model_call
def context_based_tools(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Filter tools based on Runtime Context permissions."""
    # Read from Runtime Context: get user role
    if request.runtime is None or request.runtime.context is None:
        # If no context provided, default to viewer (most restrictive)
        user_role = "viewer"
    else:
        user_role = request.runtime.context.user_role

    if user_role == "admin":
        # Admins get all tools
        pass
    elif user_role == "editor":
        # Editors can't delete
        tools = [t for t in request.tools if t.name != "delete_data"]
        request = request.override(tools=tools)
    else:
        # Viewers get read-only tools
        tools = [t for t in request.tools if t.name.startswith("read_")]
        request = request.override(tools=tools)

    return handler(request)

agent = create_agent(
    model="gpt-5.5",
    tools=[read_data, write_data, delete_data],
    middleware=[context_based_tools],
    context_schema=Context
)
```

这种方法最适合：

* 所有可能的工具在编译/启动时已知
* 想根据权限、功能标志或对话状态过滤
* 工具是静态的，但其可用性是动态的

更多示例请参阅[动态选择工具](/oss/python/langchain/middleware/custom#dynamically-selecting-tools)。

### 运行时工具注册

当工具在运行时被发现或创建（例如从 MCP 服务器加载、根据用户数据生成或从远程注册表获取）时，你需要同时注册工具并动态处理其执行。

这需要两个中间件钩子：

1. `wrap_model_call` —— 将动态工具添加到请求中
2. `wrap_tool_call` —— 处理动态添加的工具的执行

```python
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ToolCallRequest

# A tool that will be added dynamically at runtime
@tool
def calculate_tip(bill_amount: float, tip_percentage: float = 20.0) -> str:
    """Calculate the tip amount for a bill."""
    tip = bill_amount * (tip_percentage / 100)
    return f"Tip: ${tip:.2f}, Total: ${bill_amount + tip:.2f}"

class DynamicToolMiddleware(AgentMiddleware):
    """Middleware that registers and handles dynamic tools."""

    def wrap_model_call(self, request: ModelRequest, handler):
        # Add dynamic tool to the request
        # This could be loaded from an MCP server, database, etc.
        updated = request.override(tools=[*request.tools, calculate_tip])
        return handler(updated)

    def wrap_tool_call(self, request: ToolCallRequest, handler):
        # Handle execution of the dynamic tool
        if request.tool_call["name"] == "calculate_tip":
            return handler(request.override(tool=calculate_tip))
        return handler(request)

agent = create_agent(
    model="gpt-5.5",
    tools=[get_weather],  # Only static tools registered here
    middleware=[DynamicToolMiddleware()],
)

# The agent can now use both get_weather AND calculate_tip
result = agent.invoke({
    "messages": [{"role": "user", "content": "Calculate a 20% tip on $85"}]
})
```

这种方法最适合：

* 工具在运行时被发现（例如来自 MCP 服务器）
* 工具根据用户数据或配置动态生成
* 正在与外部工具注册表集成

> 注意：运行时注册的工具必须使用 `wrap_tool_call` 钩子，因为代理需要知道如何执行不在原始工具列表中的工具。没有它，代理将不知道如何调用动态添加的工具。

## 无头工具

有些工具应该运行在**你的用户应用运行的地方**（通常是浏览器），而不是进程内部。**无头工具**是工具定义——包括名称、描述和参数 schema——你在**服务端**与代理一起注册。**实现**只在**客户端**注册，并在短暂的 interrupt/resume 握手后执行。

这与函数体在服务端运行的普通工具不同，也与[服务端工具调用](#服务端工具调用)（模型提供商远程执行内置工具）不同。

### 何时使用无头工具

当工作依赖只存在于客户端的**环境、设备或 UI** 时使用。例如：

* **浏览器 API：** Geolocation、IndexedDB、Clipboard、Canvas 2D、文件选择器、Battery API 等。
* **隐私与本地性：** 数据留在设备上（例如 IndexedDB 中的本地"记忆"）。
* **延迟：** 纯本地操作无需额外的服务端往返。
* **结构化、安全的副作用：** 倾向于许多小而类型化的工具（例如每个 canvas 原语一个工具），而不是向 `eval` 发送任意代码。

### 模式如何工作

在两种运行时中，模型看到的是一个可以正常调用的工具，但实际执行发生在服务端进程之外。

1. **定义** 一个无头工具，使用 `langchain.tools` 中的 `tool(name=..., description=..., args_schema=...)`。无头工具只有 schema，没有进程内实现。
2. **注册** 该工具到 `create_agent` 或你的 LangGraph 图中，使模型可以正常调用它。
3. **处理** 工具被调用时的中断负载。图不是本地执行，而是以形如 `{"type": "tool", "tool_call": {"id", "name", "args"}}` 的负载暂停。
4. **恢复** 图——在你的应用、另一个服务或人工步骤执行该操作之后。对于基于浏览器的流程，你可以在前端镜像 schema，并在那里附加 `.implement(...)`。

> 提示：如果在 Python 中只使用 `name`、`description` 和 `args_schema` 调用 `tool(...)`，LangChain 会返回一个 `HeadlessTool`。Python 端没有 `.implement()` API。

当模型对这些工具之一发出工具调用时，运行会**中断**而不是在本地执行工具。你的应用可以检查负载，在正确的环境（例如浏览器、另一个服务或人工审核步骤）中执行操作，然后使用工具结果**恢复**图。使用受支持的 JS SDK 钩子时，它们可以检测无头工具中断、运行匹配的客户端实现并为你提交恢复命令。

使用可选的 **`onTool`** 回调观察生命周期事件（`start`、`success`、`error`），用于 spinner 或 toast 等 UI 反馈。

### 无头工具前端模式

> 参见 [Headless tools frontend pattern](/oss/python/langchain/frontend/headless-tools)：在客户端使用 `useStream` 执行仅 schema 工具的端到端示例。

## 预构建工具

LangChain 提供了大量预构建工具和工具包，涵盖常见任务，如网络搜索、代码解释、数据库访问等。这些开箱即用的工具可以直接集成到你的代理中，无需编写自定义代码。

参见[工具与工具包](/oss/python/integrations/tools)集成页面，获取按类别组织的可用工具完整列表。

## 服务端工具调用

某些聊天模型带有由模型提供商在服务端执行的内置工具。这些包括网络搜索和代码解释器等能力，不需要你定义或托管工具逻辑。

有关启用和使用这些内置工具的细节，请参阅各个[聊天模型集成页面](/oss/python/integrations/providers)和[工具调用文档](/oss/python/langchain/models#server-side-tool-use)。

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

## 代理（Agents）

代理（agent）是一个模型在循环中反复调用工具，直到完成给定任务。

（官方文档在此处提供了一张核心代理循环示意图。）

Harness 是围绕这个循环的一切：提示词、工具，以及任何塑造模型行为的中间件。

> 注意：**代理 = 模型 + Harness**
>
> Harness 的职责：在正确的时机为模型提供给定任务所需的正确上下文。

[`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 是一个高度可配置的 harness。最简单的用法如下：

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
from langchain.agents import create_agent

agent = create_agent(model="google_genai:gemini-3.6-flash", tools=tools)
```

在此基础上，你可以直接用 `model=`、`tools=` 和 `system_prompt=` 参数配置基本能力。如需更高级的功能，可以用[中间件](#配置-harness)扩展 harness。

> 提示：[Deep Agents](/oss/python/deepagents/overview) 构建在 `create_agent` 之上，并预置了常用的能力，如规划、文件系统工具、子代理和记忆。当你需要自行配置 harness 时，使用 `create_agent`。

## 核心组件

（官方文档在此处提供了一张"代理模型与 harness 组件"示意图。）

### 模型

传入模型标识符字符串（`"provider:model"`）或一个已初始化的模型实例，为你的代理选择模型。参数、提供商设置和动态模型选择请参阅[模型](/oss/python/langchain/models)。

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
from langchain.agents import create_agent

agent = create_agent(model="google_genai:gemini-3.6-flash", tools=tools)
```

### 工具

要为代理提供工具，传入任何 Python 可调用对象、LangChain 工具或工具字典。工具定义、上下文访问和动态工具选择请参阅[工具](/oss/python/langchain/tools)。

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
from langchain.agents import create_agent
from langchain.tools import tool

@tool
def search(query: str) -> str:
    """Search for information."""
    return f"Results for: {query}"

agent = create_agent(model="google_genai:gemini-3.6-flash", tools=[search])
```

### 系统提示词

塑造代理处理任务的方式。`system_prompt` 参数接受字符串或 `SystemMessage`。如需在运行时使用动态提示词，请使用[中间件](/oss/python/langchain/middleware)。

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=tools,
    system_prompt="You are a helpful assistant. Be concise and accurate.",
)
```

### 结构化输出

使用 `response_format=` 从代理返回经过校验的 schema。策略和示例请参阅[结构化输出](/oss/python/langchain/structured-output)。

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

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

### 代理状态

每个代理都通过 [`AgentState`](https://reference.langchain.com/python/langchain/agents/middleware/types/AgentState) 管理其执行上下文。这是一个类型化字典，保存当前对话历史以及你的工具和中间件所需的任何自定义字段。

内置字段为：

| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| `messages` | `list[BaseMessage]` | 当前线程的完整对话历史。仅追加：新消息会被添加，永远不会被替换。 |

`AgentState` 也是每个节点式中间件钩子（`before_model`、`after_model` 等）的类型签名。钩子接收当前状态，并可返回一个更新字典合并回状态中。

要添加自定义字段（例如 `user_id` 或计数器），请继承 `AgentState`，并通过 `state_schema=` 将子类传给 `create_agent`：

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

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

完整细节、示例以及中间件层的状态 schema 请参阅[短期记忆](/oss/python/langchain/short-term-memory#customizing-agent-memory)和[自定义中间件](/oss/python/langchain/middleware/custom#state-updates)。

## 调用

> 提示：使用 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-agents) 跟踪此循环的每一步、调试工具调用并评估代理输出。按照[追踪快速入门](/langsmith/trace-with-langchain)进行设置。我们还建议你设置 [LangSmith Engine](/langsmith/engine)，它会监控你的追踪、发现问题并提出修复建议。

你可以用一条消息调用代理。在幕后，这会向代理的 [`State`](/oss/python/langgraph/graph-api#state) 传入一个更新。所有代理的状态中都包含一个[消息序列](/oss/python/langgraph/use-graph-api#messagesstate)；要调用代理，请传入一条新消息以及一个 `thread_id`，这样代理就能持久化并恢复对话历史：

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

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

> 注意：要用 `thread_id` 持久化对话历史，代理必须配置[检查点器（checkpointer）](/oss/python/langchain/long-term-memory)。在 [LangSmith](/langsmith/deployment) 上部署时，检查点器会自动配置。在本地，需要显式传入一个，例如 `create_agent(..., checkpointer=InMemorySaver())`。

如果你还需要向工具和中间件传递每次运行（per-run）的配置（例如用户 ID、API 密钥或功能开关），请将其作为 `context` 与 `config` 一起传入。用 `context_schema` 定义该数据的结构，并通过 `runtime.context` 访问它：

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

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

`thread_id` 限定*对话*的范围（消息历史、检查点），而 `context` 携带*每次运行*的数据，供你的工具和中间件在调用时读取。两者通常一起传入。更多内容请参阅[工具上下文](/oss/python/langchain/tools#context)和[运行时（Runtime）](/oss/python/langchain/runtime)。

## 流式输出

`invoke` 在运行结束时返回最终响应。如果代理执行了多次工具调用，用户通常需要在完成前看到进度更新。使用流式输出在事件发生时即时呈现中间消息和工具活动。

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

> 提示：流式输出模式、事件类型和 UI 模式请参阅[流式输出](/oss/python/langchain/streaming)。

## 配置 harness

`create_agent` 高度可扩展。中间件是自定义的基本原语：每个中间件处理一个关注点，在正确的时机接入代理循环，并能与任何其他中间件自由组合。只取你的用例所需的，跳过其余部分。

常见模式已预置为一等公民中间件。你可以把任何其他需求构建为[自定义中间件](/oss/python/langchain/middleware/custom)。

（官方文档在此处提供了一张"按类别划分的代理 harness 能力"示意图。）

随着代理承担越来越复杂的工作，它们需要在几个关键领域获得支持。中间件生态提供了：

- **执行环境**（[#execution-environment](#执行环境)）：工具、文件系统、沙箱和代码执行
- **上下文管理**（[#context-management](#上下文管理)）：摘要、记忆、技能和提示词缓存
- **规划与委派**（[#planning-and-delegation](#规划与委派)）：待办列表和子代理，用于并行、隔离的工作
- **容错**（[#fault-tolerance](#容错)）：重试、回退和调用限制
- **护栏**（[#guardrails](#护栏)）：PII 检测和内容控制
- **引导**（[#steering](#引导)）：在高影响操作前进行人机协同审批

> 提示：`create_deep_agent` 为长时间运行的编码和研究任务预组装了这套栈（默认包含文件系统、摘要、子代理和提示词缓存）。完整的预置 harness 请参阅 [Deep Agents](/oss/python/deepagents/harness)。

### 执行环境

当代理能够采取行动而不仅仅是生成文本时，它们尤其有用。执行环境为代理提供工作区：它可以调用的工具、用于跨轮次读写文件的文件系统，以及用于运行脚本或 shell 命令的代码执行。

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

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

参阅 [`FilesystemMiddleware`](https://reference.langchain.com/python/deepagents/middleware/filesystem/FilesystemMiddleware)、[沙箱](/oss/python/deepagents/sandboxes)、[解释器](/oss/python/deepagents/interpreters)。

> 注意：此示例从 `deepagents` 包导入。安装方式：
>
> ```bash
> pip install deepagents
> ```
>
> 或使用 uv：
>
> ```bash
> uv add deepagents
> ```

### 上下文管理

每次模型调用都有固定的上下文窗口。随着代理运行，该窗口会不断被累积的历史、工具结果和中间步骤填满。摘要（summarization）会在溢出发生前压缩历史；记忆在启动时加载持久化指令，使知识跨会话保留；技能按需呈现领域知识，而不是一开始就全部加载。

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

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

参阅 [`SummarizationMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/SummarizationMiddleware)、[`MemoryMiddleware`](https://reference.langchain.com/python/deepagents/middleware/memory/MemoryMiddleware)、[技能](/oss/python/langchain/multi-agent/skills)、[上下文工程](/oss/python/deepagents/context-engineering)。

> 注意：此示例从 `deepagents` 包导入。安装方式：
>
> ```bash
> pip install deepagents
> ```
>
> 或使用 uv：
>
> ```bash
> uv add deepagents
> ```

### 规划与委派

复杂任务往往超出单个上下文窗口的承载能力。委派让主代理把工作拆分成若干部分，交给各自在独立上下文中运行的子代理，自己专注于协调而非执行。工作可以并行运行；主代理的上下文保持干净。

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

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

参阅[子代理](/oss/python/langchain/multi-agent/subagents)。

> 注意：此示例从 `deepagents` 包导入。安装方式：
>
> ```bash
> pip install deepagents
> ```
>
> 或使用 uv：
>
> ```bash
> uv add deepagents
> ```

### 为代理命名

可选地为代理使用标识符。当把代理作为子图嵌入[多代理](/oss/python/langchain/multi-agent)系统时，这一点尤其有用。

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
agent = create_agent(model="google_genai:gemini-3.6-flash", tools=tools, name="research_assistant")
```

### 容错

生产环境中的代理会遇到开发中很少出现的故障：速率限制、模型超时、临时性 API 错误。容错中间件在基础设施层面处理这些问题，这样你的工具和业务逻辑就不必在每次调用周围都写 try/catch。

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

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

参阅 [`ModelRetryMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/model_retry/ModelRetryMiddleware)、[`ToolRetryMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/tool_retry/ToolRetryMiddleware)、[预置中间件](/oss/python/langchain/middleware/built-in)。

### 护栏

有些策略无法写进提示词——无论模型做什么，它们都需要被确定性地强制执行。护栏会在数据流经代理循环时拦截数据，在工具结果进入模型上下文之前应用合规规则或内容策略。

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

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

参阅 [`PIIMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/pii/PIIMiddleware)、[预置中间件](/oss/python/langchain/middleware/built-in)。

### 引导

完全自主并不总是合适的。引导让你把人类放在特定的决策点上——在破坏性写入、昂贵 API 调用或任何需要判断的操作之前——而无需重构你的代理。代理暂停并等待；人类批准、修改或拒绝；执行继续。

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

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

参阅 [`HumanInTheLoopMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/human_in_the_loop/HumanInTheLoopMiddleware)、[人机协同](/oss/python/langchain/human-in-the-loop)。

### 中间件资源

- [中间件概览](/oss/python/langchain/middleware/overview)：中间件栈如何工作以及钩子在何时触发
- [预置中间件](/oss/python/langchain/middleware/built-in)：带配置示例的完整参考
- [自定义中间件](/oss/python/langchain/middleware/custom)：为业务逻辑、PII 清理等编写你自己的钩子

# 中间件

> 在每一步控制和定制代理执行

中间件提供了一种更紧密地控制代理内部行为的方式。中间件适用于以下场景：

* 通过日志、分析和调试来追踪代理行为。
* 转换提示词、[工具选择](/oss/python/langchain/middleware/built-in#llm-tool-selector)和输出格式。
* 添加[重试](/oss/python/langchain/middleware/built-in#tool-retry)、[回退](/oss/python/langchain/middleware/built-in#model-fallback)和提前终止逻辑。
* 应用[调用次数限制](/oss/python/langchain/middleware/built-in#model-call-limit)、护栏和 [PII 检测](/oss/python/langchain/middleware/built-in#pii-detection)。

通过将中间件传给 [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 来添加：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware, HumanInTheLoopMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[
        SummarizationMiddleware(...),
        HumanInTheLoopMiddleware(...)
    ],
)
```

## 代理循环

核心代理循环涉及调用模型、让模型选择要执行的工具，并在它不再调用工具时结束：

（核心代理循环示意图：调用模型 → 选择并执行工具 → 不再调用工具时结束。）

中间件在以上每个步骤之前和之后暴露钩子：

（中间件流程图：在模型调用、工具执行等步骤的前后均可挂接钩子。）

## 在 LangGraph 工作流中使用中间件

中间件并不是一个独立的运行时：钩子运行在 [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 返回的已编译 [LangGraph](/oss/python/langgraph/overview) 内部。你可以把整个代理（包括中间件）作为一个节点或子图放入更大的 [StateGraph](https://reference.langchain.com/python/langgraph/graph/state/StateGraph) 中，所有中间件钩子都会继续运行。

当周围的拓扑结构超出标准的"循环直到完成"时，可以使用这种模式：在路由到多个代理之一之前对输入进行分类、并行分发工作，或用确定性步骤串联代理调用。

`HumanInTheLoopMiddleware` 会根据每个工具的 `.name` 进行匹配。

使用 `@tool` 装饰的函数以函数名作为名称，因此下面的键是 `"send_email"`。

```python
from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.graph import START, StateGraph

# Assumes read_email, send_email, classify_node, and route are defined elsewhere.
email_agent = create_agent(
    model="claude-sonnet-4-6",
    tools=[read_email, send_email],
    middleware=[HumanInTheLoopMiddleware(interrupt_on={"send_email": True})],
)

graph = (
    StateGraph(AgentState)
    .add_node("classify", classify_node)
    .add_node("email_agent", email_agent)
    .add_edge(START, "classify")
    .add_conditional_edges("classify", route)
    .compile()
)
```

人机协同（HITL）中断、摘要、PII 脱敏、重试以及任何自定义钩子都会随代理节点一起传递。完整的组合模式集合参见 [使用子图](/oss/python/langgraph/use-subgraphs)，包括子图检查点作用域（按调用 vs 按线程）。

## 其他资源

* [预构建中间件](/oss/python/langchain/middleware/built-in)：探索面向常见用例的预构建中间件。
* [自定义中间件](/oss/python/langchain/middleware/custom)：使用钩子和装饰器构建你自己的中间件。
* [中间件 API 参考](https://reference.langchain.com/python/langchain/middleware/)：中间件的完整 API 参考。
* [中间件集成](/oss/python/integrations/middleware/)：面向 Anthropic、AWS、OpenAI 等提供商的专用中间件。
* [测试代理](/oss/python/langchain/test/)：使用 LangSmith 测试你的代理。

---

# 预构建中间件

> 面向常见代理用例的预构建中间件

LangChain 和 [Deep Agents](/oss/python/deepagents/overview) 为常见用例提供了预构建中间件。每个中间件都可用于生产环境，并可根据你的具体需求进行配置。

## 与提供商无关的中间件

以下中间件可与任何 LLM 提供商配合使用：

| 中间件                                    | 描述                                                                                   |
| --------------------------------------------- | --------------------------------------------------------------------------------------------- |
| [工具错误](#tool-error)                     | 捕获工具执行异常并将其转换为模型可读的错误消息。             |
| [工具重试](#tool-retry)                     | 使用指数退避自动重试失败的工具调用。                               |
| [模型重试](#model-retry)                   | 使用指数退避自动重试失败的模型调用。                              |
| [模型回退](#model-fallback)             | 当主模型失败时自动回退到备选模型。                              |
| [摘要](#summarization)               | 接近令牌限制时自动总结对话历史。                   |
| [人机协同](#human-in-the-loop)       | 暂停执行以等待人工批准工具调用。                                             |
| [模型调用限制](#model-call-limit)         | 限制模型调用次数以防止过度成本。                                   |
| [工具调用限制](#tool-call-limit)           | 通过限制调用次数来控制工具执行。                                               |
| [PII 检测](#pii-detection)               | 检测并处理个人身份信息（PII）。                                  |
| [待办列表](#to-do-list)                     | 为代理配备任务规划与跟踪能力。                                    |
| [LLM 工具选择器](#llm-tool-selector)       | 在调用主模型之前使用 LLM 选择相关工具。                                |
| [提供商工具搜索](#provider-tool-search) | 将工具延迟到提供商的服务器端工具搜索之后，按需浮现。              |
| [Shell 工具](#shell-tool)                     | 向代理暴露持久的 shell 会话用于执行命令。                            |
| [文件系统](#filesystem-middleware)          | 为代理提供文件系统以存储上下文和长期记忆。                  |
| [子代理](#subagent)                         | 添加生成子代理的能力。                                                           |
| [评分标准评分（Beta）](#rubric-grading)      | 应用 LLM 作为评审的评分，使代理自我评估并迭代直到满足评分标准。 |
| [文件搜索](#file-search)                   | 提供针对文件系统文件的 Glob 和 Grep 搜索工具。                                     |
| [上下文编辑](#context-editing)           | 通过裁剪或清除工具调用来管理对话上下文。                                |
| [LLM 工具模拟器](#llm-tool-emulator)       | 使用 LLM 模拟工具执行，用于测试目的。                                     |

### 工具错误

捕获工具执行期间抛出的异常，并将其转换为模型可见、可恢复的错误 `ToolMessage`，而不是中止代理运行。工具错误适用于以下场景：

* 让模型使用修正后的参数重试失败的工具调用。
* 展示受控、净化的错误消息，而不是原始的异常详情。
* 防止意外的工具异常导致代理崩溃。

> 注意：工具错误中间件不会自动重试失败的调用。如需重试，请将 [工具重试](#tool-retry) 中间件放置在列表**内层**（在 `middleware` 列表中更靠前），并配置 `on_failure="error"`，以便异常能够到达工具错误中间件。参见下面的[完整示例](#tool-error-full-example)。

**API 参考：** [`ToolErrorMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/tool_error/ToolErrorMiddleware)

> 注意：`ToolErrorMiddleware` 需要 `langchain>=1.3.14`。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ToolErrorMiddleware

def on_error(exc: Exception, request: ToolCallRequest) -> str | None:
    if isinstance(exc, ValueError):
        return f"`{request.tool_call['name']}` failed with {type(exc).__name__}."
    # propagate everything else

agent = create_agent(
    model="gpt-5.5",
    tools=[your_tools],
    middleware=[ToolErrorMiddleware(on_error)],
)
```

#### 配置选项

- `on_error`（`Callable[[Exception, ToolCallRequest], str | list[ContentBlock] | None]`）：同步处理器，在工具执行抛出的每个异常上调用。返回内容（`str` 或内容块列表）可将异常转换为 `ToolMessage(status="error")`。返回 `None` 或不写返回语句则让异常继续传播。用于同步路径，且除非给出 `aon_error`，否则也用于异步路径。
- `aon_error`（`Callable[[Exception, ToolCallRequest], Awaitable[str | list[ContentBlock] | None]]`）：可选的异步处理器，用于异步执行路径。未提供时回退到 `on_error`。
- `tools`（`list[BaseTool | str]`）：可选的工具或工具名列表，用于指定要应用错误处理的工具。若为 `None`，则应用于所有工具。

#### 工具错误完整示例

`on_error` 处理器接收异常和 `ToolCallRequest`（其中包含工具调用字典，含名称、参数和调用 ID）。对不想处理的异常返回 `None`，它们会正常传播。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ToolErrorMiddleware, ToolRetryMiddleware

def on_error(exc: Exception, request: ToolCallRequest) -> str | None:
    # Surface ValueError to the model so it can correct the input
    if isinstance(exc, ValueError):
        return f"`{request.tool_call['name']}` failed: {type(exc).__name__}. Fix the input and retry."
    # Let all other exceptions propagate (halts the run)
    return None

# Async-only usage
async def aon_error(exc: Exception, request: ToolCallRequest) -> str | None:
    if isinstance(exc, ConnectionError):
        return f"Tool `{request.tool_call['name']}` encountered a connection error."
    return None

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, database_tool],
    middleware=[
        # Place retry inner so exceptions reach ToolErrorMiddleware after retries are exhausted
        ToolRetryMiddleware(max_retries=3, on_failure="error"),
        ToolErrorMiddleware(on_error=on_error, tools=["search_tool"]),
    ],
)

# Async-only: pass aon_error alone (do not pass on_error)
async_agent = create_agent(
    model="gpt-5.5",
    tools=[api_tool],
    middleware=[ToolErrorMiddleware(aon_error=aon_error)],
)
```

> 注意：最好返回指明异常类型的内容，而不是原始异常消息，后者可能携带敏感或内部细节。`on_error` 处理器控制披露范围：除非你选择包含，否则原始异常消息绝不会发送给模型。

### 工具重试

使用可配置的指数退避自动重试失败的工具调用。工具重试适用于以下场景：

* 处理外部 API 调用中的瞬时故障。
* 提高依赖网络的工具的可靠性。
* 构建能够优雅处理临时错误的弹性代理。

**API 参考：** [`ToolRetryMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/tool_retry/ToolRetryMiddleware)

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ToolRetryMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, database_tool],
    middleware=[
        ToolRetryMiddleware(
            max_retries=3,
            backoff_factor=2.0,
            initial_delay=1.0,
        ),
    ],
)
```

#### 配置选项

- `max_retries`（`number`，默认 `2`）：初始调用之后的最大重试次数（默认共 3 次尝试）。
- `tools`（`list[BaseTool | str]`）：可选的工具或工具名列表，用于指定要应用重试逻辑的工具。若为 `None`，则应用于所有工具。
- `retry_on`（`tuple[type[Exception], ...] | callable`，默认 `default_retry_on`）：可以是需要重试的异常类型元组，也可以是接收异常并返回 `True`（表示应重试）的可调用对象。使用 `langchain>=1.3.16` 时，默认重试会重试可重试的[模型错误](/oss/python/langchain/models#model-exceptions)以及所有未分类的异常，并且不再重试被标记为不可重试的模型错误。
- `on_failure`（`string | callable`，默认 `continue`）：所有重试都耗尽时的行为。选项：
  - `'continue'`（默认）— 返回带错误详情的 `ToolMessage`，让 LLM 处理失败。
  - `'error'` — 重新抛出异常，停止代理执行。
  - 自定义可调用对象 — 接收异常并返回字符串作为 `ToolMessage` 内容的函数。
  - **已弃用的值：** `'return_message'`（改用 `'continue'`）和 `'raise'`（改用 `'error'`）。
- `backoff_factor`（`number`，默认 `2.0`）：指数退避的乘数。每次重试等待 `initial_delay * (backoff_factor ** retry_number)` 秒。设为 `0.0` 表示恒定延迟。
- `initial_delay`（`number`，默认 `1.0`）：第一次重试前的初始延迟（秒）。
- `max_delay`（`number`，默认 `60.0`）：重试之间的最大延迟（秒）（限制指数退避的增长）。
- `jitter`（`boolean`，默认 `true`）：是否在延迟上添加随机抖动（`±25%`）以避免惊群效应。

#### 完整示例

该中间件使用指数退避自动重试失败的工具调用。

**关键配置：**

* `max_retries` — 重试次数（默认：2）
* `backoff_factor` — 指数退避乘数（默认：2.0）
* `initial_delay` — 起始延迟秒数（默认：1.0）
* `max_delay` — 延迟增长上限（默认：60.0）
* `jitter` — 添加随机变化（默认：True）

**失败处理：**

* `on_failure='continue'`（默认）— 返回错误消息
* `on_failure='error'` — 重新抛出异常
* 自定义函数 — 返回错误消息的函数

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ToolRetryMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, database_tool, api_tool],
    middleware=[
        ToolRetryMiddleware(
            max_retries=3,
            backoff_factor=2.0,
            initial_delay=1.0,
            max_delay=60.0,
            jitter=True,
            tools=["api_tool"],
            retry_on=(ConnectionError, TimeoutError),
            on_failure="continue",
        ),
    ],
)
```

### 模型重试

使用可配置的指数退避自动重试失败的模型调用。模型重试适用于以下场景：

* 处理模型 API 调用中的瞬时故障。
* 提高依赖网络的模型请求的可靠性。
* 构建能够优雅处理临时模型错误的弹性代理。

**API 参考：** [`ModelRetryMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/model_retry/ModelRetryMiddleware)

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, database_tool],
    middleware=[
        ModelRetryMiddleware(
            max_retries=3,
            backoff_factor=2.0,
            initial_delay=1.0,
        ),
    ],
)
```

#### 配置选项

- `max_retries`（`number`，默认 `2`）：初始调用之后的最大重试次数（默认共 3 次尝试）。
- `retry_on`（`tuple[type[Exception], ...] | callable`，默认 `default_retry_on`）：可以是需要重试的异常类型元组，也可以是接收异常并返回 `True`（表示应重试）的可调用对象。使用 `langchain>=1.3.16` 时，默认重试会重试可重试的[模型错误](/oss/python/langchain/models#model-exceptions)以及所有未分类的异常，并且不再重试被标记为不可重试的模型错误。
- `on_failure`（`string | callable`，默认 `continue`）：所有重试都耗尽时的行为。选项：
  - `'continue'`（默认）— 返回带错误详情的 `AIMessage`，让代理有机会优雅地处理失败。
  - `'error'` — 重新抛出异常（停止代理执行）。
  - 自定义可调用对象 — 接收异常并返回字符串作为 `AIMessage` 内容的函数。
- `backoff_factor`（`number`，默认 `2.0`）：指数退避的乘数。每次重试等待 `initial_delay * (backoff_factor ** retry_number)` 秒。设为 `0.0` 表示恒定延迟。
- `initial_delay`（`number`，默认 `1.0`）：第一次重试前的初始延迟（秒）。
- `max_delay`（`number`，默认 `60.0`）：重试之间的最大延迟（秒）（限制指数退避的增长）。
- `jitter`（`boolean`，默认 `true`）：是否在延迟上添加随机抖动（`±25%`）以避免惊群效应。

#### 完整示例

该中间件使用指数退避自动重试失败的模型调用。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware

# Basic usage with default settings (2 retries, exponential backoff)
agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool],
    middleware=[ModelRetryMiddleware()],
)

# Custom exception filtering
class TimeoutError(Exception):
    """Custom exception for timeout errors."""
    pass

class ConnectionError(Exception):
    """Custom exception for connection errors."""
    pass

# Retry specific exceptions only
retry = ModelRetryMiddleware(
    max_retries=4,
    retry_on=(TimeoutError, ConnectionError),
    backoff_factor=1.5,
)

def should_retry(error: Exception) -> bool:
    # Only retry on rate limit errors
    if isinstance(error, TimeoutError):
        return True
    # Or check for specific HTTP status codes
    if hasattr(error, "status_code"):
        return error.status_code in (429, 503)
    return False

retry_with_filter = ModelRetryMiddleware(
    max_retries=3,
    retry_on=should_retry,
)

# Return error message instead of raising
retry_continue = ModelRetryMiddleware(
    max_retries=4,
    on_failure="continue",  # Return AIMessage with error instead of raising
)

# Custom error message formatting
def format_error(error: Exception) -> str:
    return f"Model call failed: {error}. Please try again later."

retry_with_formatter = ModelRetryMiddleware(
    max_retries=4,
    on_failure=format_error,
)

# Constant backoff (no exponential growth)
constant_backoff = ModelRetryMiddleware(
    max_retries=5,
    backoff_factor=0.0,  # No exponential growth
    initial_delay=2.0,  # Always wait 2 seconds
)

# Raise exception on failure
strict_retry = ModelRetryMiddleware(
    max_retries=2,
    on_failure="error",  # Re-raise exception instead of returning message
)
```

### 模型回退

当主模型失败时自动回退到备选模型。模型回退适用于以下场景：

* 构建能够处理模型故障的弹性代理。
* 通过回退到更便宜的模型来优化成本。
* 在 OpenAI、Anthropic 等提供商之间实现冗余。

**API 参考：** [`ModelFallbackMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/model_fallback/ModelFallbackMiddleware)

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelFallbackMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[],
    middleware=[
        ModelFallbackMiddleware(
            "gpt-5.4-mini",
            "claude-3-5-sonnet-20241022",
        ),
    ],
)
```

> 信息：观看这个[视频指南](https://www.youtube.com/watch?v=8rCRO0DUeIM)，演示 Model Fallback 中间件的行为。

#### 配置选项

- `first_model`（`string | BaseChatModel`，必填）：当主模型失败时首先尝试的回退模型。可以是模型标识符字符串（例如 `'openai:gpt-5.4-mini'`）或 `BaseChatModel` 实例。
- `*additional_models`（`string | BaseChatModel`）：如果前面的模型都失败，按顺序尝试的额外回退模型。

### 摘要

在接近令牌限制时自动总结对话历史，保留最近的消息，同时压缩较旧的上下文。摘要适用于以下场景：

* 超出上下文窗口的长时间对话。
* 具有大量历史的多轮对话。
* 需要保留完整对话上下文的应用。

> 注意：摘要是面向文本的上下文压缩。它不会调整大小、降采样或以其他方式压缩图像/音频/视频载荷。由 `keep` 保留的近期消息仍包含其原始多模态块，而被摘要的较旧多模态消息仅由生成的文本摘要表示。对于图像密集型应用，请将媒体存储在文件系统或对象存储中，并通过消息历史传递 URL 或文件引用。

**API 参考：** [`SummarizationMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/SummarizationMiddleware)

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[your_weather_tool, your_calculator_tool],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger=("tokens", 4000),
            keep=("messages", 20),
        ),
    ],
)
```

#### 配置选项

> 提示：下面展示的 `trigger` 和 `keep` 的 `fraction` 条件，在使用 `langchain>=1.1` 时依赖聊天模型的[配置数据](/oss/python/langchain/models#model-profiles)。如果数据不可用，请改用其他条件或手动指定：
>
> ```python
> from langchain.chat_models import init_chat_model
>
> custom_profile = {
>     "max_input_tokens": 100_000,
>     # ...
> }
> model = init_chat_model("gpt-5.5", profile=custom_profile)
> ```

- `model`（`string | BaseChatModel`，必填）：用于生成摘要的模型。可以是模型标识符字符串（例如 `'openai:gpt-5.4-mini'`）或 `BaseChatModel` 实例。更多信息参见 [`init_chat_model`](https://reference.langchain.com/python/langchain/chat_models/base/init_chat_model)。
- `trigger`（`ContextSize | TriggerClause | list[ContextSize | TriggerClause] | None`）：触发摘要的条件。可以是：
  - 单个 [`ContextSize`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/ContextSize) 元组（必须满足指定阈值）
  - 单个 [`TriggerClause`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/TriggerClause) 字典（必须满足所有指定阈值 — AND 逻辑）
  - 混合两种形式的列表（满足任意一项即可 — OR 逻辑）
  - 支持的阈值：
    - `fraction`（float）：模型上下文大小的比例（0-1）
    - `tokens`（int）：绝对令牌数
    - `messages`（int）：消息数
  - [`ContextSize`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/ContextSize) 元组精确表达一个阈值。[`TriggerClause`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/TriggerClause) 字典可以包含一个或多个阈值，例如 `{"tokens": 4000, "messages": 10}`，字典中的所有阈值都必须满足（AND）。
  - 每个 [`TriggerClause`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/TriggerClause) 字典必须至少指定一个阈值。如果未提供 `trigger`，摘要不会自动触发。
  - 更多信息参见 [`ContextSize`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/ContextSize) 和 [`TriggerClause`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/TriggerClause) 的 API 参考。
- `keep`（`ContextSize`，默认 `('messages', 20)`）：摘要后保留多少上下文。精确指定以下之一：
  - `fraction`（float）：保留模型上下文大小的比例（0-1）
  - `tokens`（int）：保留的绝对令牌数
  - `messages`（int）：保留的最近消息数
  - 更多信息参见 [`ContextSize`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/ContextSize) 的 API 参考。
- `token_counter`（`function`）：自定义令牌计数函数。默认基于字符计数。
- `summary_prompt`（`string`）：用于摘要的自定义提示模板。未指定时使用内置模板。模板应包含 `{messages}` 占位符，对话历史将插入其中。
- `trim_tokens_to_summarize`（`number`，默认 `4000`）：生成摘要时要包含的最大令牌数。在摘要之前，消息将被裁剪以符合此限制。
- `summary_prefix`（`string`，已弃用）：**已弃用：** 改用 `summary_prompt` 提供完整提示。
- `max_tokens_before_summary`（`number`，已弃用）：**已弃用：** 改用 `trigger: ("tokens", value)`。触发摘要的令牌阈值。
- `messages_to_keep`（`number`，已弃用）：**已弃用：** 改用 `keep: ("messages", value)`。要保留的最近消息数。

#### 完整示例

摘要中间件监视消息令牌数，并在达到阈值时自动总结较旧的消息。

**触发条件**控制摘要何时运行：

* 单个阈值在满足时触发
* 包含多个阈值的触发子句仅在所有阈值都满足时触发（AND 逻辑）
* 触发条件列表在满足任意一项时触发（OR 逻辑）
* 每个阈值可以使用 `fraction`（模型上下文大小比例）、`tokens`（绝对数量）或 `messages`（消息数量）

**保留条件**控制保留多少上下文（精确指定一项）：

* `fraction` - 保留模型上下文大小的比例
* `tokens` - 保留的绝对令牌数
* `messages` - 保留的最近消息数

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

# Single condition: trigger if tokens >= 4000
agent = create_agent(
    model="gpt-5.5",
    tools=[your_weather_tool, your_calculator_tool],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger=("tokens", 4000),
            keep=("messages", 20),
        ),
    ],
)

# Multiple conditions: trigger if number of tokens >= 3000 OR messages >= 6
agent2 = create_agent(
    model="gpt-5.5",
    tools=[your_weather_tool, your_calculator_tool],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger=[
                ("tokens", 3000),
                ("messages", 6),
            ],
            keep=("messages", 20),
        ),
    ],
)

# AND logic: trigger only when tokens >= 4000 AND messages >= 10
agent3 = create_agent(
    model="gpt-5.5",
    tools=[your_weather_tool, your_calculator_tool],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger={"tokens": 4000, "messages": 10},
            keep=("messages", 20),
        ),
    ],
)

# Combine AND and OR: trigger if (tokens >= 5000 AND messages >= 3)
# OR (tokens >= 3000 AND messages >= 6)
agent4 = create_agent(
    model="gpt-5.5",
    tools=[your_weather_tool, your_calculator_tool],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger=[
                {"tokens": 5000, "messages": 3},
                {"tokens": 3000, "messages": 6},
            ],
            keep=("messages", 20),
        ),
    ],
)

# Using fractional limits
agent5 = create_agent(
    model="gpt-5.5",
    tools=[your_weather_tool, your_calculator_tool],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger=("fraction", 0.8),
            keep=("fraction", 0.3),
        ),
    ],
)
```

### 人机协同

在工具执行之前暂停代理执行，等待人工批准、编辑或拒绝。 [人机协同](/oss/python/langchain/human-in-the-loop) 适用于以下场景：

* 需要人工批准的高风险操作（例如数据库写入、金融交易）。
* 必须有人工监督的合规工作流。
* 人工反馈引导代理的长时间对话。

**API 参考：** [`HumanInTheLoopMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/human_in_the_loop/HumanInTheLoopMiddleware)

> 警告：人机协同中间件需要一个[检查点](/oss/python/langgraph/checkpointers#checkpoints)来在中断期间维护状态。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver

def your_read_email_tool(email_id: str) -> str:
    """Mock function to read an email by its ID."""
    return f"Email content for ID: {email_id}"

def your_send_email_tool(recipient: str, subject: str, body: str) -> str:
    """Mock function to send an email."""
    return f"Email sent to {recipient} with subject '{subject}'"

agent = create_agent(
    model="gpt-5.5",
    tools=[your_read_email_tool, your_send_email_tool],
    checkpointer=InMemorySaver(),
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "your_send_email_tool": {
                    "allowed_decisions": ["approve", "edit", "reject"],
                },
                "your_read_email_tool": False,
            }
        ),
    ],
)
```

> 提示：完整的示例、配置选项和集成模式，参见[人机协同文档](/oss/python/langchain/human-in-the-loop)。

> 信息：观看这个[视频指南](https://www.youtube.com/watch?v=SpfT6-YAVPk)，演示 Human-in-the-loop 中间件的行为。

### 模型调用限制

限制模型调用次数以防止无限循环或过度成本。模型调用限制适用于以下场景：

* 防止失控的代理发出过多的 API 调用。
* 在生产部署中强制执行成本控制。
* 在特定的调用预算内测试代理行为。

**API 参考：** [`ModelCallLimitMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/model_call_limit/ModelCallLimitMiddleware)

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="gpt-5.5",
    checkpointer=InMemorySaver(),  # Required for thread limiting
    tools=[],
    middleware=[
        ModelCallLimitMiddleware(
            thread_limit=10,
            run_limit=5,
            exit_behavior="end",
        ),
    ],
)
```

> 信息：观看这个[视频指南](https://www.youtube.com/watch?v=nJEER0uaNkE)，演示 Model Call Limit 中间件的行为。

#### 配置选项

- `thread_limit`（`number`）：线程中所有运行的最大模型调用次数。默认无限制。
- `run_limit`（`number`）：单次调用的最大模型调用次数。默认无限制。
- `exit_behavior`（`string`，默认 `end`）：达到限制时的行为。选项：`'end'`（优雅终止）或 `'error'`（抛出异常）。

### 工具调用限制

通过限制工具调用次数来控制代理执行，可以全局限制所有工具，也可以针对特定工具。工具调用限制适用于以下场景：

* 防止对昂贵的外部 API 进行过度调用。
* 限制网络搜索或数据库查询。
* 对特定工具的用量强制执行速率限制。
* 防止失控的代理循环。

**API 参考：** [`ToolCallLimitMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/tool_call_limit/ToolCallLimitMiddleware)

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, database_tool],
    middleware=[
        # Global limit
        ToolCallLimitMiddleware(thread_limit=20, run_limit=10),
        # Tool-specific limit
        ToolCallLimitMiddleware(
            tool_name="search",
            thread_limit=5,
            run_limit=3,
        ),
    ],
)
```

> 信息：观看这个[视频指南](https://www.youtube.com/watch?v=6gYlaJJ8t0w)，演示 Tool Call Limit 中间件的行为。

#### 配置选项

- `tool_name`（`string`）：要限制的特定工具的名称。如果未提供，限制将**全局应用于所有工具**。
- `thread_limit`（`number`）：线程（对话）中所有运行的最大工具调用次数。在相同线程 ID 的多次调用之间持久保持。需要检查点来维护状态。`None` 表示没有线程限制。
- `run_limit`（`number`）：单次调用（一次用户消息 → 响应周期）的最大工具调用次数。每次新的用户消息都会重置。`None` 表示没有运行限制。
  - **注意：** `thread_limit` 和 `run_limit` 至少必须指定一个。
- `exit_behavior`（`string`，默认 `continue`）：达到限制时的行为：
  - `'continue'`（默认）— 用错误消息阻止超限的工具调用，让其他工具和模型继续。模型根据错误消息决定何时结束。
  - `'error'` — 抛出 `ToolCallLimitExceededError` 异常，立即停止执行。
  - `'end'` — 立即停止执行，并为超限的工具调用生成 `ToolMessage` 和 AI 消息。仅在限制单个工具时有效；如果其他工具有待处理的调用，则抛出 `NotImplementedError`。

#### 完整示例

使用以下方式指定限制：

* **线程限制** - 对话中所有运行的最大调用次数（需要检查点）
* **运行限制** - 单次调用的最大调用次数（每轮重置）

退出行为：

* `'continue'`（默认）— 用错误消息阻止超限调用，代理继续
* `'error'` — 立即抛出异常
* `'end'` — 用 ToolMessage + AI 消息停止（仅限单工具场景）

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware

global_limiter = ToolCallLimitMiddleware(thread_limit=20, run_limit=10)
search_limiter = ToolCallLimitMiddleware(tool_name="search", thread_limit=5, run_limit=3)
database_limiter = ToolCallLimitMiddleware(tool_name="query_database", thread_limit=10)
strict_limiter = ToolCallLimitMiddleware(tool_name="scrape_webpage", run_limit=2, exit_behavior="error")

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, database_tool, scraper_tool],
    middleware=[global_limiter, search_limiter, database_limiter, strict_limiter],
)
```

### PII 检测

使用可配置的策略检测和处理对话中的个人身份信息（PII）。PII 检测适用于以下场景：

* 有合规要求的医疗和金融应用。
* 需要净化日志的客户服务代理。
* 任何处理敏感用户数据的应用。

> 注意：使用 `apply_to_output=True` 时，`PIIMiddleware` 还会通过注册的流式转换器对流式传输的线上输出（文本增量、工具调用参数、工具输出和状态快照）进行脱敏。需要 `langchain>=1.3.2`。参见[在中间件上注册转换器](/oss/python/langchain/event-streaming#register-transformers-on-middleware)。

**API 参考：** [`PIIMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/pii/PIIMiddleware)

```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[],
    middleware=[
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        PIIMiddleware("credit_card", strategy="mask", apply_to_input=True),
    ],
)
```

#### 自定义 PII 类型

你可以通过提供 `detector` 参数来创建自定义 PII 类型。这允许你检测内置类型之外的、特定于你的用例的模式。

**创建自定义检测器的三种方式：**

1. **正则模式字符串** - 简单的模式匹配

2. **自定义函数** - 带有验证的复杂检测逻辑

```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware
import re

# Method 1: Regex pattern string
agent1 = create_agent(
    model="gpt-5.5",
    tools=[],
    middleware=[
        PIIMiddleware(
            "api_key",
            detector=r"sk-[a-zA-Z0-9]{32}",
            strategy="block",
        ),
    ],
)

# Method 2: Compiled regex pattern
agent2 = create_agent(
    model="gpt-5.5",
    tools=[],
    middleware=[
        PIIMiddleware(
            "phone_number",
            detector=re.compile(r"\+?\d{1,3}[\s.-]?\d{3,4}[\s.-]?\d{4}"),
            strategy="mask",
        ),
    ],
)

# Method 3: Custom detector function
def detect_ssn(content: str) -> list[dict[str, str | int]]:
    """Detect SSN with validation.

    Returns a list of dictionaries with 'text', 'start', and 'end' keys.
    """
    import re
    matches = []
    pattern = r"\d{3}-\d{2}-\d{4}"
    for match in re.finditer(pattern, content):
        ssn = match.group(0)
        # Validate: first 3 digits shouldn't be 000, 666, or 900-999
        first_three = int(ssn[:3])
        if first_three not in [0, 666] and not (900 <= first_three <= 999):
            matches.append({
                "text": ssn,
                "start": match.start(),
                "end": match.end(),
            })
    return matches

agent3 = create_agent(
    model="gpt-5.5",
    tools=[],
    middleware=[
        PIIMiddleware(
            "ssn",
            detector=detect_ssn,
            strategy="hash",
        ),
    ],
)
```

**自定义检测器函数签名：**

检测器函数必须接收一个字符串（内容）并返回匹配结果：

返回带有 `text`、`start` 和 `end` 键的字典列表：

```python
def detector(content: str) -> list[dict[str, str | int]]:
    return [
        {"text": "matched_text", "start": 0, "end": 12},
        # ... more matches
    ]
```

> 提示：对于自定义检测器：
>
> * 简单模式使用正则字符串
> * 需要标志（例如不区分大小写的匹配）时使用 RegExp 对象
> * 需要超出模式匹配的验证逻辑时使用自定义函数
> * 自定义函数让你完全控制检测逻辑，可以实现复杂的验证规则

#### 配置选项

- `pii_type`（`string`，必填）：要检测的 PII 类型。可以是内置类型（`email`、`credit_card`、`ip`、`mac_address`、`url`）或自定义类型名称。
- `strategy`（`string`，默认 `redact`）：如何处理检测到的 PII。选项：
  - `'block'` — 检测到时抛出异常
  - `'redact'` — 替换为 `[REDACTED_{PII_TYPE}]`
  - `'mask'` — 部分掩码（例如 `****-****-****-1234`）
  - `'hash'` — 替换为确定性哈希
- `detector`（`function | regex`）：自定义检测器函数或正则模式。如果未提供，则使用该 PII 类型的内置检测器。
- `apply_to_input`（`boolean`，默认 `True`）：在模型调用前检查用户消息。
- `apply_to_output`（`boolean`，默认 `False`）：在模型调用后检查 AI 消息。使用 `langchain>=1.3.2` 时，还会通过注册的流式转换器对流式传输的线上输出（文本增量、工具调用参数、工具输出、状态快照）进行脱敏。参见[事件流式输出](/oss/python/langchain/event-streaming#register-transformers-on-middleware)。
- `apply_to_tool_results`（`boolean`，默认 `False`）：执行后检查工具结果消息。

### 待办列表

为代理配备任务规划和跟踪能力，用于复杂的多步骤任务。待办列表适用于以下场景：

* 需要跨多个工具协调的复杂多步骤任务。
* 进度可见性很重要的长时间运行操作。

> 注意：此中间件会自动为代理提供一个 `write_todos` 工具和系统提示，以指导有效的任务规划。

**API 参考：** [`TodoListMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/todo/TodoListMiddleware)

```python
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[read_file, write_file, run_tests],
    middleware=[TodoListMiddleware()],
)
```

> 信息：观看这个[视频指南](https://www.youtube.com/watch?v=yTWocbVKQxw)，演示 To-do List 中间件的行为。

#### 配置选项

- `system_prompt`（`string`）：用于指导待办事项使用的自定义系统提示。未指定时使用内置提示。
- `tool_description`（`string`）：`write_todos` 工具的自定义描述。未指定时使用内置描述。

### LLM 工具选择器

在调用主模型之前使用 LLM 智能地选择相关工具。LLM 工具选择器适用于以下场景：

* 工具很多（10+）且大多数与每次查询无关的代理。
* 通过过滤不相关的工具来减少令牌使用。
* 提高模型的专注度和准确性。

该中间件使用结构化输出询问 LLM 哪些工具与当前查询最相关。结构化输出模式定义了可用的工具名称和描述。模型提供商通常会在幕后将此结构化输出信息添加到系统提示中。

**API 参考：** [`LLMToolSelectorMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/tool_selection/LLMToolSelectorMiddleware)

```python
from langchain.agents import create_agent
from langchain.agents.middleware import LLMToolSelectorMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[tool1, tool2, tool3, tool4, tool5, ...],
    middleware=[
        LLMToolSelectorMiddleware(
            model="gpt-5.4-mini",
            max_tools=3,
            always_include=["search"],
        ),
    ],
)
```

#### 配置选项

- `model`（`string | BaseChatModel`）：用于工具选择的模型。可以是模型标识符字符串（例如 `'openai:gpt-5.4-mini'`）或 `BaseChatModel` 实例。更多信息参见 [`init_chat_model`](https://reference.langchain.com/python/langchain/chat_models/base/init_chat_model)。
  - 默认为代理的主模型。
- `system_prompt`（`string`）：给选择模型的指令。未指定时使用内置提示。
- `max_tools`（`number`）：要选择的最大工具数。如果模型选择了更多，只使用前 max\_tools 个。未指定则无限制。
- `always_include`（`list[string]`）：无论选择结果如何都始终包含的工具名称。这些不计入 max\_tools 限制。

### 提供商工具搜索

将选定的工具延迟到模型提供商的服务器端工具搜索之后，让模型按需发现它们，而不是一开始就接收所有工具模式。提供商工具搜索适用于：

* 使用大量工具时减少上下文膨胀。
* 通过只浮现相关工具来提高工具选择准确性。

> 注意：需要支持服务器端工具搜索的模型：Anthropic（Claude Sonnet 4+/Opus 4+/Haiku 4.5+）或 OpenAI（gpt-5.5+）。其他提供商会抛出 `ValueError`。

**API 参考：** [`ProviderToolSearchMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/provider_tool_search/ProviderToolSearchMiddleware)

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ProviderToolSearchMiddleware

agent = create_agent(
    model="anthropic:claude-opus-4-8",
    tools=[get_weather, lookup_order],
    middleware=[
        ProviderToolSearchMiddleware(searchable_tools=["lookup_order"]),
    ],
)
```

#### 配置选项

- `searchable_tools`（`list[str | BaseTool]`）：要延迟到提供商工具搜索之后的工具，按名称或实例给出。延迟的工具在模型的搜索将其浮现之前会被扣留。使用 `extras={"defer_loading": True}` 构造的工具无论此选项如何都会被延迟；如果省略 `searchable_tools`，则只延迟这些预先标记的工具。

#### 完整示例

该中间件将 `searchable_tools` 中包含的所有工具选择性地加入延迟和搜索。工具也可以在构造时通过设置 `extras={"defer_loading": True}` 选择加入延迟。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ProviderToolSearchMiddleware
from langchain.tools import tool

# Marked `defer_loading` at construction, so it's deferred on its own —
# no need to list it in `searchable_tools`.
@tool(extras={"defer_loading": True})
def send_email(to: str) -> str:
    """Send an email."""
    return "sent"

agent = create_agent(
    model="anthropic:claude-opus-4-8",
    tools=[send_email],
    middleware=[ProviderToolSearchMiddleware()],
)
```

### Shell 工具

向代理暴露持久的 shell 会话用于执行命令。Shell 工具中间件适用于以下场景：

* 需要执行系统命令的代理
* 开发和部署自动化任务
* 测试和验证工作流
* 文件系统操作和脚本执行

> 警告：**安全考虑：** 使用适当的执行策略（`HostExecutionPolicy`、`DockerExecutionPolicy` 或 `CodexSandboxExecutionPolicy`）来匹配你的部署安全要求。

> 注意：**限制：** 持久 shell 会话目前无法与中断（人机协同）一起使用。我们预计未来会添加对此的支持。

**API 参考：** [`ShellToolMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/shell_tool/ShellToolMiddleware)

```python
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ShellToolMiddleware,
    HostExecutionPolicy,
)

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool],
    middleware=[
        ShellToolMiddleware(
            workspace_root="/workspace",
            execution_policy=HostExecutionPolicy(),
        ),
    ],
)
```

#### 配置选项

- `workspace_root`（`str | Path | None`）：shell 会话的基目录。如果省略，会在代理启动时创建一个临时目录，并在代理结束时删除。
- `startup_commands`（`tuple[str, ...] | list[str] | str | None`）：会话启动后按顺序执行的可选命令。
- `shutdown_commands`（`tuple[str, ...] | list[str] | str | None`）：会话关闭前执行的可选命令。
- `execution_policy`（`BaseExecutionPolicy | None`）：控制超时、输出限制和资源配置的执行策略。选项：
  - `HostExecutionPolicy` - 完全的主机访问（默认）；最适合代理已经在容器或 VM 内运行的受信任环境。
  - `DockerExecutionPolicy` - 为每次代理运行启动一个单独的 Docker 容器，提供更强的隔离。
  - `CodexSandboxExecutionPolicy` - 复用 Codex CLI 沙箱以获得额外的系统调用/文件系统限制。
- `redaction_rules`（`tuple[RedactionRule, ...] | list[RedactionRule] | None`）：可选的脱敏规则，在将命令输出返回给模型之前对其进行净化。
  - > 警告：脱敏规则在执行后应用，无法在使用 `HostExecutionPolicy` 时防止秘密或敏感数据的泄露。
- `tool_description`（`str | None`）：可选，覆盖注册的 shell 工具描述。
- `shell_command`（`Sequence[str] | str | None`）：可选的 shell 可执行文件（字符串）或用于启动持久会话的参数序列。默认为 `/bin/bash`。
- `env`（`Mapping[str, Any] | None`）：提供给 shell 会话的可选环境变量。在执行命令前，值会被强制转换为字符串。

#### 完整示例

该中间件提供一个单一的持久 shell 会话，代理可以用它按顺序执行命令。

**执行策略：**

* `HostExecutionPolicy`（默认）— 具有完全主机访问权限的原生执行
* `DockerExecutionPolicy` — 隔离的 Docker 容器执行
* `CodexSandboxExecutionPolicy` — 通过 Codex CLI 进行沙箱化执行

```python
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ShellToolMiddleware,
    HostExecutionPolicy,
    DockerExecutionPolicy,
    RedactionRule,
)

# Basic shell tool with host execution
agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool],
    middleware=[
        ShellToolMiddleware(
            workspace_root="/workspace",
            execution_policy=HostExecutionPolicy(),
        ),
    ],
)

# Docker isolation with startup commands
agent_docker = create_agent(
    model="gpt-5.5",
    tools=[],
    middleware=[
        ShellToolMiddleware(
            workspace_root="/workspace",
            startup_commands=["pip install requests", "export PYTHONPATH=/workspace"],
            execution_policy=DockerExecutionPolicy(
                image="python:3.11-slim",
                command_timeout=60.0,
            ),
        ),
    ],
)

# With output redaction (applied post execution)
agent_redacted = create_agent(
    model="gpt-5.5",
    tools=[],
    middleware=[
        ShellToolMiddleware(
            workspace_root="/workspace",
            redaction_rules=[
                RedactionRule(pii_type="api_key", detector=r"sk-[a-zA-Z0-9]{32}"),
            ],
        ),
    ],
)
```

### 文件系统中间件

上下文工程是构建有效代理的主要挑战。当使用返回可变长度结果的工具（例如 `web_search` 和 RAG）时尤其困难，因为较长的工具结果会迅速填满你的上下文窗口。

来自 [Deep Agents](/oss/python/deepagents/overview) 的 `FilesystemMiddleware` 提供了四个工具，用于与短期和长期记忆交互：

* `ls`：列出文件系统中的文件
* `read_file`：读取整个文件或文件中的一定行数
* `write_file`：向文件系统写入新文件
* `edit_file`：编辑文件系统中的现有文件

```python
from langchain.agents import create_agent
from deepagents.middleware.filesystem import FilesystemMiddleware

# FilesystemMiddleware is included by default in create_deep_agent
# You can customize it if building a custom agent
agent = create_agent(
    model="claude-sonnet-4-6",
    middleware=[
        FilesystemMiddleware(
            backend=None,  # Optional: custom backend (defaults to StateBackend)
            system_prompt="Write to the filesystem when...",  # Optional custom addition to the system prompt
            custom_tool_descriptions={
                "ls": "Use the ls tool when...",
                "read_file": "Use the read_file tool to..."
            },  # Optional: Custom descriptions for filesystem tools
            tools=["read_file", "ls", "glob", "grep"],  # Optional: Allowlist restricting which filesystem tools are exposed
        ),
    ],
)
```

#### 短期与长期文件系统

默认情况下，这些工具写入图形状态中的本地"文件系统"。要启用跨线程的持久存储，请配置一个 `CompositeBackend`，将特定路径（如 `/memories/`）路由到 `StoreBackend`。

```python
from langchain.agents import create_agent
from deepagents.middleware import FilesystemMiddleware
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

agent = create_agent(
    model="claude-sonnet-4-6",
    store=store,
    middleware=[
        FilesystemMiddleware(
            backend=CompositeBackend(
                default=StateBackend(),
                routes={"/memories/": StoreBackend()}
            ),
            custom_tool_descriptions={
                "ls": "Use the ls tool when...",
                "read_file": "Use the read_file tool to..."
            }  # Optional: Custom descriptions for filesystem tools
        ),
    ],
)
```

当你为 `/memories/` 配置带有 `StoreBackend` 的 `CompositeBackend` 时，任何以 **/memories/** 为前缀的文件都会保存到持久存储中，并在不同线程之间存续。没有此前缀的文件则保留在临时状态存储中。

### 子代理

将任务移交给子代理可以隔离上下文，保持主（监督者）代理的上下文窗口干净，同时仍然深入处理任务。

来自 [Deep Agents](/oss/python/deepagents/overview) 的子代理中间件允许你通过一个 `task` 工具提供子代理。

```python
from langchain.tools import tool
from langchain.agents import create_agent
from deepagents.middleware.subagents import SubAgentMiddleware

@tool
def get_weather(city: str) -> str:
    """Get the weather in a city."""
    return f"The weather in {city} is sunny."

agent = create_agent(
    model="claude-sonnet-4-6",
    middleware=[
        SubAgentMiddleware(
            default_model="claude-sonnet-4-6",
            default_tools=[],
            subagents=[
                {
                    "name": "weather",
                    "description": "This subagent can get weather in cities.",
                    "system_prompt": "Use the get_weather tool to get the weather in a city.",
                    "tools": [get_weather],
                    "model": "gpt-5.5",
                    "middleware": [],
                }
            ],
        )
    ],
)
```

子代理由**名称**、**描述**、**系统提示**和**工具**定义。你还可以为子代理提供自定义**模型**，或额外的**中间件**。当你希望给子代理一个额外的状态键与主代理共享时，这尤其有用。

对于更复杂的用例，你还可以提供自己预构建的 LangGraph 图作为子代理。

```python
from langchain.agents import create_agent
from deepagents.middleware.subagents import SubAgentMiddleware
from deepagents import CompiledSubAgent
from langgraph.graph import StateGraph

# Create a custom LangGraph graph
def create_weather_graph():
    workflow = StateGraph(...)
    # Build your custom graph
    return workflow.compile()

weather_graph = create_weather_graph()

# Wrap it in a CompiledSubAgent
weather_subagent = CompiledSubAgent(
    name="weather",
    description="This subagent can get weather in cities.",
    runnable=weather_graph
)

agent = create_agent(
    model="claude-sonnet-4-6",
    middleware=[
        SubAgentMiddleware(
            default_model="claude-sonnet-4-6",
            default_tools=[],
            subagents=[weather_subagent],
        )
    ],
)
```

除了任何用户定义的子代理之外，主代理随时可以访问一个 `general-purpose` 子代理。该子代理拥有与主代理相同的指令以及主代理可以访问的所有工具。`general-purpose` 子代理的主要目的是上下文隔离——主代理可以将复杂任务委托给该子代理，并得到一个简洁的答案，而不会被中间工具调用的信息淹没。

### 评分标准评分

> 注意：`RubricMiddleware` 需要 `deepagents>=0.6.5`。它处于[**beta**](/oss/python/versioning)阶段；API 未来可能发生变化。

有些任务有明确的"完成"定义，而代理无法在第一次尝试时可靠地命中。`RubricMiddleware` 让你把*完成应该是什么样子*声明为评分标准，并让代理自我评估、迭代，直到满足评分标准或达到最大迭代上限。

**API 参考：** [`RubricMiddleware`](https://reference.langchain.com/python/deepagents/middleware/rubric/RubricMiddleware)

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

**Google**
```python
from deepagents import RubricMiddleware, create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver

agent = create_deep_agent(
    model="google_genai:gemini-3.6-flash",
    middleware=[
        RubricMiddleware(
            model="anthropic:claude-haiku-4-5",
            max_iterations=3,
        ),
    ],
    checkpointer=InMemorySaver(),
)
```

完整的配置选项、流式输出事件以及完整的代码生成示例，参见[评分标准](/oss/python/deepagents/rubric)。

### 文件搜索

提供针对文件系统的 Glob 和 Grep 搜索工具。文件搜索中间件适用于以下场景：

* 代码探索和分析
* 按名称模式查找文件
* 使用正则表达式搜索代码内容
* 需要文件发现功能的大型代码库

**API 参考：** [`FilesystemFileSearchMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/file_search/FilesystemFileSearchMiddleware)

```python
from langchain.agents import create_agent
from langchain.agents.middleware import FilesystemFileSearchMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[],
    middleware=[
        FilesystemFileSearchMiddleware(
            root_path="/workspace",
            use_ripgrep=True,
        ),
    ],
)
```

#### 配置选项

- `root_path`（`str`，必填）：要搜索的根目录。所有文件操作都相对于此路径。
- `use_ripgrep`（`bool`，默认 `True`）：是否使用 ripgrep 进行搜索。如果 ripgrep 不可用，则回退到 Python 正则表达式。
- `max_file_size_mb`（`int`，默认 `10`）：要搜索的最大文件大小（MB）。大于此大小的文件会被跳过。

#### 完整示例

该中间件为代理添加两个搜索工具：

**Glob 工具** - 快速文件模式匹配：

* 支持 `**/*.py`、`src/**/*.ts` 等模式
* 返回按修改时间排序的匹配文件路径

**Grep 工具** - 带正则表达式的内容搜索：

* 完整的正则表达式语法支持
* 使用 `include` 参数按文件模式过滤
* 三种输出模式：`files_with_matches`、`content`、`count`

```python
from langchain.agents import create_agent
from langchain.agents.middleware import FilesystemFileSearchMiddleware
from langchain.messages import HumanMessage

agent = create_agent(
    model="gpt-5.5",
    tools=[],
    middleware=[
        FilesystemFileSearchMiddleware(
            root_path="/workspace",
            use_ripgrep=True,
            max_file_size_mb=10,
        ),
    ],
)

# Agent can now use glob_search and grep_search tools
result = agent.invoke({
    "messages": [HumanMessage("Find all Python files containing 'async def'")]
})

# The agent will use:
# 1. glob_search(pattern="**/*.py") to find Python files
# 2. grep_search(pattern="async def", include="*.py") to find async functions
```

### 上下文编辑

在达到令牌限制时，通过清除较旧的工具调用输出来管理对话上下文，同时保留最近的结果。这有助于在具有大量工具调用的长对话中保持上下文窗口可管理。上下文编辑适用于以下场景：

* 具有许多工具调用、超出令牌限制的长对话
* 通过移除不再相关的较旧工具输出来降低令牌成本
* 仅在上下文中保留最近的 N 个工具结果

**API 参考：** [`ContextEditingMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/context_editing/ContextEditingMiddleware)、[`ClearToolUsesEdit`](https://reference.langchain.com/python/langchain/agents/middleware/context_editing/ClearToolUsesEdit)

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ContextEditingMiddleware, ClearToolUsesEdit

agent = create_agent(
    model="gpt-5.5",
    tools=[],
    middleware=[
        ContextEditingMiddleware(
            edits=[
                ClearToolUsesEdit(
                    trigger=100000,
                    keep=3,
                ),
            ],
        ),
    ],
)
```

#### 配置选项

- `edits`（`list[ContextEdit]`，默认 `[ClearToolUsesEdit()]`）：要应用的 [`ContextEdit`](https://reference.langchain.com/python/langchain/agents/middleware/context_editing/ContextEdit) 策略列表。
- `token_count_method`（`string`，默认 `approximate`）：令牌计数方法。选项：`'approximate'` 或 `'model'`。

**[`ClearToolUsesEdit`](https://reference.langchain.com/python/langchain/agents/middleware/context_editing/ClearToolUsesEdit) 选项：**

- `trigger`（`number`，默认 `100000`）：触发编辑的令牌数。当对话超过此令牌数时，较旧的工具输出将被清除。
- `clear_at_least`（`number`，默认 `0`）：编辑运行时至少要回收的最小令牌数。如果设置为 0，则按需清除尽可能多。
- `keep`（`number`，默认 `3`）：必须保留的最近工具结果数。这些永远不会被清除。
- `clear_tool_inputs`（`boolean`，默认 `False`）：是否清除 AI 消息上发起调用的工具参数。为 `True` 时，工具调用参数会被替换为空对象。
- `exclude_tools`（`list[string]`，默认 `()`）：要从清除中排除的工具名称列表。这些工具的输出永远不会被清除。
- `placeholder`（`string`，默认 `[cleared]`）：为被清除的工具输出插入的占位文本。这会替换原始工具消息内容。

#### 完整示例

该中间件在达到令牌限制时应用上下文编辑策略。最常见的策略是 `ClearToolUsesEdit`，它清除较旧的工具结果，同时保留较新的结果。

**工作原理：**

1. 监视对话中的令牌数
2. 达到阈值时，清除较旧的工具输出
3. 保留最近的 N 个工具结果
4. 可选地保留工具调用参数作为上下文

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ContextEditingMiddleware, ClearToolUsesEdit

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, your_calculator_tool, database_tool],
    middleware=[
        ContextEditingMiddleware(
            edits=[
                ClearToolUsesEdit(
                    trigger=2000,
                    keep=3,
                    clear_tool_inputs=False,
                    exclude_tools=[],
                    placeholder="[cleared]",
                ),
            ],
        ),
      ],
  )
```

### LLM 工具模拟器

使用 LLM 模拟工具执行，用 AI 生成的响应替换实际的工具调用，用于测试目的。LLM 工具模拟器适用于以下场景：

* 在不执行真实工具的情况下测试代理行为。
* 在外部工具不可用或昂贵时开发代理。
* 在实现实际工具之前对代理工作流进行原型设计。

**API 参考：** [`LLMToolEmulator`](https://reference.langchain.com/python/langchain/agents/middleware/tool_emulator/LLMToolEmulator)

```python
from langchain.agents import create_agent
from langchain.agents.middleware import LLMToolEmulator

agent = create_agent(
    model="gpt-5.5",
    tools=[get_weather, search_database, send_email],
    middleware=[
        LLMToolEmulator(),  # Emulate all tools
    ],
)
```

#### 配置选项

- `tools`（`list[str | BaseTool]`）：要模拟的工具名称（str）或 BaseTool 实例列表。如果为 `None`（默认），则模拟**所有**工具。如果为空列表 `[]`，则不模拟任何工具。如果为带工具名称/实例的数组，则只模拟这些工具。
- `model`（`string | BaseChatModel`）：用于生成模拟工具响应的模型。可以是模型标识符字符串（例如 `'google_genai:gemini-3.6-flash'`）或 `BaseChatModel` 实例。未指定时默认为代理的模型。更多信息参见 [`init_chat_model`](https://reference.langchain.com/python/langchain/chat_models/base/init_chat_model)。

#### 完整示例

该中间件使用 LLM 为工具调用生成合理的响应，而不是执行实际工具。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import LLMToolEmulator
from langchain.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    return f"Weather in {location}"

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    return "Email sent"

# Emulate all tools (default behavior)
agent = create_agent(
    model="gpt-5.5",
    tools=[get_weather, send_email],
    middleware=[LLMToolEmulator()],
)

# Emulate specific tools only
agent2 = create_agent(
    model="gpt-5.5",
    tools=[get_weather, send_email],
    middleware=[LLMToolEmulator(tools=["get_weather"])],
)

# Use custom model for emulation
agent4 = create_agent(
    model="gpt-5.5",
    tools=[get_weather, send_email],
    middleware=[LLMToolEmulator(model="claude-sonnet-4-6")],
)
```

## 提供商专用中间件

这些中间件针对特定的 LLM 提供商进行了优化。完整详情和示例参见各提供商的文档。

* **Anthropic**（[/oss/python/integrations/middleware/anthropic](/oss/python/integrations/middleware/anthropic)）：面向 Claude 模型的提示缓存、bash 工具、文本编辑器、记忆和文件搜索中间件。
* **AWS**（[/oss/python/integrations/middleware/aws](/oss/python/integrations/middleware/aws)）：面向 Amazon Bedrock 模型的提示缓存中间件。
* **OpenAI**（[/oss/python/integrations/middleware/openai](/oss/python/integrations/middleware/openai)）：面向 OpenAI 模型的内容审核中间件。

---

# 自定义中间件

通过实现钩子在代理执行流的特定点运行，来构建自定义中间件。

## 钩子

中间件提供两种风格的钩子来拦截代理执行：

* **节点式钩子**（[#node-style-hooks](#node-style-hooks)）：在特定的执行点按顺序运行。
* **包裹式钩子**（[#wrap-style-hooks](#wrap-style-hooks)）：围绕每次模型或工具调用运行。

### 节点式钩子

在特定的执行点按顺序运行。用于日志记录、验证和状态更新。

选择你的中间件需要的钩子。你可以在节点式钩子和包裹式钩子之间选择。

**节点式钩子**在特定的执行点运行：

| 钩子           | 运行时机                                |
| -------------- | ------------------------------------------- |
| `before_agent` | 代理启动之前（每次调用一次）   |
| `before_model` | 每次模型调用之前                      |
| `after_model`  | 每次模型响应之后                   |
| `after_agent`  | 代理完成后（每次调用一次） |

**包裹式钩子**围绕每次调用运行，让你控制执行：

| 钩子              | 运行时机           |
| ----------------- | ---------------------- |
| `wrap_model_call` | 围绕每次模型调用 |
| `wrap_tool_call`  | 围绕每次工具调用  |

**示例：**

<Tabs>
  <Tab title="Decorator">
    ```python
    from langchain.agents.middleware import before_model, after_model, AgentState
    from langchain.messages import AIMessage
    from langgraph.runtime import Runtime
    from typing import Any

    @before_model(can_jump_to=["end"])
    def check_message_limit(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        if len(state["messages"]) >= 50:
            return {
                "messages": [AIMessage("Conversation limit reached.")],
                "jump_to": "end"
            }
        return None

    @after_model
    def log_response(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        print(f"Model returned: {state['messages'][-1].content}")
        return None
    ```
  </Tab>

  <Tab title="Class">
    ```python
    from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
    from langchain.messages import AIMessage
    from langgraph.runtime import Runtime
    from typing import Any

    class MessageLimitMiddleware(AgentMiddleware):
        def __init__(self, max_messages: int = 50):
            super().__init__()
            self.max_messages = max_messages

        @hook_config(can_jump_to=["end"])
        def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
            if len(state["messages"]) >= self.max_messages:
                return {
                    "messages": [AIMessage("Conversation limit reached.")],
                    "jump_to": "end"
                }
            return None

        def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
            print(f"Model returned: {state['messages'][-1].content}")
            return None
    ```
  </Tab>
</Tabs>

### 包裹式钩子

拦截执行并控制处理器的调用时机。用于重试、缓存和转换。

你决定处理器被调用零次（短路）、一次（正常流程）还是多次（重试逻辑）。

**可用钩子：**

* `wrap_model_call` - 围绕每次模型调用
* `wrap_tool_call` - 围绕每次工具调用

**示例：**

<Tabs>
  <Tab title="Decorator">
    ```python
    from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
    from typing import Callable

    @wrap_model_call
    def retry_model(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        for attempt in range(3):
            try:
                return handler(request)
            except Exception as e:
                if attempt == 2:
                    raise
                print(f"Retry {attempt + 1}/3 after error: {e}")
    ```
  </Tab>

  <Tab title="Class">
    ```python
    from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
    from typing import Callable

    class RetryMiddleware(AgentMiddleware):
        def __init__(self, max_retries: int = 3):
            super().__init__()
            self.max_retries = max_retries

        def wrap_model_call(
            self,
            request: ModelRequest,
            handler: Callable[[ModelRequest], ModelResponse],
        ) -> ModelResponse:
            for attempt in range(self.max_retries):
                try:
                    return handler(request)
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise
                    print(f"Retry {attempt + 1}/{self.max_retries} after error: {e}")
    ```
  </Tab>
</Tabs>

## 状态更新

节点式钩子和包裹式钩子都可以更新代理状态。机制不同：

* **节点式钩子**（`before_agent`、`before_model`、`after_model`、`after_agent`）：直接返回一个字典。该字典使用图的 reducer 应用到代理状态上。
* **包裹式钩子**（`wrap_model_call`、`wrap_tool_call`）：对于模型调用，返回带有 [`Command`](https://reference.langchain.com/python/langgraph/types/Command) 的 [`ExtendedModelResponse`](https://reference.langchain.com/python/langchain/agents/middleware/types/ExtendedModelResponse)，以在模型响应旁边注入状态更新。对于工具调用，直接返回 [`Command`](https://reference.langchain.com/python/langgraph/types/Command)。当你需要基于模型或工具调用期间运行的逻辑来跟踪或更新状态时使用这些，例如摘要触发点、用量元数据或从请求/响应计算的自定义字段。

### 节点式钩子

从节点式钩子返回一个字典以合并更新到代理状态。字典键映射到状态字段。

```python
from langchain.agents.middleware import after_model, AgentState
from langgraph.runtime import Runtime
from typing import Any
from typing_extensions import NotRequired

class TrackingState(AgentState):
    model_call_count: NotRequired[int]

@after_model(state_schema=TrackingState)
def increment_after_model(state: TrackingState, runtime: Runtime) -> dict[str, Any] | None:
    return {"model_call_count": state.get("model_call_count", 0) + 1}
```

### 包裹式钩子

从 `wrap_model_call` 返回带有 [`Command`](https://reference.langchain.com/python/langgraph/types/Command) 的 [`ExtendedModelResponse`](https://reference.langchain.com/python/langchain/agents/middleware/types/ExtendedModelResponse)，以从模型调用层注入状态更新：

```python
from typing import Callable
from langchain.agents.middleware import (
    wrap_model_call,
    ModelRequest,
    ModelResponse,
    AgentState,
    ExtendedModelResponse
)
from langgraph.types import Command
from typing_extensions import NotRequired

class UsageTrackingState(AgentState):
    """Agent state with token usage tracking."""

    last_model_call_tokens: NotRequired[int]

@wrap_model_call(state_schema=UsageTrackingState)
def track_usage(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ExtendedModelResponse:
    response = handler(request)
    return ExtendedModelResponse(
        model_response=response,
        command=Command(update={"last_model_call_tokens": 150}),
    )
```

[`Command`](https://reference.langchain.com/python/langgraph/types/Command) 流经图的 reducer，因此更新会被正确应用，消息是累加的，而不是替换现有状态。

#### 与多个中间件组合

当多个中间件层返回 `ExtendedModelResponse` 时，它们的命令会组合：

* **命令通过 reducer 应用：** 每个 `Command` 成为一次独立的状态更新。对于消息，这意味着它们是累加的。
* **冲突时外层获胜：** 对于非 reducer 状态字段，命令按内层到外层的顺序应用。在冲突的键上，最外层中间件的值优先。
* **重试安全：** 如果外层中间件实现了可能导致再次调用 `handler()` 的逻辑（例如重试逻辑），则早期调用的命令会被丢弃。

```python
from typing import Annotated, Callable

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ExtendedModelResponse,
    ModelRequest,
    ModelResponse,
)
from langchain.messages import SystemMessage
from langgraph.types import Command
from typing_extensions import NotRequired

def _last_wins(_a: str, b: str) -> str:
    """Reducer: last writer wins (outer overwrites inner)."""
    return b

class CustomMiddlewareState(AgentState):
    """Agent state: trace_layer uses last-wins (outer wins), messages use additive reducer."""

    # Non-reducer field with last-wins: both middleware write; outermost value wins
    trace_layer: NotRequired[Annotated[str, _last_wins]]

class OuterMiddleware(AgentMiddleware):
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ExtendedModelResponse:
        response = handler(request)
        return ExtendedModelResponse(
            model_response=response,
            command=Command(update={
                "trace_layer": "outer",
                "messages": [SystemMessage(content="[Outer ran]")],
            }),
        )

class InnerMiddleware(AgentMiddleware):
    """Adds trace_layer and message. Outer adds to same keys; trace_layer: outer wins, messages: additive."""

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ):
        response = handler(request)
        return ExtendedModelResponse(
            model_response=response,
            command=Command(update={
                "trace_layer": "inner",
                "messages": [SystemMessage(content="[Inner ran]")],
            }),
        )
```

## 创建中间件

你可以用两种方式创建中间件：

* **基于装饰器的中间件**（[#decorator-based-middleware](#decorator-based-middleware)）：对于单钩子中间件快速简单。使用装饰器包装单个函数。
* **基于类的中间件**（[#class-based-middleware](#class-based-middleware)）：对于具有多个钩子或配置的复杂中间件更强大。

### 基于装饰器的中间件

对于单钩子中间件快速简单。使用装饰器包装单个函数。

**可用装饰器：**

**节点式：**

* [`@before_agent`](https://reference.langchain.com/python/langchain/agents/middleware/types/before_agent) - 在代理启动前运行（每次调用一次）
* [`@before_model`](https://reference.langchain.com/python/langchain/agents/middleware/types/before_model) - 在每次模型调用前运行
* [`@after_model`](https://reference.langchain.com/python/langchain/agents/middleware/types/after_model) - 在每次模型响应后运行
* [`@after_agent`](https://reference.langchain.com/python/langchain/agents/middleware/types/after_agent) - 在代理完成后运行（每次调用一次）

**包裹式：**

* [`@wrap_model_call`](https://reference.langchain.com/python/langchain/agents/middleware/types/wrap_model_call) - 用自定义逻辑包装每次模型调用
* [`@wrap_tool_call`](https://reference.langchain.com/python/langchain/agents/middleware/types/wrap_tool_call) - 用自定义逻辑包装每次工具调用

**便捷：**

* [`@dynamic_prompt`](https://reference.langchain.com/python/langchain/agents/middleware/types/dynamic_prompt) - 生成动态系统提示

**示例：**

```python
from langchain.agents.middleware import (
    before_model,
    wrap_model_call,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain.agents import create_agent
from langgraph.runtime import Runtime
from typing import Any, Callable

@before_model
def log_before_model(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    print(f"About to call model with {len(state['messages'])} messages")
    return None

@wrap_model_call
def retry_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    for attempt in range(3):
        try:
            return handler(request)
        except Exception as e:
            if attempt == 2:
                raise
            print(f"Retry {attempt + 1}/3 after error: {e}")

agent = create_agent(
    model="gpt-5.5",
    middleware=[log_before_model, retry_model],
    tools=[...],
)
```

**何时使用装饰器：**

* 只需要单个钩子
* 没有复杂配置
* 快速原型设计

### 基于类的中间件

对于具有多个钩子或配置的复杂中间件更强大。当你需要为同一钩子定义同步和异步实现，或者想在单个中间件中组合多个钩子时，使用类。

一个 `AgentMiddleware` 子类可以声明三个类属性，代理工厂会在编译时拾取：

* `state_schema` — 用自定义字段扩展代理状态。参见[自定义状态模式](#custom-state-schema)。
* `tools` — 注册随中间件附带的额外工具（例如待办列表中间件上的 `write_todos`）。
* `transformers` — 注册作用域感知的流式转换器工厂。参见[自定义流式转换器](#custom-stream-transformers)。

**示例：**

```python
from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langgraph.runtime import Runtime
from typing import Any, Callable

class LoggingMiddleware(AgentMiddleware):
    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        print(f"About to call model with {len(state['messages'])} messages")
        return None

    def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        print(f"Model returned: {state['messages'][-1].content}")
        return None

    async def abefore_model(
        self, state: AgentState, runtime: Runtime
    ) -> dict[str, Any] | None:
        # Async version of before_model
        return None

    async def aafter_model(
        self, state: AgentState, runtime: Runtime
    ) -> dict[str, Any] | None:
        # Async version of after_model
        print(f"Model returned: {state['messages'][-1].content}")
        return None

agent = create_agent(
    model="gpt-5.5",
    middleware=[LoggingMiddleware()],
    tools=[...],
)
```

**何时使用类：**

* 为同一钩子定义同步和异步实现
* 单个中间件中需要多个钩子
* 需要复杂配置（例如可配置的阈值、自定义模型）
* 在项目之间复用，带初始化时配置

## 自定义状态模式

如果你的中间件需要在钩子之间跟踪状态，中间件可以用自定义属性扩展代理的状态。这使中间件能够：

* **跨执行跟踪状态**：维护在代理的整个执行生命周期中持续存在的计数器、标志或其他值
* **在钩子之间共享数据**：将信息从 `before_model` 传递到 `after_model`，或在不同的中间件实例之间传递
* **实现横切关注点**：添加速率限制、用量跟踪、用户上下文或审计日志等功能，而无需修改核心代理逻辑
* **做出条件决策**：使用累积的状态来决定是否继续执行、跳转到不同节点或动态修改行为

<Tabs>
  <Tab title="Decorator">
    ```python
    from langchain.agents import create_agent
    from langchain.messages import HumanMessage
    from langchain.agents.middleware import AgentState, before_model, after_model
    from typing_extensions import NotRequired
    from typing import Any
    from langgraph.runtime import Runtime

    class CustomState(AgentState):
        model_call_count: NotRequired[int]
        user_id: NotRequired[str]

    @before_model(state_schema=CustomState, can_jump_to=["end"])
    def check_call_limit(state: CustomState, runtime: Runtime) -> dict[str, Any] | None:
        count = state.get("model_call_count", 0)
        if count > 10:
            return {"jump_to": "end"}
        return None

    @after_model(state_schema=CustomState)
    def increment_counter(state: CustomState, runtime: Runtime) -> dict[str, Any] | None:
        return {"model_call_count": state.get("model_call_count", 0) + 1}

    agent = create_agent(
        model="gpt-5.5",
        middleware=[check_call_limit, increment_counter],
        tools=[],
    )

    # Invoke with custom state
    result = agent.invoke({
        "messages": [HumanMessage("Hello")],
        "model_call_count": 0,
        "user_id": "user-123",
    })
    ```
  </Tab>

  <Tab title="Class">
    ```python
    from langchain.agents import create_agent
    from langchain.messages import HumanMessage
    from langchain.agents.middleware import AgentState, AgentMiddleware
    from typing_extensions import NotRequired
    from typing import Any

    class CustomState(AgentState):
        model_call_count: NotRequired[int]
        user_id: NotRequired[str]

    class CallCounterMiddleware(AgentMiddleware[CustomState]):
        state_schema = CustomState

        def before_model(self, state: CustomState, runtime) -> dict[str, Any] | None:
            count = state.get("model_call_count", 0)
            if count > 10:
                return {"jump_to": "end"}
            return None

        def after_model(self, state: CustomState, runtime) -> dict[str, Any] | None:
            return {"model_call_count": state.get("model_call_count", 0) + 1}

    agent = create_agent(
        model="gpt-5.5",
        middleware=[CallCounterMiddleware()],
        tools=[],
    )

    # Invoke with custom state
    result = agent.invoke({
        "messages": [HumanMessage("Hello")],
        "model_call_count": 0,
        "user_id": "user-123",
    })
    ```
  </Tab>
</Tabs>

## 自定义流式转换器

> 注意：中间件注册的转换器需要 `langchain>=1.3.2`。

中间件可以注册流式转换器工厂，将实时代理流中的事件投影到类型化的扩展通道上。这对于浮现计数器、旁路通道工件、部分输出或线上级别的脱敏很有用，而无需耦合到框架的内置投影。

在编译时，中间件注册的工厂会与调用者直接传给代理工厂的任何内容合并。[最终排序规则](/oss/python/langchain/event-streaming#register-transformers-on-middleware)将内置的 `ToolCallTransformer` 保持在最前面，并让调用者提供的条目落在最后。

将 `transformers` 类属性设置为工厂可调用对象的元组。每个工厂的形式为 `Callable[[tuple[str, ...]], StreamTransformer]`，并以 `factory(scope)` 方式调用，其中 `scope` 是 mini-mux 作用域元组（`()` 表示根，非空表示子图）；每次调用返回一个新的转换器，以保持每个子图隔离。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware

class ToolActivityMiddleware(AgentMiddleware):
    transformers = (ToolActivityTransformer,)

agent = create_agent(
    model="gpt-5-nano",
    tools=[...],
    middleware=[ToolActivityMiddleware()],
)
```

完整的排序规则和 PII 脱敏示例，参见[在中间件上注册转换器](/oss/python/langchain/event-streaming#register-transformers-on-middleware)。

## 执行顺序

使用多个中间件时，要了解它们如何执行：

```python
agent = create_agent(
    model="gpt-5.5",
    middleware=[middleware1, middleware2, middleware3],
    tools=[...],
)
```

#### 执行流程

**Before 钩子按顺序运行：**

1. `middleware1.before_agent()`
2. `middleware2.before_agent()`
3. `middleware3.before_agent()`

**代理循环开始**

4. `middleware1.before_model()`
5. `middleware2.before_model()`
6. `middleware3.before_model()`

**Wrap 钩子像函数调用一样嵌套：**

7. `middleware1.wrap_model_call()` → `middleware2.wrap_model_call()` → `middleware3.wrap_model_call()` → model

**After 钩子按相反顺序运行：**

8. `middleware3.after_model()`
9. `middleware2.after_model()`
10. `middleware1.after_model()`

**代理循环结束**

11. `middleware3.after_agent()`
12. `middleware2.after_agent()`
13. `middleware1.after_agent()`

**关键规则：**

* `before_*` 钩子：从第一个到最后一个
* `after_*` 钩子：从最后一个到第一个（反向）
* `wrap_*` 钩子：嵌套（第一个中间件包裹所有其他）

## 代理跳转

要从中间件提前退出，返回一个带 `jump_to` 的字典：

**可用跳转目标：**

* `'end'`：跳到代理执行的结尾（或第一个 `after_agent` 钩子）
* `'tools'`：跳到工具节点
* `'model'`：跳到模型节点（或第一个 `before_model` 钩子）

<Tabs>
  <Tab title="Decorator">
    ```python
    from langchain.agents.middleware import after_model, hook_config, AgentState
    from langchain.messages import AIMessage
    from langgraph.runtime import Runtime
    from typing import Any

    @after_model
    @hook_config(can_jump_to=["end"])
    def check_for_blocked(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        last_message = state["messages"][-1]
        if "BLOCKED" in last_message.content:
            return {
                "messages": [AIMessage("I cannot respond to that request.")],
                "jump_to": "end"
            }
        return None
    ```
  </Tab>

  <Tab title="Class">
    ```python
    from langchain.agents.middleware import AgentMiddleware, hook_config, AgentState
    from langchain.messages import AIMessage
    from langgraph.runtime import Runtime
    from typing import Any

    class BlockedContentMiddleware(AgentMiddleware):
        @hook_config(can_jump_to=["end"])
        def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
            last_message = state["messages"][-1]
            if "BLOCKED" in last_message.content:
                return {
                    "messages": [AIMessage("I cannot respond to that request.")],
                    "jump_to": "end"
                }
            return None
    ```
  </Tab>
</Tabs>

## 配置追踪

> 注意：需要 `langchain>=1.3.15`。

中间件钩子跨度（span）默认会追踪其输入和输出。设置一个 `trace_policy` 来塑造它们记录的内容。`TracePolicy` 接受可调用对象，例如 `process_inputs` 和 `process_outputs`，它们会转换被追踪的值；`omit_payload` 会完全丢弃它。当完整消息历史对中间件的功能没有信息量时，这可以作为优化手段。

要省略中间件追踪中的输入载荷：

```python
from langchain.agents.middleware import AgentMiddleware, TracePolicy, omit_payload

class MyMiddleware(AgentMiddleware):
    trace_policy = TracePolicy(process_inputs=omit_payload)
```

要为所有中间件应用策略，配置一个全局默认值：

```python
from langchain.agents.middleware import configure_trace_policy, TracePolicy, omit_payload

configure_trace_policy(TracePolicy(process_inputs=omit_payload))  # pass None to clear
```

中间件自身的 `trace_policy` 会覆盖全局默认值。

## 最佳实践

1. 保持中间件专注——每个中间件只做好一件事
2. 优雅地处理错误——不要让中间件错误使代理崩溃
3. **使用适当的钩子类型**：
   * 顺序逻辑（日志、验证）使用节点式
   * 控制流（重试、回退、缓存）使用包裹式
4. 清晰地记录任何自定义状态属性
5. 在集成之前独立地单元测试中间件
6. 考虑执行顺序——将关键中间件放在列表前面
7. 尽可能使用内置中间件

## 示例

### 动态提示

在每次模型调用之前动态修改系统提示，以注入上下文、用户特定指令或其他信息。这是最常见的中间件用例之一。

使用 `ModelRequest` 上的 `system_message` 字段来读取和修改系统提示。它包含一个 [`SystemMessage`](https://reference.langchain.com/python/langchain-core/messages/system/SystemMessage) 对象（即使代理是用字符串 `system_prompt` 创建的）。

<Tabs>
  <Tab title="Decorator">
    ```python
    from collections.abc import Callable

    from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
    from langchain.messages import SystemMessage

    @wrap_model_call
    def add_context(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": "Additional context."}
        ]
        new_system_message = SystemMessage(content=new_content)
        return handler(request.override(system_message=new_system_message))
    ```
  </Tab>

  <Tab title="Class">
    ```python
    from collections.abc import Callable

    from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse

    class ContextMiddleware(AgentMiddleware):
        def wrap_model_call(
            self,
            request: ModelRequest,
            handler: Callable[[ModelRequest], ModelResponse],
        ) -> ModelResponse:
            new_content = list(request.system_message.content_blocks) + [
                {"type": "text", "text": "Additional context."}
            ]
            new_system_message = SystemMessage(content=new_content)
            return handler(request.override(system_message=new_system_message))
    ```
  </Tab>
</Tabs>

> 注意：
> * `ModelRequest.system_message` 始终是一个 [`SystemMessage`](https://reference.langchain.com/python/langchain-core/messages/system/SystemMessage) 对象，即使代理是用 `system_prompt="string"` 创建的
> * 使用 `SystemMessage.content_blocks` 以块列表的形式访问内容，无论原始内容是字符串还是列表
> * 修改系统消息时，使用 `content_blocks` 并追加新块以保留现有结构
> * 你可以将 [`SystemMessage`](https://reference.langchain.com/python/langchain-core/messages/system/SystemMessage) 对象直接传给 `create_agent` 的 `system_prompt` 参数，用于缓存控制等高级用例

### 动态模型选择

<Tabs>
  <Tab title="Decorator">
    ```python
    from collections.abc import Callable

    from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
    from langchain.chat_models import init_chat_model

    complex_model = init_chat_model("claude-sonnet-4-6")
    simple_model = init_chat_model("claude-haiku-4-5-20251001")

    @wrap_model_call
    def dynamic_model(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        if len(request.messages) > 10:
            model = complex_model
        else:
            model = simple_model
        return handler(request.override(model=model))
    ```
  </Tab>

  <Tab title="Class">
    ```python
    from collections.abc import Callable

    from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
    from langchain.chat_models import init_chat_model

    complex_model = init_chat_model("claude-sonnet-4-6")
    simple_model = init_chat_model("claude-haiku-4-5-20251001")

    class DynamicModelMiddleware(AgentMiddleware):
        def wrap_model_call(
            self,
            request: ModelRequest,
            handler: Callable[[ModelRequest], ModelResponse],
        ) -> ModelResponse:
            if len(request.messages) > 10:
                model = complex_model
            else:
                model = simple_model
            return handler(request.override(model=model))
    ```
  </Tab>
</Tabs>

### 动态选择工具

在运行时选择相关工具以提高性能和准确性。本节介绍过滤预先注册的工具。关于注册运行时发现的工具（例如来自 MCP 服务器），参见[运行时工具注册](/oss/python/langchain/tools#dynamic-tool-selection)。

**好处：**

* **更短的提示词** - 通过只暴露相关工具来降低复杂性
* **更高的准确性** - 模型从更少的选项中正确选择
* **权限控制** - 根据用户访问权限动态过滤工具

<Tabs>
  <Tab title="Decorator">
    ```python
    from langchain.agents import create_agent
    from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
    from typing import Callable

    @wrap_model_call
    def select_tools(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Middleware to select relevant tools based on state/context."""
        # Select a small, relevant subset of tools based on state/context
        relevant_tools = select_relevant_tools(request.state, request.runtime)
        return handler(request.override(tools=relevant_tools))

    agent = create_agent(
        model="gpt-5.5",
        tools=all_tools,  # All available tools need to be registered upfront
        middleware=[select_tools],
    )
    ```
  </Tab>

  <Tab title="Class">
    ```python
    from langchain.agents import create_agent
    from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
    from typing import Callable

    class ToolSelectorMiddleware(AgentMiddleware):
        def wrap_model_call(
            self,
            request: ModelRequest,
            handler: Callable[[ModelRequest], ModelResponse],
        ) -> ModelResponse:
            """Middleware to select relevant tools based on state/context."""
            # Select a small, relevant subset of tools based on state/context
            relevant_tools = select_relevant_tools(request.state, request.runtime)
            return handler(request.override(tools=relevant_tools))

    agent = create_agent(
        model="gpt-5.5",
        tools=all_tools,  # All available tools need to be registered upfront
        middleware=[ToolSelectorMiddleware()],
    )
    ```
  </Tab>
</Tabs>

### 工具调用监控

<Tabs>
  <Tab title="Decorator">
    ```python
    from collections.abc import Callable

    from langchain.agents.middleware import wrap_tool_call
    from langchain.messages import ToolMessage
    from langchain.tools.tool_node import ToolCallRequest
    from langgraph.types import Command

    @wrap_tool_call
    def monitor_tool(
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        print(f"Executing tool: {request.tool_call['name']}")
        print(f"Arguments: {request.tool_call['args']}")
        try:
            result = handler(request)
            print("Tool completed successfully")
            return result
        except Exception as e:
            print(f"Tool failed: {e}")
            raise
    ```
  </Tab>

  <Tab title="Class">
    ```python
    from collections.abc import Callable

    from langchain.agents.middleware import AgentMiddleware
    from langchain.messages import ToolMessage
    from langchain.tools.tool_node import ToolCallRequest
    from langgraph.types import Command

    class ToolMonitoringMiddleware(AgentMiddleware):
        def wrap_tool_call(
            self,
            request: ToolCallRequest,
            handler: Callable[[ToolCallRequest], ToolMessage | Command],
        ) -> ToolMessage | Command:
            print(f"Executing tool: {request.tool_call['name']}")
            print(f"Arguments: {request.tool_call['args']}")
            try:
                result = handler(request)
                print("Tool completed successfully")
                return result
            except Exception as e:
                print(f"Tool failed: {e}")
                raise
    ```
  </Tab>
</Tabs>

### 提示缓存（Anthropic）

使用 Anthropic 模型时，使用带缓存控制指令的结构化内容块来缓存大型系统提示：

<Tabs>
  <Tab title="Decorator">
    ```python
    from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
    from langchain.messages import SystemMessage
    from typing import Callable

    @wrap_model_call
    def add_cached_context(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        # Always work with content blocks
        new_content = list(request.system_message.content_blocks) + [
            {
                "type": "text",
                "text": "Here is a large document to analyze:\n\n<document>...</document>",
                # content up until this point is cached
                "cache_control": {"type": "ephemeral"}
            }
        ]

        new_system_message = SystemMessage(content=new_content)
        return handler(request.override(system_message=new_system_message))
    ```
  </Tab>

  <Tab title="Class">
    ```python
    from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
    from langchain.messages import SystemMessage
    from typing import Callable

    class CachedContextMiddleware(AgentMiddleware):
        def wrap_model_call(
            self,
            request: ModelRequest,
            handler: Callable[[ModelRequest], ModelResponse],
        ) -> ModelResponse:
            # Always work with content blocks
            new_content = list(request.system_message.content_blocks) + [
                {
                    "type": "text",
                    "text": "Here is a large document to analyze:\n\n<document>...</document>",
                    "cache_control": {"type": "ephemeral"}  # This content will be cached
                }
            ]

            new_system_message = SystemMessage(content=new_content)
            return handler(request.override(system_message=new_system_message))
    ```
  </Tab>
</Tabs>

**注意：**

* `ModelRequest.system_message` 始终是一个 [`SystemMessage`](https://reference.langchain.com/python/langchain-core/messages/system/SystemMessage) 对象，即使代理是用 `system_prompt="string"` 创建的
* 使用 `SystemMessage.content_blocks` 以块列表的形式访问内容，无论原始内容是字符串还是列表
* 修改系统消息时，使用 `content_blocks` 并追加新块以保留现有结构
* 你可以将 [`SystemMessage`](https://reference.langchain.com/python/langchain-core/messages/system/SystemMessage) 对象直接传给 `create_agent` 的 `system_prompt` 参数，用于缓存控制等高级用例

## 其他资源

* [中间件 API 参考](https://reference.langchain.com/python/langchain/middleware/)
* [预构建中间件](/oss/python/langchain/middleware/built-in)
* [测试代理](/oss/python/langchain/test/)

# 流式输出

> 从代理运行中流式输出实时更新

> 提示：对于新应用，我们推荐使用[事件流式输出](/oss/python/langchain/event-streaming)——这是 LangChain v1.3 引入的 typed-projection API。事件流式输出为每个投影（消息、值、工具调用、子图）提供独立的迭代器，你可以单独消费它们，而不必根据 `stream_mode` 的分块做分支判断。

LangChain 实现了一套流式输出系统，用于呈现实时更新。

流式输出对于提升基于 LLM 的应用的响应性至关重要。通过逐步显示输出，即使在完整响应就绪之前，流式输出也能显著改善用户体验（UX），尤其是在面对 LLM 的延迟时。

## 概述

LangChain 的流式输出系统让你能够把代理运行的实时反馈呈现给你的应用。

LangChain 流式输出能做什么：

* [**流式输出代理进度**](#agent-progress)——在代理每一步之后获取状态更新。
* [**流式输出 LLM token**](#llm-tokens)——在语言模型生成 token 时进行流式输出。
* [**流式输出思考 / 推理 token**](#streaming-thinking-/-reasoning-tokens)——在模型推理时呈现其推理过程。
* [**流式输出自定义更新**](#custom-updates)——发出用户自定义的信号（例如 `"已获取 10/100 条记录"`）。
* [**流式输出多种模式**](#stream-multiple-modes)——从 `updates`（代理进度）、`messages`（LLM token + 元数据）或 `custom`（任意用户数据）中选择。

更多端到端示例参见下文[常见模式](#common-patterns)一节。

## 支持的流式模式

将一个或多个流式模式以列表形式传给 [`stream`](https://reference.langchain.com/python/langgraph/graphs/#langgraph.graph.state.CompiledStateGraph.stream) 或 [`astream`](https://reference.langchain.com/python/langgraph/graphs/#langgraph.graph.state.CompiledStateGraph.astream) 方法：

| 模式 | 说明 |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `updates` | 在代理每一步之后流式输出状态更新。如果同一步中有多次更新（例如运行了多个节点），这些更新会分别流式输出。 |
| `messages` | 从任何调用 LLM 的图节点流式输出 `(token, metadata)` 元组。 |
| `custom` | 使用流写入器从图节点内部流式输出自定义数据。 |

## 代理进度

要流式输出代理进度，请使用带有 `stream_mode="updates"` 的 [`stream`](https://reference.langchain.com/python/langgraph/graphs/#langgraph.graph.state.CompiledStateGraph.stream) 或 [`astream`](https://reference.langchain.com/python/langgraph/graphs/#langgraph.graph.state.CompiledStateGraph.astream) 方法。这会在每次代理步骤之后发出一个事件。

例如，如果你的代理调用了一次工具，你应该会看到以下更新：

* **LLM 节点**：带有工具调用请求的 [`AIMessage`](https://reference.langchain.com/python/langchain-core/messages/ai/AIMessage)
* **工具节点**：带有执行结果的 [`ToolMessage`](https://reference.langchain.com/python/langchain-core/messages/tool/ToolMessage)
* **LLM 节点**：最终的 AI 响应

通过 `config` 传入 `thread_id`，以便会话被检查点保存，后续轮次可以继续相同的历史记录。`thread_id` 独立于 `stream_mode`；你也可以在它旁边传入 `context`，用于存放你的工具从 `runtime.context` 读取的每次运行数据。

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
from langchain.agents import create_agent
from langchain_core.utils.uuid import uuid7
from langgraph.checkpoint.memory import InMemorySaver

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[get_weather],
    checkpointer=InMemorySaver()
)
config = {"configurable": {"thread_id": str(uuid7())}}
stream = agent.stream_events(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    config=config,
    version="v3",
)
for kind, item in stream.interleave("messages", "tool_calls"):
    if kind == "messages":
        for token in item.text:
            print(token, end="", flush=True)
    elif kind == "tool_calls":
        print(f"\nTool call: {item.tool_name}({item.input})")
        for delta in item.output_deltas:
            print(delta, end="", flush=True)
        print(f"\nTool result: {item.output}")

final_state = stream.output
```

```shell
step: model
content: [{'type': 'tool_call', 'name': 'get_weather', 'args': {'city': 'San Francisco'}, 'id': 'call_9lBtsDbmmobzyA8xc4I4Ctne'}]
step: tools
content: [{'type': 'text', 'text': "It's always sunny in San Francisco!"}]
step: model
content: [{'type': 'text', 'text': "San Francisco weather: It's always sunny in San Francisco!\n\nIf you’d like the exact current conditions (temperature, humidity, wind) and a short forecast, I can fetch that next. Would you like me to pull live details for San Francisco?"}]
```

> 注意：使用 `thread_id` 持久化会话历史记录，需要代理配置了[检查点](/oss/python/langchain/long-term-memory)。在 [LangSmith 部署](/langsmith/deployment) 上，检查点会自动配置。在本地，请显式传入一个，例如 `create_agent(..., checkpointer=InMemorySaver())`。本页其余代码片段为简洁起见省略了 `thread_id`，但在生产环境中你应该传入它。

## LLM token

要流式输出 LLM 生成的 token，请使用 `stream_mode="messages"`。下面你可以看到代理流式输出工具调用和最终响应的输出。

```python
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""

    return f"It's always sunny in {city}!"

agent = create_agent(
    model="gpt-5-nano",
    tools=[get_weather],
)
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode="messages",
    version="v2",
):
    if chunk["type"] == "messages":
        token, metadata = chunk["data"]
        print(f"node: {metadata['langgraph_node']}")
        print(f"content: {token.content_blocks}")
        print("\n")
```

```shell
node: model
content: [{'type': 'tool_call_chunk', 'id': 'call_vbCyBcP8VuneUzyYlSBZZsVa', 'name': 'get_weather', 'args': '', 'index': 0}]

node: model
content: [{'type': 'tool_call_chunk', 'id': None, 'name': None, 'args': '{"', 'index': 0}]

node: model
content: [{'type': 'tool_call_chunk', 'id': None, 'name': None, 'args': 'city', 'index': 0}]

node: model
content: [{'type': 'tool_call_chunk', 'id': None, 'name': None, 'args': '":"', 'index': 0}]

node: model
content: [{'type': 'tool_call_chunk', 'id': None, 'name': None, 'args': 'San', 'index': 0}]

node: model
content: [{'type': 'tool_call_chunk', 'id': None, 'name': None, 'args': ' Francisco', 'index': 0}]

node: model
content: [{'type': 'tool_call_chunk', 'id': None, 'name': None, 'args': '"}', 'index': 0}]

node: model
content: []

node: tools
content: [{'type': 'text', 'text': "It's always sunny in San Francisco!"}]

node: model
content: []

node: model
content: [{'type': 'text', 'text': 'Here'}]

node: model
content: [{'type': 'text', 'text': ''s'}]

node: model
content: [{'type': 'text', 'text': ' what'}]

node: model
content: [{'type': 'text', 'text': ' I'}]

node: model
content: [{'type': 'text', 'text': ' got'}]

node: model
content: [{'type': 'text', 'text': ':'}]

node: model
content: [{'type': 'text', 'text': ' "'}]

node: model
content: [{'type': 'text', 'text': "It's"}]

node: model
content: [{'type': 'text', 'text': ' always'}]

node: model
content: [{'type': 'text', 'text': ' sunny'}]

node: model
content: [{'type': 'text', 'text': ' in'}]

node: model
content: [{'type': 'text', 'text': ' San'}]

node: model
content: [{'type': 'text', 'text': ' Francisco'}]

node: model
content: [{'type': 'text', 'text': '!"\n\n'}]
```

> 注意：**把代理包装为父 `StateGraph` 的一个节点？**[`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 返回的是编译后的图，因此把它作为节点使用会使其成为子图。父图上的 `stream_mode="messages"` 不会发出内部代理 LLM 调用的 token 分块，除非你传入 `subgraphs=True`。参见[子图输出](/oss/python/langgraph/streaming#subgraph-outputs)。

## 自定义更新

要从工具中流式输出执行过程中的更新，你可以使用 [`get_stream_writer`](https://reference.langchain.com/python/langgraph/config/get_stream_writer)。

```python
from langchain.agents import create_agent
from langgraph.config import get_stream_writer

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    writer = get_stream_writer()
    # stream any arbitrary data
    writer(f"Looking up data for city: {city}")
    writer(f"Acquired data for city: {city}")
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="claude-sonnet-4-6",
    tools=[get_weather],
)

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode="custom",
    version="v2",
):
    if chunk["type"] == "custom":
        print(chunk["data"])
```

```shell
Looking up data for city: San Francisco
Acquired data for city: San Francisco
```

> 注意：如果你在工具内部添加了 [`get_stream_writer`](https://reference.langchain.com/python/langgraph/config/get_stream_writer)，你将无法在 LangGraph 执行上下文之外调用该工具。

## 流式输出多种模式

你可以通过把流式模式作为列表传入来指定多种流式模式：`stream_mode=["updates", "custom"]`。

每个流式分块都是带有 `type`、`ns` 和 `data` 键的 `StreamPart` 字典。使用 `chunk["type"]` 判断流式模式，用 `chunk["data"]` 访问负载。

```python
from langchain.agents import create_agent
from langgraph.config import get_stream_writer

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    writer = get_stream_writer()
    writer(f"Looking up data for city: {city}")
    writer(f"Acquired data for city: {city}")
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="gpt-5-nano",
    tools=[get_weather],
)

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode=["updates", "custom"],
    version="v2",
):
    print(f"stream_mode: {chunk['type']}")
    print(f"content: {chunk['data']}")
    print("\n")
```

```shell
stream_mode: updates
content: {'model': {'messages': [AIMessage(content='', response_metadata={'token_usage': {'completion_tokens': 280, 'prompt_tokens': 132, 'total_tokens': 412, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 256, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_provider': 'openai', 'model_name': 'gpt-5-nano-2025-08-07', 'system_fingerprint': None, 'id': 'chatcmpl-C9tlgBzGEbedGYxZ0rTCz5F7OXpL7', 'service_tier': 'default', 'finish_reason': 'tool_calls', 'logprobs': None}, id='lc_run--480c07cb-e405-4411-aa7f-0520fddeed66-0', tool_calls=[{'name': 'get_weather', 'args': {'city': 'San Francisco'}, 'id': 'call_KTNQIftMrl9vgNwEfAJMVu7r', 'type': 'tool_call'}], usage_metadata={'input_tokens': 132, 'output_tokens': 280, 'total_tokens': 412, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 256}})]}}

stream_mode: custom
content: Looking up data for city: San Francisco

stream_mode: custom
content: Acquired data for city: San Francisco

stream_mode: updates
content: {'tools': {'messages': [ToolMessage(content="It's always sunny in San Francisco!", name='get_weather', tool_call_id='call_KTNQIftMrl9vgNwEfAJMVu7r')]}}

stream_mode: updates
content: {'model': {'messages': [AIMessage(content='San Francisco weather: It's always sunny in San Francisco!\n\n', response_metadata={'token_usage': {'completion_tokens': 764, 'prompt_tokens': 168, 'total_tokens': 932, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 704, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_provider': 'openai', 'model_name': 'gpt-5-nano-2025-08-07', 'system_fingerprint': None, 'id': 'chatcmpl-C9tljDFVki1e1haCyikBptAuXuHYG', 'service_tier': 'default', 'finish_reason': 'stop', 'logprobs': None}, id='lc_run--acbc740a-18fe-4a14-8619-da92a0d0ee90-0', usage_metadata={'input_tokens': 168, 'output_tokens': 764, 'total_tokens': 932, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 704}})]}}
```

## 常见模式

下面是一些展示流式输出常见用例的示例。

### 流式输出思考 / 推理 token

某些模型在给出最终答案之前会进行内部推理。你可以通过按 `"reasoning"` 类型的[标准内容块](/oss/python/langchain/messages#standard-content-blocks)进行过滤，在生成时流式输出这些思考 / 推理 token。

> 注意：必须在模型上启用推理输出。
>
> 配置详情参见[推理一节](/oss/python/langchain/models#reasoning)和你的[提供商的集成页面](/oss/python/integrations/providers/overview)。
>
> 要快速检查模型的推理支持情况，参见 [models.dev](https://models.dev)。

要从代理流式输出思考 token，请使用 `stream_mode="messages"` 并过滤推理内容块：

```python
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import Runnable

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

model = ChatAnthropic(
    model_name="claude-sonnet-4-6",
    timeout=None,
    stop=None,
    thinking={"type": "enabled", "budget_tokens": 5000},
)
agent: Runnable = create_agent(
    model=model,
    tools=[get_weather],
)

stream = agent.stream_events(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    version="v3",
)
for message in stream.messages:
    for token in message.reasoning:
        print(f"[thinking] {token}", end="")
    for token in message.text:
        print(token, end="", flush=True)
```

```shell
[thinking] The user is asking about the weather in San Francisco. I have a tool
[thinking]  available to get this information. Let me call the get_weather tool
[thinking]  with "San Francisco" as the city parameter.
The weather in San Francisco is: It's always sunny in San Francisco!
```

无论模型提供商是谁，这种方式都同样有效——LangChain 通过 [`content_blocks`](/oss/python/langchain/messages#standard-content-blocks) 属性将提供商特有的格式（Anthropic 的 `thinking` 块、OpenAI 的 `reasoning` 摘要等）规范化为标准的 `"reasoning"` 内容块类型。

要直接从聊天模型（不经过代理）流式输出推理 token，参见[聊天模型的流式输出](/oss/python/langchain/models#reasoning)。

### 流式输出工具调用

你可能想同时流式输出：

1. [工具调用](/oss/python/langchain/models#tool-calling)生成过程中的部分 JSON
2. 已完成的、被解析并执行的工具调用

指定 [`stream_mode="messages"`](#llm-tokens) 会流式输出代理中所有 LLM 调用生成的增量[消息分块](/oss/python/langchain/messages#streaming-and-chunks)。要访问带有已解析工具调用的完整消息：

1. 如果这些消息被记录在[状态](/oss/python/langchain/short-term-memory)中（例如 [`create_agent`](/oss/python/langchain/agents) 的模型节点），使用 `stream_mode=["messages", "updates"]` 通过[状态更新](#agent-progress)访问完整消息（如下演示）。
2. 如果这些消息没有被记录在状态中，使用[自定义更新](#custom-updates)，或在流式循环中聚合分块（[下一节](#accessing-completed-messages)）。

> 注意：如果你的代理包含多个 LLM，请参阅下面关于[从子代理流式输出](#streaming-from-sub-agents)的章节。

```python
from typing import Any

from langchain.agents import create_agent
from langchain.messages import AIMessage, AIMessageChunk, AnyMessage, ToolMessage

def get_weather(city: str) -> str:
    """Get weather for a given city."""

    return f"It's always sunny in {city}!"

agent = create_agent("openai:gpt-5.5", tools=[get_weather])

def _render_message_chunk(token: AIMessageChunk) -> None:
    if token.text:
        print(token.text, end="|")
    if token.tool_call_chunks:
        print(token.tool_call_chunks)
    # N.B. all content is available through token.content_blocks

def _render_completed_message(message: AnyMessage) -> None:
    if isinstance(message, AIMessage) and message.tool_calls:
        print(f"Tool calls: {message.tool_calls}")
    if isinstance(message, ToolMessage):
        print(f"Tool response: {message.content_blocks}")

input_message = {"role": "user", "content": "What is the weather in Boston?"}
for chunk in agent.stream(
    {"messages": [input_message]},
    stream_mode=["messages", "updates"],
    version="v2",
):
    if chunk["type"] == "messages":
        token, metadata = chunk["data"]
        if isinstance(token, AIMessageChunk):
            _render_message_chunk(token)
    elif chunk["type"] == "updates":
        for source, update in chunk["data"].items():
            if source in ("model", "tools"):  # `source` captures node name
                _render_completed_message(update["messages"][-1])
```

```shell
[{'name': 'get_weather', 'args': '', 'id': 'call_D3Orjr89KgsLTZ9hTzYv7Hpf', 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '{"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'city', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '":"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'Boston', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '"}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
Tool calls: [{'name': 'get_weather', 'args': {'city': 'Boston'}, 'id': 'call_D3Orjr89KgsLTZ9hTzYv7Hpf', 'type': 'tool_call'}]
Tool response: [{'type': 'text', 'text': "It's always sunny in Boston!"}]
The| weather| in| Boston| is| **|sun|ny|**|.|
```

#### 访问已完成的消息

> 注意：如果已完成的消息被记录在代理的[状态](/oss/python/langchain/short-term-memory)中，你可以如[流式输出工具调用](#streaming-tool-calls)一节所示，使用 `stream_mode=["messages", "updates"]` 在流式输出过程中访问完整消息。

在某些情况下，已完成的消息不会反映在[状态更新](#agent-progress)中。如果你能访问代理内部，可以使用[自定义更新](#custom-updates)在流式输出过程中访问这些消息。否则，你可以在流式循环中聚合消息分块（见下文）。

考虑下面的示例，我们把一个[流写入器](#custom-updates)整合进一个简化的[护栏中间件](/oss/python/langchain/guardrails#after-agent-guardrails)。这个中间件演示了使用工具调用生成结构化的"安全 / 不安全"评估（也可以使用[结构化输出](/oss/python/langchain/models#structured-output)来实现）：

```python
from typing import Any, Literal

from langchain.agents.middleware import after_agent, AgentState
from langgraph.runtime import Runtime
from langchain.messages import AIMessage
from langchain.chat_models import init_chat_model
from langgraph.config import get_stream_writer
from pydantic import BaseModel

class ResponseSafety(BaseModel):
    """Evaluate a response as safe or unsafe."""
    evaluation: Literal["safe", "unsafe"]

safety_model = init_chat_model("openai:gpt-5.5")

@after_agent(can_jump_to=["end"])
def safety_guardrail(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Model-based guardrail: Use an LLM to evaluate response safety."""
    stream_writer = get_stream_writer()
    # Get the model response
    if not state["messages"]:
        return None

    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        return None

    # Use another model to evaluate safety
    model_with_tools = safety_model.bind_tools([ResponseSafety], tool_choice="any")
    result = model_with_tools.invoke(
        [
            {
                "role": "system",
                "content": "Evaluate this AI response as generally safe or unsafe."
            },
            {
                "role": "user",
                "content": f"AI response: {last_message.text}"
            }
        ]
    )
    stream_writer(result)

    tool_call = result.tool_calls[0]
    if tool_call["args"]["evaluation"] == "unsafe":
        last_message.content = "I cannot provide that response. Please rephrase your request."

    return None
```

然后我们可以把这个中间件整合进我们的代理，并包含它的自定义流事件：

```python
from typing import Any

from langchain.agents import create_agent
from langchain.messages import AIMessageChunk, AIMessage, AnyMessage

def get_weather(city: str) -> str:
    """Get weather for a given city."""

    return f"It's always sunny in {city}!"

agent = create_agent(
    model="openai:gpt-5.5",
    tools=[get_weather],
    middleware=[safety_guardrail],
)

def _render_message_chunk(token: AIMessageChunk) -> None:
    if token.text:
        print(token.text, end="|")
    if token.tool_call_chunks:
        print(token.tool_call_chunks)

def _render_completed_message(message: AnyMessage) -> None:
    if isinstance(message, AIMessage) and message.tool_calls:
        print(f"Tool calls: {message.tool_calls}")
    if isinstance(message, ToolMessage):
        print(f"Tool response: {message.content_blocks}")

input_message = {"role": "user", "content": "What is the weather in Boston?"}
for chunk in agent.stream(
    {"messages": [input_message]},
    stream_mode=["messages", "updates", "custom"],
    version="v2",
):
    if chunk["type"] == "messages":
        token, metadata = chunk["data"]
        if isinstance(token, AIMessageChunk):
            _render_message_chunk(token)
    elif chunk["type"] == "updates":
        for source, update in chunk["data"].items():
            if source in ("model", "tools"):
                _render_completed_message(update["messages"][-1])
    elif chunk["type"] == "custom":
        # access completed message in stream
        print(f"Tool calls: {chunk['data'].tool_calls}")
```

```shell
[{'name': 'get_weather', 'args': '', 'id': 'call_je6LWgxYzuZ84mmoDalTYMJC', 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '{"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'city', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '":"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'Boston', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '"}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
Tool calls: [{'name': 'get_weather', 'args': {'city': 'Boston'}, 'id': 'call_je6LWgxYzuZ84mmoDalTYMJC', 'type': 'tool_call'}]
Tool response: [{'type': 'text', 'text': "It's always sunny in Boston!"}]
The| weather| in| **|Boston|**| is| **|sun|ny|**|.|[{'name': 'ResponseSafety', 'args': '', 'id': 'call_O8VJIbOG4Q9nQF0T8ltVi58O', 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '{"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'evaluation', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '":"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'safe', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '"}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
Tool calls: [{'name': 'ResponseSafety', 'args': {'evaluation': 'safe'}, 'id': 'call_O8VJIbOG4Q9nQF0T8ltVi58O', 'type': 'tool_call'}]
```

另外，如果你无法向流中添加自定义事件，你可以在流式循环内聚合消息分块：

```python
input_message = {"role": "user", "content": "What is the weather in Boston?"}
full_message = None
for chunk in agent.stream(
    {"messages": [input_message]},
    stream_mode=["messages", "updates"],
    version="v2",
):
    if chunk["type"] == "messages":
        token, metadata = chunk["data"]
        if isinstance(token, AIMessageChunk):
            _render_message_chunk(token)
            full_message = token if full_message is None else full_message + token
            if token.chunk_position == "last":
                if full_message.tool_calls:
                    print(f"Tool calls: {full_message.tool_calls}")
                full_message = None
    elif chunk["type"] == "updates":
        for source, update in chunk["data"].items():
            if source == "tools":
                _render_completed_message(update["messages"][-1])
```

### 人机协同下的流式输出

要处理人机协同[中断](/oss/python/langchain/human-in-the-loop)，我们在[上面的示例](#streaming-tool-calls)基础上构建：

1. 我们为代理配置[人机协同中间件和检查点](/oss/python/langchain/human-in-the-loop#configuring-interrupts)
2. 我们收集在 `"updates"` 流式模式期间产生的中断
3. 我们用[命令](/oss/python/langchain/human-in-the-loop#responding-to-interrupts)响应这些中断

```python
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.messages import AIMessage, AIMessageChunk, AnyMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, Interrupt

def get_weather(city: str) -> str:
    """Get weather for a given city."""

    return f"It's always sunny in {city}!"

checkpointer = InMemorySaver()

agent = create_agent(
    "openai:gpt-5.5",
    tools=[get_weather],
    middleware=[
        HumanInTheLoopMiddleware(interrupt_on={"get_weather": True}),
    ],
    checkpointer=checkpointer,
)

def _render_message_chunk(token: AIMessageChunk) -> None:
    if token.text:
        print(token.text, end="|")
    if token.tool_call_chunks:
        print(token.tool_call_chunks)

def _render_completed_message(message: AnyMessage) -> None:
    if isinstance(message, AIMessage) and message.tool_calls:
        print(f"Tool calls: {message.tool_calls}")
    if isinstance(message, ToolMessage):
        print(f"Tool response: {message.content_blocks}")

def _render_interrupt(interrupt: Interrupt) -> None:
    interrupts = interrupt.value
    for request in interrupts["action_requests"]:
        print(request["description"])

input_message = {
    "role": "user",
    "content": (
        "Can you look up the weather in Boston and San Francisco?"
    ),
}
config = {"configurable": {"thread_id": "some_id"}}
interrupts = []
for chunk in agent.stream(
    {"messages": [input_message]},
    config=config,
    stream_mode=["messages", "updates"],
    version="v2",
):
    if chunk["type"] == "messages":
        token, metadata = chunk["data"]
        if isinstance(token, AIMessageChunk):
            _render_message_chunk(token)
    elif chunk["type"] == "updates":
        for source, update in chunk["data"].items():
            if source in ("model", "tools"):
                _render_completed_message(update["messages"][-1])
            if source == "__interrupt__":
                interrupts.extend(update)
                _render_interrupt(update[0])
```

```shell
[{'name': 'get_weather', 'args': '', 'id': 'call_GOwNaQHeqMixay2qy80padfE', 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '{"ci', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'ty": ', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '"Bosto', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'n"}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': 'get_weather', 'args': '', 'id': 'call_Ndb4jvWm2uMA0JDQXu37wDH6', 'index': 1, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '{"ci', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'ty": ', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '"San F', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'ranc', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'isco"', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '}', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}]
Tool calls: [{'name': 'get_weather', 'args': {'city': 'Boston'}, 'id': 'call_GOwNaQHeqMixay2qy80padfE', 'type': 'tool_call'}, {'name': 'get_weather', 'args': {'city': 'San Francisco'}, 'id': 'call_Ndb4jvWm2uMA0JDQXu37wDH6', 'type': 'tool_call'}]
Tool execution requires approval

Tool: get_weather
Args: {'city': 'Boston'}
Tool execution requires approval

Tool: get_weather
Args: {'city': 'San Francisco'}
```

接下来我们为每个中断收集一个[决策](/oss/python/langchain/human-in-the-loop#interrupt-decision-types)。重要的是，决策的顺序必须与我们收集的操作顺序一致。

为了说明，我们将编辑一个工具调用并接受另一个：

```python
def _get_interrupt_decisions(interrupt: Interrupt) -> list[dict]:
    return [
        {
            "type": "edit",
            "edited_action": {
                "name": "get_weather",
                "args": {"city": "Boston, U.K."},
            },
        }
        if "boston" in request["description"].lower()
        else {"type": "approve"}
        for request in interrupt.value["action_requests"]
    ]

decisions = {}
for interrupt in interrupts:
    decisions[interrupt.id] = {
        "decisions": _get_interrupt_decisions(interrupt)
    }

decisions
```

```shell
{
    'a96c40474e429d661b5b32a8d86f0f3e': {
        'decisions': [
            {
                'type': 'edit',
                 'edited_action': {
                     'name': 'get_weather',
                     'args': {'city': 'Boston, U.K.'}
                 }
            },
            {'type': 'approve'},
        ]
    }
}
```

然后我们可以通过把[命令](/oss/python/langchain/human-in-the-loop#responding-to-interrupts)传入同一个流式循环来恢复执行：

```python
interrupts = []
for chunk in agent.stream(
    Command(resume=decisions),
    config=config,
    stream_mode=["messages", "updates"],
    version="v2",
):
    # Streaming loop is unchanged
    if chunk["type"] == "messages":
        token, metadata = chunk["data"]
        if isinstance(token, AIMessageChunk):
            _render_message_chunk(token)
    elif chunk["type"] == "updates":
        for source, update in chunk["data"].items():
            if source in ("model", "tools"):
                _render_completed_message(update["messages"][-1])
            if source == "__interrupt__":
                interrupts.extend(update)
                _render_interrupt(update[0])
```

```shell
Tool response: [{'type': 'text', 'text': "It's always sunny in Boston, U.K.!"}]
Tool response: [{'type': 'text', 'text': "It's always sunny in San Francisco!"}]
-| **|Boston|**|:| It|'s| always| sunny| in| Boston|,| U|.K|.|
|-| **|San| Francisco|**|:| It|'s| always| sunny| in| San| Francisco|!|
```

### 从子代理流式输出

当代理中任意位置有多个 LLM 时，通常需要区分生成消息的来源。

要做到这一点，在创建每个代理时传入一个 [`name`](https://reference.langchain.com/python/langchain/agents/#langchain.agents.create_agent\(name\))。在以 `"messages"` 模式流式输出时，这个名称会通过 `lc_agent_name` 键在元数据中提供。

下面，我们更新[流式输出工具调用](#streaming-tool-calls)示例：

1. 我们用 `call_weather_agent` 工具替换我们的工具，该工具在内部调用一个代理
2. 我们给每个代理添加一个 `name`
3. 在创建流时我们指定 [`subgraphs=True`](/oss/python/langgraph/use-subgraphs#stream-subgraph-outputs)
4. 我们的流处理与之前相同，但我们添加逻辑，用 `create_agent` 的 `name` 参数跟踪哪个代理处于活动状态

> 提示：当你为代理设置 `name` 时，该名称也会附加到该代理生成的任何 `AIMessage` 上。

首先我们构建代理：

```python
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, AnyMessage

def get_weather(city: str) -> str:
    """Get weather for a given city."""

    return f"It's always sunny in {city}!"

weather_model = init_chat_model("openai:gpt-5.5")
weather_agent = create_agent(
    model=weather_model,
    tools=[get_weather],
    name="weather_agent",
)

def call_weather_agent(query: str) -> str:
    """Query the weather agent."""
    result = weather_agent.invoke({
        "messages": [{"role": "user", "content": query}]
    })
    return result["messages"][-1].text

supervisor_model = init_chat_model("openai:gpt-5.5")
agent = create_agent(
    model=supervisor_model,
    tools=[call_weather_agent],
    name="supervisor",
)
```

接下来，我们向流式循环添加逻辑，报告哪个代理正在发出 token：

```python
def _render_message_chunk(token: AIMessageChunk) -> None:
    if token.text:
        print(token.text, end="|")
    if token.tool_call_chunks:
        print(token.tool_call_chunks)

def _render_completed_message(message: AnyMessage) -> None:
    if isinstance(message, AIMessage) and message.tool_calls:
        print(f"Tool calls: {message.tool_calls}")
    if isinstance(message, ToolMessage):
        print(f"Tool response: {message.content_blocks}")

input_message = {"role": "user", "content": "What is the weather in Boston?"}
current_agent = None
for chunk in agent.stream(
    {"messages": [input_message]},
    stream_mode=["messages", "updates"],
    subgraphs=True,
    version="v2",
):
    if chunk["type"] == "messages":
        token, metadata = chunk["data"]
        if agent_name := metadata.get("lc_agent_name"):
            if agent_name != current_agent:
                print(f"🤖 {agent_name}: ")
                current_agent = agent_name
        if isinstance(token, AIMessageChunk):
            _render_message_chunk(token)
    elif chunk["type"] == "updates":
        for source, update in chunk["data"].items():
            if source in ("model", "tools"):
                _render_completed_message(update["messages"][-1])
```

```shell
🤖 supervisor:
[{'name': 'call_weather_agent', 'args': '', 'id': 'call_asorzUf0mB6sb7MiKfgojp7I', 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '{"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'query', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '":"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'Boston', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': ' weather', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': ' right', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': ' now', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': ' and', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': " today's", 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': ' forecast', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '"}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
Tool calls: [{'name': 'call_weather_agent', 'args': {'query': "Boston weather right now and today's forecast"}, 'id': 'call_asorzUf0mB6sb7MiKfgojp7I', 'type': 'tool_call'}]
🤖 weather_agent:
[{'name': 'get_weather', 'args': '', 'id': 'call_LZ89lT8fW6w8vqck5pZeaDIx', 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '{"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'city', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '":"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'Boston', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '"}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
Tool calls: [{'name': 'get_weather', 'args': {'city': 'Boston'}, 'id': 'call_LZ89lT8fW6w8vqck5pZeaDIx', 'type': 'tool_call'}]
Tool response: [{'type': 'text', 'text': "It's always sunny in Boston!"}]
Boston| weather| right| now|:| **|Sunny|**|.

|Today|'s| forecast| for| Boston|:| **|Sunny| all| day|**|.|Tool response: [{'type': 'text', 'text': 'Boston weather right now: **Sunny**.\n\nToday's forecast for Boston: **Sunny all day**.'}]
🤖 supervisor:
Boston| weather| right| now|:| **|Sunny|**|.

|Today|'s| forecast| for| Boston|:| **|Sunny| all| day|**|.|
```

## 禁用流式输出

在某些应用中，你可能需要为给定模型禁用单个 token 的流式输出。这在以下情况很有用：

* 使用[多代理](/oss/python/langchain/multi-agent)系统时，控制哪些代理流式输出它们的结果
* 混合支持流式输出和不支持流式输出的模型
* 部署到 [LangSmith](/langsmith/observability)，希望阻止某些模型输出被流式输出到客户端

初始化模型时设置 `streaming=False`。

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="gpt-5.5",
    streaming=False
)
```

> 提示：部署到 LangSmith 时，对任何你不想流式输出到客户端的模型设置 `streaming=False`。这在部署前于你的图代码中配置。

> 注意：并非所有聊天模型集成都支持 `streaming` 参数。如果你的模型不支持它，请改用 `disable_streaming=True`。所有聊天模型都通过基类提供该参数。

关于更多细节，参见 [LangGraph 流式输出指南](/oss/python/langgraph/streaming#disable-streaming-for-specific-chat-models)。

## v2 流式输出格式

> 注意：需要 LangGraph >= 1.1。

向 `stream()` 或 `astream()` 传入 `version="v2"` 以获得统一的输出格式。每个分块都是带有 `type`、`ns` 和 `data` 键的 `StreamPart` 字典——无论流式模式或模式数量如何，形状都相同：

**v2（新）**：

```python
# Unified format — no more tuple unpacking
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode=["updates", "custom"],
    version="v2",
):
    print(chunk["type"])  # "updates" or "custom"
    print(chunk["data"])  # payload
```

**v1（当前默认）**：

```python
# Must unpack (mode, data) tuples
for mode, chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode=["updates", "custom"],
):
    print(mode)   # "updates" or "custom"
    print(chunk)  # payload
```

v2 格式还改进了 `invoke()`——它返回一个带有 `.value` 和 `.interrupts` 属性的 `GraphOutput` 对象，把状态与中断元数据清晰地分离开来：

```python
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Hello"}]},
    version="v2",
)
print(result.value)       # state (dict, Pydantic model, or dataclass)
print(result.interrupts)  # tuple of Interrupt objects (empty if none)
```

关于 v2 格式的更多细节，包括类型收窄、Pydantic/dataclass 强制转换和子图流式输出，参见 [LangGraph 流式输出文档](/oss/python/langgraph/streaming#stream-output-format-v2)。

## 相关

* [前端流式输出](/oss/python/langchain/frontend/overview)——使用 [`useStream`](https://reference.langchain.com/javascript/langchain-react/index/useStream) 构建 React UI 以实现实时代理交互
* [聊天模型的流式输出](/oss/python/langchain/models#stream)——直接从一个聊天模型流式输出 token，而不使用代理或图
* [聊天模型的推理](/oss/python/langchain/models#reasoning)——配置并访问聊天模型的推理输出
* [标准内容块](/oss/python/langchain/messages#standard-content-blocks)——理解用于推理、文本和其他内容类型的规范化内容块格式
* [人机协同下的流式输出](/oss/python/langchain/human-in-the-loop#streaming-with-human-in-the-loop)——在处理供人工审核的中断时流式输出代理进度
* [LangGraph 流式输出](/oss/python/langgraph/streaming)——高级流式选项，包括 `values`、`debug` 模式和子图流式输出

# 结构化输出

结构化输出允许代理以特定、可预测的格式返回数据。你无需解析自然语言响应，而是可以直接获得应用可以使用的、以 JSON 对象、[Pydantic 模型](https://docs.pydantic.dev/latest/concepts/models/#basic-model-usage)或 dataclass 形式呈现的结构化数据。

> 提示：本页介绍使用 `create_agent` 的代理结构化输出。要在模型上直接使用结构化输出（不经过代理），参见[模型 - 结构化输出](/oss/python/langchain/models#structured-output)。

LangChain 的 [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 会自动处理结构化输出。用户设置他们期望的结构化输出 schema，当模型生成结构化数据时，它会被捕获、校验，并通过代理状态的 `'structured_response'` 键返回。

```python
def create_agent(
    ...
    response_format: Union[
        ToolStrategy[StructuredResponseT],
        ProviderStrategy[StructuredResponseT],
        type[StructuredResponseT],
        None,
    ]
)
```

## 响应格式

使用 `response_format` 控制代理如何返回结构化数据：

* **`ToolStrategy[StructuredResponseT]`**：使用工具调用实现结构化输出
* **`ProviderStrategy[StructuredResponseT]`**：使用提供商原生的结构化输出
* **`type[StructuredResponseT]`**：schema 类型——根据模型能力自动选择最佳策略
* **`None`**：不显式请求结构化输出

当直接提供 schema 类型时，LangChain 会自动选择：

* 如果所选的模型和提供商支持原生结构化输出（例如 [OpenAI](/oss/python/integrations/providers/openai)、[Anthropic (Claude)](/oss/python/integrations/providers/anthropic) 或 [xAI (Grok)](/oss/python/integrations/providers/xai)），则选择 `ProviderStrategy`。
* 对所有其他模型选择 `ToolStrategy`。

> 警告：JSON Schema 字典必须用显式策略（`ProviderStrategy` 或 `ToolStrategy`）包装。直接传给 `response_format` 时不会被自动识别。

> 注意：如果使用 `langchain>=1.1`，对原生结构化输出特性的支持情况会从模型的[配置文件数据](/oss/python/langchain/models#model-profiles)中动态读取。如果数据不可用，请使用其他条件或手动指定：
>
> ```python
> custom_profile = {
>     "structured_output": True,
>     # ...
> }
> model = init_chat_model("...", profile=custom_profile)
> ```
>
> 如果指定了工具，模型必须支持同时使用工具和结构化输出。

结构化响应通过代理最终状态的 `structured_response` 键返回。

## 提供商策略

一些模型提供商通过它们的 API 原生支持结构化输出（例如 OpenAI、xAI (Grok)、Gemini、Anthropic (Claude)）。在可用时，这是最可靠的方法。

要使用此策略，请配置 `ProviderStrategy`：

```python
class ProviderStrategy(Generic[SchemaT]):
    schema: type[SchemaT]
    strict: bool | None = None
```

> 信息：`strict` 参数需要 `langchain>=1.2`。

**`schema`**（必需）：定义结构化输出格式的 schema。支持：

* **Pydantic 模型**：带字段校验的 `BaseModel` 子类。返回经过校验的 Pydantic 实例。
* **Dataclass**：带类型注解的 Python dataclass。返回 dict。
* **TypedDict**：类型化字典类。返回 dict。
* **JSON Schema**：带有 JSON schema 规范的字典。必须包含顶层的 `title` 和 `description` 键。返回 dict。

**`strict`**：可选的布尔参数，用于启用严格的 schema 遵从。部分提供商支持（例如 [OpenAI](/oss/python/integrations/chat/openai) 和 [xAI](/oss/python/integrations/chat/xai)）。默认为 `None`（禁用）。

当你把 schema 类型直接传给 [`create_agent.response_format`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 且模型支持原生结构化输出时，LangChain 会自动使用 `ProviderStrategy`：

**Pydantic 模型**：

```python
from pydantic import BaseModel, Field
from langchain.agents import create_agent

class ContactInfo(BaseModel):
    """Contact information for a person."""
    name: str = Field(description="The name of the person")
    email: str = Field(description="The email address of the person")
    phone: str = Field(description="The phone number of the person")

agent = create_agent(
    model="gpt-5.5",
    response_format=ContactInfo  # Auto-selects ProviderStrategy
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Extract contact info from: John Doe, john@example.com, (555) 123-4567"}]
})

print(result["structured_response"])
# ContactInfo(name='John Doe', email='john@example.com', phone='(555) 123-4567')
```

**Dataclass**：

```python
from dataclasses import dataclass
from langchain.agents import create_agent

@dataclass
class ContactInfo:
    """Contact information for a person."""
    name: str # The name of the person
    email: str # The email address of the person
    phone: str # The phone number of the person

agent = create_agent(
    model="gpt-5.5",
    tools=tools,
    response_format=ContactInfo  # Auto-selects ProviderStrategy
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Extract contact info from: John Doe, john@example.com, (555) 123-4567"}]
})

result["structured_response"]
# {'name': 'John Doe', 'email': 'john@example.com', 'phone': '(555) 123-4567'}
```

**TypedDict**：

```python
from typing_extensions import TypedDict
from langchain.agents import create_agent

class ContactInfo(TypedDict):
    """Contact information for a person."""
    name: str # The name of the person
    email: str # The email address of the person
    phone: str # The phone number of the person

agent = create_agent(
    model="gpt-5.5",
    tools=tools,
    response_format=ContactInfo  # Auto-selects ProviderStrategy
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Extract contact info from: John Doe, john@example.com, (555) 123-4567"}]
})

result["structured_response"]
# {'name': 'John Doe', 'email': 'john@example.com', 'phone': '(555) 123-4567'}
```

**JSON Schema**：

```python
from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy

contact_info_schema = {
    "title": "ContactInfo",
    "type": "object",
    "description": "Contact information for a person.",
    "properties": {
        "name": {"type": "string", "description": "The name of the person"},
        "email": {"type": "string", "description": "The email address of the person"},
        "phone": {"type": "string", "description": "The phone number of the person"}
    },
    "required": ["name", "email", "phone"]
}

agent = create_agent(
    model="gpt-5.5",
    tools=tools,
    response_format=ProviderStrategy(contact_info_schema)
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Extract contact info from: John Doe, john@example.com, (555) 123-4567"}]
})

result["structured_response"]
# {'name': 'John Doe', 'email': 'john@example.com', 'phone': '(555) 123-4567'}
```

提供商原生的结构化输出提供高可靠性和严格的校验，因为模型提供商强制执行 schema。在可用时使用它。

> 注意：如果提供商对你选择的模型原生支持结构化输出，写 `response_format=ProductReview` 与写 `response_format=ProviderStrategy(ProductReview)` 在功能上是等价的。
>
> 无论哪种情况，如果不支持结构化输出，代理都会回退到工具调用策略。

## 工具调用策略

对于不支持原生结构化输出的模型，LangChain 使用工具调用达到同样的效果。这适用于所有支持工具调用的模型（大多数现代模型）。

要使用此策略，请配置 `ToolStrategy`：

```python
class ToolStrategy(Generic[SchemaT]):
    schema: type[SchemaT]
    tool_message_content: str | None
    handle_errors: Union[
        bool,
        str,
        type[Exception],
        tuple[type[Exception], ...],
        Callable[[Exception], str],
    ]
```

**`schema`**（必需）：定义结构化输出格式的 schema。支持：

* **Pydantic 模型**：带字段校验的 `BaseModel` 子类。返回经过校验的 Pydantic 实例。
* **Dataclass**：带类型注解的 Python dataclass。返回 dict。
* **TypedDict**：类型化字典类。返回 dict。
* **JSON Schema**：带有 JSON schema 规范的字典。必须包含顶层的 `title` 和 `description` 键。返回 dict。
* **联合类型**：多个 schema 选项。模型会根据上下文选择最合适的 schema。

**`tool_message_content`**：生成结构化输出时返回的工具消息的自定义内容。如果未提供，默认为一条显示结构化响应数据的消息。

**`handle_errors`**：结构化输出校验失败时的错误处理策略。默认为 `True`。

* **`True`**：用默认错误模板捕获所有错误
* **`str`**：用这条自定义消息捕获所有错误
* **`type[Exception]`**：仅用默认消息捕获这种异常类型
* **`tuple[type[Exception], ...]`**：仅用默认消息捕获这些异常类型
* **`Callable[[Exception], str]`**：返回错误消息的自定义函数
* **`False`**：不重试，让异常向上传播

**Pydantic 模型**：

```python
from pydantic import BaseModel, Field
from typing import Literal
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

class ProductReview(BaseModel):
    """Analysis of a product review."""
    rating: int | None = Field(description="The rating of the product", ge=1, le=5)
    sentiment: Literal["positive", "negative"] = Field(description="The sentiment of the review")
    key_points: list[str] = Field(description="The key points of the review. Lowercase, 1-3 words each.")

agent = create_agent(
    model="gpt-5.5",
    tools=tools,
    response_format=ToolStrategy(ProductReview)
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Analyze this review: 'Great product: 5 out of 5 stars. Fast shipping, but expensive'"}]
})
result["structured_response"]
# ProductReview(rating=5, sentiment='positive', key_points=['fast shipping', 'expensive'])
```

**Dataclass**：

```python
from dataclasses import dataclass
from typing import Literal
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

@dataclass
class ProductReview:
    """Analysis of a product review."""
    rating: int | None  # The rating of the product (1-5)
    sentiment: Literal["positive", "negative"]  # The sentiment of the review
    key_points: list[str]  # The key points of the review

agent = create_agent(
    model="gpt-5.5",
    tools=tools,
    response_format=ToolStrategy(ProductReview)
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Analyze this review: 'Great product: 5 out of 5 stars. Fast shipping, but expensive'"}]
})
result["structured_response"]
# {'rating': 5, 'sentiment': 'positive', 'key_points': ['fast shipping', 'expensive']}
```

**TypedDict**：

```python
from typing import Literal
from typing_extensions import TypedDict
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

class ProductReview(TypedDict):
    """Analysis of a product review."""
    rating: int | None  # The rating of the product (1-5)
    sentiment: Literal["positive", "negative"]  # The sentiment of the review
    key_points: list[str]  # The key points of the review

agent = create_agent(
    model="gpt-5.5",
    tools=tools,
    response_format=ToolStrategy(ProductReview)
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Analyze this review: 'Great product: 5 out of 5 stars. Fast shipping, but expensive'"}]
})
result["structured_response"]
# {'rating': 5, 'sentiment': 'positive', 'key_points': ['fast shipping', 'expensive']}
```

**JSON Schema**：

```python
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

product_review_schema = {
    "title": "ProductReview",
    "type": "object",
    "description": "Analysis of a product review.",
    "properties": {
        "rating": {
            "type": ["integer", "null"],
            "description": "The rating of the product (1-5)",
            "minimum": 1,
            "maximum": 5
        },
        "sentiment": {
            "type": "string",
            "enum": ["positive", "negative"],
            "description": "The sentiment of the review"
        },
        "key_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The key points of the review"
        }
    },
    "required": ["sentiment", "key_points"]
}

agent = create_agent(
    model="gpt-5.5",
    tools=tools,
    response_format=ToolStrategy(product_review_schema)
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Analyze this review: 'Great product: 5 out of 5 stars. Fast shipping, but expensive'"}]
})
result["structured_response"]
# {'rating': 5, 'sentiment': 'positive', 'key_points': ['fast shipping', 'expensive']}
```

**联合类型**：

```python
from pydantic import BaseModel, Field
from typing import Literal, Union
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

class ProductReview(BaseModel):
    """Analysis of a product review."""
    rating: int | None = Field(description="The rating of the product", ge=1, le=5)
    sentiment: Literal["positive", "negative"] = Field(description="The sentiment of the review")
    key_points: list[str] = Field(description="The key points of the review. Lowercase, 1-3 words each.")

class CustomerComplaint(BaseModel):
    """A customer complaint about a product or service."""
    issue_type: Literal["product", "service", "shipping", "billing"] = Field(description="The type of issue")
    severity: Literal["low", "medium", "high"] = Field(description="The severity of the complaint")
    description: str = Field(description="Brief description of the complaint")

agent = create_agent(
    model="gpt-5.5",
    tools=tools,
    response_format=ToolStrategy(Union[ProductReview, CustomerComplaint])
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Analyze this review: 'Great product: 5 out of 5 stars. Fast shipping, but expensive'"}]
})
result["structured_response"]
# ProductReview(rating=5, sentiment='positive', key_points=['fast shipping', 'expensive'])
```

### 自定义工具消息内容

`tool_message_content` 参数允许你自定义生成结构化输出时出现在会话历史记录中的消息：

```python
from pydantic import BaseModel, Field
from typing import Literal
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

class MeetingAction(BaseModel):
    """Action items extracted from a meeting transcript."""
    task: str = Field(description="The specific task to be completed")
    assignee: str = Field(description="Person responsible for the task")
    priority: Literal["low", "medium", "high"] = Field(description="Priority level")

agent = create_agent(
    model="gpt-5.5",
    tools=[],
    response_format=ToolStrategy(
        schema=MeetingAction,
        tool_message_content="Action item captured and added to meeting notes!"
    )
)

agent.invoke({
    "messages": [{"role": "user", "content": "From our meeting: Sarah needs to update the project timeline as soon as possible"}]
})
```

```
================================ Human Message =================================

From our meeting: Sarah needs to update the project timeline as soon as possible
================================== Ai Message ==================================
Tool Calls:
  MeetingAction (call_1)
 Call ID: call_1
  Args:
    task: Update the project timeline
    assignee: Sarah
    priority: high
================================= Tool Message =================================
Name: MeetingAction

Action item captured and added to meeting notes!
```

如果没有 `tool_message_content`，我们最终的 [`ToolMessage`](https://reference.langchain.com/python/langchain-core/messages/tool/ToolMessage) 会是：

```
================================= Tool Message =================================
Name: MeetingAction

Returning structured response: {'task': 'update the project timeline', 'assignee': 'Sarah', 'priority': 'high'}
```

### 错误处理

模型在通过工具调用生成结构化输出时可能会犯错。LangChain 提供智能重试机制来自动处理这些错误。

#### 多个结构化输出错误

当模型错误地调用多个结构化输出工具时，代理会在 [`ToolMessage`](https://reference.langchain.com/python/langchain-core/messages/tool/ToolMessage) 中提供错误反馈，并提示模型重试：

```python
from pydantic import BaseModel, Field
from typing import Union
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

class ContactInfo(BaseModel):
    name: str = Field(description="Person's name")
    email: str = Field(description="Email address")

class EventDetails(BaseModel):
    event_name: str = Field(description="Name of the event")
    date: str = Field(description="Event date")

agent = create_agent(
    model="gpt-5.5",
    tools=[],
    response_format=ToolStrategy(Union[ContactInfo, EventDetails])  # Default: handle_errors=True
)

agent.invoke({
    "messages": [{"role": "user", "content": "Extract info: John Doe (john@email.com) is organizing Tech Conference on March 15th"}]
})
```

```
================================ Human Message =================================

Extract info: John Doe (john@email.com) is organizing Tech Conference on March 15th
None
================================== Ai Message ==================================
Tool Calls:
  ContactInfo (call_1)
 Call ID: call_1
  Args:
    name: John Doe
    email: john@email.com
  EventDetails (call_2)
 Call ID: call_2
  Args:
    event_name: Tech Conference
    date: March 15th
================================= Tool Message =================================
Name: ContactInfo

Error: Model incorrectly returned multiple structured responses (ContactInfo, EventDetails) when only one is expected.
 Please fix your mistakes.
================================= Tool Message =================================
Name: EventDetails

Error: Model incorrectly returned multiple structured responses (ContactInfo, EventDetails) when only one is expected.
 Please fix your mistakes.
================================== Ai Message ==================================
Tool Calls:
  ContactInfo (call_3)
 Call ID: call_3
  Args:
    name: John Doe
    email: john@email.com
================================= Tool Message =================================
Name: ContactInfo

Returning structured response: {'name': 'John Doe', 'email': 'john@email.com'}
```

#### Schema 校验错误

当结构化输出与预期 schema 不匹配时，代理会提供具体的错误反馈：

```python
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

class ProductRating(BaseModel):
    rating: int | None = Field(description="Rating from 1-5", ge=1, le=5)
    comment: str = Field(description="Review comment")

agent = create_agent(
    model="gpt-5.5",
    tools=[],
    response_format=ToolStrategy(ProductRating),  # Default: handle_errors=True
    system_prompt="You are a helpful assistant that parses product reviews. Do not make any field or value up."
)

agent.invoke({
    "messages": [{"role": "user", "content": "Parse this: Amazing product, 10/10!"}]
})
```

```
================================ Human Message =================================

Parse this: Amazing product, 10/10!
================================== Ai Message ==================================
Tool Calls:
  ProductRating (call_1)
 Call ID: call_1
  Args:
    rating: 10
    comment: Amazing product
================================= Tool Message =================================
Name: ProductRating

Error: Failed to parse structured output for tool 'ProductRating': 1 validation error for ProductRating.rating
  Input should be less than or equal to 5 [type=less_than_equal, input_value=10, input_type=int].
 Please fix your mistakes.
================================== Ai Message ==================================
Tool Calls:
  ProductRating (call_2)
 Call ID: call_2
  Args:
    rating: 5
    comment: Amazing product
================================= Tool Message =================================
Name: ProductRating

Returning structured response: {'rating': 5, 'comment': 'Amazing product'}
```

#### 错误处理策略

你可以使用 `handle_errors` 参数自定义错误的处理方式：

**自定义错误消息：**

```python
ToolStrategy(
    schema=ProductRating,
    handle_errors="Please provide a valid rating between 1-5 and include a comment."
)
```

如果 `handle_errors` 是字符串，代理将*始终*用一条固定的工具消息提示模型重试：

```
================================= Tool Message =================================
Name: ProductRating

Please provide a valid rating between 1-5 and include a comment.
```

**仅处理特定异常：**

```python
ToolStrategy(
    schema=ProductRating,
    handle_errors=ValueError  # Only retry on ValueError, raise others
)
```

如果 `handle_errors` 是异常类型，代理将仅在引发的异常是指定类型时重试（使用默认错误消息）。在所有其他情况下，异常会被抛出。

**处理多种异常类型：**

```python
ToolStrategy(
    schema=ProductRating,
    handle_errors=(ValueError, TypeError)  # Retry on ValueError and TypeError
)
```

如果 `handle_errors` 是异常元组，代理将仅在引发的异常是指定类型之一时重试（使用默认错误消息）。在所有其他情况下，异常会被抛出。

**自定义错误处理函数：**

```python

from langchain.agents.structured_output import StructuredOutputValidationError
from langchain.agents.structured_output import MultipleStructuredOutputsError

def custom_error_handler(error: Exception) -> str:
    if isinstance(error, StructuredOutputValidationError):
        return "There was an issue with the format. Try again."
    elif isinstance(error, MultipleStructuredOutputsError):
        return "Multiple structured outputs were returned. Pick the most relevant one."
    else:
        return f"Error: {str(error)}"

agent = create_agent(
    model="gpt-5.5",
    tools=[],
    response_format=ToolStrategy(
                        schema=Union[ContactInfo, EventDetails],
                        handle_errors=custom_error_handler
                    )  # Default: handle_errors=True
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Extract info: John Doe (john@email.com) is organizing Tech Conference on March 15th"}]
})

for msg in result['messages']:
    # If message is actually a ToolMessage object (not a dict), check its class name
    if type(msg).__name__ == "ToolMessage":
        print(msg.content)
    # If message is a dictionary or you want a fallback
    elif isinstance(msg, dict) and msg.get('tool_call_id'):
        print(msg['content'])

```

在 `StructuredOutputValidationError` 时：

```
================================= Tool Message =================================
Name: ToolStrategy

There was an issue with the format. Try again.
```

在 `MultipleStructuredOutputsError` 时：

```
================================= Tool Message =================================
Name: ToolStrategy

Multiple structured outputs were returned. Pick the most relevant one.
```

在其他错误时：

```
================================= Tool Message =================================
Name: ToolStrategy

Error: <error message>
```

**不进行错误处理：**

```python
response_format = ToolStrategy(
    schema=ProductRating,
    handle_errors=False  # All errors raised
)
```

# 短期记忆

## 概述

记忆（memory）是一种记住之前交互信息的系统。对于 AI 代理来说，记忆至关重要，因为它能让代理记住之前的交互、从反馈中学习，并适应用户的偏好。随着代理处理包含大量用户交互的越来越复杂的任务，这一能力对于效率和用户满意度都变得不可或缺。

短期记忆让你的应用能够在单个线程或对话中记住之前的交互。

> 注意：线程（thread）在会话中组织多次交互，类似于电子邮件将消息分组到同一对话中的方式。

对话历史是短期记忆最常见的形式。长时间的对话对当今的 LLM 来说是一个挑战：完整的历史可能无法放入 LLM 的上下文窗口，从而导致上下文丢失或错误。

即使你的模型支持完整的上下文长度，大多数 LLM 在处理长上下文时仍然表现不佳。它们会被过时或无关的内容"分心"，同时还遭受响应速度变慢和成本升高的困扰。

聊天模型通过[消息](/oss/python/langchain/messages)接收上下文，消息包括指令（系统消息）和输入（人类消息）。在聊天应用中，消息在人类输入和模型响应之间交替，形成随时间不断变长的消息列表。由于上下文窗口有限，许多应用可以通过使用删除或"遗忘"过时信息的技术来获益。

> 提示：需要在**跨**会话之间记住信息？请使用[长期记忆](/oss/python/langchain/long-term-memory)，在不同的线程和会话之间存储和回忆用户特定或应用级的数据。

## 用法

要给代理添加短期记忆（线程级持久化），你需要在创建代理时指定一个 `checkpointer`。

> 信息：LangChain 的代理将短期记忆作为代理状态（state）的一部分进行管理。
>
> 通过将这些内容存储在图的 state 中，代理可以在保持不同线程之间相互隔离的同时，访问给定对话的完整上下文。
>
> 状态通过检查点（checkpointer）持久化到数据库（或内存）中，以便线程可以随时恢复。
>
> 短期记忆在代理被调用或某个步骤（如工具调用）完成时更新，并在每个步骤开始时读取状态。

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

def get_user_info() -> str:
    """Look up information about the current user."""
    return "No user profile on file."

agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[get_user_info],
    checkpointer=InMemorySaver(),
)

thread_config = {"configurable": {"thread_id": "1"}}
response = agent.invoke(
    {"messages": [{"role": "user", "content": "Hi! My name is Bob."}]},
    thread_config,
)["messages"][-1].content

print(response)  # "Hi Bob! Nice to see you here. How are you doing?"

response = agent.invoke(
    {"messages": [{"role": "user", "content": "What's my name?"}]},
    thread_config,
)["messages"][-1].content

print(response)  # "You are Bob!"
```

### 生产环境

在生产环境中，请使用由数据库支撑的检查点：

**pip**
```bash
pip install -U langgraph-checkpoint-postgres "psycopg[binary]"
```

**uv**
```bash
uv add langgraph-checkpoint-postgres "psycopg[binary]"
```

> 注意：默认情况下，`langgraph-checkpoint-postgres` 安装不带 extras 的 `psycopg`（Psycopg 3）。上面的安装命令添加了 `psycopg[binary]`，推荐大多数用户使用。其他选项请参阅 [Psycopg 安装文档](https://www.psycopg.org/psycopg3/docs/basic/install.html)。

```python
from langchain.agents import create_agent
from langgraph.checkpoint.postgres import PostgresSaver

def get_user_info() -> str:
    """Look up information about the current user."""
    return "No user profile on file."

DB_URI = "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable"
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup() # auto create tables in PostgreSQL
    agent = create_agent(
        "gpt-5.5",
        tools=[get_user_info],
        checkpointer=checkpointer,
    )
```

> 注意：更多检查点选项（包括 SQLite、Postgres 和 Azure Cosmos DB），请参阅持久化文档中的[检查点库列表](/oss/python/langgraph/checkpointers#checkpointer-libraries)。

## 自定义代理记忆

默认情况下，代理使用 [`AgentState`](https://reference.langchain.com/python/langchain/agents/middleware/types/AgentState) 来管理短期记忆，具体来说是通过 `messages` 键管理对话历史。

你可以扩展 [`AgentState`](https://reference.langchain.com/python/langchain/agents/middleware/types/AgentState) 来添加额外的字段。自定义状态模式通过 [`state_schema`](https://reference.langchain.com/python/langchain/middleware/#langchain.agents.middleware.AgentMiddleware.state_schema) 参数传给 [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent)。

```python
from langchain.agents import create_agent, AgentState
from langgraph.checkpoint.memory import InMemorySaver

class CustomAgentState(AgentState):
    user_id: str
    preferences: dict

agent = create_agent(
    "gpt-5.5",
    tools=[get_user_info],
    state_schema=CustomAgentState,
    checkpointer=InMemorySaver(),
)

# Custom state can be passed in invoke
result = agent.invoke(
    {
        "messages": [{"role": "user", "content": "Hello"}],
        "user_id": "user_123",
        "preferences": {"theme": "dark"}
    },
    {"configurable": {"thread_id": "1"}})
```

## 常见模式

启用[短期记忆](#usage)后，长时间对话可能会超出 LLM 的上下文窗口。常见的解决方案有：

- **裁剪消息**（[Trim messages](#trim-messages)）— 在调用 LLM 之前移除前 N 条或后 N 条消息
- **删除消息**（[Delete messages](#delete-messages)）— 从 LangGraph 状态中永久删除消息
- **总结消息**（[Summarize messages](#summarize-messages)）— 总结历史中较早的消息，并用摘要替换它们
- **自定义策略** — 自定义策略（例如消息过滤等）

这样，代理就能在不超出 LLM 上下文窗口的情况下跟踪对话。

### 裁剪消息

大多数 LLM 都有最大支持的上下文窗口（以 token 计）。

决定何时截断消息的一种方法是：统计消息历史中的 token 数，当接近该限制时进行截断。如果你使用 LangChain，可以使用裁剪消息工具，指定要从列表中保留的 token 数量，以及用于处理边界的 `strategy`（例如保留最后 `max_tokens` 条）。

要在代理中裁剪消息历史，请使用 [`@before_model`](https://reference.langchain.com/python/langchain/agents/middleware/types/before_model) 中间件装饰器：

```python
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import before_model
from langgraph.runtime import Runtime
from langchain_core.runnables import RunnableConfig
from typing import Any

@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Keep only the last few messages to fit context window."""
    messages = state["messages"]

    if len(messages) <= 3:
        return None  # No changes needed

    first_msg = messages[0]
    recent_messages = messages[-3:] if len(messages) % 2 == 0 else messages[-4:]
    new_messages = [first_msg] + recent_messages

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }

agent = create_agent(
    "gpt-5.5",
    tools=[...],
    middleware=[trim_messages],
    checkpointer=InMemorySaver(),
)

config: RunnableConfig = {"configurable": {"thread_id": "1"}}

agent.invoke({"messages": "hi, my name is bob"}, config)
agent.invoke({"messages": "write a short poem about cats"}, config)
agent.invoke({"messages": "now do the same but for dogs"}, config)
final_response = agent.invoke({"messages": "what's my name?"}, config)

final_response["messages"][-1].pretty_print()
"""
================================== Ai Message ==================================

Your name is Bob. You told me that earlier.
If you'd like me to call you a nickname or use a different name, just say the word.
"""
```

### 删除消息

你可以从图状态中删除消息来管理消息历史。

当你想要移除特定消息或清空整个消息历史时，这很有用。

要从图状态中删除消息，可以使用 `RemoveMessage`。

要让 `RemoveMessage` 生效，你需要使用带有 [`add_messages`](https://reference.langchain.com/python/langgraph/graph/message/add_messages) [reducer](/oss/python/langgraph/graph-api#reducers) 的状态键。

默认的 [`AgentState`](https://reference.langchain.com/python/langchain/agents/middleware/types/AgentState) 就提供了这一点。

要删除特定消息：

```python
from langchain.messages import RemoveMessage

def delete_messages(state):
    messages = state["messages"]
    if len(messages) > 2:
        # remove the earliest two messages
        return {"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}
```

要删除**所有**消息：

```python
from langgraph.graph.message import REMOVE_ALL_MESSAGES

def delete_messages(state):
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)]}
```

> 警告：删除消息时，**务必确保**生成的消息历史是有效的。请检查你所使用的 LLM 提供商的限制。例如：
>
> - 有些提供商要求消息历史以 `user` 消息开头
> - 大多数提供商要求带工具调用的 `assistant` 消息后面必须跟相应的 `tool` 结果消息

```python
from langchain.messages import RemoveMessage
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import after_model
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.runtime import Runtime
from langchain_core.runnables import RunnableConfig

@after_model
def delete_old_messages(state: AgentState, runtime: Runtime) -> dict | None:
    """Remove old messages to keep conversation manageable."""
    messages = state["messages"]
    if len(messages) > 2:
        # remove the earliest two messages
        return {"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}
    return None

agent = create_agent(
    "gpt-5-nano",
    tools=[...],
    system_prompt="Please be concise and to the point.",
    middleware=[delete_old_messages],
    checkpointer=InMemorySaver(),
)

config: RunnableConfig = {"configurable": {"thread_id": "1"}}

stream = agent.stream_events(
    {"messages": [{"role": "user", "content": "hi! I'm bob"}]},
    config,
    version="v3",
)
for snapshot in stream.values:
    print([(message.type, message.content) for message in snapshot["messages"]])

stream = agent.stream_events(
    {"messages": [{"role": "user", "content": "write a short poem about cats"}]},
    config,
    version="v3",
)
for snapshot in stream.values:
    print([(message.type, message.content) for message in snapshot["messages"]])

stream = agent.stream_events(
    {"messages": [{"role": "user", "content": "what's my name?"}]},
    config,
    version="v3",
)
for snapshot in stream.values:
    print([(message.type, message.content) for message in snapshot["messages"]])
```

```
[('human', "hi! I'm bob")]
[('human', "hi! I'm bob"), ('ai', 'Hi Bob! Nice to meet you. How can I help you today? I can answer questions, brainstorm ideas, draft text, explain things, or help with code.')]
[('human', "hi! I'm bob"), ('ai', 'Hi Bob! Nice to meet you. How can I help you today? I can answer questions, brainstorm ideas, draft text, explain things, or help with code.'), ('human', "write a short poem about cats")]
[('human', "hi! I'm bob"), ('ai', 'Hi Bob! Nice to meet you. How can I help you today? I can answer questions, brainstorm ideas, draft text, explain things, or help with code.'), ('human', "write a short poem about cats"), ('ai', 'There once was a cat on a wall, Who barely moved at all...')]
[('human', 'write a short poem about cats'), ('ai', 'There once was a cat on a wall, Who barely moved at all...')]
[('human', 'write a short poem about cats'), ('ai', 'There once was a cat on a wall, Who barely moved at all...'), ('human', "what's my name?")]
[('human', 'write a short poem about cats'), ('ai', 'There once was a cat on a wall, Who barely moved at all...'), ('human', "what's my name?"), ('ai', "I don't know your name - you haven't told me!")]
[('human', "what's my name?"), ('ai', "I don't know your name - you haven't told me!")]
```

### 总结消息

如上所示，裁剪或删除消息的问题在于，你可能会因为削减消息队列而丢失信息。
因此，一些应用受益于一种更精细的方法：使用聊天模型来总结消息历史。

（该小节中的示意图 summary.png 仅用于展示总结流程，此处省略。）

要在代理中总结消息历史，请使用内置的 [`SummarizationMiddleware`](/oss/python/langchain/middleware#summarization)：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.runnables import RunnableConfig

checkpointer = InMemorySaver()

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger=("tokens", 4000),
            keep=("messages", 20)
        )
    ],
    checkpointer=checkpointer,
)

config: RunnableConfig = {"configurable": {"thread_id": "1"}}
agent.invoke({"messages": "hi, my name is bob"}, config)
agent.invoke({"messages": "write a short poem about cats"}, config)
agent.invoke({"messages": "now do the same but for dogs"}, config)
final_response = agent.invoke({"messages": "what's my name?"}, config)

final_response["messages"][-1].pretty_print()
"""
================================== Ai Message ==================================

Your name is Bob!
"""
```

更多配置选项请参阅 [`SummarizationMiddleware`](/oss/python/langchain/middleware#summarization)。

## 访问记忆

你可以通过多种方式访问和修改代理的短期记忆（状态）：

### 工具

#### 在工具中读取短期记忆

使用 `runtime` 参数（类型为 `ToolRuntime`）在工具中访问短期记忆（状态）。

`runtime` 参数对工具签名是隐藏的（因此模型看不到它），但工具可以通过它访问状态。

```python
from langchain.agents import create_agent, AgentState
from langchain.tools import tool, ToolRuntime

class CustomState(AgentState):
    user_id: str

@tool
def get_user_info(
    runtime: ToolRuntime
) -> str:
    """Look up user info."""
    user_id = runtime.state["user_id"]
    return "User is John Smith" if user_id == "user_123" else "Unknown user"

agent = create_agent(
    model="gpt-5-nano",
    tools=[get_user_info],
    state_schema=CustomState,
)

result = agent.invoke({
    "messages": "look up user information",
    "user_id": "user_123"
})
print(result["messages"][-1].content)
# > User is John Smith.
```

#### 从工具写入短期记忆

要在执行期间修改代理的短期记忆（状态），你可以直接从工具返回状态更新。

这对于持久化中间结果或让后续工具或提示词能够访问信息非常有用。

```python
from langchain.tools import tool, ToolRuntime
from langchain_core.runnables import RunnableConfig
from langchain.messages import ToolMessage
from langchain.agents import create_agent, AgentState
from langgraph.types import Command
from pydantic import BaseModel

class CustomState(AgentState):
    user_name: str

class CustomContext(BaseModel):
    user_id: str

@tool
def update_user_info(
    runtime: ToolRuntime[CustomContext, CustomState],
) -> Command:
    """Look up and update user info."""
    user_id = runtime.context.user_id
    name = "John Smith" if user_id == "user_123" else "Unknown user"
    return Command(update={
        "user_name": name,
        # update the message history
        "messages": [
            ToolMessage(
                "Successfully looked up user information",
                tool_call_id=runtime.tool_call_id
            )
        ]
    })

@tool
def greet(
    runtime: ToolRuntime[CustomContext, CustomState]
) -> str | Command:
    """Use this to greet the user once you found their info."""
    user_name = runtime.state.get("user_name", None)
    if user_name is None:
       return Command(update={
            "messages": [
                ToolMessage(
                    "Please call the 'update_user_info' tool it will get and update the user's name.",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        })
    return f"Hello {user_name}!"

agent = create_agent(
    model="gpt-5-nano",
    tools=[update_user_info, greet],
    state_schema=CustomState,
    context_schema=CustomContext,
)

agent.invoke(
    {"messages": [{"role": "user", "content": "greet the user"}]},
    context=CustomContext(user_id="user_123"),
)
```

### 提示词

在中间件中访问短期记忆（状态），根据对话历史或自定义状态字段创建动态提示词。

```python
from langchain.agents import create_agent
from typing import TypedDict
from langchain.agents.middleware import dynamic_prompt, ModelRequest

class CustomContext(TypedDict):
    user_name: str

def get_weather(city: str) -> str:
    """Get the weather in a city."""
    return f"The weather in {city} is always sunny!"

@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    user_name = request.runtime.context["user_name"]
    system_prompt = f"You are a helpful assistant. Address the user as {user_name}."
    return system_prompt

agent = create_agent(
    model="gpt-5-nano",
    tools=[get_weather],
    middleware=[dynamic_system_prompt],
    context_schema=CustomContext,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    context=CustomContext(user_name="John Smith"),
)
for msg in result["messages"]:
    msg.pretty_print()
```

```shell
================================ Human Message =================================

What is the weather in SF?
================================== Ai Message ==================================
Tool Calls:
  get_weather (call_WFQlOGn4b2yoJrv7cih342FG)
 Call ID: call_WFQlOGn4b2yoJrv7cih342FG
  Args:
    city: San Francisco
================================= Tool Message =================================
Name: get_weather

The weather in San Francisco is always sunny!
================================== Ai Message ==================================

Hi John Smith, the weather in San Francisco is always sunny!
```

### 模型调用前

在 [`@before_model`](https://reference.langchain.com/python/langchain/agents/middleware/types/before_model) 中间件中访问短期记忆（状态），在模型调用之前处理消息。

（该小节中的 Mermaid 流程图展示了 before_model 的位置：`__start__` → before_model → model，工具结果会循环回 before_model。）

```python
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import before_model
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from typing import Any

@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Keep only the last few messages to fit context window."""
    messages = state["messages"]

    if len(messages) <= 3:
        return None  # No changes needed

    first_msg = messages[0]
    recent_messages = messages[-3:] if len(messages) % 2 == 0 else messages[-4:]
    new_messages = [first_msg] + recent_messages

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }

agent = create_agent(
    "gpt-5-nano",
    tools=[],
    middleware=[trim_messages],
    checkpointer=InMemorySaver()
)

config: RunnableConfig = {"configurable": {"thread_id": "1"}}

agent.invoke({"messages": "hi, my name is bob"}, config)
agent.invoke({"messages": "write a short poem about cats"}, config)
agent.invoke({"messages": "now do the same but for dogs"}, config)
final_response = agent.invoke({"messages": "what's my name?"}, config)

final_response["messages"][-1].pretty_print()
"""
================================== Ai Message ==================================

Your name is Bob. You told me that earlier.
If you'd like me to call you a nickname or use a different name, just say the word.
"""
```

### 模型调用后

在 [`@after_model`](https://reference.langchain.com/python/langchain/agents/middleware/types/after_model) 中间件中访问短期记忆（状态），在模型调用之后处理消息。

（该小节中的 Mermaid 流程图展示了 after_model 的位置：`__start__` → model → after_model，工具结果会循环回 model。）

```python
from langchain.messages import RemoveMessage
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import after_model
from langgraph.runtime import Runtime

@after_model
def validate_response(state: AgentState, runtime: Runtime) -> dict | None:
    """Remove messages containing sensitive words."""
    STOP_WORDS = ["password", "secret"]
    last_message = state["messages"][-1]
    if any(word in last_message.content for word in STOP_WORDS):
        return {"messages": [RemoveMessage(id=last_message.id)]}
    return None

agent = create_agent(
    model="gpt-5-nano",
    tools=[],
    middleware=[validate_response],
    checkpointer=InMemorySaver(),
)
```

---

# 长期记忆

> 为 LangChain 代理添加长期记忆，以跨对话和会话存储和回忆数据。

长期记忆让代理能够跨不同的对话和会话存储和回忆信息。
与[短期记忆](/oss/python/langchain/short-term-memory)（其作用范围仅限于单个线程）不同，长期记忆跨线程持久存在，并且可以随时回忆。

长期记忆构建在 [LangGraph 存储（stores）](/oss/python/langgraph/stores)之上，存储以 JSON 文档的形式保存数据，并按命名空间（namespace）和键（key）组织。

## 用法

要给代理添加长期记忆，请创建一个 store 并将其传给 [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent)：

**InMemoryStore**

```python
from langchain.agents import create_agent
from langchain_core.runnables import Runnable
from langgraph.store.memory import InMemoryStore

# InMemoryStore saves data to an in-memory dictionary. Use a DB-backed store in production use.
store = InMemoryStore()

agent: Runnable = create_agent(
    "claude-sonnet-4-6",
    tools=[],
    store=store,
)
```

**PostgreSQL**

**pip**
```bash
pip install -U langgraph-checkpoint-postgres "psycopg[binary]"
```

**uv**
```bash
uv add langgraph-checkpoint-postgres "psycopg[binary]"
```

> 注意：默认情况下，`langgraph-checkpoint-postgres` 安装不带 extras 的 `psycopg`（Psycopg 3）。上面的安装命令添加了 `psycopg[binary]`，推荐大多数用户使用。其他选项请参阅 [Psycopg 安装文档](https://www.psycopg.org/psycopg3/docs/basic/install.html)。

```python
from langchain.agents import create_agent
from langchain_core.runnables import Runnable
from langgraph.store.postgres import PostgresStore  # type: ignore[import-not-found]

DB_URI = "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable"

with PostgresStore.from_conn_string(DB_URI) as store:
    store.setup()
    agent: Runnable = create_agent(
        "claude-sonnet-4-6",
        tools=[],
        store=store,
    )
```

然后，工具可以使用 `runtime.store` 参数从存储中读取和写入数据。示例请参阅[在工具中读取长期记忆](#read-long-term-memory-in-tools)和[从工具写入长期记忆](#write-long-term-memory-from-tools)。

> 提示：想深入了解记忆类型（语义、情景、程序性）以及写入记忆的策略，请参阅[记忆概念指南](/oss/python/concepts/memory#long-term-memory)。

## 记忆存储

LangGraph 将长期记忆以 JSON 文档的形式存储在[store](/oss/python/langgraph/stores)中。

每条记忆都组织在自定义的 `namespace`（类似于文件夹）和独特的 `key`（类似于文件名）之下。命名空间通常包含用户或组织 ID，或其他有助于组织信息的标签。

这种结构支持记忆的分层组织。跨命名空间的搜索随后可以通过内容过滤器来实现。

**InMemoryStore**

```python
from collections.abc import Sequence

from langgraph.store.base import IndexConfig
from langgraph.store.memory import InMemoryStore

def embed(texts: Sequence[str]) -> list[list[float]]:
    # Replace with an actual embedding function or LangChain embeddings object
    return [[1.0, 2.0] for _ in texts]

# InMemoryStore saves data to an in-memory dictionary. Use a DB-backed store in production use.
store = InMemoryStore(index=IndexConfig(embed=embed, dims=2))
user_id = "my-user"
application_context = "chitchat"
namespace = (user_id, application_context)
store.put(
    namespace,
    "a-memory",
    {
        "rules": [
            "User likes short, direct language",
            "User only speaks English & python",
        ],
        "my-key": "my-value",
    },
)
# get the "memory" by ID
item = store.get(namespace, "a-memory")
# search for "memories" within this namespace, filtering on content equivalence, sorted by vector similarity
items = store.search(
    namespace, filter={"my-key": "my-value"}, query="language preferences"
)
```

**PostgreSQL**

```python
from collections.abc import Sequence

from langgraph.store.base import IndexConfig
from langgraph.store.postgres import PostgresStore  # type: ignore[import-not-found]

def embed(texts: Sequence[str]) -> list[list[float]]:
    # Replace with an actual embedding function or LangChain embeddings object
    return [[1.0, 2.0] for _ in texts]

DB_URI = "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable"

with PostgresStore.from_conn_string(
    DB_URI,
    index=IndexConfig(embed=embed, dims=2),  # type: ignore[arg-type]
) as store:
    store.setup()
    user_id = "my-user"
    application_context = "chitchat"
    namespace = (user_id, application_context)
    store.put(
        namespace,
        "a-memory",
        {
            "rules": [
                "User likes short, direct language",
                "User only speaks English & python",
            ],
            "my-key": "my-value",
        },
    )
    item = store.get(namespace, "a-memory")
    items = store.search(
        namespace, filter={"my-key": "my-value"}, query="language preferences"
    )
```

关于记忆存储的更多信息，请参阅[持久化（Persistence）](/oss/python/langgraph/stores)指南。

## 在工具中读取长期记忆

**InMemoryStore**

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.runnables import Runnable
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

# InMemoryStore saves data to an in-memory dictionary. Use a DB-backed store in production.
store = InMemoryStore()

# Write sample data to the store using the put method
store.put(
    (
        "users",
    ),  # Namespace to group related data together (users namespace for user data)
    "user_123",  # Key within the namespace (user ID as key)
    {
        "name": "John Smith",
        "language": "English",
    },  # Data to store for the given user
)

@tool
def get_user_info(runtime: ToolRuntime[Context]) -> str:
    """Look up user info."""
    # Access the store - same as that provided to `create_agent`
    assert runtime.store is not None
    user_id = runtime.context.user_id
    # Retrieve data from store - returns StoreValue object with value and metadata
    user_info = runtime.store.get(("users",), user_id)
    return str(user_info.value) if user_info else "Unknown user"

agent: Runnable = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[get_user_info],
    # Pass store to agent - enables agent to access store when running tools
    store=store,
    context_schema=Context,
)

# Run the agent
agent.invoke(
    {"messages": [{"role": "user", "content": "look up user information"}]},
    context=Context(user_id="user_123"),
)
```

**PostgreSQL**

```python
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.runnables import Runnable
from langgraph.store.postgres import PostgresStore  # type: ignore[import-not-found]

@dataclass
class Context:
    user_id: str

DB_URI = "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable"

with PostgresStore.from_conn_string(DB_URI) as store:
    store.setup()
    store.put(("users",), "user_123", {"name": "John Smith", "language": "English"})

    @tool
    def get_user_info(runtime: ToolRuntime[Context]) -> str:
        """Look up user info."""
        assert runtime.store is not None
        user_info = runtime.store.get(("users",), runtime.context.user_id)
        return str(user_info.value) if user_info else "Unknown user"

    agent: Runnable = create_agent(
        "claude-sonnet-4-6",
        tools=[get_user_info],
        store=store,
        context_schema=Context,
    )

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "look up user information"}]},
        context=Context(user_id="user_123"),
    )
```

## 从工具写入长期记忆

**InMemoryStore**

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.runnables import Runnable
from langgraph.store.memory import InMemoryStore
from typing_extensions import TypedDict

# InMemoryStore saves data to an in-memory dictionary. Use a DB-backed store in production.
store = InMemoryStore()

@dataclass
class Context:
    user_id: str

# TypedDict defines the structure of user information for the LLM
class UserInfo(TypedDict):
    name: str

# Tool that allows agent to update user information (useful for chat applications)
@tool
def save_user_info(user_info: UserInfo, runtime: ToolRuntime[Context]) -> str:
    """Save user info."""
    # Access the store - same as that provided to `create_agent`
    assert runtime.store is not None
    store = runtime.store
    user_id = runtime.context.user_id
    # Store data in the store (namespace, key, data)
    store.put(("users",), user_id, dict(user_info))
    return "Successfully saved user info."

agent: Runnable = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[save_user_info],
    store=store,
    context_schema=Context,
)

# Run the agent
agent.invoke(
    {"messages": [{"role": "user", "content": "My name is John Smith"}]},
    # user_id passed in context to identify whose information is being updated
    context=Context(user_id="user_123"),
)

# You can access the store directly to get the value
item = store.get(("users",), "user_123")
```

**PostgreSQL**

```python
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.runnables import Runnable
from langgraph.store.postgres import PostgresStore  # type: ignore[import-not-found]
from typing_extensions import TypedDict

@dataclass
class Context:
    user_id: str

class UserInfo(TypedDict):
    name: str

@tool
def save_user_info(user_info: UserInfo, runtime: ToolRuntime[Context]) -> str:
    """Save user info."""
    assert runtime.store is not None
    runtime.store.put(("users",), runtime.context.user_id, dict(user_info))
    return "Successfully saved user info."

DB_URI = "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable"

with PostgresStore.from_conn_string(DB_URI) as store:
    store.setup()
    agent: Runnable = create_agent(
        "claude-sonnet-4-6",
        tools=[save_user_info],
        store=store,
        context_schema=Context,
    )

    agent.invoke(
        {"messages": [{"role": "user", "content": "My name is John Smith"}]},
        context=Context(user_id="user_123"),
    )
```

# MCP（模型上下文协议）

[模型上下文协议（Model Context Protocol，MCP）](https://modelcontextprotocol.io/introduction) 是一种开放协议，它标准化了应用程序向 LLM 提供工具和上下文的方式。LangChain 代理可以通过使用 [`langchain-mcp-adapters`](https://github.com/langchain-ai/langchain-mcp-adapters) 库来使用 MCP 服务器上定义的工具。

## 快速开始

安装 `langchain-mcp-adapters` 库：

<CodeGroup>

**pip**
  ```bash
  pip install langchain-mcp-adapters
  ```

**uv**
  ```bash
  uv add langchain-mcp-adapters
  ```
</CodeGroup>

`langchain-mcp-adapters` 使代理能够使用在一个或多个 MCP 服务器上定义的工具。

> 注意：`MultiServerMCPClient` **默认无状态**。每次工具调用都会创建一个全新的 MCP `ClientSession`，执行工具，然后清理。更多细节请参阅[有状态会话](#stateful-sessions)部分。

**Accessing multiple MCP servers**
```python
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

async def main():
    client = MultiServerMCPClient(
        {
            "math": {
                "transport": "stdio",  # Local subprocess communication
                "command": "python",
                # Absolute path to your math_server.py file
                "args": ["/path/to/math_server.py"],
            },
            "weather": {
                "transport": "http",  # HTTP-based remote server
                # Ensure you start your weather server on port 8000
                "url": "http://localhost:8000/mcp",
            }
        }
    )

    tools = await client.get_tools()
    agent = create_agent(
        "claude-sonnet-4-6",
        tools
    )
    math_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "what's (3 + 5) x 12?"}]}
    )
    weather_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "what is the weather in nyc?"}]}
    )
    print(math_response)
    print(weather_response)

if __name__ == "__main__":
    asyncio.run(main())
```

> 提示：使用 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-mcp) 将 MCP 工具调用与代理的推理步骤一起追踪。按照[追踪快速入门](/langsmith/trace-with-langchain)进行设置。

## 自定义服务器

要创建自定义 MCP 服务器，请使用 [FastMCP](https://gofastmcp.com/getting-started/welcome) 库：

<CodeGroup>

**pip**
  ```bash
  pip install fastmcp
  ```

**uv**
  ```bash
  uv add fastmcp
  ```
</CodeGroup>

要使用 MCP 工具服务器测试你的代理，请使用以下示例：

<CodeGroup>

**server (stdio transport)"**
  ```python
  from fastmcp import FastMCP

  mcp = FastMCP("Math")

  @mcp.tool()
  def add(a: int, b: int) -> int:
      """Add two numbers"""
      return a + b

  @mcp.tool()
  def multiply(a: int, b: int) -> int:
      """Multiply two numbers"""
      return a * b

  if __name__ == "__main__":
      mcp.run(transport="stdio")
  ```

**server (streamable HTTP transport)"**
  ```python
  from fastmcp import FastMCP

  mcp = FastMCP("Weather")

  @mcp.tool()
  async def get_weather(location: str) -> str:
      """Get weather for location."""
      return "It's always sunny in New York"

  if __name__ == "__main__":
      mcp.run(transport="streamable-http")
  ```
</CodeGroup>

## 传输方式

MCP 支持不同的传输机制来实现客户端与服务器之间的通信。

### HTTP

`http` 传输方式（也称为 `streamable-http`）使用 HTTP 请求进行客户端与服务器通信。更多细节请参阅 [MCP HTTP 传输规范](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http)。

对于自己运行的服务器，可以使用本地 URL；也可以使用托管 URL，例如 [LangChain 文档 MCP 服务器](/use-these-docs)（`https://docs.langchain.com/mcp`），它是公开的，不需要 API 密钥。

```python
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient(
    {
        "mcp": {
            "transport": "http",
            # "url": "http://localhost:8000/mcp",  # Local server
            "url": "https://docs.langchain.com/mcp",  # Hosted server
        }
    }
)
tools = await client.get_tools()
agent = create_agent("openai:gpt-5.4", tools)
response = await agent.ainvoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "How do I connect LangChain to an MCP server over HTTP?",
            }
        ]
    }
)
```

#### 传递请求头

通过 HTTP 连接 MCP 服务器时，可以在连接配置中使用 `headers` 字段包含自定义请求头（例如用于身份验证或追踪）。`sse`（已被 MCP 规范弃用）和 `streamable_http` 传输方式均支持此功能。

**Passing headers with MultiServerMCPClient**
```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

client = MultiServerMCPClient(
    {
        "weather": {
            "transport": "http",
            "url": "http://localhost:8000/mcp",
            "headers": {
                "Authorization": "Bearer YOUR_TOKEN",
                "X-Custom-Header": "custom-value"
            },
        }
    }
)
tools = await client.get_tools()
agent = create_agent("openai:gpt-5.5", tools)
response = await agent.ainvoke({"messages": "what is the weather in nyc?"})
```

#### 身份验证

`langchain-mcp-adapters` 库在底层使用官方 [MCP SDK](https://github.com/modelcontextprotocol/python-sdk)，通过实现 `httpx.Auth` 接口，你可以提供自定义身份验证机制。

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient(
    {
        "weather": {
            "transport": "http",
            "url": "http://localhost:8000/mcp",
            "auth": auth,
        }
    }
)
```

* [自定义身份验证实现示例](https://github.com/modelcontextprotocol/python-sdk/blob/main/examples/clients/simple-auth-client/mcp_simple_auth_client/main.py)
* [内置 OAuth 流程](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/oauth2.py#L216)

### stdio

客户端将服务器作为子进程启动，并通过标准输入/输出进行通信。最适合本地工具和简单设置。

> 注意：与 HTTP 传输方式不同，`stdio` 连接本质上**有状态**：子进程在客户端连接的整个生命周期内持续存在。但是，当使用 `MultiServerMCPClient` 而没有显式的会话管理时，每次工具调用仍会创建新的会话。有关管理持久连接，请参阅[有状态会话](#stateful-sessions)。

```python
client = MultiServerMCPClient(
    {
        "math": {
            "transport": "stdio",
            "command": "python",
            "args": ["/path/to/math_server.py"],
        }
    }
)
```

## 有状态会话

默认情况下，`MultiServerMCPClient` **无状态**：每次工具调用都会创建全新的 MCP 会话，执行工具，然后清理。

如果需要控制 MCP 会话的[生命周期](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle)（例如，与跨工具调用维护上下文的服务器一起工作时），可以使用 `client.session()` 创建持久的 `ClientSession`。

**Using MCP ClientSession for stateful tool usage**
```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent

client = MultiServerMCPClient({...})

# Create a session explicitly
async with client.session("server_name") as session:
    # Pass the session to load tools, resources, or prompts
    tools = await load_mcp_tools(session)
    agent = create_agent(
        "google_genai:gemini-3.6-flash",
        tools
    )
```

## 核心功能

### 工具

[工具](https://modelcontextprotocol.io/docs/concepts/tools) 允许 MCP 服务器公开可执行的函数，LLM 可以调用这些函数来执行操作——例如查询数据库、调用 API 或与外部系统交互。LangChain 会将 MCP 工具转换为 LangChain [工具](/oss/python/langchain/tools)，使其可以直接用于任何 LangChain 代理或工作流。

#### 加载工具

使用 `client.get_tools()` 从 MCP 服务器获取工具并传递给代理：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

client = MultiServerMCPClient({...})
tools = await client.get_tools()
agent = create_agent("claude-sonnet-4-6", tools)
```

默认情况下，当 MCP 工具失败时，错误会作为带有 `status="error"` 的工具消息传回给模型，而不是抛出异常。这让代理可以读取错误并重试。若要改为抛出异常，请在 `MultiServerMCPClient` 或 `load_mcp_tools` 上设置 `handle_tool_errors=False`。

这仅适用于工具执行错误（`CallToolResult(isError=True)`）。传输、会话和内容转换失败始终会抛出异常。

> 注意：将 MCP 工具错误作为失败的工具消息返回需要 `langchain-mcp-adapters>=0.3.0`。较早版本会抛出 `ToolException`。

#### 结构化内容

MCP 工具可以在人类可读的文本响应之外返回[结构化内容](https://modelcontextprotocol.io/specification/2025-03-26/server/tools#structured-content)。当工具需要返回机器可解析的数据（如 JSON）以及展示给模型的文本时，这非常有用。

当 MCP 工具返回 `structuredContent` 时，适配器会将其包装在 [`MCPToolArtifact`](https://reference.langchain.com/python/langchain_mcp_adapters/#langchain_mcp_adapters.tools.MCPToolArtifact) 中，并作为工具的 artifact 返回。你可以使用 `ToolMessage` 上的 `artifact` 字段访问它。你还可以使用[拦截器](#tool-interceptors)自动处理或转换结构化内容。

**从 artifact 中提取结构化内容**

调用代理后，可以从响应中的工具消息访问结构化内容：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain.messages import ToolMessage

client = MultiServerMCPClient({...})
tools = await client.get_tools()
agent = create_agent("claude-sonnet-4-6", tools)

result = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "Get data from the server"}]}
)

# Extract structured content from tool messages
for message in result["messages"]:
    if isinstance(message, ToolMessage) and message.artifact:
        structured_content = message.artifact["structured_content"]
```

**通过拦截器追加结构化内容**

如果希望结构化内容出现在对话历史中（对模型可见），可以使用[拦截器](#tool-interceptors)自动将结构化内容追加到工具结果：

```python
import json

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from mcp.types import TextContent

async def append_structured_content(request: MCPToolCallRequest, handler):
    """Append structured content from artifact to tool message."""
    result = await handler(request)
    if result.structuredContent:
        result.content += [
            TextContent(type="text", text=json.dumps(result.structuredContent)),
        ]
    return result

client = MultiServerMCPClient({...}, tool_interceptors=[append_structured_content])
```

#### 多模态工具内容

MCP 工具可以在其响应中返回[多模态内容](https://modelcontextprotocol.io/specification/2025-03-26/server/tools#tool-result)（图像、文本等）。当 MCP 服务器返回包含多个部分的内容（例如文本和图像）时，适配器会将其转换为 LangChain 的[标准内容块](/oss/python/langchain/messages#standard-content-blocks)。你可以通过 `ToolMessage` 上的 `content_blocks` 属性访问标准化表示：

```python
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

async def access_multimodal_tool_content():
    client = MultiServerMCPClient({})
    tools = await client.get_tools()
    agent = create_agent("claude-sonnet-4-6", tools)

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "Take a screenshot of the current page"}]}
    )

    # Access multimodal content from tool messages
    for message in result["messages"]:
        if message.type == "tool":
            # Raw content in provider-native format
            print(f"Raw content: {message.content}")

            # Standardized content blocks
            for block in message.content_blocks:
                if block["type"] == "text":
                    print(f"Text: {block['text']}")
                elif block["type"] == "image":
                    print(f"Image URL: {block.get('url')}")
                    print(f"Image base64: {block.get('base64', '')[:50]}...")
```

这使你可以以与提供商无关的方式处理多模态工具响应，无论底层 MCP 服务器如何格式化其内容。

### 资源

[资源](https://modelcontextprotocol.io/docs/concepts/resources) 允许 MCP 服务器公开数据——例如文件、数据库记录或 API 响应——供客户端读取。LangChain 会将 MCP 资源转换为 [Blob](https://reference.langchain.com/python/langchain_core/documents/#langchain_core.documents.base.Blob) 对象，它提供了统一的接口来处理文本和二进制内容。

#### 加载资源

使用 `client.get_resources()` 从 MCP 服务器加载资源：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({...})

# Load all resources from a server
blobs = await client.get_resources("server_name")

# Or load specific resources by URI
blobs = await client.get_resources("server_name", uris=["file:///path/to/file.txt"])

for blob in blobs:
    print(f"URI: {blob.metadata['uri']}, MIME type: {blob.mimetype}")
    print(blob.as_string())  # For text content
```

还可以直接使用带会话的 [`load_mcp_resources`](https://reference.langchain.com/python/langchain_mcp_adapters/#langchain_mcp_adapters.resources.load_mcp_resources) 以获得更多控制：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.resources import load_mcp_resources

client = MultiServerMCPClient({...})

async with client.session("server_name") as session:
    # Load all resources
    blobs = await load_mcp_resources(session)

    # Or load specific resources by URI
    blobs = await load_mcp_resources(session, uris=["file:///path/to/file.txt"])
```

### 提示

[提示](https://modelcontextprotocol.io/docs/concepts/prompts) 允许 MCP 服务器公开可复用的提示模板，客户端可以检索并使用。LangChain 会将 MCP 提示转换为[消息](/oss/python/langchain/messages)，使其易于集成到基于聊天的流程中。

#### 加载提示

使用 `client.get_prompt()` 从 MCP 服务器加载提示：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({...})

# Load a prompt by name
messages = await client.get_prompt("server_name", "summarize")

# Load a prompt with arguments
messages = await client.get_prompt(
    "server_name",
    "code_review",
    arguments={"language": "python", "focus": "security"}
)

# Use the messages in your workflow
for message in messages:
    print(f"{message.type}: {message.content}")
```

还可以直接使用带会话的 [`load_mcp_prompt`](https://reference.langchain.com/python/langchain_mcp_adapters/#langchain_mcp_adapters.prompts.load_mcp_prompt) 以获得更多控制：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.prompts import load_mcp_prompt

client = MultiServerMCPClient({...})

async with client.session("server_name") as session:
    # Load a prompt by name
    messages = await load_mcp_prompt(session, "summarize")

    # Load a prompt with arguments
    messages = await load_mcp_prompt(
        session,
        "code_review",
        arguments={"language": "python", "focus": "security"}
    )
```

## 高级功能

### 工具拦截器

MCP 服务器作为独立进程运行——它们无法访问 LangGraph 运行时信息，例如[存储](/oss/python/langgraph/stores)、[上下文](/oss/python/langchain/context-engineering)或代理状态。**拦截器弥补了这一差距**，让你在 MCP 工具执行期间可以访问这些运行时上下文。

拦截器还提供类似中间件的工具调用控制：你可以修改请求、实现重试、动态添加请求头，或完全短路执行。

| 章节 | 描述 |
| --- | --- |
| [访问运行时上下文](#accessing-runtime-context) | 读取用户 ID、API 密钥、存储数据和代理状态 |
| [状态更新与命令](#state-updates-and-commands) | 使用 `Command` 更新代理状态或控制图执行流程 |
| [编写拦截器](#custom-interceptors) | 修改请求、组合拦截器和错误处理的模式 |

#### 访问运行时上下文

当 MCP 工具在 LangChain 代理中使用时（通过 `create_agent`），拦截器可以访问 `ToolRuntime` 上下文。这提供了对工具调用 ID、状态、配置和存储的访问——支持访问用户数据、持久化信息和控制代理行为的强大模式。

**运行时上下文**

访问在调用时传递的用户特定配置，如用户 ID、API 密钥或权限：

**Inject user context into MCP tool calls**
```python
from dataclasses import dataclass
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain.agents import create_agent

@dataclass
class Context:
    user_id: str
    api_key: str

async def inject_user_context(
    request: MCPToolCallRequest,
    handler,
):
    """Inject user credentials into MCP tool calls."""
    runtime = request.runtime
    user_id = runtime.context.user_id
    api_key = runtime.context.api_key

    # Add user context to tool arguments
    modified_request = request.override(
        args={**request.args, "user_id": user_id}
    )
    return await handler(modified_request)

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[inject_user_context],
)
tools = await client.get_tools()
agent = create_agent("gpt-5.5", tools, context_schema=Context)

# Invoke with user context
result = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "Search my orders"}]},
    context={"user_id": "user_123", "api_key": "sk-..."}
)
```

**存储**

访问长期记忆以检索用户偏好或在对话之间持久化数据：

**Access user preferences from store**
```python
from dataclasses import dataclass
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain.agents import create_agent
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

async def personalize_search(
    request: MCPToolCallRequest,
    handler,
):
    """Personalize MCP tool calls using stored preferences."""
    runtime = request.runtime
    user_id = runtime.context.user_id
    store = runtime.store

    # Read user preferences from store
    prefs = store.get(("preferences",), user_id)

    if prefs and request.name == "search":
        # Apply user's preferred language and result limit
        modified_args = {
            **request.args,
            "language": prefs.value.get("language", "en"),
            "limit": prefs.value.get("result_limit", 10),
        }
        request = request.override(args=modified_args)

    return await handler(request)

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[personalize_search],
)
tools = await client.get_tools()
agent = create_agent(
    "gpt-5.5",
    tools,
    context_schema=Context,
    store=InMemoryStore()
)
```

**状态**

访问对话状态，以便根据当前会话做出决策：

**Filter tools based on authentication state**
```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain.messages import ToolMessage

async def require_authentication(
    request: MCPToolCallRequest,
    handler,
):
    """Block sensitive MCP tools if user is not authenticated."""
    runtime = request.runtime
    state = runtime.state
    is_authenticated = state.get("authenticated", False)

    sensitive_tools = ["delete_file", "update_settings", "export_data"]

    if request.name in sensitive_tools and not is_authenticated:
        # Return error instead of calling tool
        return ToolMessage(
            content="Authentication required. Please log in first.",
            tool_call_id=runtime.tool_call_id,
        )

    return await handler(request)

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[require_authentication],
)
```

**工具调用 ID**

访问工具调用 ID 以返回格式正确的响应或跟踪工具执行：

**Return custom responses with tool call ID**
```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain.messages import ToolMessage

async def rate_limit_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """Rate limit expensive MCP tool calls."""
    runtime = request.runtime
    tool_call_id = runtime.tool_call_id

    # Check rate limit (simplified example)
    if is_rate_limited(request.name):
        return ToolMessage(
            content="Rate limit exceeded. Please try again later.",
            tool_call_id=tool_call_id,
        )

    result = await handler(request)

    # Log successful tool call
    log_tool_execution(tool_call_id, request.name, success=True)

    return result

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[rate_limit_interceptor],
)
```

有关更多上下文工程模式，请参阅[上下文工程](/oss/python/langchain/context-engineering)和[工具](/oss/python/langchain/tools)。

#### 状态更新与命令

拦截器可以返回 `Command` 对象来更新代理状态或控制图的执行流程。这对于跟踪任务进度、在代理之间切换或提前结束执行非常有用。

**Mark task complete and switch agents**
```python
from langchain.agents import AgentState, create_agent
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain.messages import ToolMessage
from langgraph.types import Command

async def handle_task_completion(
    request: MCPToolCallRequest,
    handler,
):
    """Mark task complete and hand off to summary agent."""
    result = await handler(request)

    if request.name == "submit_order":
        return Command(
            update={
                "messages": [result] if isinstance(result, ToolMessage) else [],
                "task_status": "completed",
            },
            goto="summary_agent",
        )

    return result
```

使用带 `goto="__end__"` 的 `Command` 提前结束执行：

**End agent run on completion**
```python
async def end_on_success(
    request: MCPToolCallRequest,
    handler,
):
    """End agent run when task is marked complete."""
    result = await handler(request)

    if request.name == "mark_complete":
        return Command(
            update={"messages": [result], "status": "done"},
            goto="__end__",
        )

    return result
```

#### 自定义拦截器

拦截器是包装工具执行的异步函数，支持请求/响应修改、重试逻辑和其他横切关注点。它们遵循"洋葱"模式，列表中的第一个拦截器是最外层。

**基本模式**

拦截器是接收请求和 handler 的异步函数。你可以在调用 handler 之前修改请求、在之后修改响应，或者完全跳过 handler。

**Basic interceptor pattern**
```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest

async def logging_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """Log tool calls before and after execution."""
    print(f"Calling tool: {request.name} with args: {request.args}")
    result = await handler(request)
    print(f"Tool {request.name} returned: {result}")
    return result

client = MultiServerMCPClient(
    {"math": {"transport": "stdio", "command": "python", "args": ["/path/to/server.py"]}},
    tool_interceptors=[logging_interceptor],
)
```

**修改请求**

使用 `request.override()` 创建修改后的请求。这遵循不可变模式，保持原始请求不变。

**Modifying tool arguments**
```python
async def double_args_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """Double all numeric arguments before execution."""
    modified_args = {k: v * 2 for k, v in request.args.items()}
    modified_request = request.override(args=modified_args)
    return await handler(modified_request)

# Original call: add(a=2, b=3) becomes add(a=4, b=6)
```

**在运行时修改请求头**

拦截器可以根据请求上下文动态修改 HTTP 请求头：

**Dynamic header modification**
```python
async def auth_header_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """Add authentication headers based on the tool being called."""
    token = get_token_for_tool(request.name)
    modified_request = request.override(
        headers={"Authorization": f"Bearer {token}"}
    )
    return await handler(modified_request)
```

**组合拦截器**

多个拦截器以"洋葱"顺序组合——列表中的第一个拦截器是最外层：

**Composing multiple interceptors**
```python
async def outer_interceptor(request, handler):
    print("outer: before")
    result = await handler(request)
    print("outer: after")
    return result

async def inner_interceptor(request, handler):
    print("inner: before")
    result = await handler(request)
    print("inner: after")
    return result

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[outer_interceptor, inner_interceptor],
)

# Execution order:
# outer: before -> inner: before -> tool execution -> inner: after -> outer: after
```

**错误处理**

使用拦截器捕获工具执行中的异常（例如传输或运行时故障），并添加重试逻辑。工具执行错误（`CallToolResult(isError=True)`）默认不会抛出，因此捕获异常的拦截器永远不会在它们上触发。要在此处将这些错误作为异常捕获，请设置 `handle_tool_errors=False`。

**Retry on error**
```python
import asyncio

async def retry_interceptor(
    request: MCPToolCallRequest,
    handler,
    max_retries: int = 3,
    delay: float = 1.0,
):
    """Retry failed tool calls with exponential backoff."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await handler(request)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = delay * (2 ** attempt)  # Exponential backoff
                print(f"Tool {request.name} failed (attempt {attempt + 1}), retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
    raise last_error

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[retry_interceptor],
)
```

还可以捕获特定错误类型并返回回退值：

**Error handling with fallback**
```python
async def fallback_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """Return a fallback value if tool execution fails."""
    try:
        return await handler(request)
    except TimeoutError:
        return f"Tool {request.name} timed out. Please try again later."
    except ConnectionError:
        return f"Could not connect to {request.name} service. Using cached data."
```

### 进度通知

订阅长时间运行的工具执行的进度更新：

**Progress callback**
```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.callbacks import Callbacks, CallbackContext

async def on_progress(
    progress: float,
    total: float | None,
    message: str | None,
    context: CallbackContext,
):
    """Handle progress updates from MCP servers."""
    percent = (progress / total * 100) if total else progress
    tool_info = f" ({context.tool_name})" if context.tool_name else ""
    print(f"[{context.server_name}{tool_info}] Progress: {percent:.1f}% - {message}")

client = MultiServerMCPClient(
    {...},
    callbacks=Callbacks(on_progress=on_progress),
)
```

`CallbackContext` 提供：

* `server_name`：MCP 服务器的名称
* `tool_name`：正在执行的工具的名称（工具调用期间可用）

### 日志

MCP 协议支持来自服务器的[日志](https://modelcontextprotocol.io/specification/2025-03-26/server/utilities/logging#log-levels)通知。使用 `Callbacks` 类订阅这些事件。

**Logging callback**
```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.callbacks import Callbacks, CallbackContext
from mcp.types import LoggingMessageNotificationParams

async def on_logging_message(
    params: LoggingMessageNotificationParams,
    context: CallbackContext,
):
    """Handle log messages from MCP servers."""
    print(f"[{context.server_name}] {params.level}: {params.data}")

client = MultiServerMCPClient(
    {...},
    callbacks=Callbacks(on_logging_message=on_logging_message),
)
```

### 征求输入

[征求输入](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation#elicitation) 允许 MCP 服务器在工具执行期间向用户请求额外输入。服务器无需提前要求所有输入，可以根据需要以交互方式询问信息。

#### 服务器端设置

定义一个使用 `ctx.elicit()` 通过 schema 请求用户输入的工具：

**MCP server with elicitation**
```python
from pydantic import BaseModel
from mcp.server.fastmcp import Context, FastMCP

server = FastMCP("Profile")

class UserDetails(BaseModel):
    email: str
    age: int

@server.tool()
async def create_profile(name: str, ctx: Context) -> str:
    """Create a user profile, requesting details via elicitation."""
    result = await ctx.elicit(
        message=f"Please provide details for {name}'s profile:",
        schema=UserDetails,
    )
    if result.action == "accept" and result.data:
        return f"Created profile for {name}: email={result.data.email}, age={result.data.age}"
    if result.action == "decline":
        return f"User declined. Created minimal profile for {name}."
    return "Profile creation cancelled."

if __name__ == "__main__":
    server.run(transport="http")
```

#### 客户端设置

通过向 `MultiServerMCPClient` 提供回调来处理征求输入请求：

**Handling elicitation requests**
```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.callbacks import Callbacks, CallbackContext
from mcp.shared.context import RequestContext
from mcp.types import ElicitRequestParams, ElicitResult

async def on_elicitation(
    mcp_context: RequestContext,
    params: ElicitRequestParams,
    context: CallbackContext,
) -> ElicitResult:
    """Handle elicitation requests from MCP servers."""
    # In a real application, you would prompt the user for input
    # based on params.message and params.requestedSchema
    return ElicitResult(
        action="accept",
        content={"email": "user@example.com", "age": 25},
    )

client = MultiServerMCPClient(
    {
        "profile": {
            "url": "http://localhost:8000/mcp",
            "transport": "http",
        }
    },
    callbacks=Callbacks(on_elicitation=on_elicitation),
)
```

#### 响应动作

征求输入回调可以返回以下三种动作之一：

| 动作 | 描述 |
| --- | --- |
| `accept` | 用户提供了有效输入。在 `content` 字段中包含数据。 |
| `decline` | 用户选择不提供请求的信息。 |
| `cancel` | 用户完全取消了操作。 |

**Response action examples**
```python
# Accept with data
ElicitResult(action="accept", content={"email": "user@example.com", "age": 25})

# Decline (user doesn't want to provide info)
ElicitResult(action="decline")

# Cancel (abort the operation)
ElicitResult(action="cancel")
```

## 其他资源

* [MCP 文档](https://modelcontextprotocol.io/introduction)
* [MCP 传输文档](https://modelcontextprotocol.io/docs/concepts/transports)
* [`langchain-mcp-adapters`](https://github.com/langchain-ai/langchain-mcp-adapters)

# 检索

大型语言模型（LLM）功能强大，但有两个关键局限：

* **有限的上下文**：它们无法一次性读入整个语料库。
* **静态知识**：它们的训练数据在某个时间点后就固定不变了。

检索通过在查询时获取相关的外部知识来解决这些问题。这就是**检索增强生成（Retrieval-Augmented Generation，RAG）** 的基础，它用与上下文相关的信息来增强 LLM 的回答。

## 构建知识库

**知识库**（knowledge base）是检索过程中使用的文档或结构化数据的仓库。

如果你需要自定义知识库，可以使用 LangChain 的文档加载器和向量存储，从你自己的数据构建一个。

> 注意：如果你已经有一个知识库（例如 SQL 数据库、文档数据库、CRM 或内部文档系统），你**不需要**重建它。你可以：
>
> * 在 Agentic RAG 中把它作为**工具**连接到 agent。
> * 查询它，并把检索到的内容作为上下文提供给 LLM（[两步 RAG](#2-step-rag)）。

更多信息请参阅以下教程，了解如何构建可搜索的知识库和最小 RAG 工作流：

> **教程：语义搜索**（[了解更多](/oss/python/langchain/knowledge-base)）
>
> 学习如何使用 LangChain 的文档加载器、嵌入模型和向量存储，从你自己的数据创建可搜索的知识库。
> 在本教程中，你将基于 PDF 构建一个搜索引擎，能够检索与查询相关的段落。你还将在此引擎之上实现一个最小的 RAG 工作流，看看外部知识如何集成到 LLM 推理中。

### 从检索到 RAG

检索让 LLM 能够在运行时访问相关上下文。但大多数真实应用还会更进一步：它们**将检索与生成集成**，以产出有依据、与上下文相关的答案。

这正是**检索增强生成（RAG）** 背后的核心理念。检索管线成为把搜索与生成结合起来的更广泛系统的基础。

### 检索管线

一个典型的检索工作流如下所示：

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 12, 'rankSpacing': 18, 'padding': 4}, 'themeVariables': {'fontSize': '12px'}}}%%
flowchart TB
  subgraph ingest[" "]
    direction LR
    S(["Sources<br>(Google Drive, Slack, Notion, etc.)"]) --> L[Document Loaders]
    L --> A([Documents])
  end
  A --> B[Split into chunks]
  B --> C[Turn into embeddings]
  C --> D[(Vector Store)]
  Q([User Query]) --> E[Query embedding]
  E --> D
  D --> F[Retriever]
  F --> G[LLM uses retrieved info]
  G --> H([Answer])

  classDef trigger fill:#F6FFDB,stroke:#6E8900,stroke-width:2px,color:#2E3900
  classDef process fill:#E5F4FF,stroke:#006DDD,stroke-width:2px,color:#030710
  classDef output fill:#EBD0F0,stroke:#885270,stroke-width:2px,color:#441E33
  classDef neutral fill:#F2FAFF,stroke:#40668D,stroke-width:2px,color:#2F4B68

  class S,Q trigger
  class L,B,C,E,F,G process
  class D output
  class A,H neutral
```

（流程图概述了 RAG 管线：来源 → 文档加载器 → 文档 → 分块 → 嵌入 → 向量存储；用户查询经查询嵌入后在向量存储中检索，再由 LLM 使用检索到的信息生成答案。）

每个组件都是模块化的：你可以替换加载器、切分器、嵌入模型或向量存储，而无需重写应用逻辑。

### 构建模块

* **文档加载器**（[了解更多](/oss/python/integrations/document_loaders)）：从外部来源（Google Drive、Slack、Notion 等）摄取数据，返回标准化的 [`Document`](https://reference.langchain.com/python/langchain-core/documents/base/Document) 对象。
* **文本切分器**（[了解更多](/oss/python/integrations/splitters)）：把大型文档拆成更小的块，这些块可以单独检索，并能放进模型的上下文窗口。
* **嵌入模型**（[了解更多](/oss/python/integrations/embeddings)）：嵌入模型把文本转换成数字向量，使语义相近的文本在向量空间中彼此靠近。
* **向量存储**（[了解更多](/oss/python/integrations/vectorstores/)）：专门用于存储和搜索嵌入向量的数据库。
* **检索器**（[了解更多](/oss/python/integrations/retrievers/)）：检索器是一个接口，给定非结构化查询，返回文档。

## RAG 架构

根据系统的需求，RAG 可以有多种实现方式。我们在下面的小节中逐一说明每种类型。

| 架构 | 描述 | 控制力 | 灵活性 | 延迟 | 示例用例 |
| --------------- | -------------------------------------------------------------------------- | --------- | ----------- | ---------- | ------------------------------------------------- |
| **两步 RAG** | 检索总是发生在生成之前。简单且可预测 | ✅ 高 | ❌ 低 | ⚡ 快 | 常见问题解答、文档机器人 |
| **Agentic RAG** | 由 LLM 驱动的 agent 在推理过程中决定*何时*以及*如何*检索 | ❌ 低 | ✅ 高 | ⏳ 可变 | 可访问多个工具的研究助手 |
| **混合式** | 结合两种方法的特点，并加入验证步骤 | ⚖️ 中等 | ⚖️ 中等 | ⏳ 可变 | 带质量验证的领域特定问答 |

> 信息：**延迟**：在**两步 RAG** 中，延迟通常更**可预测**，因为 LLM 调用的最大次数是已知且有上限的。这种可预测性假设 LLM 推理时间是主导因素。不过，实际延迟也可能受到检索步骤性能的影响，例如 API 响应时间、网络延迟或数据库查询，这些都会因所使用的工具和基础设施而异。

### 两步 RAG

在**两步 RAG** 中，检索步骤总是在生成步骤之前执行。这种架构简单且可预测，适合许多应用场景——在这些场景中，检索相关文档是生成答案的明确前置条件。

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 12, 'rankSpacing': 18, 'padding': 4}, 'themeVariables': {'fontSize': '12px'}}}%%
graph TB
    A[User Question] --> B["Retrieve Relevant Documents"]
    B --> C["Generate Answer"]
    C --> D[Return Answer to User]

    %% Styling
    classDef startend fill:#F6FFDB,stroke:#6E8900,stroke-width:2px,color:#2E3900
    classDef process fill:#E5F4FF,stroke:#006DDD,stroke-width:1.5px,color:#030710

    class A,D startend
    class B,C process
```

（流程图展示了两步 RAG 流程：用户问题 → 检索相关文档 → 生成答案 → 返回答案给用户。）

* **教程：语义搜索**（[了解更多](/oss/python/langchain/knowledge-base)）：使用文档加载器、嵌入模型和向量存储构建可搜索的知识库，然后在它之上运行一个最小的"先检索后生成"RAG 工作流。
* **教程：评估 RAG 应用**（[了解更多](/langsmith/evaluate-rag-tutorial)）：构建一个简单的"先检索后生成"RAG 应用，并使用 LangSmith 衡量答案正确性、相关性、有依据性和检索质量。

### Agentic RAG

**Agentic 检索增强生成（Agentic RAG）** 结合了检索增强生成与基于 agent 的推理的优势。它不是先检索文档再回答，而是由（LLM 驱动的）agent 逐步推理，并在交互过程中决定**何时**以及**如何**检索信息。

> 提示：要让 agent 具备 RAG 行为，唯一需要的就是一个或多个能够获取外部知识的**工具**，例如文档加载器、Web API 或数据库查询。

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 12, 'rankSpacing': 18, 'padding': 4}, 'themeVariables': {'fontSize': '12px'}}}%%
graph TB
    A[User Input / Question] --> B["Agent (LLM)"]
    B --> C{Need external info?}
    C -- Yes --> D["Search using tool(s)"]
    D --> H{Enough to answer?}
    H -- No --> B
    H -- Yes --> I[Generate final answer]
    C -- No --> I
    I --> J[Return to user]

    %% Dark-mode friendly styling
    classDef startend fill:#F6FFDB,stroke:#6E8900,stroke-width:2px,color:#2E3900
    classDef decision fill:#FDF3FF,stroke:#7E65AE,stroke-width:2px,color:#504B5F
    classDef process fill:#E5F4FF,stroke:#006DDD,stroke-width:1.5px,color:#030710

    class A,J startend
    class B,D,I process
    class C,H decision
```

（流程图展示了 Agentic RAG 流程：用户输入交给 agent（LLM），agent 判断是否需要外部信息；需要时用工具搜索，若信息不足则回到 agent 继续推理，直到足够后生成最终答案并返回给用户。）

```python
import requests
from langchain.tools import tool
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent

@tool
def fetch_url(url: str) -> str:
    """Fetch text content from a URL"""
    response = requests.get(url, timeout=10.0)
    response.raise_for_status()
    return response.text

system_prompt = """\
Use fetch_url when you need to fetch information from a web-page; quote relevant snippets.
"""

agent = create_agent(
    model="claude-sonnet-4-6",
    tools=[fetch_url], # A tool for retrieval
    system_prompt=system_prompt,
)
```

<details>
<summary>扩展示例：针对 LangGraph 的 llms.txt 的 Agentic RAG</summary>

本示例实现了一个**Agentic RAG 系统**，用于帮助用户查询 LangGraph 文档。agent 首先加载列出可用文档 URL 的 [llms.txt](https://llmstxt.org/)，然后根据用户的问题，动态使用 `fetch_documentation` 工具检索和处理相关内容。

  ```python
  import requests
  from langchain.agents import create_agent
  from langchain.messages import HumanMessage
  from langchain.tools import tool
  from markdownify import markdownify

  ALLOWED_DOMAINS = ["https://langchain-ai.github.io/"]
  LLMS_TXT = 'https://langchain-ai.github.io/langgraph/llms.txt'

  @tool
  def fetch_documentation(url: str) -> str:
      """Fetch and convert documentation from a URL"""
      if not any(url.startswith(domain) for domain in ALLOWED_DOMAINS):
          return (
              "Error: URL not allowed. "
              f"Must start with one of: {', '.join(ALLOWED_DOMAINS)}"
          )
      response = requests.get(url, timeout=10.0)
      response.raise_for_status()
      return markdownify(response.text)

  # We will fetch the content of llms.txt, so this can
  # be done ahead of time without requiring an LLM request.
  llms_txt_content = requests.get(LLMS_TXT).text

  # System prompt for the agent
  system_prompt = f"""
  You are an expert Python developer and technical assistant.
  Your primary role is to help users with questions about LangGraph and related tools.

  Instructions:

  1. If a user asks a question you're unsure about—or one that likely involves API usage,
     behavior, or configuration—you MUST use the `fetch_documentation` tool to consult the relevant docs.
  2. When citing documentation, summarize clearly and include relevant context from the content.
  3. Do not use any URLs outside of the allowed domain.
  4. If a documentation fetch fails, tell the user and proceed with your best expert understanding.

  You can access official documentation from the following approved sources:

  {llms_txt_content}

  You MUST consult the documentation to get up to date documentation
  before answering a user's question about LangGraph.

  Your answers should be clear, concise, and technically accurate.
  """

  tools = [fetch_documentation]

  model = init_chat_model("claude-sonnet-4-6", max_tokens=32_000)

  agent = create_agent(
      model=model,
      tools=tools,
      system_prompt=system_prompt,
      name="Agentic RAG",
  )

  response = agent.invoke({
      'messages': [
          HumanMessage(content=(
              "Write a short example of a langgraph agent using the "
              "prebuilt create react agent. the agent should be able "
              "to look up stock pricing information."
          ))
      ]
  })

  print(response['messages'][-1].content)
  ```
</details>

> **教程：使用 Deep Agents 实现 RAG**（[了解更多](/oss/python/deepagents/rag)）：构建一个文档问答 agent，在查询时检索相关块、将其卸载到文件系统，并把分析工作委托给子 agent。

### 混合式 RAG

混合式 RAG 结合了两步 RAG 和 Agentic RAG 的特点。它引入了中间步骤，例如查询预处理、检索验证和生成后检查。与固定管线相比，这类系统提供了更多灵活性，同时保留了对执行过程的一定控制。

典型组件包括：

* **查询增强**：修改输入问题以提高检索质量。这可以包括重写模糊查询、生成多个变体，或附加更多上下文来扩展查询。
* **检索验证**：评估检索到的文档是否相关且充分。如果不是，系统可能会优化查询并再次检索。
* **答案验证**：检查生成的答案在准确性、完整性以及与源内容的一致性方面是否达标。如有需要，系统可以重新生成或修改答案。

这种架构通常支持在这些步骤之间进行多轮迭代：

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 12, 'rankSpacing': 18, 'padding': 4}, 'themeVariables': {'fontSize': '12px'}}}%%
graph TB
    A[User Question] --> B[Query Enhancement]
    B --> C[Retrieve Documents]
    C --> D{Sufficient Info?}
    D -- No --> E[Refine Query]
    E --> C
    D -- Yes --> F[Generate Answer]
    F --> G{Answer Quality OK?}
    G -- No --> H{Try Different Approach?}
    H -- Yes --> E
    H -- No --> I[Return Best Answer]
    G -- Yes --> I
    I --> J[Return to User]

    classDef startend fill:#F6FFDB,stroke:#6E8900,stroke-width:2px,color:#2E3900
    classDef decision fill:#FDF3FF,stroke:#7E65AE,stroke-width:2px,color:#504B5F
    classDef process fill:#E5F4FF,stroke:#006DDD,stroke-width:1.5px,color:#030710

    class A,J startend
    class B,C,E,F,I process
    class D,G,H decision
```

（流程图展示了混合式 RAG 的迭代流程：用户问题 → 查询增强 → 检索文档 → 判断信息是否充分；不足则优化查询重新检索，充分则生成答案，再验证答案质量，必要时尝试不同方法，最终返回最佳答案。）

这种架构适用于：

* 查询含糊或说明不充分的应用
* 需要验证或质量控制步骤的系统
* 涉及多个来源或迭代优化的工作流

> **教程：带自我纠正的 Agentic RAG**（[了解更多](/oss/python/langgraph/agentic-rag)）：一个**混合式 RAG** 示例，把 agent 推理与检索和自我纠正结合起来。

---

# 护栏

> 为你的 agent 实现安全检查与内容过滤

护栏通过在 agent 执行的关键节点验证和过滤内容，帮助你构建安全、合规的 AI 应用。它们可以检测敏感信息、执行内容策略、验证输出，并在不安全行为造成问题之前加以阻止。

常见用例包括：

* 防止 PII（个人身份信息）泄露
* 检测并阻止提示注入攻击
* 阻止不恰当或有害内容
* 执行业务规则和合规要求
* 验证输出质量和准确性

你可以使用 [middleware](/oss/python/langchain/middleware) 实现护栏，在关键位置拦截执行——在 agent 开始之前、完成后，或围绕模型调用和工具调用。

![Middleware flow diagram](https://mintcdn.com/langchain-5e9cc07a/RAP6mjwE5G00xYsA/oss/images/middleware_final.png?fit=max&auto=format&n=RAP6mjwE5G00xYsA&q=85&s=eb4404b137edec6f6f0c8ccb8323eaf1)

护栏可以用两种互补的方法实现：

* **确定性护栏**：使用基于规则逻辑的方法，如正则表达式模式、关键词匹配或显式检查。快速、可预测且成本低，但可能漏掉微妙的违规。
* **基于模型的护栏**：使用 LLM 或分类器，以语义理解来评估内容。能捕捉规则漏掉的细微问题，但更慢、更昂贵。

LangChain 既提供内置护栏（例如 [PII 检测](#pii-detection)、[人机协同](#human-in-the-loop)），也提供灵活的 middleware 系统，用于使用上述任一方法构建自定义护栏。

## 内置护栏

### PII 检测

LangChain 提供了用于检测和处理对话中个人身份信息（PII）的内置 middleware。该 middleware 可以检测常见的 PII 类型，如电子邮件、信用卡、IP 地址等。

PII 检测 middleware 适用于以下场景：有合规要求的医疗和金融应用、需要清理日志的客服 agent，以及任何处理敏感用户数据的应用。

PII middleware 支持多种处理已检测 PII 的策略：

| 策略 | 描述 | 示例 |
| -------- | --------------------------------------- | --------------------- |
| `redact` | 替换为 `[REDACTED_{PII_TYPE}]` | `[REDACTED_EMAIL]` |
| `mask` | 部分遮蔽（例如只保留后 4 位） | `****-****-****-1234` |
| `hash` | 替换为确定性哈希 | `a8f5f167...` |
| `block` | 检测到时抛出异常 | 抛出错误 |

> 注意：启用 `apply_to_output=True` 后，`PIIMiddleware` 还会通过注册的流转换器（stream transformer）对流式输出的线上数据——文本增量、工具调用参数、工具输出和状态快照——进行脱敏。需要 `langchain>=1.3.2`。参见[在 middleware 上注册转换器](/oss/python/langchain/event-streaming#register-transformers-on-middleware)。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[customer_service_tool, email_tool],
    middleware=[
        # Redact emails in user input before sending to model
        PIIMiddleware(
            "email",
            strategy="redact",
            apply_to_input=True,
        ),
        # Mask credit cards in user input
        PIIMiddleware(
            "credit_card",
            strategy="mask",
            apply_to_input=True,
        ),
        # Block API keys - raise error if detected
        PIIMiddleware(
            "api_key",
            detector=r"sk-[a-zA-Z0-9]{32}",
            strategy="block",
            apply_to_input=True,
        ),
    ],
)

# When user provides PII, it will be handled according to the strategy
result = agent.invoke({
    "messages": [{"role": "user", "content": "My email is john.doe@example.com and card is 5105-1051-0510-5100"}]
})
```

<details>
<summary>内置 PII 类型与配置</summary>

**内置 PII 类型：**

* `email` - 电子邮件地址
* `credit_card` - 信用卡号（经 Luhn 校验）
* `ip` - IP 地址
* `mac_address` - MAC 地址
* `url` - URL

**配置选项：**

| 参数 | 描述 | 默认值 |
| ----------------------- | ---------------------------------------------------------------------- | ---------------------- |
| `pii_type` | 要检测的 PII 类型（内置或自定义） | 必填 |
| `strategy` | 如何处理检测到的 PII（`"block"`、`"redact"`、`"mask"`、`"hash"`） | `"redact"` |
| `detector` | 自定义检测函数或正则模式 | `None`（使用内置） |
| `apply_to_input` | 在模型调用前检查用户消息 | `True` |
| `apply_to_output` | 在模型调用后检查 AI 消息 | `False` |
| `apply_to_tool_results` | 在执行后检查工具结果消息 | `False` |
</details>

关于 PII 检测能力的完整细节，请参阅 [middleware 文档](/oss/python/langchain/middleware#pii-detection)。

### 人机协同

LangChain 提供了内置 middleware，用于在执行敏感操作之前要求人工批准。这是针对高风险决策最有效的护栏之一。

人机协同 middleware 适用于以下场景：金融交易和转账、删除或修改生产数据、向外部方发送通信，以及任何具有重大业务影响的操作。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, send_email_tool, delete_database_tool],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                # Require approval for sensitive operations
                "send_email": True,
                "delete_database": True,
                # Auto-approve safe operations
                "search": False,
            }
        ),
    ],
    # Persist the state across interrupts
    checkpointer=InMemorySaver(),
)

# Human-in-the-loop requires a thread ID for persistence
config = {"configurable": {"thread_id": "some_id"}}

# Agent will pause and wait for approval before executing sensitive tools
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Send an email to the team"}]},
    config=config
)

result = agent.invoke(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config=config  # Same thread ID to resume the paused conversation
)
```

> 提示：参见[人机协同文档](/oss/python/langchain/human-in-the-loop)，了解实现审批工作流的完整细节。

## 自定义护栏

对于更复杂的护栏，你可以创建在 agent 执行之前或之后运行的自定义 middleware。这让你可以完全控制验证逻辑、内容过滤和安全检查。

### agent 之前的护栏

使用"before agent"钩子在每次调用的开始一次性验证请求。这对于会话级检查很有用，例如身份验证、限流，或在任何处理开始之前阻止不当请求。

**类语法：**

```python
from typing import Any

from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langgraph.runtime import Runtime

class ContentFilterMiddleware(AgentMiddleware):
    """Deterministic guardrail: Block requests containing banned keywords."""

    def __init__(self, banned_keywords: list[str]):
        super().__init__()
        self.banned_keywords = [kw.lower() for kw in banned_keywords]

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        # Get the first user message
        if not state["messages"]:
            return None

        first_message = state["messages"][0]
        if first_message.type != "human":
            return None

        content = first_message.content.lower()

        # Check for banned keywords
        for keyword in self.banned_keywords:
            if keyword in content:
                # Block execution before any processing
                return {
                    "messages": [{
                        "role": "assistant",
                        "content": "I cannot process requests containing inappropriate content. Please rephrase your request."
                    }],
                    "jump_to": "end"
                }

        return None

# Use the custom guardrail
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, calculator_tool],
    middleware=[
        ContentFilterMiddleware(
            banned_keywords=["hack", "exploit", "malware"]
        ),
    ],
)

# This request will be blocked before any processing
result = agent.invoke({
    "messages": [{"role": "user", "content": "How do I hack into a database?"}]
})
```

**装饰器语法：**

```python
from typing import Any

from langchain.agents.middleware import before_agent, AgentState, hook_config
from langgraph.runtime import Runtime

banned_keywords = ["hack", "exploit", "malware"]

@before_agent(can_jump_to=["end"])
def content_filter(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Deterministic guardrail: Block requests containing banned keywords."""
    # Get the first user message
    if not state["messages"]:
        return None

    first_message = state["messages"][0]
    if first_message.type != "human":
        return None

    content = first_message.content.lower()

    # Check for banned keywords
    for keyword in banned_keywords:
        if keyword in content:
            # Block execution before any processing
            return {
                "messages": [{
                    "role": "assistant",
                    "content": "I cannot process requests containing inappropriate content. Please rephrase your request."
                }],
                "jump_to": "end"
            }

    return None

# Use the custom guardrail
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, calculator_tool],
    middleware=[content_filter],
)

# This request will be blocked before any processing
result = agent.invoke({
    "messages": [{"role": "user", "content": "How do I hack into a database?"}]
})
```

### agent 之后的护栏

使用"after agent"钩子在返回给用户之前，对最终输出做一次性验证。这对于基于模型的安全检查、质量验证，或对完整 agent 响应做最终合规扫描很有用。

**类语法：**

```python
from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langgraph.runtime import Runtime
from langchain.messages import AIMessage
from langchain.chat_models import init_chat_model
from typing import Any

class SafetyGuardrailMiddleware(AgentMiddleware):
    """Model-based guardrail: Use an LLM to evaluate response safety."""

    def __init__(self):
        super().__init__()
        self.safety_model = init_chat_model("gpt-5.4-mini")

    @hook_config(can_jump_to=["end"])
    def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        # Get the final AI response
        if not state["messages"]:
            return None

        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage):
            return None

        # Use a model to evaluate safety
        safety_prompt = f"""Evaluate if this response is safe and appropriate.
        Respond with only 'SAFE' or 'UNSAFE'.

        Response: {last_message.content}"""

        result = self.safety_model.invoke([{"role": "user", "content": safety_prompt}])

        if "UNSAFE" in result.content:
            last_message.content = "I cannot provide that response. Please rephrase your request."

        return None

# Use the safety guardrail
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, calculator_tool],
    middleware=[SafetyGuardrailMiddleware()],
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "How do I make explosives?"}]
})
```

**装饰器语法：**

```python
from langchain.agents.middleware import after_agent, AgentState, hook_config
from langgraph.runtime import Runtime
from langchain.messages import AIMessage
from langchain.chat_models import init_chat_model
from typing import Any

safety_model = init_chat_model("gpt-5.4-mini")

@after_agent(can_jump_to=["end"])
def safety_guardrail(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Model-based guardrail: Use an LLM to evaluate response safety."""
    # Get the final AI response
    if not state["messages"]:
        return None

    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        return None

    # Use a model to evaluate safety
    safety_prompt = f"""Evaluate if this response is safe and appropriate.
    Respond with only 'SAFE' or 'UNSAFE'.

    Response: {last_message.content}"""

    result = safety_model.invoke([{"role": "user", "content": safety_prompt}])

    if "UNSAFE" in result.content:
        last_message.content = "I cannot provide that response. Please rephrase your request."

    return None

# Use the safety guardrail
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, calculator_tool],
    middleware=[safety_guardrail],
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "How do I make explosives?"}]
})
```

### 组合多个护栏

你可以把多个护栏加入 middleware 数组来叠加使用。它们按顺序执行，让你构建分层防护：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware, HumanInTheLoopMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, send_email_tool],
    middleware=[
        # Layer 1: Deterministic input filter (before agent)
        ContentFilterMiddleware(banned_keywords=["hack", "exploit"]),

        # Layer 2: PII protection (before and after model)
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        PIIMiddleware("email", strategy="redact", apply_to_output=True),

        # Layer 3: Human approval for sensitive tools
        HumanInTheLoopMiddleware(interrupt_on={"send_email": True}),

        # Layer 4: Model-based safety check (after agent)
        SafetyGuardrailMiddleware(),
    ],
)
```

## 其他资源

* [Middleware 文档](/oss/python/langchain/middleware) - 自定义 middleware 的完整指南
* [Middleware API 参考](https://reference.langchain.com/python/langchain/middleware/) - 自定义 middleware 的完整指南
* [人机协同](/oss/python/langchain/human-in-the-loop) - 为敏感操作添加人工审查
* [测试 agents](/oss/python/langchain/test/) - 测试安全机制的策略

---

# 人机协同

人机协同（HITL）[middleware](/oss/python/langchain/middleware/built-in#human-in-the-loop) 让你可以为 agent 的工具调用添加人工监督。
当模型提出的某个操作可能需要审查时——例如写入文件或执行 SQL——middleware 可以暂停执行并等待决策。

它的做法是把每次工具调用与一个可配置的策略进行核对。如果需要干预，middleware 会发出一个 [interrupt](https://reference.langchain.com/python/langgraph/types/interrupt) 来暂停执行。图状态会使用 LangGraph 的[持久化层](/oss/python/langgraph/persistence)保存，因此执行可以安全地暂停并在之后恢复。

随后由人工决策决定接下来发生什么：操作可以原样批准（`approve`）、执行前修改（`edit`）、带反馈地拒绝（`reject`），或直接回复（`respond`）——用于"询问用户"风格的工具。

## 中断决策类型

[middleware](/oss/python/langchain/middleware/built-in#human-in-the-loop) 定义了四种内置的、人类可以响应中断的方式：

| 决策类型 | 描述 | 示例用例 |
| ------------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| ✅ `approve` | 按 agent 提出的原始参数执行该工具。 | 按原样发送邮件草稿 |
| ✏️ `edit` | 在执行前修改工具参数。 | 发送邮件前更改收件人 |
| ❌ `reject` | 完全跳过执行此工具调用，并把拒绝反馈返回给 agent。 | 拒绝删除文件并解释原因 |
| 💬 `respond` | 把人类的回复直接作为合成的工具结果返回，跳过执行，用于"询问用户"风格的工具。 | 用直接回复来应答 `"ask_user"` 提示 |

每种工具可用的决策类型取决于你在 `interrupt_on` 中配置的策略。
当多个工具调用同时被暂停时，每个操作都需要一个单独的决策。
决策必须按操作在中断请求中出现的相同顺序提供。

当人类在拒绝所请求的操作时使用 `reject`。只有当人类充当工具本身时——例如回答 `ask_user` 提示——才使用 `respond`。不要用 `respond` 来拒绝有副作用（side-effecting）的工具，因为它的消息会被当作一次成功的工具结果。

> 提示：**编辑**工具参数时，要保守地进行修改。对原始参数的显著改动可能使模型重新评估其方案，并可能多次执行该工具或采取意外行动。

## 配置中断

要使用 HITL，请在创建 agent 时把 [middleware](/oss/python/langchain/middleware/built-in#human-in-the-loop) 加入 agent 的 `middleware` 列表。

你需要用一个映射来配置它：把工具操作映射到每个操作允许的决策类型。当工具调用与映射中的某个操作匹配时，middleware 就会中断执行。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="gpt-5.5",
    tools=[write_file, execute_sql, read_data],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "write_file": True,  # All decisions (approve, edit, reject, respond) allowed
                "execute_sql": {"allowed_decisions": ["approve", "reject"]},  # No editing allowed
                "read_data": False, # Safe operation, no approval needed
            },
            # Prefix for interrupt messages - combined with tool name and args to form the full message
            # e.g., "Tool execution pending approval: execute_sql with query='DELETE FROM...'"
            # Individual tools can override this by specifying a "description" in their interrupt config
            description_prefix="Tool execution pending approval",
        ),
    ],
    # Human-in-the-loop requires checkpointing to handle interrupts.
    # In production, use a persistent checkpointer like AsyncPostgresSaver or MongoDBSaver.
    checkpointer=InMemorySaver(),
)
```

> 信息：你必须配置检查点器（checkpointer）来跨中断持久化图状态。
> 在生产环境中，使用持久化的检查点器，例如 [`AsyncPostgresSaver`](https://reference.langchain.com/python/langgraph/checkpoints/#langgraph.checkpoint.postgres.aio.AsyncPostgresSaver) 或 [`MongoDBSaver`](https://pypi.org/project/langgraph-checkpoint-mongodb/)。在测试或原型开发中，使用 [`InMemorySaver`](https://reference.langchain.com/python/langgraph/checkpoints/#langgraph.checkpoint.memory.InMemorySaver)。
>
> 调用 agent 时，传入一个包含 **thread ID** 的 `config`，把执行与会话线程关联起来。
> 详见 [LangGraph 中断文档](/oss/python/langgraph/interrupts)。

<details>
<summary>配置选项</summary>

* **`interrupt_on`**（dict，必填）：工具名到审批配置的映射。值可以是 `True`（使用默认配置中断）、`False`（自动批准），或一个 `InterruptOnConfig` 对象。
* **`description_prefix`**（string，默认 `"Tool execution requires approval"`）：操作请求描述的前缀。

**`InterruptOnConfig` 选项：**

* **`allowed_decisions`**（list[string]）：允许的决策列表：`'approve'`、`'edit'`、`'reject'` 或 `'respond'`。
* **`description`**（string | callable）：自定义描述的静态字符串或可调用函数。
* **`when`**（callable）：可选谓词，接收一个 [ToolCallRequest](https://reference.langchain.com/python/langgraph.prebuilt/tool_node/ToolCallRequest)，返回 `True` 表示中断，返回 `False` 表示自动批准。用它来按调用的参数决定是否中断。需要 `langchain>=1.3.3`。
</details>

## 条件中断

默认情况下，`interrupt_on` 中列出的每个工具调用都会暂停等待审查。若只想暂停部分调用，请为工具的 `InterruptOnConfig` 添加 `when` 谓词。该谓词接收一个 `ToolCallRequest`，返回 `True` 表示中断，返回 `False` 表示自动批准，因此你可以根据工具的参数来决定。

> 注意：条件中断需要 `langchain>=1.3.3`。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, ToolCallRequest
from langgraph.checkpoint.memory import InMemorySaver

def writes_outside_workspace(request: ToolCallRequest) -> bool:
    """Pause writes to paths outside the workspace directory."""
    path = request.tool_call["args"].get("path", "")
    return not path.startswith("/workspace/")

def is_write_query(request: ToolCallRequest) -> bool:
    """Pause SQL that isn't a read-only SELECT."""
    query = request.tool_call["args"].get("query", "")
    return not query.lstrip().upper().startswith("SELECT")

agent = create_agent(
    model="gpt-5.5",
    tools=[write_file, execute_sql, read_data],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "write_file": {
                    "allowed_decisions": ["approve", "edit", "reject"],
                    "when": writes_outside_workspace,
                },
                "execute_sql": {
                    "allowed_decisions": ["approve", "reject"],
                    "when": is_write_query,
                },
            },
        ),
    ],
    checkpointer=InMemorySaver(),
)
```

当 `when` 谓词返回 `False` 时，该调用会直接运行而不会中断。当它返回 `True`，或你省略了 `when` 时，调用会照常暂停。求值为 `False` 的调用永远不会被加入中断批次，因此审查者只会看到需要决策的操作。

## 响应中断

当你调用 agent 时，它会一直运行到完成或触发中断为止。当工具调用与你配置在 `interrupt_on` 中的策略匹配时，就会触发中断。使用 `version="v2"` 时，结果是一个带有 `interrupts` 属性的 `GraphOutput`，其中包含需要审查的操作。然后你可以把这些操作呈现给审查者，并在提供决策后恢复执行。

```python
from langgraph.types import Command

# Human-in-the-loop leverages LangGraph's persistence layer.
# You must provide a thread ID to associate the execution with a conversation thread,
# so the conversation can be paused and resumed (as is needed for human review).
config = {"configurable": {"thread_id": "some_id"}}
# Run the graph until the interrupt is hit.
result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Delete old records from the database",
            }
        ]
    },
    config=config,
    version="v2",
)

# result is a GraphOutput with .value and .interrupts
print(result.interrupts)
# > (
# >    Interrupt(
# >       value={
# >          'action_requests': [
# >             {
# >                'name': 'execute_sql',
# >                'arguments': {'query': 'DELETE FROM records WHERE created_at < NOW() - INTERVAL \'30 days\';'},
# >                'description': 'Tool execution pending approval\n\nTool: execute_sql\nArgs: {...}'
# >             }
# >          ],
# >          'review_configs': [
# >             {
# >                'action_name': 'execute_sql',
# >                'allowed_decisions': ['approve', 'reject']
# >             }
# >          ]
# >       }
# >    ),
# > )

# Resume with approval decision
agent.invoke(
    Command(
        resume={"decisions": [{"type": "approve"}]}  # or "reject"
    ),
    config=config, # Same thread ID to resume the paused conversation
    version="v2",
)
```

### 决策类型

#### ✅ approve

使用 `approve` 原样批准工具调用并执行，不做任何更改。

```python
agent.invoke(
    Command(
        # Decisions are provided as a list, one per action under review.
        # The order of decisions must match the order of actions
        # in the interrupt request.
        resume={
            "decisions": [
                {
                    "type": "approve",
                }
            ]
        }
    ),
    config=config,  # Same thread ID to resume the paused conversation
    version="v2",
)
```

#### ✏️ edit

使用 `edit` 在执行前修改工具调用。
提供带有新工具名和参数编辑后的操作。

```python
agent.invoke(
    Command(
        # Decisions are provided as a list, one per action under review.
        # The order of decisions must match the order of actions
        # in the interrupt request.
        resume={
            "decisions": [
                {
                    "type": "edit",
                    # Edited action with tool name and args
                    "edited_action": {
                        # Tool name to call.
                        # Will usually be the same as the original action.
                        "name": "new_tool_name",
                        # Arguments to pass to the tool.
                        "args": {"key1": "new_value", "key2": "original_value"},
                    }
                }
            ]
        }
    ),
    config=config,  # Same thread ID to resume the paused conversation
    version="v2",
)
```

> 提示：**编辑**工具参数时，要保守地进行修改。对原始参数的显著改动可能使模型重新评估其方案，并可能多次执行该工具或采取意外行动。

#### ❌ reject

使用 `reject` 拒绝工具调用，并提供反馈而非执行。该工具不会被执行。

```python
agent.invoke(
    Command(
        # Decisions are provided as a list, one per action under review.
        # The order of decisions must match the order of actions
        # in the interrupt request.
        resume={
            "decisions": [
                {
                    "type": "reject",
                    # Optional: explain why the action was rejected
                    # and whether the agent should retry a different approach.
                    "message": "User rejected this action. Do not retry this tool call.",
                }
            ]
        }
    ),
    config=config,  # Same thread ID to resume the paused conversation
    version="v2",
)
```

`message` 会被加入对话，作为帮助 agent 理解该操作为何被拒绝以及应该改做什么的反馈。当你省略 `message` 时，middleware 会使用一条默认的拒绝消息，告诉模型该工具未被执行，并且除非用户要求，否则不要重试相同的工具调用。对于有副作用的工具，请提供领域特定的消息，明确说明 agent 是应该放弃该操作、提出后续问题，还是尝试更安全的替代方案。

#### 💬 respond

对于"询问用户"风格的工具（工具真正的实现就是人类的回复），使用 `respond`。`message` 的内容会直接作为工具结果返回；工具本身不会被执行。

```python
agent.invoke(
    Command(
        # Decisions are provided as a list, one per action under review.
        # The order of decisions must match the order of actions
        # in the interrupt request.
        resume={
            "decisions": [
                {
                    "type": "respond",
                    # The human's reply, returned directly as the tool result
                    "message": "Blue.",
                }
            ]
        }
    ),
    config=config,  # Same thread ID to resume the paused conversation
    version="v2",
)
```

`message` 会作为一条成功的 `ToolMessage` 返回给 agent。当工具有意作为人工输入的占位符时——例如提示澄清的 `ask_user` 工具——请使用 `respond`。不要用 `respond` 来拒绝提议的操作，因为它会告诉模型该工具已成功完成。

### 多个决策

当多个操作同时处于审查中时，请按它们在中断中出现的顺序为每个操作提供决策：

```python
{
    "decisions": [
        {"type": "approve"},
        {
            "type": "edit",
            "edited_action": {
                "name": "tool_name",
                "args": {"param": "new_value"}
            }
        },
        {
            "type": "reject",
            "message": "This action is not allowed"
        }
    ]
}
```

## 人机协同与流式输出

你可以使用 `stream_events()` 在 agent 运行和处理中断时流式获取实时更新。使用 `stream.messages` 流式获取 LLM token，使用 `stream.values` 检查 agent 状态快照中的中断。

```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "some_id"}}

# Stream agent progress and LLM tokens until interrupt
stream = agent.stream_events(
    {"messages": [{"role": "user", "content": "Delete old records from the database"}]},
    config=config,
    version="v3",
)
for message in stream.messages:
    for token in message.text:
        print(token, end="", flush=True)

# Check whether the run paused for human input
if stream.interrupted:
    print(f"\n\nInterrupt: {stream.interrupts}")

# Resume with streaming after human decision
stream = agent.stream_events(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config=config,
    version="v3",
)
for message in stream.messages:
    for token in message.text:
        print(token, end="", flush=True)
```

关于流式模式的更多细节，请参阅[流式输出](/oss/python/langchain/streaming)指南。

## 执行生命周期

middleware 定义了一个 `after_model` 钩子，它在模型生成响应之后、任何工具调用执行之前运行：

1. agent 调用模型生成响应。
2. middleware 检查响应中是否有工具调用。
3. 如果有任何调用需要人工输入，middleware 会构建一个带有 `action_requests` 和 `review_configs` 的 `HITLRequest`，并调用 [interrupt](https://reference.langchain.com/python/langgraph/types/interrupt)。
4. agent 等待人工决策。
5. 根据 `HITLResponse` 中的决策，middleware 执行被批准或被编辑的调用，为被拒绝的调用合成 [ToolMessage](https://reference.langchain.com/python/langchain-core/messages/tool/ToolMessage)，为 `respond` 决策直接把人工回复作为 [ToolMessage](https://reference.langchain.com/python/langgraph/types/interrupt) 返回，然后恢复执行。

## 自定义 HITL 逻辑

对于更专门的工作流，你可以直接使用 [interrupt](https://reference.langchain.com/python/langgraph/types/interrupt) 原语和 [middleware](/oss/python/langchain/middleware) 抽象来构建自定义 HITL 逻辑。

请回顾上面的[执行生命周期](#execution-lifecycle)，了解如何把中断集成到 agent 的运行中。

# 多代理

多代理系统通过协调专业化的组件来处理复杂工作流。然而，并非所有复杂任务都需要这种方法——一个配备合适（有时是动态的）工具和提示词的单一代理往往也能达到类似的效果。

> 提示：如需内置的多代理支持，请使用 [Deep Agents](/oss/python/deepagents/overview)：一个构建在 LangChain 之上的更高级封装，内置[子代理](/oss/python/deepagents/subagents)、[技能](/oss/python/deepagents/skills)、规划、虚拟文件系统和上下文管理。

## 为什么需要多代理？

当开发者说他们需要"多代理"时，通常是在寻找以下一种或多种能力：

* 🧠 **上下文管理**：提供专业知识而不淹没模型的上下文窗口。如果上下文无限且延迟为零，你可以把所有知识塞进一个提示词里——但事实并非如此，所以你需要用一些模式来选择性地呈现相关信息。
* 👥 **分布式开发**：让不同团队独立开发和维护能力，再以清晰的边界组合成更大的系统。
* 🔀 **并行化**：为子任务生成专门的 worker 并并发执行，以获得更快的结果。

当单一代理拥有太多[工具](/oss/python/langchain/tools)而难以决定用哪个时，当任务需要专业知识且伴随大量上下文（长提示词和领域专用工具）时，或者当你需要强制执行顺序约束（只有在满足特定条件后才解锁某些能力）时，多代理模式尤其有价值。

> 提示：多代理设计的核心是 **[上下文工程](/oss/python/langchain/context-engineering)**——决定每个代理看到什么信息。你的系统质量取决于确保每个代理都能访问到适合其任务的正确数据。

## 模式

以下是构建多代理系统的主要模式，每种都适用于不同的用例：

| 模式 | 工作原理 |
| --- | --- |
| [**子代理（Subagents）**](/oss/python/langchain/multi-agent/subagents) | 主代理把子代理当作工具来协调。所有路由都经过主代理，由它决定何时以及如何调用每个子代理。 |
| [**交接（Handoffs）**](/oss/python/langchain/multi-agent/handoffs) | 行为根据状态动态变化。工具调用会更新一个状态变量，从而触发路由或配置变更，切换代理或调整当前代理的工具与提示词。 |
| [**技能（Skills）**](/oss/python/langchain/multi-agent/skills) | 按需加载专业化的提示词和知识。单一代理保持控制权，同时按需从技能中加载上下文。 |
| [**路由器（Router）**](/oss/python/langchain/multi-agent/router) | 一个路由步骤对输入进行分类，并将其导向一个或多个专业化代理。结果被综合成组合响应。 |
| [**自定义工作流**](/oss/python/langchain/multi-agent/custom-workflow) | 使用 [LangGraph](/oss/python/langgraph/overview) 构建定制执行流程，混合确定性逻辑与代理行为。把其他模式作为节点嵌入你的工作流。 |

### 选择模式

使用下表将你的需求与正确的模式匹配：

| 模式 | 分布式开发 | 并行化 | 多跳 | 直接与用户交互 |
| --- | :---: | :---: | :---: | :---: |
| [**子代理（Subagents）**](/oss/python/langchain/multi-agent/subagents) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| [**交接（Handoffs）**](/oss/python/langchain/multi-agent/handoffs) | - | - | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| [**技能（Skills）**](/oss/python/langchain/multi-agent/skills) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| [**路由器（Router）**](/oss/python/langchain/multi-agent/router) | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | - | ⭐⭐⭐ |

* **分布式开发**：不同团队能否独立维护组件？
* **并行化**：多个代理能否并发执行？
* **多跳**：该模式是否支持串联调用多个子代理？
* **直接与用户交互**：子代理能否直接与用户对话？

> 提示：你可以混合使用这些模式！例如，**子代理**架构可以调用工具，而工具又可以调用自定义工作流或路由器代理。子代理甚至可以使用**技能**模式按需加载上下文。可能性无穷无尽！

### 可视化概览

**子代理**：主代理把子代理当作工具来协调。所有路由都经过主代理。（结构图见原文，此处省略。）

**交接**：代理通过工具调用把控制权转交给彼此。每个代理都可以交接给其他代理，或直接响应用户。（结构图见原文，此处省略。）

**技能**：单一代理按需加载专业化的提示词和知识，同时保持控制权。（结构图见原文，此处省略。）

**路由器**：路由步骤对输入进行分类，并将其导向专业化代理。结果被综合处理。（结构图见原文，此处省略。）

> 提示：使用 [LangSmith](https://smith.langchain.com?utm_source=docs&utm_medium=cta&utm_campaign=langsmith-signup&utm_content=oss-langchain-multi-agent-index) 跨代理追踪完整的协调流程。按[追踪快速入门](/langsmith/trace-with-langchain)进行设置。
>
> 我们还建议你设置 [LangSmith Engine](/langsmith/engine)，它会监控你的追踪、检测问题并提出修复建议。

## 性能对比

不同模式有不同的性能特征。理解这些权衡有助于你根据延迟和成本需求选择正确的模式。

**关键指标：**

* **模型调用次数**：LLM 调用次数。调用越多 = 延迟越高（尤其是顺序调用时），单次请求的 API 成本也越高。
* **处理的令牌数**：所有调用中[上下文窗口](/oss/python/langchain/context-engineering)的总使用量。令牌越多 = 处理成本越高，还可能触及上下文限制。

### 单次请求

> **用户**："买咖啡"

一个专门的咖啡代理/技能可以调用 `buy_coffee` 工具。

| 模式 | 模型调用次数 | 最合适 |
| --- | :---: | :---: |
| [**子代理（Subagents）**](/oss/python/langchain/multi-agent/subagents) | 4 | |
| [**交接（Handoffs）**](/oss/python/langchain/multi-agent/handoffs) | 3 | ✅ |
| [**技能（Skills）**](/oss/python/langchain/multi-agent/skills) | 3 | ✅ |
| [**路由器（Router）**](/oss/python/langchain/multi-agent/router) | 3 | ✅ |

**子代理**：**4 次模型调用：**（调用流程示意图见原文，此处省略。）

**交接**：**3 次模型调用：**（调用流程示意图见原文，此处省略。）

**技能**：**3 次模型调用：**（调用流程示意图见原文，此处省略。）

**路由器**：**3 次模型调用：**（调用流程示意图见原文，此处省略。）

**关键洞察：**交接、技能和路由器对单一任务最高效（各 3 次调用）。子代理多出一次调用，因为结果要流经主代理——这种开销换来的是集中式控制。

### 重复请求

> **第 1 轮**："买咖啡"
> **第 2 轮**："再买一次咖啡"

用户在同一个对话中重复相同的请求。

| 模式 | 第 2 轮调用次数 | 总计（两轮） | 最合适 |
| --- | :---: | :---: | :---: |
| [**子代理（Subagents）**](/oss/python/langchain/multi-agent/subagents) | 4 | 8 | |
| [**交接（Handoffs）**](/oss/python/langchain/multi-agent/handoffs) | 2 | 5 | ✅ |
| [**技能（Skills）**](/oss/python/langchain/multi-agent/skills) | 2 | 5 | ✅ |
| [**路由器（Router）**](/oss/python/langchain/multi-agent/router) | 3 | 6 | |

**子代理**：**又是 4 次调用 → 共 8 次**

* 子代理**按设计无状态**——每次调用都遵循相同的流程
* 主代理维护对话上下文，但子代理每次都重新开始
* 这提供了强上下文隔离，但会重复整个流程

**交接**：**2 次调用 → 共 5 次**

* 咖啡代理从第 1 轮起**仍然活跃**（状态持续存在）
* 无需交接——代理直接调用 `buy_coffee` 工具（第 1 次调用）
* 代理响应用户（第 2 次调用）
* **跳过交接省下 1 次调用**

**技能**：**2 次调用 → 共 5 次**

* 技能上下文**已经加载**在对话历史中
* 无需重新加载——代理直接调用 `buy_coffee` 工具（第 1 次调用）
* 代理响应用户（第 2 次调用）
* **复用已加载的技能省下 1 次调用**

**路由器**：**又是 3 次调用 → 共 6 次**

* 路由器是**无状态的**——每个请求都需要一次 LLM 路由调用
* 第 2 轮：路由器 LLM 调用（1）→ Milk 代理调用 buy\_coffee（2）→ Milk 代理响应（3）
* 可以优化为把它包装成有状态代理中的一个工具

**关键洞察：**有状态模式（交接、技能）在重复请求上节省 40-50% 的调用次数。子代理每次请求的成本保持一致——这种无状态设计提供了强上下文隔离，但代价是重复的模型调用。

### 多领域

> **用户**："比较 Python、JavaScript 和 Rust 在 Web 开发中的表现"

每种语言的代理/技能包含约 2000 令牌的文档。所有模式都可以并行调用工具。

| 模式 | 模型调用次数 | 总令牌数 | 最合适 |
| --- | :---: | :---: | :---: |
| [**子代理（Subagents）**](/oss/python/langchain/multi-agent/subagents) | 5 | ~9K | ✅ |
| [**交接（Handoffs）**](/oss/python/langchain/multi-agent/handoffs) | 7+ | ~14K+ | |
| [**技能（Skills）**](/oss/python/langchain/multi-agent/skills) | 3 | ~15K | |
| [**路由器（Router）**](/oss/python/langchain/multi-agent/router) | 5 | ~9K | ✅ |

**子代理**：**5 次调用，约 9K 令牌**（并行执行示意图见原文，此处省略。）

每个子代理在**隔离**环境中工作，只包含与其相关的上下文。总计：**9K 令牌**。

**交接**：**7+ 次调用，约 14K+ 令牌**（顺序调用示意图见原文，此处省略。）

交接**顺序**执行——无法并行研究这三种语言。不断增长的对话历史增加了开销。总计：**约 14K+ 令牌**。

**技能**：**3 次调用，约 15K 令牌**（上下文累积示意图见原文，此处省略。）

加载之后，**每一次后续调用都要处理全部 6K 令牌的技能文档**。子代理凭借上下文隔离，整体处理的令牌少 67%。总计：**15K 令牌**。

**路由器**：**5 次调用，约 9K 令牌**（并行执行示意图见原文，此处省略。）

路由器使用 **LLM 进行路由**，然后并行调用代理。与子代理类似，但多了明确的路由步骤。总计：**9K 令牌**。

**关键洞察：**对于多领域任务，支持并行执行的模式（子代理、路由器）效率最高。技能调用次数更少，但上下文累积导致令牌使用量高。交接在这里效率低下——它必须顺序执行，无法利用并行工具调用来同时咨询多个领域。

### 总结

以下是四种模式在三种场景下的对比：

| 模式 | 单次请求 | 重复请求 | 多领域 |
| --- | :---: | :---: | :---: |
| [**子代理（Subagents）**](/oss/python/langchain/multi-agent/subagents) | 4 次调用 | 8 次调用（4+4） | 5 次调用，9K 令牌 |
| [**交接（Handoffs）**](/oss/python/langchain/multi-agent/handoffs) | 3 次调用 | 5 次调用（3+2） | 7+ 次调用，14K+ 令牌 |
| [**技能（Skills）**](/oss/python/langchain/multi-agent/skills) | 3 次调用 | 5 次调用（3+2） | 3 次调用，15K 令牌 |
| [**路由器（Router）**](/oss/python/langchain/multi-agent/router) | 3 次调用 | 6 次调用（3+3） | 5 次调用，9K 令牌 |

**选择模式：**

| 优化目标 | [子代理](/oss/python/langchain/multi-agent/subagents) | [交接](/oss/python/langchain/multi-agent/handoffs) | [技能](/oss/python/langchain/multi-agent/skills) | [路由器](/oss/python/langchain/multi-agent/router) |
| --- | :---: | :---: | :---: | :---: |
| 单次请求 | | ✅ | ✅ | ✅ |
| 重复请求 | | ✅ | ✅ | |
| 并行执行 | ✅ | | | ✅ |
| 大上下文领域 | ✅ | | | ✅ |
| 简单、聚焦的任务 | | | ✅ | |

# 交接（Handoffs）

在**交接**架构中，行为会根据状态动态变化。核心机制是：[工具](/oss/python/langchain/tools)更新一个跨轮次持久化的状态变量（例如 `current_step` 或 `active_agent`），系统读取该变量来调整行为——要么应用不同的配置（系统提示词、工具），要么路由到不同的[代理](/oss/python/langchain/agents)。这种模式既支持不同代理之间的交接，也支持单一代理内部的动态配置变更。

> 提示：**交接**一词由 [OpenAI](https://openai.github.io/openai-agents-python/handoffs/) 提出，指用工具调用（例如 `transfer_to_sales_agent`）在代理或状态之间转移控制权。

> 该图展示了一个典型的保修支持交接流程：用户报告手机故障，代理先记录保修状态（步骤：获取保修状态，工具：record_warranty_status），再询问并记录问题类型（步骤：分类问题，工具：record_issue_type），最后根据状态提供解决方案或升级到人工（步骤：提供解决方案，工具：provide_solution、escalate_to_human）。

## 关键特征

* 状态驱动行为：行为基于状态变量（例如 `current_step` 或 `active_agent`）变化
* 基于工具的转换：工具更新状态变量以在状态之间移动
* 直接与用户交互：每个状态的配置直接处理用户消息
* 持久状态：状态跨对话轮次持续存在

## 何时使用

当你需要强制执行顺序约束（只有满足前置条件后才解锁能力）、代理需要跨不同状态直接与用户对话，或者你正在构建多阶段对话流程时，请使用交接模式。这种模式在客户支持场景中尤其有价值，因为你需要按特定顺序收集信息——例如，在处理退款之前先收集保修 ID。

## 基本实现

核心机制是一个返回 [`Command`](/oss/python/langgraph/graph-api#command) 来更新状态、触发到新步骤或新代理转换的[工具](/oss/python/langchain/tools)：

```python
from langchain.tools import tool
from langchain.messages import ToolMessage
from langgraph.types import Command

@tool
def transfer_to_specialist(runtime) -> Command:
    """Transfer to the specialist agent."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content="Transferred to specialist",
                    tool_call_id=runtime.tool_call_id
                )
            ],
            "current_step": "specialist"  # Triggers behavior change
        }
    )
```

> 注意：**为什么需要包含 `ToolMessage`？** 当 LLM 调用工具时，它期望得到响应。带有匹配 `tool_call_id` 的 `ToolMessage` 完成了这个请求-响应循环——没有它，对话历史就会变得畸形。只要你的交接工具更新消息，就必须这样做。

> **教程：用交接模式构建客户支持** [了解更多](/oss/python/langchain/multi-agent/handoffs-customer-support)
> 学习如何使用交接模式构建客户支持代理——单一代理在不同配置之间转换。

## 实现方式

实现交接有两种方式：**[带中间件的单一代理](#single-agent-with-middleware)**（一个代理配合动态配置）或 **[多个代理子图](#multiple-agent-subgraphs)**（不同的代理作为图节点）。

### 带中间件的单一代理

单一代理根据状态改变其行为。中间件拦截每次模型调用，并动态调整系统提示词和可用工具。工具更新状态变量以触发转换：

```python
from langchain.tools import ToolRuntime, tool
from langchain.messages import ToolMessage
from langgraph.types import Command

@tool
def record_warranty_status(
    status: str,
    runtime: ToolRuntime[None, SupportState]
) -> Command:
    """Record warranty status and transition to next step."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Warranty status recorded: {status}",
                    tool_call_id=runtime.tool_call_id
                )
            ],
            "warranty_status": status,
            "current_step": "specialist"  # Update state to trigger transition
        }
    )
```

> 信息：完整示例——带中间件的客户支持

```python
from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langgraph.types import Command
from typing import Callable

# 1. Define state with current_step tracker
class SupportState(AgentState):
    """Track which step is currently active."""
    current_step: str = "triage"
    warranty_status: str | None = None

# 2. Tools update current_step via Command
@tool
def record_warranty_status(
    status: str,
    runtime: ToolRuntime[None, SupportState]
) -> Command:
    """Record warranty status and transition to next step."""
    return Command(update={
        "messages": [
            ToolMessage(
                content=f"Warranty status recorded: {status}",
                tool_call_id=runtime.tool_call_id
            )
        ],
        "warranty_status": status,
        # Transition to next step
        "current_step": "specialist"
    })

# 3. Middleware applies dynamic configuration based on current_step
@wrap_model_call
def apply_step_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Configure agent behavior based on current_step."""
    step = request.state.get("current_step", "triage")

    # Map steps to their configurations
    configs = {
        "triage": {
            "prompt": "Collect warranty information...",
            "tools": [record_warranty_status]
        },
        "specialist": {
            "prompt": "Provide solutions based on warranty: {warranty_status}",
            "tools": [provide_solution, escalate]
        }
    }

    config = configs[step]
    request = request.override(
        system_prompt=config["prompt"].format(**request.state),
        tools=config["tools"]
    )
    return handler(request)

# 4. Create agent with middleware
agent = create_agent(
    model,
    tools=[record_warranty_status, provide_solution, escalate],
    state_schema=SupportState,
    middleware=[apply_step_config],
    checkpointer=InMemorySaver()  # Persist state across turns
)
```

### 多个代理子图

多个不同的代理作为图中的独立节点存在。交接工具使用 `Command.PARENT` 指定下一步要执行哪个节点，从而在代理节点之间导航。

> 警告：子图交接需要仔细的**[上下文工程](/oss/python/langchain/context-engineering)**。与单一代理中间件（消息历史自然流动）不同，你必须明确决定哪些消息在代理之间传递。弄错了，代理就会收到畸形的对话历史或臃肿的上下文。参见下文[上下文工程](#context-engineering)。

```python
from langchain.messages import AIMessage, ToolMessage
from langchain.tools import tool, ToolRuntime
from langgraph.types import Command

@tool
def transfer_to_sales(
    runtime: ToolRuntime,
) -> Command:
    """Transfer to the sales agent."""
    last_ai_message = next(
        msg for msg in reversed(runtime.state["messages"]) if isinstance(msg, AIMessage)
    )
    transfer_message = ToolMessage(
        content="Transferred to sales agent",
        tool_call_id=runtime.tool_call_id,
    )
    return Command(
        goto="sales_agent",
        update={
            "active_agent": "sales_agent",
            "messages": [last_ai_message, transfer_message],
        },
        graph=Command.PARENT
    )
```

> 信息：完整示例——带交接的销售与支持
> 此示例展示了一个包含独立销售和支持代理的多代理系统。每个代理都是一个独立的图节点，交接工具允许代理之间转移对话。

```python
from typing import Literal

from langchain.agents import AgentState, create_agent
from langchain.messages import AIMessage, ToolMessage
from langchain.tools import tool, ToolRuntime
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from typing_extensions import NotRequired

# 1. Define state with active_agent tracker
class MultiAgentState(AgentState):
    active_agent: NotRequired[str]

# 2. Create handoff tools
@tool
def transfer_to_sales(
    runtime: ToolRuntime,
) -> Command:
    """Transfer to the sales agent."""
    last_ai_message = next(
        msg for msg in reversed(runtime.state["messages"]) if isinstance(msg, AIMessage)
    )
    transfer_message = ToolMessage(
        content="Transferred to sales agent from support agent",
        tool_call_id=runtime.tool_call_id,
    )
    return Command(
        goto="sales_agent",
        update={
            "active_agent": "sales_agent",
            "messages": [last_ai_message, transfer_message],
        },
        graph=Command.PARENT,
    )

@tool
def transfer_to_support(
    runtime: ToolRuntime,
) -> Command:
    """Transfer to the support agent."""
    last_ai_message = next(
        msg for msg in reversed(runtime.state["messages"]) if isinstance(msg, AIMessage)
    )
    transfer_message = ToolMessage(
        content="Transferred to support agent from sales agent",
        tool_call_id=runtime.tool_call_id,
    )
    return Command(
        goto="support_agent",
        update={
            "active_agent": "support_agent",
            "messages": [last_ai_message, transfer_message],
        },
        graph=Command.PARENT,
    )

# 3. Create agents with handoff tools
sales_agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[transfer_to_support],
    system_prompt="You are a sales agent. Help with sales inquiries. If asked about technical issues or support, transfer to the support agent.",
)

support_agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[transfer_to_sales],
    system_prompt="You are a support agent. Help with technical issues. If asked about pricing or purchasing, transfer to the sales agent.",
)

# 4. Create agent nodes that invoke the agents
def call_sales_agent(state: MultiAgentState) -> Command:
    """Node that calls the sales agent."""
    response = sales_agent.invoke(state)
    return response

def call_support_agent(state: MultiAgentState) -> Command:
    """Node that calls the support agent."""
    response = support_agent.invoke(state)
    return response

# 5. Create router that checks if we should end or continue
def route_after_agent(
    state: MultiAgentState,
) -> Literal["sales_agent", "support_agent", "__end__"]:
    """Route based on active_agent, or END if the agent finished without handoff."""
    messages = state.get("messages", [])

    # Check the last message - if it's an AIMessage without tool calls, we're done
    if messages:
        last_msg = messages[-1]
        if isinstance(last_msg, AIMessage) and not last_msg.tool_calls:
            return "__end__"

    # Otherwise route to the active agent
    active = state.get("active_agent", "sales_agent")
    return active if active else "sales_agent"

def route_initial(
    state: MultiAgentState,
) -> Literal["sales_agent", "support_agent"]:
    """Route to the active agent based on state, default to sales agent."""
    return state.get("active_agent") or "sales_agent"

# 6. Build the graph
builder = StateGraph(MultiAgentState)
builder.add_node("sales_agent", call_sales_agent)
builder.add_node("support_agent", call_support_agent)

# Start with conditional routing based on initial active_agent
builder.add_conditional_edges(START, route_initial, ["sales_agent", "support_agent"])

# After each agent, check if we should end or route to another agent
builder.add_conditional_edges(
    "sales_agent", route_after_agent, ["sales_agent", "support_agent", END]
)
builder.add_conditional_edges(
    "support_agent", route_after_agent, ["sales_agent", "support_agent", END]
)

graph = builder.compile()
result = graph.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Hi, I'm having trouble with my account login. Can you help?",
            }
        ]
    }
)

for msg in result["messages"]:
    msg.pretty_print()
```

> 提示：大多数交接用例请使用**带中间件的单一代理**——它更简单。只有当你需要定制化的代理实现（例如，一个本身就是包含反思或检索步骤的复杂图的节点）时，才使用**多个代理子图**。

#### 上下文工程

使用子图交接时，你可以精确控制消息在代理之间的流动。这种精确性对于维护有效的对话历史、避免可能让下游代理困惑的上下文膨胀至关重要。更多相关内容，请参阅[上下文工程](/oss/python/langchain/context-engineering)。

**交接期间处理上下文**

在代理之间交接时，你需要确保对话历史保持有效。LLM 期望工具调用与它们的响应配对，因此在使用 `Command.PARENT` 交接给另一个代理时，你必须同时包含两者：

1. **包含工具调用的 `AIMessage`**（触发交接的消息）
2. **确认交接的 `ToolMessage`**（对该工具调用的人工响应）

没有这种配对，接收方代理会看到一个不完整的对话，可能产生错误或意外行为。

下面的示例假设只调用了交接工具（没有并行工具调用）：

```python
@tool
def transfer_to_sales(runtime: ToolRuntime) -> Command:
    # Get the AI message that triggered this handoff
    last_ai_message = runtime.state["messages"][-1]

    # Create an artificial tool response to complete the pair
    transfer_message = ToolMessage(
        content="Transferred to sales agent",
        tool_call_id=runtime.tool_call_id,
    )

    return Command(
        goto="sales_agent",
        update={
            "active_agent": "sales_agent",
            # Pass only these two messages, not the full subagent history
            "messages": [last_ai_message, transfer_message],
        },
        graph=Command.PARENT,
    )
```

> 注意：**为什么不传递所有子代理消息？** 虽然你可以在交接中包含完整的子代理对话，但这通常会带来问题。接收方代理可能被无关的内部推理搞糊涂，令牌成本也会不必要地增加。只传递交接配对，可以让父图的上下文专注于高层协调。如果接收方代理需要额外上下文，考虑在 `ToolMessage` 内容中总结子代理的工作，而不是传递原始消息历史。

**把控制权交还给用户**

当把控制权交还给用户（结束代理的回合）时，请确保最后一条消息是 `AIMessage`。这样可以保持有效的对话历史，并向用户界面发出代理已完成工作的信号。

## 实现考量

在设计多代理系统时，请考虑：

* **上下文过滤策略**：每个代理会收到完整的对话历史、过滤后的部分，还是摘要？根据角色的不同，不同代理可能需要不同的上下文。
* **工具语义**：明确交接工具是只更新路由状态，还是也会产生副作用。例如，`transfer_to_sales()` 是否也应该创建支持工单，还是那应该是单独的操作？
* **令牌效率**：在上下文完整性和令牌成本之间取得平衡。随着对话变长，摘要和选择性上下文传递变得越来越重要。

# 路由器（Router）

在**路由器**架构中，一个路由步骤对输入进行分类，并将其导向专门的[代理](/oss/python/langchain/agents)。当你拥有不同的**垂直领域**（各自需要独立代理的独立知识域）时，这很有用。

> 该图展示了一条典型的路由流程：查询进入路由器，路由器把它分发到代理 A/B/C，各代理的结果再汇总到"综合（Synthesize）"步骤，最终产出组合答案。

## 关键特征

* 路由器分解查询
* 并行调用零个或多个专门代理
* 结果被综合成连贯的响应

## 何时使用

当你拥有不同的垂直领域（各自需要独立代理的独立知识域）、需要并行查询多个来源，并且想把结果综合成组合响应时，请使用路由器模式。

## 基本实现

路由器对查询进行分类，并将其导向合适的代理。使用 [`Command`](/oss/python/langgraph/graph-api#command) 进行单代理路由，或使用 [`Send`](/oss/python/langgraph/graph-api#send) 进行并行扇出到多个代理。

### 单一代理

使用 `Command` 路由到单个专门代理：

```python
from langgraph.types import Command

def classify_query(query: str) -> str:
    """Use LLM to classify query and determine the appropriate agent."""
    # Classification logic here
    ...

def route_query(state: State) -> Command:
    """Route to the appropriate agent based on query classification."""
    active_agent = classify_query(state["query"])

    # Route to the selected agent
    return Command(goto=active_agent)
```

### 多个代理（并行）

使用 `Send` 并行扇出到多个专门代理：

```python
from typing import TypedDict
from langgraph.types import Send

class ClassificationResult(TypedDict):
    query: str
    agent: str

def classify_query(query: str) -> list[ClassificationResult]:
    """Use LLM to classify query and determine which agents to invoke."""
    # Classification logic here
    ...

def route_query(state: State):
    """Route to relevant agents based on query classification."""
    classifications = classify_query(state["query"])

    # Fan out to selected agents in parallel
    return [
        Send(c["agent"], {"query": c["query"]})
        for c in classifications
    ]
```

> **教程：用路由构建多源知识库** [了解更多](/oss/python/langchain/multi-agent/router-knowledge-base)
> 构建一个并行查询 GitHub、Notion 和 Slack 的路由器，然后把结果综合成连贯的答案。涵盖状态定义、专门代理、使用 `Send` 的并行执行以及结果综合。

## 无状态 vs. 有状态

两种方式：

* [**无状态路由器**](#stateless)独立处理每个请求
* [**有状态路由器**](#stateful)跨请求维护对话历史

## 无状态

每个请求独立路由——调用之间没有记忆。对于多轮对话，请参阅[有状态路由器](#stateful)。

> 提示：**路由器 vs. 子代理**：两种模式都可以把工作分派给多个代理，但它们的路由决策方式不同：
>
> * **路由器**：一个专门的路由步骤（通常是单次 LLM 调用或基于规则的逻辑），对输入进行分类并分派给代理。路由器本身通常不维护对话历史，也不进行多轮编排——它是一个预处理步骤。
> * **子代理**：一个主监督代理在持续对话中动态决定调用哪些[子代理](/oss/python/langchain/multi-agent/subagents)。主代理维护上下文，可以跨轮次调用多个子代理，并编排复杂的多步工作流。
>
> 当你拥有清晰的输入类别并想要确定性或轻量级的分类时，使用**路由器**。当你需要灵活的、感知对话的编排（由 LLM 根据不断变化的上下文决定下一步做什么）时，使用**监督代理**。

## 有状态

对于多轮对话，你需要跨调用维护上下文。

### 工具包装

最简单的方法：把无状态路由器包装成对话代理可以调用的工具。对话代理负责记忆和上下文；路由器保持无状态。这避免了跨多个并行代理管理对话历史的复杂性。

```python
@tool
def search_docs(query: str) -> str:
    """Search across multiple documentation sources."""
    result = workflow.invoke({"query": query})
    return result["final_answer"]

# Conversational agent uses the router as a tool
conversational_agent = create_agent(
    model,
    tools=[search_docs],
    prompt="You are a helpful assistant. Use search_docs to answer questions."
)
```

### 完整持久化

如果你需要路由器自身维护状态，请使用[持久化](/oss/python/langchain/short-term-memory)来存储消息历史。路由到代理时，从状态中取出先前的消息，并选择性地把它们包含在代理的上下文中——这是[上下文工程](/oss/python/langchain/context-engineering)的一个杠杆。

> 警告：**有状态路由器需要自定义历史管理。** 如果路由器在轮次之间切换代理，当代理的语气或提示词不同时，对话对终端用户来说可能不够流畅。使用并行调用时，你需要在路由器层面维护历史（输入和综合后的输出），并在路由逻辑中利用这些历史。请考虑改用[交接模式](/oss/python/langchain/multi-agent/handoffs)或[子代理模式](/oss/python/langchain/multi-agent/subagents)——两者都为多轮对话提供了更清晰的语义。

# 技能（Skills）

在**技能**架构中，专门的能力被封装成可调用的"技能"，以增强[代理](/oss/python/langchain/agents)的行为。技能主要是提示词驱动的专业化能力，代理可以按需调用。
如需内置技能支持，请参阅 [Deep Agents](/oss/python/deepagents/skills)。

> 提示：这种模式在概念上与 [Agent Skills](https://agentskills.io/) 和 [llms.txt](https://llmstxt.org/)（由 Jeremy Howard 提出）相同，后者使用工具调用进行文档的渐进式披露。技能模式把渐进式披露应用于专门化的提示词和领域知识，而不仅仅是文档页面。
>
> 如需现成的、能提升代理在 LangChain 生态任务上表现的技能，请参阅 [LangChain Skills](https://github.com/langchain-ai/langchain-skills) 仓库。

> 该图展示了一条典型的技能调用流程：用户 → 代理 → 技能 A/B/C，技能的结果返回给代理，代理再回应用户。

## 关键特征

* 提示词驱动的专业化：技能主要由专门化的提示词定义
* 渐进式披露：技能根据上下文或用户需求变为可用
* 团队分布：不同团队可以独立开发和维护技能
* 轻量级组合：技能比完整的子代理更简单
* 资源感知：技能可以引用脚本、模板和其他资源

## 何时使用

当你想要一个拥有多种可能专业化的单一[代理](/oss/python/langchain/agents)、不需要在技能之间强制执行特定约束、或者不同团队需要独立开发能力时，请使用技能模式。常见例子包括编码助手（面向不同语言或任务的技能）、知识库（面向不同领域的技能）和创意助手（面向不同格式的技能）。

## 基本实现

```python
from langchain.tools import tool
from langchain.agents import create_agent

@tool
def load_skill(skill_name: str) -> str:
    """Load a specialized skill prompt.

    Available skills:
    - write_sql: SQL query writing expert
    - review_legal_doc: Legal document reviewer

    Returns the skill's prompt and context.
    """
    # Load skill content from file/database
    ...

agent = create_agent(
    model="gpt-5.5",
    tools=[load_skill],
    system_prompt=(
        "You are a helpful assistant. "
        "You have access to two skills: "
        "write_sql and review_legal_doc. "
        "Use load_skill to access them."
    ),
)
```

> **教程：用按需技能构建 SQL 助手** [了解更多](/oss/python/langchain/multi-agent/skills-sql-assistant)
> 学习如何使用渐进式披露实现技能——代理按需加载专业化的提示词和模式，而不是提前加载。

## 扩展模式

编写自定义实现时，你可以用几种方式扩展基本的技能模式：

* **动态工具注册**：把渐进式披露与状态管理结合起来，在技能加载时注册新的[工具](/oss/python/langchain/tools)。例如，加载一个"database\_admin"技能既可以添加专门化的上下文，也可以注册数据库专用工具（备份、恢复、迁移）。这使用了多代理模式中通用的工具与状态机制——工具更新状态以动态改变代理能力。

* **层级技能**：技能可以用树状结构定义其他技能，创建嵌套的专业化。例如，加载一个"data\_science"技能可能会让"pandas\_expert"、"visualization"和"statistical\_analysis"等子技能可用。每个子技能都可以按需独立加载，允许对领域知识进行细粒度的渐进式披露。这种层级方法通过把能力组织成可发现的逻辑分组并按需加载，帮助管理大型知识库。

* **资源感知**：虽然每个技能只有一个提示词，但这个提示词可以引用其他资产的存储位置，并提供代理何时应该使用这些资产的信息。当这些资产变得相关时，代理就会知道这些文件存在，并在需要时把它们读入内存以完成任务。这同样遵循渐进式披露模式，并限制上下文窗口中的信息量。

# 子代理（Subagents）

在**子代理**架构中，一个中心化的主[代理](/oss/python/langchain/agents)（通常被称为**监督者**）通过把子代理作为[工具](/oss/python/langchain/tools)调用来协调它们。主代理决定调用哪个子代理、提供什么输入，以及如何组合结果。子代理是无状态的——它们不记得过去的交互，所有对话记忆都由主代理维护。这提供了[上下文](/oss/python/langchain/context-engineering)隔离：每次子代理调用都在干净的上下文窗口中工作，防止主对话中出现上下文膨胀。

如需内置子代理支持，请参阅 [Deep Agents](/oss/python/deepagents/subagents)。

> 该图展示了一条典型的子代理流程：用户 → 主代理 → 子代理 A/B/C，子代理的结果返回主代理，主代理再向用户给出响应。

## 关键特征

* 集中式控制：所有路由都经过主代理
* 不直接与用户交互：子代理把结果返回给主代理，而不是用户（不过你可以在子代理内部使用[中断](/oss/python/langgraph/interrupts#pause-using-interrupt)来允许用户交互）
* 通过工具调用子代理：子代理通过工具被调用
* 并行执行：主代理可以在单个回合内调用多个子代理

> 注意：**监督者 vs. 路由器**：监督代理（本模式）不同于[路由器](/oss/python/langchain/multi-agent/router)。监督者是一个完整的代理，它维护对话上下文，并跨多个回合动态决定调用哪些子代理。路由器通常是一个单一的分类步骤，在不维护持续对话状态的情况下分派给代理。

## 何时使用

当你拥有多个不同的领域（例如日历、邮件、CRM、数据库）、子代理不需要直接与用户对话，或者你想要集中式工作流控制时，请使用子代理模式。对于只有少量[工具](/oss/python/langchain/tools)的更简单情况，请使用[单一代理](/oss/python/langchain/agents)。

> 提示：**需要在子代理内进行用户交互？** 虽然子代理通常把结果返回给主代理而不是直接与用户对话，但你可以在子代理内部使用[中断](/oss/python/langgraph/interrupts#pause-using-interrupt)来暂停执行并收集用户输入。当子代理在继续之前需要澄清或批准时，这很有用。主代理仍然是编排者，但子代理可以在任务进行中收集用户信息。

## 基本实现

核心机制是把子代理包装成主代理可以调用的工具：

```python
from langchain.tools import tool
from langchain.agents import create_agent

# Create a subagent
subagent = create_agent(model="google_genai:gemini-3.6-flash", tools=[...])

# Wrap it as a tool
@tool("research", description="Research a topic and return findings")
def call_research_agent(query: str):
    result = subagent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content

# Main agent with subagent as a tool
main_agent = create_agent(model="google_genai:gemini-3.6-flash", tools=[call_research_agent])
```

> **教程：用子代理构建个人助理** [了解更多](/oss/python/langchain/multi-agent/subagents-personal-assistant)
> 学习如何使用子代理模式构建个人助理——一个中心化的主代理（监督者）协调专门的 worker 代理。

## 设计决策

实现子代理模式时，你会做出几个关键的设计选择。下表总结了这些选项——每个选项都在下文详细介绍。

| 决策 | 选项 |
| --- | --- |
| [**同步 vs. 异步**](#sync-vs-async) | 同步（阻塞）vs. 异步（后台） |
| [**工具模式**](#tool-patterns) | 每个代理一个工具 vs. 单一分发工具 |
| [**子代理规格**](#subagent-specs) | 系统提示词 vs. 枚举约束 vs. 基于工具的发现（仅限单一分发工具） |
| [**子代理输入**](#subagent-inputs) | 仅查询 vs. 完整上下文 |
| [**子代理输出**](#subagent-outputs) | 子代理结果 vs. 完整对话历史 |

## 同步 vs. 异步

子代理执行可以是**同步**的（阻塞）或**异步**的（后台）。你的选择取决于主代理是否需要结果才能继续。

| 模式 | 主代理行为 | 最适合 | 权衡 |
| --- | --- | --- | --- |
| **同步** | 等待子代理完成 | 主代理需要结果才能继续 | 简单，但会阻塞对话 |
| **异步** | 子代理在后台运行时继续 | 独立任务，用户不应等待 | 响应迅速，但更复杂 |

> 提示：不要与 Python 的 `async`/`await` 混淆。这里的"异步"意味着主代理启动一个后台作业（通常在单独的进程或服务中）并继续执行而不阻塞。

### 同步（默认）

默认情况下，子代理调用是**同步**的：主代理等待每个子代理完成后再继续。当主代理的下一步行动依赖于子代理的结果时，使用同步。

> 该图展示了一条同步调用流程：用户询问"东京天气怎么样？"，主代理调用 research 子代理并阻塞等待结果，子代理返回"当前 72°F，晴"，主代理再回复用户。

**何时使用同步：**

* 主代理需要子代理的结果来组织其响应
* 任务存在顺序依赖（例如，获取数据 → 分析 → 响应）
* 子代理失败应阻塞主代理的响应

**权衡：**

* 实现简单——只需调用并等待
* 在所有子代理完成之前，用户看不到响应
* 长时间运行的任务会冻结对话

### 异步

当子代理的工作是独立的——主代理不需要结果就能继续与用户对话时，使用**异步执行**。主代理启动一个后台作业并保持响应能力。

> 该图展示了一条异步调用流程：用户要求审阅 M&A 合同，主代理向作业系统提交任务并立即返回 job_id，用户可随时查询状态；作业完成后，主代理获取结果并向用户呈现合同分析。

**何时使用异步：**

* 子代理工作独立于主对话流程
* 用户应该能够在工作进行的同时候继续聊天
* 你想要并行运行多个独立任务

**三工具模式：**

1. **启动作业**：启动后台任务，返回作业 ID
2. **检查状态**：返回当前状态（pending、running、completed、failed）
3. **获取结果**：检索已完成的结果

**处理作业完成：**当作业完成时，你的应用程序需要通知用户。一种做法：显示一个通知，点击后发送一条 `HumanMessage`，例如"检查 job\_123 并总结结果。"

## 工具模式

有两种主要方式把子代理暴露为工具：

| 模式 | 最适合 | 权衡 |
| --- | --- | --- |
| [**每个代理一个工具**](#tool-per-agent) | 对每个子代理的输入/输出进行细粒度控制 | 设置更多，但定制化更强 |
| [**单一分发工具**](#single-dispatch-tool) | 大量代理、分布式团队、约定优于配置 | 组合更简单，但每个代理的定制化较少 |

### 每个代理一个工具

（结构图与上文"子代理"总览图相同：主代理 → 子代理 A/B/C，结果返回主代理 → 用户响应。）

关键思路是把子代理包装成主代理可以调用的工具：

```python
from langchain.tools import tool
from langchain.agents import create_agent

# Create a sub-agent
subagent = create_agent(model="...", tools=[...])

# Wrap it as a tool
@tool("subagent_name", description="subagent_description")
def call_subagent(query: str):
    result = subagent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content

# Main agent with subagent as a tool
main_agent = create_agent(model="...", tools=[call_subagent])
```

主代理在判断任务与子代理描述匹配时调用子代理工具，接收结果并继续编排。参见[上下文工程](#context-engineering)以获得细粒度控制。

### 单一分发工具

另一种方法使用单一参数化工具来为独立任务调用临时的子代理。与[每个代理一个工具](#tool-per-agent)方法（每个子代理被包装成单独的工具）不同，这种方法使用基于约定的单一 `task` 工具：任务描述作为人类消息传给子代理，子代理的最终消息作为工具结果返回。

当你想要把代理开发分发给多个团队、需要把复杂任务隔离到独立的上下文窗口中、需要一种无需修改协调器即可扩展新代理的方式、或者更喜欢约定优于定制化时，使用这种方法。这种方法用上下文工程的灵活性换取代理组合的简单性和强上下文隔离。

> 该图展示了一条单一分发工具流程：主代理 → task 工具（agent_name、description），按名称把任务分发给 Research/Writer/Reviewer 代理，结果返回 task 工具再交回主代理，主代理向用户给出响应。

**关键特征：**

* 单一任务工具：一个参数化工具，可以按名称调用任何已注册的子代理
* 基于约定的调用：按名称选择代理，任务作为人类消息传递，最终消息作为工具结果返回
* 团队分布：不同团队可以独立开发和部署代理
* 代理发现：子代理可以通过系统提示词（列出可用代理）或通过[渐进式披露](/oss/python/langchain/multi-agent/skills-sql-assistant)（通过工具按需加载代理信息）被发现

> 提示：这种方法的一个有趣之处在于，子代理可能与主代理拥有完全相同的能力。在这种情况下，调用子代理**实际上是出于上下文隔离**这个主要原因——让复杂的多步任务在隔离的上下文窗口中运行，而不会让主代理的对话历史膨胀。子代理自主完成工作并只返回简洁的摘要，让主线程保持专注和高效。

> 信息：带任务分发器的代理注册表

```python
from langchain.tools import tool
from langchain.agents import create_agent

# Sub-agents developed by different teams
research_agent = create_agent(
    model="gpt-5.5",
    prompt="You are a research specialist..."
)

writer_agent = create_agent(
    model="gpt-5.5",
    prompt="You are a writing specialist..."
)

# Registry of available sub-agents
SUBAGENTS = {
    "research": research_agent,
    "writer": writer_agent,
}

@tool
def task(
    agent_name: str,
    description: str
) -> str:
    """Launch an ephemeral subagent for a task.

    Available agents:
    - research: Research and fact-finding
    - writer: Content creation and editing
    """
    agent = SUBAGENTS[agent_name]
    result = agent.invoke({
        "messages": [
            {"role": "user", "content": description}
        ]
    })
    return result["messages"][-1].content

# Main coordinator agent
main_agent = create_agent(
    model="gpt-5.5",
    tools=[task],
    system_prompt=(
        "You coordinate specialized sub-agents. "
        "Available: research (fact-finding), "
        "writer (content creation). "
        "Use the task tool to delegate work."
    ),
)
```

## 上下文工程

控制上下文如何在主代理与其子代理之间流动：

| 类别 | 目的 | 影响 |
| --- | --- | --- |
| [**子代理规格**](#subagent-specs) | 确保子代理在应该被调用时被调用 | 主代理的路由决策 |
| [**子代理输入**](#subagent-inputs) | 确保子代理能以优化的上下文良好执行 | 子代理性能 |
| [**子代理输出**](#subagent-outputs) | 确保监督者能基于子代理结果行动 | 主代理性能 |

另请参阅我们为代理编写的综合[上下文工程](/oss/python/langchain/context-engineering)指南。

### 子代理规格

与子代理关联的**名称**和**描述**是主代理知道该调用哪个子代理的主要方式。这些是提示词杠杆——请谨慎选择。

* **名称**：主代理引用子代理的方式。保持清晰且面向行动（例如 `research_agent`、`code_reviewer`）。
* **描述**：主代理了解子代理能力的途径。要具体说明它处理什么任务以及何时使用它。

对于[单一分发工具](#single-dispatch-tool)设计，你还必须向主代理提供关于它可以调用的子代理的信息。你可以根据代理数量和注册表是静态还是动态，以不同方式提供这些信息：

| 方法 | 最适合 | 权衡 |
| --- | --- | --- |
| **系统提示词枚举** | 小型、静态的代理列表（< 10 个代理） | 简单，但代理变化时需要更新提示词 |
| **枚举约束** | 小型、静态的代理列表（< 10 个代理） | 类型安全且明确，但代理变化时需要改代码 |
| **基于工具的发现** | 大型或动态的代理注册表 | 灵活且可扩展，但增加了复杂性 |

#### 系统提示词枚举

直接在主代理的系统提示词中列出可用代理。主代理把代理列表及其描述作为其指令的一部分。

**何时使用：**

* 你有一个小型、固定的代理集合（< 10 个）
* 代理注册表很少变化
* 你想要最简单的实现

**示例：**

```python
main_agent = create_agent(
    model="...",
    tools=[task],
    system_prompt=(
        "You coordinate specialized sub-agents. "
        "Available agents:\n"
        "- research: Research and fact-finding\n"
        "- writer: Content creation and editing\n"
        "- reviewer: Code and document review\n"
        "Use the task tool to delegate work."
    ),
)
```

#### 分发工具上的枚举约束

在分发工具的 `agent_name` 参数上添加枚举约束。这提供了类型安全，并使可用代理在工具模式中明确可见。

**何时使用：**

* 你有一个小型、固定的代理集合（< 10 个）
* 你想要类型安全和明确的代理名称
* 你更喜欢基于模式的验证而非基于提示词的引导

**示例：**

```python
from enum import Enum

class AgentName(str, Enum):
    RESEARCH = "research"
    WRITER = "writer"
    REVIEWER = "reviewer"

@tool
def task(
    agent_name: AgentName,  # Enum constraint
    description: str
) -> str:
    """Launch an ephemeral subagent for a task."""
    # ...
```

#### 基于工具的发现

提供一个单独的工具（例如 `list_agents` 或 `search_agents`），主代理可以调用它来按需发现可用代理。这实现了渐进式披露，并支持动态注册表。

**何时使用：**

* 你有很多代理（> 10 个）或不断增长的注册表
* 代理注册表频繁变化或是动态的
* 你想要减少提示词大小和令牌使用量
* 不同团队独立管理不同的代理

**示例：**

```python
@tool
def list_agents(query: str = "") -> str:
    """List available subagents, optionally filtered by query."""
    agents = search_agent_registry(query)
    return format_agent_list(agents)

@tool
def task(agent_name: str, description: str) -> str:
    """Launch an ephemeral subagent for a task."""
    # ...

main_agent = create_agent(
    model="...",
    tools=[task, list_agents],
    system_prompt="Use list_agents to discover available subagents, then use task to invoke them."
)
```

### 子代理输入

定制子代理接收什么上下文来执行其任务。通过从代理的状态中提取，添加不适合在静态提示词中捕获的输入——完整的消息历史、先前的结果或任务元数据。

**Subagent inputs example**
```python
from langchain.agents import AgentState
from langchain.tools import tool, ToolRuntime

class CustomState(AgentState):
    example_state_key: str

@tool(
    "subagent1_name",
    description="subagent1_description"
)
def call_subagent1(query: str, runtime: ToolRuntime[None, CustomState]):
    # Apply any logic needed to transform the messages into a suitable input
    subagent_input = some_logic(query, runtime.state["messages"])
    result = subagent1.invoke({
        "messages": subagent_input,
        # You could also pass other state keys here as needed.
        # Make sure to define these in both the main and subagent's
        # state schemas.
        "example_state_key": runtime.state["example_state_key"]
    })
    return result["messages"][-1].content
```

### 子代理输出

定制主代理收到什么，以便它做出好的决策。两种策略：

1. **提示子代理**：明确指定应该返回什么。一个常见的失败模式是子代理执行了工具调用或推理，但没有把结果包含在最终消息中——提醒它监督者只看到最终输出。
2. **在代码中格式化**：在返回之前调整或丰富响应。例如，使用 [`Command`](/oss/python/langgraph/graph-api#command) 在最终文本之外传回特定的状态键。

**Subagent outputs example**
```python
from typing import Annotated
from langchain.agents import AgentState
from langchain.tools import InjectedToolCallId
from langgraph.types import Command

@tool(
    "subagent1_name",
    description="subagent1_description"
)
def call_subagent1(
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    result = subagent1.invoke({
        "messages": [{"role": "user", "content": query}]
    })
    return Command(update={
        # Pass back additional state from the subagent
        "example_state_key": result["example_state_key"],
        "messages": [
            ToolMessage(
                content=result["messages"][-1].content,
                tool_call_id=tool_call_id
            )
        ]
    })
```

## 检查点与状态检查

默认情况下，子代理使用**继承的检查点器**模式——每次调用都以全新状态开始，支持[中断](/oss/python/langgraph/interrupts#pause-using-interrupt)，并且可以安全地并行运行。如果你需要子代理跨调用维护自己的持久对话历史，可以用 `checkpointer=True`（continuations 模式）编译它。有关模式的完整比较，请参阅[子图持久化](/oss/python/langgraph/use-subgraphs#subgraph-persistence)。

因为子代理在工具函数内部被调用，LangGraph 无法[静态发现](/oss/python/langgraph/use-subgraphs#view-subgraph-state)它们。这意味着带 `subgraphs` 的 [`get_state`](/oss/python/langgraph/use-subgraphs#view-subgraph-state) 不会返回子代理状态。如果你需要读取嵌套的图状态（例如在[中断](/oss/python/langgraph/interrupts#pause-using-interrupt)期间），请改为在自定义图中的[节点函数](/oss/python/langgraph/use-subgraphs#call-a-subgraph-inside-a-node)中调用子代理。有关每种模式如何影响状态可见性的细节，请参阅[子图持久化](/oss/python/langgraph/use-subgraphs#subgraph-persistence)。

> **从 langgraph-supervisor 迁移** [查看指南](/oss/python/migrate/langgraph-supervisor)
> langgraph-supervisor 包已不再积极维护。学习如何从 create\_supervisor 迁移到子代理模式，包括带外部 API 回调的中断与恢复流程。

# 测试

> 测试 LangChain 代理的策略，包括单元测试、集成测试和轨迹评估。

代理型应用让 LLM 自行决定下一步来解决问题。这种灵活性很强大，但模型的"黑盒"特性使得你难以预测代理中某一处的改动会如何影响整体。要构建生产就绪的代理，全面的测试至关重要。

测试代理有几种方法：

* **单元测试**：使用内存中的模拟对象（fakes）隔离地测试代理中小的、确定性的部分，以便快速、确定性地断言精确行为。
* **集成测试**：使用真实的网络调用测试代理，确认各组件能协同工作、凭据与模式（schema）匹配、延迟可接受。
* **评估（Evals）**：使用评估器评估代理的执行轨迹，既可通过确定性匹配，也可借助 LLM 裁判。

代理型应用往往更依赖集成测试，因为它们将多个组件串联在一起，并且必须应对 LLM 非确定性带来的不稳定性。

> 提示：使用 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-test-index) 大规模运行评估、跟踪结果随时间的变化并比较实验。参见[评估 LLM 应用](/langsmith/evaluate-llm-application) 开始使用。

* [单元测试](/oss/python/langchain/test/unit-testing)：模拟聊天模型并使用内存持久化，无需 API 调用即可测试代理逻辑。
* [集成测试](/oss/python/langchain/test/integration-testing)：使用真实 LLM API 测试代理。组织测试、管理密钥、处理不稳定性并控制成本。
* [评估](/oss/python/langchain/test/evals)：使用确定性匹配或 LLM 作为裁判的评估器评估代理轨迹。

# 单元测试

> 使用模拟聊天模型和内存持久化，无需 API 调用即可测试代理逻辑。

单元测试隔离地测试代理中小的、确定性的部分。通过用内存中的模拟对象（又称 fixture）替换真实 LLM，你可以脚本化精确的响应（文本、工具调用和错误），使测试无需 API 密钥即可快速、免费且可重复。

## 模拟聊天模型

LangChain 提供 [`GenericFakeChatModel`](https://reference.langchain.com/python/langchain-core/language_models/fake_chat_models/GenericFakeChatModel) 用于模拟文本响应。它接受一个响应迭代器（[`AIMessage`](https://reference.langchain.com/python/langchain-core/messages/ai/AIMessage) 对象或字符串），每次调用返回一个。它同时支持常规和流式用法。

```python
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

model = GenericFakeChatModel(messages=iter([
    AIMessage(content="", tool_calls=[ToolCall(name="foo", args={"bar": "baz"}, id="call_1")]),
    "bar"
]))

model.invoke("hello")
# AIMessage(content='', ..., tool_calls=[{'name': 'foo', 'args': {'bar': 'baz'}, 'id': 'call_1', 'type': 'tool_call'}])
```

如果我们再次调用模型，它将返回迭代器中的下一个条目：

```python
model.invoke("hello, again!")
# AIMessage(content='bar', ...)
```

## InMemorySaver 检查点

为了在测试期间启用持久化，你可以使用 [`InMemorySaver`](https://reference.langchain.com/python/langgraph/checkpoints/#langgraph.checkpoint.memory.InMemorySaver) 检查点。这允许你模拟多轮对话，以测试依赖状态的行为：

```python
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model,
    tools=[],
    checkpointer=InMemorySaver()
)

# First invocation
agent.invoke(
    {"messages": [HumanMessage(content="I live in Sydney, Australia")]},
    config={"configurable": {"thread_id": "session-1"}}
)

# Second invocation: the first message is persisted (Sydney location), so the model returns GMT+10 time
agent.invoke(
    {"messages": [HumanMessage(content="What's my local time?")]},
    config={"configurable": {"thread_id": "session-1"}}
)
```

## 下一步

了解如何在[集成测试](/oss/python/langchain/test/integration-testing)中使用真实的模型提供商 API 测试你的代理。

# 集成测试

> 通过组织测试、管理密钥、处理不稳定性并控制成本，使用真实 LLM API 测试代理。

集成测试验证你的代理能与模型 API 和外部服务正确协同工作。与使用模拟对象和替身（mocks）的[单元测试](/oss/python/langchain/test/unit-testing)不同，集成测试会发起真实的网络调用，以确认各组件能协同工作、凭据有效、延迟可接受。

由于 LLM 响应是非确定性的，集成测试需要与传统软件测试不同的策略。本指南介绍如何为你的代理组织、编写和运行集成测试。若要了解为 LangChain 本身做贡献时的一般测试基础设施，参见[为代码做贡献](/oss/python/contributing/code#running-tests)。

## 将单元测试与集成测试分开

集成测试较慢且需要 API 凭据，因此请将它们与单元测试分开。这样你可以在每次变更时运行快速的单元测试，而把集成测试保留给 CI 或部署前检查。

使用 pytest 标记来标记集成测试：

```python
import pytest

@pytest.mark.integration
def test_agent_with_real_model():
    agent = create_agent("claude-sonnet-4-6", tools=[get_weather])
    result = agent.invoke({
        "messages": [HumanMessage(content="What's the weather in SF?")]
    })
    assert len(result["messages"]) > 1
```

配置 pytest 识别该标记，并从默认运行中排除集成测试：

文件 `pytest.ini`：

```ini
[pytest]
markers =
    integration: tests that call real LLM APIs
addopts = -m "not integration"
```

文件 `pyproject.toml`：

```toml
[tool.pytest.ini_options]
markers = [
  "integration: tests that call real LLM APIs"
]
addopts = "-m 'not integration'"
```

显式运行集成测试：

```bash
pytest -m integration
```

## 管理 API 密钥

集成测试需要真实的 API 凭据。请从环境变量中加载它们，使密钥不进入源代码控制。

使用 `conftest.py` 中的 fixture 验证所需的密钥是否可用：

```python
import os
import pytest

@pytest.fixture(autouse=True)
def check_api_keys():
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
```

对于本地开发，将密钥存储在 `.env` 文件中，并使用 [`python-dotenv`](https://pypi.org/project/python-dotenv/) 加载：

文件 `.env`：

```bash
OPENAI_API_KEY=sk-...
```

文件 `conftest.py`：

```python
from dotenv import load_dotenv

load_dotenv()
```

> 警告：将 `.env` 添加到你的 `.gitignore` 中，避免提交凭据。在 CI 中，通过提供商的安全管理（例如 GitHub Actions secrets）注入密钥。

## 断言结构而非内容

LLM 响应在每次运行之间会有所不同。不要对精确的输出字符串做断言，而是验证响应的结构属性：消息类型、工具调用名称、参数形状和消息数量。

```python
def test_agent_calls_weather_tool():
    agent = create_agent("claude-sonnet-4-6", tools=[get_weather])
    result = agent.invoke({
        "messages": [HumanMessage(content="What's the weather in SF?")]
    })

    messages = result["messages"]
    tool_calls = [
        tc
        for msg in messages
        if hasattr(msg, "tool_calls")
        for tc in (msg.tool_calls or [])
    ]

    assert any(tc["name"] == "get_weather" for tc in tool_calls)
    assert isinstance(messages[-1], AIMessage)
    assert len(messages[-1].content) > 0
```

> 提示：如需更严格的轨迹断言，请使用支持 `unordered` 和 `superset` 等模糊匹配模式的 [AgentEvals](/oss/python/langchain/test/evals) 评估器。

## 降低成本与延迟

调用 LLM API 的集成测试会产生真实成本。以下实践有助于保持测试套件快速且经济：

* **使用更小的模型**：`gemini-3.1-flash-lite` 或等效模型，用于只需验证工具调用和响应结构的测试。
* **设置 `maxTokens`**：限制响应长度，避免冗长昂贵的补全。
* **限制测试范围**：每个测试只测一种行为。当单轮测试足够时，避免串联多次 LLM 调用的端到端场景。
* **选择性运行**：使用上文[测试分离](#separate-unit-and-integration-tests)只在 CI 或部署前运行集成测试，而不是每次保存文件时都运行。

```python
agent = create_agent(
    "gemini-3.1-flash-lite",
    tools=[get_weather],
    model_kwargs={"max_tokens": 256},
)
```

## 记录并重放 HTTP 调用

对于在 CI 中频繁运行的测试，你可以在首次运行时记录 HTTP 交互，并在后续运行中重放它们，而无需发起真实 API 调用。这可以在初始记录之后消除成本和延迟。

[`vcrpy`](https://pypi.org/project/vcrpy/1.5.2/) 将 HTTP 请求/响应对记录到 YAML "cassette" 文件中。[`pytest-recording`](https://pypi.org/project/pytest-recording/) 插件将其与 pytest 集成。

设置你的 `conftest.py`，从 cassette 中过滤敏感信息：

文件 `conftest.py`：

```py
import pytest

@pytest.fixture(scope="session")
def vcr_config():
    return {
        "filter_headers": [
            ("authorization", "XXXX"),
            ("x-api-key", "XXXX"),
        ],
        "filter_query_parameters": [
            ("api_key", "XXXX"),
            ("key", "XXXX"),
        ],
    }
```

配置你的项目以识别 `vcr` 标记：

文件 `pytest.ini`：

```ini
[pytest]
markers =
    vcr: record/replay HTTP via VCR
addopts = --record-mode=once
```

文件 `pyproject.toml`：

```toml
[tool.pytest.ini_options]
markers = [
  "vcr: record/replay HTTP via VCR"
]
addopts = "--record-mode=once"
```

> 信息：`--record-mode=once` 选项会在首次运行时记录 HTTP 交互，并在后续运行中重放它们。

用 `vcr` 标记装饰你的测试：

```python
@pytest.mark.vcr()
def test_agent_trajectory():
    agent = create_agent("claude-sonnet-4-6", tools=[get_weather])
    result = agent.invoke({
        "messages": [HumanMessage(content="What's the weather in SF?")]
    })
    assert any(
        tc["name"] == "get_weather"
        for msg in result["messages"]
        if hasattr(msg, "tool_calls")
        for tc in (msg.tool_calls or [])
    )
```

首次运行会发起真实的网络调用，并在 `tests/cassettes/` 中生成 cassette 文件。后续运行会重放记录的响应。

> 警告：当你修改提示词、添加新工具或更改预期轨迹时，保存的 cassette 会过期，你的现有测试**将失败**。删除相应的 cassette 文件并重新运行测试，以记录新的交互。

## 下一步

了解如何使用确定性匹配或 LLM 作为裁判的评估器评估代理轨迹，参见[评估](/oss/python/langchain/test/evals)。

# 代理评估（Agent Evals）

> 使用 AgentEvals 和 LangSmith，通过确定性匹配或 LLM 作为裁判的评估器评估代理轨迹。

评估（"evals"）通过评估代理的执行轨迹——它产生的消息和工具调用序列——来衡量代理的表现。与验证基本正确性的[集成测试](/oss/python/langchain/test/integration-testing)不同，评估会对照参考或评分标准对代理行为打分，因此在更改提示词、工具或模型时，它们对捕捉回归很有用。

评估器是一个函数，接收代理输出（以及可选的参考输出）并返回一个分数：

```python
def evaluator(*, outputs: dict, reference_outputs: dict):
    output_messages = outputs["messages"]
    reference_messages = reference_outputs["messages"]
    score = compare_messages(output_messages, reference_messages)
    return {"key": "evaluator_score", "score": score}
```

[`agentevals`](https://github.com/langchain-ai/agentevals) 包为代理轨迹提供了预构建的评估器。你可以通过**轨迹匹配**（确定性比较）或**LLM 裁判**（定性评估）进行评估：

| 方法 | 使用时机 |
| --- | --- |
| [轨迹匹配](#trajectory-match-evaluator) | 你知道预期的工具调用，并想要快速、确定性、零成本的检查 |
| [LLM 作为裁判](#llm-as-judge-evaluator) | 你想在没有严格预期的情况下评估整体质量和推理 |

## 安装 AgentEvals

使用 pip：

```bash
pip install -U agentevals
```

使用 uv：

```bash
uv add agentevals
```

或者，直接克隆 [AgentEvals 仓库](https://github.com/langchain-ai/agentevals)。

## 轨迹匹配评估器

AgentEvals 提供 `create_trajectory_match_evaluator` 函数，将你的代理轨迹与参考轨迹进行匹配。有四种模式：

| 模式 | 描述 | 使用场景 |
| --- | --- | --- |
| `strict` | 消息结构和工具调用按相同顺序精确匹配（消息内容可以不同） | 测试特定的序列（例如授权前先进行策略查询） |
| `unordered` | 与参考轨迹具有相同的消息结构和工具调用，但工具调用可以以任意顺序发生 | 验证信息检索时顺序无关紧要 |
| `subset` | 代理只调用参考轨迹中的工具（没有额外调用） | 确保代理不超出预期范围 |
| `superset` | 代理至少调用参考轨迹中的工具（允许额外调用） | 验证是否采取了最低限度的必要操作 |

下面的示例共享一个公共设置：一个带有 `get_weather` 工具的代理：

```python
from langchain.agents import create_agent
from langchain.tools import tool
from langchain.messages import HumanMessage, AIMessage, ToolMessage
from agentevals.trajectory.match import create_trajectory_match_evaluator

@tool
def get_weather(city: str):
    """Get weather information for a city."""
    return f"It's 75 degrees and sunny in {city}."

agent = create_agent("claude-sonnet-4-6", tools=[get_weather])
```

> 信息：**严格匹配（Strict match）**
>
> `strict` 模式确保轨迹包含相同顺序的相同消息和相同的工具调用，但允许消息内容不同。当需要强制执行特定的操作序列（例如在授权操作前先进行策略查询）时，这很有用。

```python
evaluator = create_trajectory_match_evaluator(
    trajectory_match_mode="strict",
)

def test_weather_tool_called_strict():
    result = agent.invoke({
        "messages": [HumanMessage(content="What's the weather in San Francisco?")]
    })

    reference_trajectory = [
        HumanMessage(content="What's the weather in San Francisco?"),
        AIMessage(content="", tool_calls=[
            {"id": "call_1", "name": "get_weather", "args": {"city": "San Francisco"}}
        ]),
        ToolMessage(content="It's 75 degrees and sunny in San Francisco.", tool_call_id="call_1"),
        AIMessage(content="The weather in San Francisco is 75 degrees and sunny."),
    ]

    evaluation = evaluator(
        outputs=result["messages"],
        reference_outputs=reference_trajectory
    )
    # {
    #     'key': 'trajectory_strict_match',
    #     'score': True,
    #     'comment': None,
    # }
    assert evaluation["score"] is True
```

> 信息：**无序匹配（Unordered match）**
>
> `unordered` 模式允许相同的工具调用以任意顺序出现。当你想验证是否检索到了特定信息但不关心顺序时，这很有帮助。例如，一个代理使用不同的工具调用检查某个城市的天气和活动。

```python
@tool
def get_events(city: str):
    """Get events happening in a city."""
    return f"Concert at the park in {city} tonight."

agent = create_agent("claude-sonnet-4-6", tools=[get_weather, get_events])

evaluator = create_trajectory_match_evaluator(
    trajectory_match_mode="unordered",
)

def test_multiple_tools_any_order():
    result = agent.invoke({
        "messages": [HumanMessage(content="What's happening in SF today?")]
    })

    reference_trajectory = [
        HumanMessage(content="What's happening in SF today?"),
        AIMessage(content="", tool_calls=[
            {"id": "call_1", "name": "get_events", "args": {"city": "SF"}},
            {"id": "call_2", "name": "get_weather", "args": {"city": "SF"}},
        ]),
        ToolMessage(content="Concert at the park in SF tonight.", tool_call_id="call_1"),
        ToolMessage(content="It's 75 degrees and sunny in SF.", tool_call_id="call_2"),
        AIMessage(content="Today in SF: 75 degrees and sunny with a concert at the park tonight."),
    ]

    evaluation = evaluator(
        outputs=result["messages"],
        reference_outputs=reference_trajectory,
    )
    assert evaluation["score"] is True
```

> 信息：**子集与超集匹配（Subset and superset match）**
>
> `superset` 和 `subset` 模式匹配部分轨迹。`superset` 模式验证代理至少调用了参考轨迹中的工具，允许额外的工具调用。`subset` 模式确保代理没有调用参考轨迹之外的任何工具。

```python
@tool
def get_detailed_forecast(city: str):
    """Get detailed weather forecast for a city."""
    return f"Detailed forecast for {city}: sunny all week."

agent = create_agent("claude-sonnet-4-6", tools=[get_weather, get_detailed_forecast])

evaluator = create_trajectory_match_evaluator(
    trajectory_match_mode="superset",
)

def test_agent_calls_required_tools_plus_extra():
    result = agent.invoke({
        "messages": [HumanMessage(content="What's the weather in Boston?")]
    })

    # Reference only requires get_weather, but agent may call additional tools
    reference_trajectory = [
        HumanMessage(content="What's the weather in Boston?"),
        AIMessage(content="", tool_calls=[
            {"id": "call_1", "name": "get_weather", "args": {"city": "Boston"}},
        ]),
        ToolMessage(content="It's 75 degrees and sunny in Boston.", tool_call_id="call_1"),
        AIMessage(content="The weather in Boston is 75 degrees and sunny."),
    ]

    evaluation = evaluator(
        outputs=result["messages"],
        reference_outputs=reference_trajectory,
    )
    assert evaluation["score"] is True
```

> 信息：你还可以设置 `tool_args_match_mode` 属性和/或 `tool_args_match_overrides`，以自定义评估器在比较实际轨迹与参考轨迹中的工具调用时如何判定相等。默认情况下，只有对同一工具使用相同参数的调用才被视为相等。更多细节请访问[仓库](https://github.com/langchain-ai/agentevals?tab=readme-ov-file#tool-args-match-modes)。

## LLM 作为裁判的评估器

你可以使用 `create_trajectory_llm_as_judge` 函数，让 LLM 评估代理的执行路径。与轨迹匹配评估器不同，它不需要参考轨迹，但如果可用，也可以提供。

> 信息：**无参考轨迹**

```python
from agentevals.trajectory.llm import create_trajectory_llm_as_judge, TRAJECTORY_ACCURACY_PROMPT

evaluator = create_trajectory_llm_as_judge(
    model="openai:o3-mini",
    prompt=TRAJECTORY_ACCURACY_PROMPT,
)

def test_trajectory_quality():
    result = agent.invoke({
        "messages": [HumanMessage(content="What's the weather in Seattle?")]
    })

    evaluation = evaluator(
        outputs=result["messages"],
    )
    assert evaluation["score"] is True
```

> 信息：**带参考轨迹**
>
> 如果你有参考轨迹，请使用预构建的 `TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE` 提示词：

```python
from agentevals.trajectory.llm import create_trajectory_llm_as_judge, TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE

evaluator = create_trajectory_llm_as_judge(
    model="openai:o3-mini",
    prompt=TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE,
)
evaluation = evaluator(
    outputs=result["messages"],
    reference_outputs=reference_trajectory,
)
```

> 信息：关于如何让 LLM 评估轨迹的更多可配置项，请访问[仓库](https://github.com/langchain-ai/agentevals?tab=readme-ov-file#trajectory-llm-as-judge)。

### 异步支持

所有 `agentevals` 评估器都支持 Python asyncio。在函数名中的 `create_` 之后加上 `async` 即可获得异步版本。

> 信息：**异步裁判和评估器示例**

```python
from agentevals.trajectory.llm import create_async_trajectory_llm_as_judge, TRAJECTORY_ACCURACY_PROMPT
from agentevals.trajectory.match import create_async_trajectory_match_evaluator

async_judge = create_async_trajectory_llm_as_judge(
    model="openai:o3-mini",
    prompt=TRAJECTORY_ACCURACY_PROMPT,
)

async_evaluator = create_async_trajectory_match_evaluator(
    trajectory_match_mode="strict",
)

async def test_async_evaluation():
    result = await agent.ainvoke({
        "messages": [HumanMessage(content="What's the weather?")]
    })

    evaluation = await async_judge(outputs=result["messages"])
    assert evaluation["score"] is True
```

## 在 LangSmith 中运行评估

为了随时间跟踪实验，请将评估器结果记录到 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-test-evals)。首先，设置所需的环境变量：

```bash
export LANGSMITH_API_KEY="your_langsmith_api_key"
export LANGSMITH_TRACING="true"
```

LangSmith 提供了两种主要的评估运行方法：[pytest](/langsmith/pytest) 集成和 `evaluate` 函数。

> 信息：**使用 pytest 集成**

```python
import pytest
from langsmith import testing as t
from agentevals.trajectory.llm import create_trajectory_llm_as_judge, TRAJECTORY_ACCURACY_PROMPT

trajectory_evaluator = create_trajectory_llm_as_judge(
    model="openai:o3-mini",
    prompt=TRAJECTORY_ACCURACY_PROMPT,
)

@pytest.mark.langsmith
def test_trajectory_accuracy():
    result = agent.invoke({
        "messages": [HumanMessage(content="What's the weather in SF?")]
    })

    reference_trajectory = [
        HumanMessage(content="What's the weather in SF?"),
        AIMessage(content="", tool_calls=[
            {"id": "call_1", "name": "get_weather", "args": {"city": "SF"}},
        ]),
        ToolMessage(content="It's 75 degrees and sunny in SF.", tool_call_id="call_1"),
        AIMessage(content="The weather in SF is 75 degrees and sunny."),
    ]

    t.log_inputs({})
    t.log_outputs({"messages": result["messages"]})
    t.log_reference_outputs({"messages": reference_trajectory})

    trajectory_evaluator(
        outputs=result["messages"],
        reference_outputs=reference_trajectory
    )
```

用 pytest 运行评估：

```bash
pytest test_trajectory.py --langsmith-output
```

> 信息：**使用 evaluate 函数**
>
> 创建一个 [LangSmith 数据集](/langsmith/manage-datasets) 并使用 `evaluate` 函数。数据集必须具有以下模式：
>
> * **input**：`{"messages": [...]}` 用于调用代理的输入消息。
> * **output**：`{"messages": [...]}` 代理输出中预期的消息历史。对于轨迹评估，你可以选择只保留助手消息。

```python
from langsmith import Client
from agentevals.trajectory.llm import create_trajectory_llm_as_judge, TRAJECTORY_ACCURACY_PROMPT

client = Client()

trajectory_evaluator = create_trajectory_llm_as_judge(
    model="openai:o3-mini",
    prompt=TRAJECTORY_ACCURACY_PROMPT,
)

def run_agent(inputs):
    return agent.invoke(inputs)["messages"]

experiment_results = client.evaluate(
    run_agent,
    data="your_dataset_name",
    evaluators=[trajectory_evaluator]
)
```

> 提示：要了解更多关于评估代理的内容，请参阅 [LangSmith 文档](/langsmith/pytest)。

# 可观测性

随着你用 LangChain 构建和运行代理，你需要了解它们的行为：调用了哪些[工具](/oss/python/langchain/tools)、生成了哪些提示词、如何做出决策。使用 [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 构建的 LangChain 代理会自动支持通过 [LangSmith](/langsmith/observability) 进行追踪——这是一个用于捕获、调试、评估和监控 LLM 应用行为的平台。

[*追踪（Traces）*](/langsmith/observability-concepts#traces) 会记录代理执行的每一个步骤，从最初的用户输入到最终响应，包括所有工具调用、模型交互和决策点。这些执行数据可以帮助你调试问题、评估不同输入下的表现，并在生产环境中监控使用模式。

本指南介绍如何为你的 LangChain 代理启用追踪，并使用 LangSmith 分析它们的执行情况。

## 前置条件

开始之前，请确保你已具备以下条件：

* **一个 LangSmith 账号**：在 [smith.langchain.com](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-observability) 免费注册或登录。
* **一个 LangSmith API 密钥**：按照[创建 API 密钥](/langsmith/create-account-api-key)指南操作。

## 启用追踪

所有 LangChain 代理都自动支持 LangSmith 追踪。要启用它，请设置以下环境变量：

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=<your-api-key>
```

## 快速开始

无需额外代码即可将追踪记录到 LangSmith。只需像平常一样运行你的代理代码：

```python
from langchain.agents import create_agent

def send_email(to: str, subject: str, body: str):
    """Send an email to a recipient."""
    # ... email sending logic
    return f"Email sent to {to}"

def search_web(query: str):
    """Search the web for information."""
    # ... web search logic
    return f"Search results for: {query}"

agent = create_agent(
    model="gpt-5.5",
    tools=[send_email, search_web],
    system_prompt="You are a helpful assistant that can send emails and search the web."
)

# Run the agent - all steps will be traced automatically
response = agent.invoke({
    "messages": [{"role": "user", "content": "Search for the latest AI news and email a summary to john@example.com"}]
})
```

默认情况下，追踪会记录到名为 `default` 的项目中。要配置自定义项目名称，请参阅[记录到项目](/langsmith/log-traces-to-project)。

## 选择性追踪

你可以使用 LangSmith 的 `tracing_context` 上下文管理器选择性地追踪特定调用或应用的特定部分：

```python
import langsmith as ls

# This WILL be traced
with ls.tracing_context(enabled=True):
    agent.invoke({"messages": [{"role": "user", "content": "Send a test email to alice@example.com"}]})

# This will NOT be traced (if LANGSMITH_TRACING is not set)
agent.invoke({"messages": [{"role": "user", "content": "Send another email"}]})
```

## 记录到项目

### 静态设置

你可以通过设置 `LANGSMITH_PROJECT` 环境变量为整个应用指定自定义项目名称：

```bash
export LANGSMITH_PROJECT=my-agent-project
```

### 动态设置

你可以通过编程方式为特定操作设置项目名称：

```python
import langsmith as ls

with ls.tracing_context(project_name="email-agent-test", enabled=True):
    response = agent.invoke({
        "messages": [{"role": "user", "content": "Send a welcome email"}]
    })
```

## 为追踪添加元数据

你可以用自定义元数据和标签为追踪添加注释：

```python
response = agent.invoke(
    {"messages": [{"role": "user", "content": "Send a welcome email"}]},
    config={
        "tags": ["production", "email-assistant", "v1.0"],
        "metadata": {
            "user_id": "user_123",
            "session_id": "session_456",
            "environment": "production"
        }
    }
)
```

`tracing_context` 也接受标签和元数据，以便进行细粒度控制：

```python
with ls.tracing_context(
    project_name="email-agent-test",
    enabled=True,
    tags=["production", "email-assistant", "v1.0"],
    metadata={"user_id": "user_123", "session_id": "session_456", "environment": "production"}):
    response = agent.invoke(
        {"messages": [{"role": "user", "content": "Send a welcome email"}]}
    )
```

这些自定义元数据和标签将附加到 LangSmith 中的追踪上。

> 提示：要了解如何使用追踪来调试、评估和监控你的代理，请参阅 [LangSmith 文档](/langsmith/observability)。

---

# 运行时

## 概述

LangChain 的 [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 在底层运行于 LangGraph 的运行时之上。

LangGraph 暴露了一个 [`Runtime`](https://reference.langchain.com/python/langgraph/runtime/Runtime) 对象，包含以下信息：

1. **Context（上下文）**：一次代理调用所需的静态信息，如用户 ID、数据库连接或其他依赖
2. **Store（存储）**：一个 [BaseStore](https://reference.langchain.com/python/langchain-core/stores/BaseStore) 实例，用于[长期记忆](/oss/python/langchain/long-term-memory)
3. **Stream writer（流写入器）**：用于通过 `"custom"` 流模式流式输出信息的对象
4. **Execution info（执行信息）**：当前执行的标识与重试信息（thread ID、run ID、尝试次数）
5. **Server info（服务器信息）**：在 LangGraph Server 上运行时特有的服务器元数据（assistant ID、graph ID、已认证用户）

> 提示：运行时上下文为你的工具和中间件提供**依赖注入**。你不必硬编码值或使用全局状态，可以在调用代理时注入运行时依赖（如数据库连接、用户 ID 或配置）。这使你的工具更具可测试性、可复用性和灵活性。

你可以在[工具](#inside-tools)和[中间件](#inside-middleware)中访问运行时信息。

## 访问

使用 [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 创建代理时，你可以指定 `context_schema` 来定义代理 [`Runtime`](https://reference.langchain.com/python/langgraph/runtime/Runtime) 中 `context` 的结构。

调用代理时，传入带有本次运行相关配置的 `context` 参数：

```python
from dataclasses import dataclass

from langchain.agents import create_agent

@dataclass
class Context:
    user_name: str

agent = create_agent(
    model="gpt-5-nano",
    tools=[...],
    context_schema=Context
)

agent.invoke(
    {"messages": [{"role": "user", "content": "What's my name?"}]},
    context=Context(user_name="John Smith")
)
```

### 在工具内部

你可以在工具内部访问运行时信息，以：

* 访问上下文
* 读取或写入长期记忆
* 写入[自定义流](/oss/python/langchain/streaming#custom-updates)（例如工具进度/更新）

使用 `ToolRuntime` 参数在工具内访问 [`Runtime`](https://reference.langchain.com/python/langgraph/runtime/Runtime) 对象。

```python
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime

@dataclass
class Context:
    user_id: str

@tool
def fetch_user_email_preferences(runtime: ToolRuntime[Context]) -> str:
    """Fetch the user's email preferences from the store."""
    user_id = runtime.context.user_id

    preferences: str = "The user prefers you to write a brief and polite email."
    if runtime.store:
        if memory := runtime.store.get(("users",), user_id):
            preferences = memory.value["preferences"]

    return preferences
```

### 工具内的执行信息与服务器信息

通过 `runtime.execution_info` 访问执行标识（thread ID、run ID），在 LangGraph Server 上运行时通过 `runtime.server_info` 访问服务器特定元数据（assistant ID、已认证用户）：

```python
from langchain.tools import tool, ToolRuntime

@tool
def context_aware_tool(runtime: ToolRuntime) -> str:
    """A tool that uses execution and server info."""
    # Access thread and run IDs
    info = runtime.execution_info
    print(f"Thread: {info.thread_id}, Run: {info.run_id}")

    # Access server info (only available on LangGraph Server)
    server = runtime.server_info
    if server is not None:
        print(f"Assistant: {server.assistant_id}")
        if server.user is not None:
            print(f"User: {server.user.identity}")

    return "done"
```

当不在 LangGraph Server 上运行时（例如本地开发时），`server_info` 为 `None`。

> 注意：`runtime.execution_info` 和 `runtime.server_info` 需要 `deepagents>=0.5.0`（或 `langgraph>=1.1.5`）。

### 在中间件内部

你可以在中间件中访问运行时信息，以基于用户上下文创建动态提示词、修改消息或控制代理行为。

在[节点式钩子（node-style hooks）](/oss/python/langchain/middleware/custom#node-style-hooks)中使用 `Runtime` 参数访问 [`Runtime`](https://reference.langchain.com/python/langgraph/runtime/Runtime) 对象。对于[包装式钩子（wrap-style hooks）](/oss/python/langchain/middleware/custom#wrap-style-hooks)，`Runtime` 对象可在 [`ModelRequest`](https://reference.langchain.com/python/langchain/agents/middleware/types/ModelRequest) 参数中获取。

```python
from dataclasses import dataclass

from langchain.messages import AnyMessage
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import dynamic_prompt, ModelRequest, before_model, after_model
from langgraph.runtime import Runtime

@dataclass
class Context:
    user_name: str

# Dynamic prompts
@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    user_name = request.runtime.context.user_name
    system_prompt = f"You are a helpful assistant. Address the user as {user_name}."
    return system_prompt

# Before model hook
@before_model
def log_before_model(state: AgentState, runtime: Runtime[Context]) -> dict | None:
    print(f"Processing request for user: {runtime.context.user_name}")
    return None

# After model hook
@after_model
def log_after_model(state: AgentState, runtime: Runtime[Context]) -> dict | None:
    print(f"Completed request for user: {runtime.context.user_name}")
    return None

agent = create_agent(
    model="gpt-5-nano",
    tools=[...],
    middleware=[dynamic_system_prompt, log_before_model, log_after_model],
    context_schema=Context
)

agent.invoke(
    {"messages": [{"role": "user", "content": "What's my name?"}]},
    context=Context(user_name="John Smith")
)
```

### 中间件内的执行信息与服务器信息

中间件钩子也可以访问 `runtime.execution_info` 和 `runtime.server_info`：

```python
from langchain.agents import AgentState
from langchain.agents.middleware import before_model
from langgraph.runtime import Runtime

@before_model
def auth_gate(state: AgentState, runtime: Runtime) -> dict | None:
    """Block unauthenticated users when running on LangGraph Server."""
    server = runtime.server_info
    if server is not None and server.user is None:
        raise ValueError("Authentication required")
    print(f"Thread: {runtime.execution_info.thread_id}")
    return None
```

> 注意：需要 `deepagents>=0.5.0`（或 `langgraph>=1.1.5`）。

---

# 部署

> 使用 LangSmith Cloud 或 JavaScript 框架与托管平台将 LangChain 代理部署到生产环境。

当你准备将 LangChain 代理部署到生产环境时，请选择一种适合你技术栈的托管模式。**[LangSmith Cloud](/langsmith/deploy-to-cloud)** 为有状态、长时间运行的代理提供完全托管的托管基础设施，支持持久化状态和后台执行。

> 提示：除了 Cloud，LangSmith 还提供多种部署选项，包括[混合部署（hybrid）](/langsmith/hybrid)、[独立服务器（standalone servers）](/langsmith/deploy-standalone-server)和[带控制平面的自托管（self-hosted with control plane）](/langsmith/deploy-with-control-plane)。更多信息请参阅 [LangSmith 部署概览](/langsmith/deployment)。

## LangSmith Cloud

本节介绍如何从 GitHub 仓库将代理部署到 LangSmith Cloud。LangSmith 负责处理基础设施、扩展和运维问题。

### 前置条件

开始之前，请确保你已具备以下条件：

* 一个 [GitHub 账号](https://github.com/)
* 一个 [LangSmith 账号](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-deploy)（免费注册）

### 部署你的代理

#### 1. 在 GitHub 上创建仓库

你的应用代码必须位于 GitHub 仓库中才能在 LangSmith 上部署。公有和私有仓库均受支持。对于本快速入门，请先按照[本地服务器设置指南](/oss/python/langchain/studio)确保你的应用与 LangGraph 兼容，然后将代码推送到仓库。

#### 2. 部署到 LangSmith

1. **导航到 LangSmith 部署**：登录 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=snippets-oss-deploy-py)。在左侧边栏中选择 **Deployments**。
2. **创建新部署**：点击 **+ New Deployment** 按钮。将打开一个面板，你可以在其中填写必填字段。
3. **关联仓库**：如果你是首次使用，或要添加之前未连接过的私有仓库，请点击 **Add new account** 按钮并按照说明连接你的 GitHub 账号。
4. **部署仓库**：选择你的应用仓库。点击 **Submit** 进行部署。这可能需要大约 15 分钟才能完成。你可以在 **Deployment details** 视图中查看状态。

#### 3. 在 Studio 中测试你的应用

部署完成后：

1. 选择你刚创建的部署以查看详情。
2. 点击右上角的 **Studio** 按钮。Studio 将打开并显示你的图。

#### 4. 获取部署的 API URL

1. 在 LangGraph 的 **Deployment details** 视图中，点击 **API URL** 将其复制到剪贴板。
2. 点击 `URL` 将其复制到剪贴板。

#### 5. 测试 API

现在你可以测试该 API：

**Python**

1. 安装 LangGraph Python：

```bash
pip install -U langgraph-sdk
```

```bash
uv add langgraph-sdk
```

2. 向代理发送消息：

```python
from langgraph_sdk import get_sync_client # or get_client for async

client = get_sync_client(url="your-deployment-url", api_key="your-langsmith-api-key")

for chunk in client.runs.stream(
    None,    # Threadless run
    "agent", # Name of agent. Defined in langgraph.json.
    input={
        "messages": [{
            "role": "human",
            "content": "What is LangGraph?",
        }],
    },
    stream_mode="updates",
):
    print(f"Receiving new event of type: {chunk.event}...")
    print(chunk.data)
    print("\n\n")
```

**Rest API**

```bash
curl -s --request POST \
    --url <DEPLOYMENT_URL>/runs/stream \
    --header 'Content-Type: application/json' \
    --header "X-Api-Key: <LANGSMITH API KEY> \
    --data "{
        \"assistant_id\": \"agent\", `# Name of agent. Defined in langgraph.json.`
        \"input\": {
            \"messages\": [
                {
                    \"role\": \"human\",
                    \"content\": \"What is LangGraph?\"
                }
            ]
        },
        \"stream_mode\": \"updates\"
    }"
```

> 提示：LangSmith 还提供其他托管选项，包括自托管和混合部署。更多信息请参阅[平台设置概览](/langsmith/platform-setup)。

---

# LangSmith Studio

在本地用 LangChain 构建代理时，可视化代理内部发生的情况、实时交互并即时调试问题会很有帮助。**LangSmith Studio** 是一个免费的可视化界面，用于从本地机器开发和测试你的 LangChain 代理。

Studio 连接到你本地运行的代理，向你展示代理执行的每个步骤：发送给模型的提示词、工具调用及其结果，以及最终输出。你可以在不编写额外代码或不进行部署的情况下测试不同输入、检查中间状态并迭代代理行为。

本页介绍如何将 Studio 与你的本地 LangChain 代理一起设置。

## 前置条件

开始之前，请确保你已具备以下条件：

* **一个 LangSmith 账号**：在 [smith.langchain.com](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=snippets-oss-studio-py) 免费注册或登录。
* **一个 LangSmith API 密钥**：按照[创建 API 密钥](/langsmith/create-account-api-key)指南操作。
* 如果你不想将数据[追踪（trace）](/langsmith/observability-concepts#traces)到 LangSmith，请在应用 `.env` 文件中设置 `LANGSMITH_TRACING=false`。禁用追踪后，不会有任何数据离开你的本地服务器。

## 设置本地 Agent 服务器

### 1. 安装 LangGraph CLI

[LangGraph CLI](/langsmith/cli) 提供了一个本地开发服务器（也称为 [Agent Server](/langsmith/agent-server)），用于将你的代理连接到 Studio。

```bash
# Python >= 3.11 is required.
pip install -U "langgraph-cli[inmem]"
```

```bash
# Python >= 3.11 is required.
uv add "langgraph-cli[inmem]"
```

### 2. 准备你的代理

如果你已经有 LangChain 代理，可以直接使用。本示例使用一个简单的邮件代理：

```python
from langchain.agents import create_agent

def send_email(to: str, subject: str, body: str):
    """Send an email"""
    email = {
        "to": to,
        "subject": subject,
        "body": body
    }
    # ... email sending logic

    return f"Email sent to {to}"

agent = create_agent(
    "gpt-5.5",
    tools=[send_email],
    system_prompt="You are an email assistant. Always use the send_email tool.",
)
```

### 3. 环境变量

Studio 需要一个 LangSmith API 密钥来连接你的本地代理。在项目根目录创建 `.env` 文件，并从 [LangSmith](https://smith.langchain.com/settings) 添加你的 API 密钥。

> 警告：确保 `.env` 文件不要提交到版本控制（如 Git）中。

**.env**
```bash
LANGSMITH_API_KEY=lsv2...
```

### 4. 创建 LangGraph 配置文件

LangGraph CLI 使用配置文件来定位你的代理并管理依赖。在你的应用目录中创建 `langgraph.json` 文件：

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agent.py:agent"
  },
  "env": ".env"
}
```

[`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 函数会自动返回一个编译后的 LangGraph 图，这正是配置文件中 `graphs` 键所期望的内容。

> 信息：关于配置文件中 JSON 对象每个键的详细说明，请参阅 [LangGraph 配置文件参考](/langsmith/cli#configuration-file)。

此时，项目结构将如下所示：

```bash
my-app/
├── src
│   └── agent.py
├── .env
└── langgraph.json
```

### 5. 安装依赖

从根目录安装项目依赖：

```shell
pip install langchain langchain-openai
```

```shell
uv add langchain langchain-openai
```

### 6. 在 Studio 中查看你的代理

启动开发服务器，将你的代理连接到 Studio：

```shell
langgraph dev
```

> 警告：Safari 会阻止 `localhost` 连接到 Studio。要解决此问题，请使用 `--tunnel` 运行上述命令，通过安全隧道访问 Studio。

服务器运行后，你的代理既可以经由 `http://127.0.0.1:2024` 的 API 访问，也可以通过 Studio UI（`https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`）访问：

![Studio UI 中的代理视图](https://mintcdn.com/langchain-5e9cc07a/TCDks4pdsHdxWmuJ/oss/images/studio_create-agent.png?fit=max&auto=format&n=TCDks4pdsHdxWmuJ&q=85&s=ebd259e9fa24af7d011dfcc568f74be2)

Studio 连接到你的本地代理后，你可以快速迭代代理的行为。运行一个测试输入，检查完整的执行追踪，包括提示词、工具参数、返回值以及 token/延迟指标。当出现问题时，Studio 会捕获异常及其周围状态，帮助你理解发生了什么。

开发服务器支持热重载——修改代码中的提示词或工具签名，Studio 会立即反映这些更改。你可以从任何步骤重新运行对话线程来测试更改，无需从头开始。这种工作流既适用于简单的单工具代理，也适用于复杂的多节点图。

关于如何运行 Studio 的更多信息，请参阅 [LangSmith 文档](/langsmith/observability) 中的以下指南：

* [运行应用（Run application）](/langsmith/use-studio#run-application)
* [管理 assistants（Manage assistants）](/langsmith/use-studio#manage-assistants)
* [管理线程（Manage threads）](/langsmith/use-studio#manage-threads)
* [迭代提示词（Iterate on prompts）](/langsmith/observability-studio)
* [调试 LangSmith 追踪（Debug LangSmith traces）](/langsmith/observability-studio#debug-langsmith-traces)
* [向数据集添加节点（Add node to dataset）](/langsmith/observability-studio#add-node-to-dataset)

## 视频指南

视频：[Studio](https://www.youtube.com/embed/Mi1gSlHwZLM?si=zA47TNuTC5aH0ahd)

> 提示：关于已部署代理的更多信息，请参阅[部署](/oss/python/langchain/deploy)。

---

# 代理聊天 UI

[Agent Chat UI](https://github.com/langchain-ai/agent-chat-ui) 是一个 Next.js 应用，提供与任何 LangChain 代理交互的对话界面。它支持实时聊天、工具可视化，以及时间旅行调试和状态分叉等高级功能。Agent Chat UI 可以与使用 [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 创建的代理无缝协作，并且只需极少的设置就能为你的代理提供交互式体验，无论你是在本地运行还是在已部署的环境中（例如 [LangSmith](/langsmith/observability)）运行。

Agent Chat UI 是开源的，可以根据你的应用需求进行定制。

视频：[Agent Chat UI](https://www.youtube.com/embed/lInrwVnZ83o?si=Uw66mPtCERJm0EjU)

> 提示：你可以在 Agent Chat UI 中使用生成式 UI。更多信息请参阅[使用 LangGraph 实现生成式用户界面](/langsmith/generative-ui-react)。

## 快速开始

最快入门方式是使用托管版本：

1. **访问 [Agent Chat UI](https://agentchat.vercel.app)**
2. **连接你的代理**，输入你的部署 URL 或本地服务器地址
3. **开始聊天** —— UI 会自动检测并渲染工具调用和中断（interrupts）

## 本地开发

如需定制或本地开发，你可以在本地运行 Agent Chat UI：

```bash
# Create a new Agent Chat UI project
npx create-agent-chat-app --project-name my-chat-ui
cd my-chat-ui

# Install dependencies and start
pnpm install
pnpm dev
```

```bash
# Clone the repository
git clone https://github.com/langchain-ai/agent-chat-ui.git
cd agent-chat-ui

# Install dependencies and start
pnpm install
pnpm dev
```

## 连接到你的代理

Agent Chat UI 可以连接[本地代理](/oss/python/langchain/studio)和[已部署的代理](/oss/python/langchain/deploy)。

启动 Agent Chat UI 后，你需要配置它来连接你的代理：

1. **Graph ID**：输入你的图名称（可以在 `langgraph.json` 文件的 `graphs` 下找到）
2. **Deployment URL**：你的 Agent 服务器端点（例如本地开发使用 `http://localhost:2024`，或你的已部署代理的 URL）
3. **LangSmith API key（可选）**：添加你的 LangSmith API 密钥（如果使用本地 Agent 服务器则不是必需的）

配置完成后，Agent Chat UI 会自动获取并显示来自你的代理的任何中断线程。

> 提示：Agent Chat UI 开箱即用地支持渲染工具调用和工具结果消息。要自定义显示哪些消息，请参阅[在聊天中隐藏消息（Hiding Messages in the Chat）](https://github.com/langchain-ai/agent-chat-ui?tab=readme-ov-file#hiding-messages-in-the-chat)。

# 组件架构

LangChain 的力量来自其组件如何协同工作以构建复杂的 AI 应用。本页通过图示展示不同组件之间的关系。

## 核心组件生态

下图展示了 LangChain 的主要组件如何连接成完整的 AI 应用：

（图示概述：输入处理（文档加载器 → 文本分割器 → 文档）→ 嵌入与存储（嵌入模型 → 向量 → 向量存储）→ 检索（用户查询 → 查询向量 → 检索器 → 相关上下文）→ 生成（聊天模型 ↔ 工具 → AI 回复）→ 编排（代理 → 模型 / 工具 / 检索器 / 记忆）。）

### 组件如何连接

每一层组件都构建在前一层之上：

1. **输入处理** —— 将原始数据转换为结构化文档
2. **嵌入与存储** —— 将文本转换为可搜索的向量表示
3. **检索** —— 根据用户查询找到相关信息
4. **生成** —— 使用 AI 模型创建回复，可选地使用工具
5. **编排** —— 通过代理和记忆系统协调一切

## 组件类别

LangChain 将组件组织为以下主要类别：

| 类别 | 用途 | 关键组件 | 使用场景 |
| --- | --- | --- | --- |
| **[模型](/oss/python/langchain/models)** | AI 推理与生成 | 聊天模型、LLM、嵌入模型 | 文本生成、推理、语义理解 |
| **[工具](/oss/python/langchain/tools)** | 外部能力 | API、数据库等 | 网页搜索、数据访问、计算 |
| **[代理](/oss/python/langchain/agents)** | 编排与推理 | ReAct 代理、工具调用代理 | 非确定性工作流、决策 |
| **[记忆](/oss/python/langchain/short-term-memory)** | 上下文保留 | 消息历史、自定义状态 | 对话、有状态交互 |
| **[检索器](/oss/python/integrations/retrievers)** | 信息访问 | 向量检索器、网页检索器 | RAG、知识库搜索 |
| **[文档处理](/oss/python/integrations/document_loaders)** | 数据摄取 | 加载器、分割器、转换器 | PDF 处理、网页抓取 |
| **[向量存储](/oss/python/integrations/vectorstores)** | 语义搜索 | Chroma、Pinecone、FAISS | 相似性搜索、嵌入存储 |

## 常见模式

### RAG（检索增强生成）

（图示概述：用户问题 → 检索器 → 相关文档，与用户问题一同输入聊天模型 → 有依据的回答。）

### 带工具的代理

（图示概述：用户请求 → 代理判断是否需要工具：需要则调用工具并将工具结果回传代理；不需要则直接给出最终答案。）

### 多代理系统

（图示概述：复杂任务 → 监督代理 → 分发给多个专家代理 → 汇总结果 → 输出协调一致的回复。）

## 了解更多

* [创建代理](/oss/python/langchain/agents)
* [使用工具](/oss/python/langchain/tools)
* [浏览集成](/oss/python/integrations/providers/overview)

---

# 哲学

> LangChain 存在的意义是成为使用 LLM 构建应用时最易上手的起点，同时保持灵活并可用于生产环境。

LangChain 由几个核心信念驱动：

* 大型语言模型（LLM）是出色而强大的新技术。
* 将 LLM 与外部数据源结合使用时，它们会更加强大。
* LLM 将改变未来应用的面貌。具体来说，未来的应用将越来越趋向于代理化（agentic）。
* 这一转变仍处于非常早期的阶段。
* 虽然构建这些代理化应用的原型很容易，但构建足够可靠、可以投入生产的代理仍然非常困难。

如今开发者可以选择如何构建代理：使用 [LangChain](/oss/python/langchain/overview) 获得最大的灵活性和控制力，或者使用 [Deep Agents](/oss/python/langchain/overview) —— 它提供类似的灵活性和控制力，但内置了有主见的规划、文件系统工具、子代理和上下文管理。两者都构建在 [LangGraph](/oss/python/langgraph/overview) 之上。

对于 LangChain，我们有两个核心重点：

1. **我们希望让开发者能够使用最好的模型进行构建。**
   不同的提供商暴露不同的 API，具有不同的模型参数和不同的消息格式。
   标准化这些模型的输入和输出是核心重点，使开发者可以轻松切换到最新的先进模型，避免被锁定。

2. **我们希望让模型易于用于编排更复杂的流程，与其它数据和计算交互。**
   模型不应只用于*文本生成*——它们还应被用于编排与其它数据交互的更复杂流程。LangChain 使得定义 LLM 可以动态使用的[工具](/oss/python/langchain/tools)变得容易，也帮助解析和访问非结构化数据。

## 历史

鉴于该领域不断变化，LangChain 也一直在演进。以下是 LangChain 多年来如何变化的简要时间线，它伴随着"用 LLM 构建"的含义一同演变：

**2022-10-24（v0.0.1）**

在 ChatGPT 问世前一个月，**LangChain 作为 Python 包发布**。它由两个主要组件构成：

* LLM 抽象
* "链（Chains）"，即针对常见用例预先确定的计算步骤。例如 RAG：先执行检索步骤，再执行生成步骤。

LangChain 这个名字来自 "Language"（如语言模型）和 "Chains"。

**2022-12**

LangChain 中加入了第一批通用代理。

这些通用代理基于 [ReAct 论文](https://arxiv.org/abs/2210.03629)（ReAct 代表 Reasoning and Acting，推理与行动）。它们使用 LLM 生成表示工具调用的 JSON，然后解析该 JSON 以决定调用哪些工具。

**2023-01**

OpenAI 发布了 'Chat Completion' API。

此前，模型接收字符串并返回字符串。在 ChatCompletions API 中，它们演变为接收消息列表并返回一条消息。其它模型提供商纷纷效仿，LangChain 也随之更新以处理消息列表。

**2023-01**

LangChain 发布了 JavaScript 版本。

LLM 和代理将改变应用的构建方式，而 JavaScript 是应用开发者的语言。

**2023-02**

**围绕开源 LangChain 项目成立了 LangChain Inc. 公司**。

主要目标是"让智能代理无处不在"。团队认识到，虽然 LangChain 是关键一环（LangChain 让 LLM 入门变得简单），但还需要其它组件。

**2023-03**

OpenAI 在其 API 中发布了 'function calling'（函数调用）。

这允许 API 显式生成表示工具调用的负载。其它模型提供商纷纷效仿，LangChain 也更新为使用这种方式作为工具调用的首选方法（而不是解析 JSON）。

**2023-06**

**LangChain Inc. 发布了闭源平台 LangSmith**，提供可观测性和评估（evals）。

构建代理的主要问题在于让它们变得可靠，而提供可观测性和评估的 LangSmith 正是为解决这一需求而构建的。LangChain 更新为与 LangSmith 无缝集成。

**2024-01（v0.1.0）**

**LangChain 发布 0.1.0**，这是第一个非 0.0.x 版本。

行业从原型走向生产，因此 LangChain 加强了对稳定性的关注。

**2024-02**

**LangGraph 作为开源库发布**。

最初的 LangChain 有两个重点：LLM 抽象，以及用于快速上手常见应用的高层接口；但它缺少一个允许开发者精确控制代理流程的低层编排层。于是有了 LangGraph。

在构建 LangGraph 时，我们从构建 LangChain 的经验中吸取教训，加入了我们发现在实践中必需的功能：流式输出、持久化执行、短期记忆、人机协同等。

**2024-06**

**LangChain 拥有超过 700 个集成。**

集成从 LangChain 核心包中拆分出来，要么迁移到各自的独立包中（针对核心集成），要么迁移到 `langchain-community`。

**2024-10**

LangGraph 成为构建任何超过单次 LLM 调用的 AI 应用的首选方式。

随着开发者努力提高应用的可靠性，他们需要比高层接口提供的更多的控制力。LangGraph 提供了这种低层灵活性。LangChain 中的大多数链和代理被标记为已弃用，并提供了迁移到 LangGraph 的指南。LangGraph 中仍然保留了一个高层抽象：代理抽象。它构建在低层 LangGraph 之上，并与 LangChain 中的 ReAct 代理具有相同的接口。

**2025-04**

模型 API 变得更加多模态。

模型开始接受文件、图片、视频等。我们相应更新了 `langchain-core` 的消息格式，允许开发者以标准方式指定这些多模态输入。

**2025-10-20（v1.0.0）**

**LangChain 发布 1.0**，包含两个重大变化：

1. 彻底重构 `langchain` 中所有的链和代理。所有链和代理现在都被替换为唯一一个高层抽象：构建在 LangGraph 之上的代理抽象。这原本是 LangGraph 中创建的高层抽象，只是移到了 LangChain。

   对于仍在使用旧版 LangChain 链/代理且不想升级的用户（注意：我们建议你升级），你可以通过安装 `langchain-classic` 包继续使用旧版 LangChain。

2. 标准消息内容格式：模型 API 从返回带有简单内容字符串的消息，演变为返回更复杂的输出类型——推理块、引用、服务端工具调用等。LangChain 演变了自己的消息格式，以跨提供商标准化这些内容。

**2026-03-15（v0.5.3）**

**Deep Agents 作为构建在 LangGraph 之上的开源代理框架发布**。

虽然 LangChain 为自定义代理架构提供了灵活的构建块，但 [Deep Agents](/oss/python/langchain/overview) 为研究和编码等复杂、长时间运行的任务提供了开箱即用的选择。它增加了内置规划工具、带有可插拔后端（内存、磁盘、LangGraph store、沙箱）的虚拟文件系统，以及用于上下文隔离的子代理生成。对于更自主、带预定义工具的代理，请使用 Deep Agents；对于需要完全控制代理架构的场景，请使用 LangChain。

---

# 代理中的上下文工程

## 概述

构建代理（或任何 LLM 应用）的难点在于让它们足够可靠。它们可能对原型有效，但在真实世界的用例中常常失败。

### 代理为什么会失败？

当代理失败时，通常是因为代理内部的 LLM 调用采取了错误的行动/没有按我们的预期行事。LLM 失败的原因有两种：

1. 底层 LLM 的能力不足
2. 没有向 LLM 传递"正确"的上下文

大多数情况下——实际上是第二个原因导致代理不可靠。

**上下文工程**是以正确的格式提供正确的信息和工具，使 LLM 能够完成任务。这是 AI 工程师的头号工作。缺乏"正确"的上下文是构建更可靠代理的头号障碍，而 LangChain 的代理抽象正是为促进上下文工程而独特设计的。

> 提示：刚接触上下文工程？从[概念概述](/oss/python/concepts/context)开始，了解不同类型的上下文以及何时使用它们。

### 代理循环

典型的代理循环由两个主要步骤组成：

1. **模型调用** —— 使用提示词和可用工具调用 LLM，返回响应或执行工具的请求
2. **工具执行** —— 执行 LLM 请求的工具，返回工具结果

（图示：核心代理循环图——模型调用与工具执行交替进行。）

这个循环一直持续，直到 LLM 决定结束。

### 你可以控制什么

要构建可靠的代理，你需要控制代理循环中每一步发生什么，以及步骤之间发生什么。

| 上下文类型 | 你控制什么 | 瞬时或持久 |
| --- | --- | --- |
| **[模型上下文](#模型上下文)** | 进入模型调用的内容（指令、消息历史、工具、响应格式） | 瞬时 |
| **[工具上下文](#工具上下文)** | 工具可以访问和产生的内容（对 state、store、运行时上下文的读写） | 持久 |
| **[生命周期上下文](#生命周期上下文)** | 模型调用与工具调用之间发生的内容（摘要、护栏、日志等） | 持久 |

**瞬时上下文**：LLM 在单次调用中看到的内容。你可以修改消息、工具或提示词，而无需改变 state 中保存的内容。

**持久上下文**：跨轮次保存在 state 中的内容。生命周期钩子和工具写入会永久修改它。

### 数据来源

在整个过程中，你的代理会访问（读取/写入）不同的数据来源：

| 数据来源 | 又称 | 范围 | 示例 |
| --- | --- | --- | --- |
| **运行时上下文** | 静态配置 | 会话作用域 | 用户 ID、API 密钥、数据库连接、权限、环境设置 |
| **State** | 短期记忆 | 会话作用域 | 当前消息、上传的文件、认证状态、工具结果 |
| **Store** | 长期记忆 | 跨会话 | 用户偏好、提取的见解、记忆、历史数据 |

### 工作原理

LangChain [中间件](/oss/python/langchain/middleware) 是让上下文工程对 LangChain 开发者切实可用的底层机制。

中间件允许你挂接到代理生命周期的任何步骤，并且可以：

* 更新上下文
* 跳转到代理生命周期的不同步骤

在本指南中，你会频繁看到中间件 API 作为实现上下文工程目标的手段。

## 模型上下文

控制每次模型调用的输入——指令、可用工具、使用哪个模型、以及输出格式。这些决策直接影响可靠性和成本。

* **系统提示词**（System Prompt）：开发者给 LLM 的基础指令。
* **消息**（Messages）：发送给 LLM 的完整消息列表（对话历史）。
* **工具**（Tools）：代理可以用于采取行动的实用程序。
* **模型**（Model）：实际要调用的模型（包括配置）。
* **响应格式**（Response Format）：模型最终响应的模式规范。

所有这些类型的模型上下文都可以从 **state**（短期记忆）、**store**（长期记忆）或**运行时上下文**（静态配置）中获取。

### 系统提示词

系统提示词设定 LLM 的行为和能力。不同的用户、上下文或对话阶段需要不同的指令。成功的代理会利用记忆、偏好和配置，为当前对话状态提供正确的指令。

**State（状态）**

从 state 中访问消息数量或对话上下文：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest

@dynamic_prompt
def state_aware_prompt(request: ModelRequest) -> str:
    # request.messages is a shortcut for request.state["messages"]
    message_count = len(request.messages)

    base = "You are a helpful assistant."

    if message_count > 10:
        base += "\nThis is a long conversation - be extra concise."

    return base

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[state_aware_prompt]
)
```

**Store（存储）**

从长期记忆中访问用户偏好：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

@dynamic_prompt
def store_aware_prompt(request: ModelRequest) -> str:
    user_id = request.runtime.context.user_id

    # Read from Store: get user preferences
    store = request.runtime.store
    user_prefs = store.get(("preferences",), user_id)

    base = "You are a helpful assistant."

    if user_prefs:
        style = user_prefs.value.get("communication_style", "balanced")
        base += f"\nUser prefers {style} responses."

    return base

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[store_aware_prompt],
    context_schema=Context,
    store=InMemoryStore()
)
```

**运行时上下文（Runtime Context）**

从运行时上下文中访问用户 ID 或配置：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest

@dataclass
class Context:
    user_role: str
    deployment_env: str

@dynamic_prompt
def context_aware_prompt(request: ModelRequest) -> str:
    # Read from Runtime Context: user role and environment
    user_role = request.runtime.context.user_role
    env = request.runtime.context.deployment_env

    base = "You are a helpful assistant."

    if user_role == "admin":
        base += "\nYou have admin access. You can perform all operations."
    elif user_role == "viewer":
        base += "\nYou have read-only access. Guide users to read operations only."

    if env == "production":
        base += "\nBe extra careful with any data modifications."

    return base

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[context_aware_prompt],
    context_schema=Context
)
```

### 消息

消息构成发送给 LLM 的提示词。
管理消息内容至关重要，以确保 LLM 拥有正确响应所需的信息。

**State（状态）**

当与当前查询相关时，从 State 注入已上传文件的上下文：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@wrap_model_call
def inject_file_context(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Inject context about files user has uploaded this session."""
    # Read from State: get uploaded files metadata
    uploaded_files = request.state.get("uploaded_files", [])

    if uploaded_files:
        # Build context about available files
        file_descriptions = []
        for file in uploaded_files:
            file_descriptions.append(
                f"- {file['name']} ({file['type']}): {file['summary']}"
            )

        file_context = f"""Files you have access to in this conversation:
{chr(10).join(file_descriptions)}

Reference these files when answering questions."""

        # Inject file context before recent messages
        messages = [
            *request.messages,
            {"role": "user", "content": file_context},
        ]
        request = request.override(messages=messages)

    return handler(request)

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[inject_file_context]
)
```

**Store（存储）**

从 Store 注入用户的邮件写作风格，以指导草稿撰写：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

@wrap_model_call
def inject_writing_style(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Inject user's email writing style from Store."""
    user_id = request.runtime.context.user_id

    # Read from Store: get user's writing style examples
    store = request.runtime.store
    writing_style = store.get(("writing_style",), user_id)

    if writing_style:
        style = writing_style.value
        # Build style guide from stored examples
        style_context = f"""Your writing style:
- Tone: {style.get('tone', 'professional')}
- Typical greeting: "{style.get('greeting', 'Hi')}"
- Typical sign-off: "{style.get('sign_off', 'Best')}"
- Example email you've written:
{style.get('example_email', '')}"""

        # Append at end - models pay more attention to final messages
        messages = [
            *request.messages,
            {"role": "user", "content": style_context}
        ]
        request = request.override(messages=messages)

    return handler(request)

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[inject_writing_style],
    context_schema=Context,
    store=InMemoryStore()
)
```

**运行时上下文（Runtime Context）**

根据用户的司法管辖区从运行时上下文注入合规规则：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@dataclass
class Context:
    user_jurisdiction: str
    industry: str
    compliance_frameworks: list[str]

@wrap_model_call
def inject_compliance_rules(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Inject compliance constraints from Runtime Context."""
    # Read from Runtime Context: get compliance requirements
    jurisdiction = request.runtime.context.user_jurisdiction
    industry = request.runtime.context.industry
    frameworks = request.runtime.context.compliance_frameworks

    # Build compliance constraints
    rules = []
    if "GDPR" in frameworks:
        rules.append("- Must obtain explicit consent before processing personal data")
        rules.append("- Users have right to data deletion")
    if "HIPAA" in frameworks:
        rules.append("- Cannot share patient health information without authorization")
        rules.append("- Must use secure, encrypted communication")
    if industry == "finance":
        rules.append("- Cannot provide financial advice without proper disclaimers")

    if rules:
        compliance_context = f"""Compliance requirements for {jurisdiction}:
{chr(10).join(rules)}"""

        # Append at end - models pay more attention to final messages
        messages = [
            *request.messages,
            {"role": "user", "content": compliance_context}
        ]
        request = request.override(messages=messages)

    return handler(request)

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[inject_compliance_rules],
    context_schema=Context
)
```

> 注意：**瞬时与持久消息更新：**
>
> 上面的示例使用 `wrap_model_call` 进行**瞬时**更新——修改单次调用发送给模型的消息，而不改变 state 中保存的内容。
>
> 对于修改 state 的**持久**更新，你可以：
>
> * 从 `wrap_model_call` 返回带有 [`Command`](https://reference.langchain.com/python/langgraph/types/Command) 的 [`ExtendedModelResponse`](https://reference.langchain.com/python/langchain/agents/middleware/types/ExtendedModelResponse)，以从模型调用层注入 state 更新。
> * 使用生命周期钩子，如 `before_model`、`after_model` 或 `wrap_tool_call`（用于工具返回），来更新对话历史。更多细节参见[中间件文档](/oss/python/langchain/middleware)。
>
> 更多信息参见 [State 更新](/oss/python/langchain/middleware/custom#state-updates)。

### 工具

工具让模型与数据库、API 和外部系统交互。你如何定义和选择工具直接决定模型能否有效完成任务。

#### 定义工具

每个工具都需要清晰的名称、描述、参数名称和参数描述。这些不只是元数据——它们指导模型推理何时以及如何使用工具。

```python
from langchain.tools import tool

@tool(parse_docstring=True)
def search_orders(
    user_id: str,
    status: str,
    limit: int = 10
) -> str:
    """Search for user orders by status.

    Use this when the user asks about order history or wants to check
    order status. Always filter by the provided status.

    Args:
        user_id: Unique identifier for the user
        status: Order status: 'pending', 'shipped', or 'delivered'
        limit: Maximum number of results to return
    """
    # Implementation here
    pass
```

#### 选择工具

并非每个工具都适合每种情况。工具过多可能会压垮模型（使上下文过载）并增加错误；过少则会限制能力。动态工具选择会根据认证状态、用户权限、功能开关或对话阶段来调整可用工具集。

**State（状态）**

只在对话达到某些里程碑后启用高级工具：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@wrap_model_call
def state_based_tools(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Filter tools based on conversation State."""
    # Read from State: check if user has authenticated
    state = request.state
    is_authenticated = state.get("authenticated", False)
    message_count = len(state["messages"])

    # Only enable sensitive tools after authentication
    if not is_authenticated:
        tools = [t for t in request.tools if t.name.startswith("public_")]
        request = request.override(tools=tools)
    elif message_count < 5:
        # Limit tools early in conversation
        tools = [t for t in request.tools if t.name != "advanced_search"]
        request = request.override(tools=tools)

    return handler(request)

agent = create_agent(
    model="gpt-5.5",
    tools=[public_search, private_search, advanced_search],
    middleware=[state_based_tools]
)
```

**Store（存储）**

根据 Store 中的用户偏好或功能开关过滤工具：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

@wrap_model_call
def store_based_tools(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Filter tools based on Store preferences."""
    user_id = request.runtime.context.user_id

    # Read from Store: get user's enabled features
    store = request.runtime.store
    feature_flags = store.get(("features",), user_id)

    if feature_flags:
        enabled_features = feature_flags.value.get("enabled_tools", [])
        # Only include tools that are enabled for this user
        tools = [t for t in request.tools if t.name in enabled_features]
        request = request.override(tools=tools)

    return handler(request)

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, analysis_tool, export_tool],
    middleware=[store_based_tools],
    context_schema=Context,
    store=InMemoryStore()
)
```

**运行时上下文（Runtime Context）**

根据运行时上下文中的用户权限过滤工具：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@dataclass
class Context:
    user_role: str

@wrap_model_call
def context_based_tools(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Filter tools based on Runtime Context permissions."""
    # Read from Runtime Context: get user role
    user_role = request.runtime.context.user_role

    if user_role == "admin":
        # Admins get all tools
        pass
    elif user_role == "editor":
        # Editors can't delete
        tools = [t for t in request.tools if t.name != "delete_data"]
        request = request.override(tools=tools)
    else:
        # Viewers get read-only tools
        tools = [t for t in request.tools if t.name.startswith("read_")]
        request = request.override(tools=tools)

    return handler(request)

agent = create_agent(
    model="gpt-5.5",
    tools=[read_data, write_data, delete_data],
    middleware=[context_based_tools],
    context_schema=Context
)
```

有关过滤预注册工具以及在运行时注册工具（例如来自 MCP 服务器）的更多信息，参见[动态工具](/oss/python/langchain/tools#dynamic-tool-selection)。

### 模型

不同模型有不同的优势、成本和上下文窗口。为手头的任务选择合适的模型，这可能在代理运行过程中发生变化。

**State（状态）**

根据 State 中的对话长度使用不同模型：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.chat_models import init_chat_model
from typing import Callable

# Initialize models once outside the middleware
large_model = init_chat_model("claude-sonnet-4-6")
standard_model = init_chat_model("gpt-5.5")
efficient_model = init_chat_model("gpt-5.4-mini")

@wrap_model_call
def state_based_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Select model based on State conversation length."""
    # request.messages is a shortcut for request.state["messages"]
    message_count = len(request.messages)

    if message_count > 20:
        # Long conversation - use model with larger context window
        model = large_model
    elif message_count > 10:
        # Medium conversation
        model = standard_model
    else:
        # Short conversation - use efficient model
        model = efficient_model

    request = request.override(model=model)

    return handler(request)

agent = create_agent(
    model="gpt-5.4-mini",
    tools=[...],
    middleware=[state_based_model]
)
```

**Store（存储）**

使用 Store 中用户偏好的模型：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.chat_models import init_chat_model
from typing import Callable
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

# Initialize available models once
MODEL_MAP = {
    "gpt-5.5": init_chat_model("gpt-5.5"),
    "gpt-5.4-mini": init_chat_model("gpt-5.4-mini"),
    "claude-sonnet": init_chat_model("claude-sonnet-4-6"),
}

@wrap_model_call
def store_based_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Select model based on Store preferences."""
    user_id = request.runtime.context.user_id

    # Read from Store: get user's preferred model
    store = request.runtime.store
    user_prefs = store.get(("preferences",), user_id)

    if user_prefs:
        preferred_model = user_prefs.value.get("preferred_model")
        if preferred_model and preferred_model in MODEL_MAP:
            request = request.override(model=MODEL_MAP[preferred_model])

    return handler(request)

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[store_based_model],
    context_schema=Context,
    store=InMemoryStore()
)
```

**运行时上下文（Runtime Context）**

根据运行时上下文中的成本限制或环境选择模型：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.chat_models import init_chat_model
from typing import Callable

@dataclass
class Context:
    cost_tier: str
    environment: str

# Initialize models once outside the middleware
premium_model = init_chat_model("claude-sonnet-4-6")
standard_model = init_chat_model("gpt-5.5")
budget_model = init_chat_model("gpt-5.4-mini")

@wrap_model_call
def context_based_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Select model based on Runtime Context."""
    # Read from Runtime Context: cost tier and environment
    cost_tier = request.runtime.context.cost_tier
    environment = request.runtime.context.environment

    if environment == "production" and cost_tier == "premium":
        # Production premium users get best model
        model = premium_model
    elif cost_tier == "budget":
        # Budget tier gets efficient model
        model = budget_model
    else:
        # Standard tier
        model = standard_model

    request = request.override(model=model)

    return handler(request)

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[context_based_model],
    context_schema=Context
)
```

更多示例参见[动态模型](/oss/python/langchain/models#dynamic-model-selection)。

### 响应格式

结构化输出将非结构化文本转换为经过验证的结构化数据。当提取特定字段或为下游系统返回数据时，自由格式文本是不够的。

**工作原理：** 当你提供模式作为响应格式时，模型的最终响应保证符合该模式。代理会持续运行模型/工具调用循环，直到模型完成工具调用，然后最终响应被强制转换为所提供的格式。

#### 定义格式

模式定义指导模型。字段名称、类型和描述精确指定输出应遵循的格式。

```python
from pydantic import BaseModel, Field

class CustomerSupportTicket(BaseModel):
    """Structured ticket information extracted from customer message."""

    category: str = Field(
        description="Issue category: 'billing', 'technical', 'account', or 'product'"
    )
    priority: str = Field(
        description="Urgency level: 'low', 'medium', 'high', or 'critical'"
    )
    summary: str = Field(
        description="One-sentence summary of the customer's issue"
    )
    customer_sentiment: str = Field(
        description="Customer's emotional tone: 'frustrated', 'neutral', or 'satisfied'"
    )
```

#### 选择格式

动态响应格式选择会根据用户偏好、对话阶段或角色调整模式——早期返回简单格式，随着复杂度增加返回详细格式。

**State（状态）**

根据对话状态配置结构化输出：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from pydantic import BaseModel, Field
from typing import Callable

class SimpleResponse(BaseModel):
    """Simple response for early conversation."""
    answer: str = Field(description="A brief answer")

class DetailedResponse(BaseModel):
    """Detailed response for established conversation."""
    answer: str = Field(description="A detailed answer")
    reasoning: str = Field(description="Explanation of reasoning")
    confidence: float = Field(description="Confidence score 0-1")

@wrap_model_call
def state_based_output(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Select output format based on State."""
    # request.messages is a shortcut for request.state["messages"]
    message_count = len(request.messages)

    if message_count < 3:
        # Early conversation - use simple format
        request = request.override(response_format=SimpleResponse)
    else:
        # Established conversation - use detailed format
        request = request.override(response_format=DetailedResponse)

    return handler(request)

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[state_based_output]
)
```

**Store（存储）**

根据 Store 中的用户偏好配置输出格式：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from pydantic import BaseModel, Field
from typing import Callable
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

class VerboseResponse(BaseModel):
    """Verbose response with details."""
    answer: str = Field(description="Detailed answer")
    sources: list[str] = Field(description="Sources used")

class ConciseResponse(BaseModel):
    """Concise response."""
    answer: str = Field(description="Brief answer")

@wrap_model_call
def store_based_output(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Select output format based on Store preferences."""
    user_id = request.runtime.context.user_id

    # Read from Store: get user's preferred response style
    store = request.runtime.store
    user_prefs = store.get(("preferences",), user_id)

    if user_prefs:
        style = user_prefs.value.get("response_style", "concise")
        if style == "verbose":
            request = request.override(response_format=VerboseResponse)
        else:
            request = request.override(response_format=ConciseResponse)

    return handler(request)

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[store_based_output],
    context_schema=Context,
    store=InMemoryStore()
)
```

**运行时上下文（Runtime Context）**

根据用户角色或环境等运行时上下文配置输出格式：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from pydantic import BaseModel, Field
from typing import Callable

@dataclass
class Context:
    user_role: str
    environment: str

class AdminResponse(BaseModel):
    """Response with technical details for admins."""
    answer: str = Field(description="Answer")
    debug_info: dict = Field(description="Debug information")
    system_status: str = Field(description="System status")

class UserResponse(BaseModel):
    """Simple response for regular users."""
    answer: str = Field(description="Answer")

@wrap_model_call
def context_based_output(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Select output format based on Runtime Context."""
    # Read from Runtime Context: user role and environment
    user_role = request.runtime.context.user_role
    environment = request.runtime.context.environment

    if user_role == "admin" and environment == "production":
        # Admins in production get detailed output
        request = request.override(response_format=AdminResponse)
    else:
        # Regular users get simple output
        request = request.override(response_format=UserResponse)

    return handler(request)

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[context_based_output],
    context_schema=Context
)
```

## 工具上下文

工具的特殊之处在于它们既读取又写入上下文。

在最基本的情况下，当工具执行时，它接收 LLM 的请求参数并返回一条工具消息。工具完成工作并产生结果。

工具还可以为模型获取重要信息，使其能够执行并完成任务。

### 读取

大多数真实世界的工具需要的不仅仅是 LLM 的参数。它们需要用于数据库查询的用户 ID、用于外部服务的 API 密钥，或用于决策的当前会话状态。工具从 state、store 和运行时上下文中读取以访问这些信息。

**State（状态）**

从 State 读取以检查当前会话信息：

```python
from langchain.tools import tool, ToolRuntime
from langchain.agents import create_agent

@tool
def check_authentication(
    runtime: ToolRuntime
) -> str:
    """Check if user is authenticated."""
    # Read from State: check current auth status
    current_state = runtime.state
    is_authenticated = current_state.get("authenticated", False)

    if is_authenticated:
        return "User is authenticated"
    else:
        return "User is not authenticated"

agent = create_agent(
    model="gpt-5.5",
    tools=[check_authentication]
)
```

**Store（存储）**

从 Store 读取以访问持久化的用户偏好：

```python
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
from langchain.agents import create_agent
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

@tool
def get_preference(
    preference_key: str,
    runtime: ToolRuntime[Context]
) -> str:
    """Get user preference from Store."""
    user_id = runtime.context.user_id

    # Read from Store: get existing preferences
    store = runtime.store
    existing_prefs = store.get(("preferences",), user_id)

    if existing_prefs:
        value = existing_prefs.value.get(preference_key)
        return f"{preference_key}: {value}" if value else f"No preference set for {preference_key}"
    else:
        return "No preferences found"

agent = create_agent(
    model="gpt-5.5",
    tools=[get_preference],
    context_schema=Context,
    store=InMemoryStore()
)
```

**运行时上下文（Runtime Context）**

从运行时上下文读取 API 密钥和用户 ID 等配置：

```python
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
from langchain.agents import create_agent

@dataclass
class Context:
    user_id: str
    api_key: str
    db_connection: str

@tool
def fetch_user_data(
    query: str,
    runtime: ToolRuntime[Context]
) -> str:
    """Fetch data using Runtime Context configuration."""
    # Read from Runtime Context: get API key and DB connection
    user_id = runtime.context.user_id
    api_key = runtime.context.api_key
    db_connection = runtime.context.db_connection

    # Use configuration to fetch data
    results = perform_database_query(db_connection, query, api_key)

    return f"Found {len(results)} results for user {user_id}"

agent = create_agent(
    model="gpt-5.5",
    tools=[fetch_user_data],
    context_schema=Context
)

# Invoke with runtime context
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Get my data"}]},
    context=Context(
        user_id="user_123",
        api_key="sk-...",
        db_connection="postgresql://..."
    )
)
```

### 写入

工具结果可以用来帮助代理完成给定的任务。工具既可以向模型直接返回结果，也可以更新代理的记忆，使重要的上下文可用于未来的步骤。

**State（状态）**

使用 Command 写入 State 以跟踪会话特定信息：

```python
from langchain.tools import tool, ToolRuntime
from langchain.agents import create_agent
from langgraph.types import Command

@tool
def authenticate_user(
    password: str,
    runtime: ToolRuntime
) -> Command:
    """Authenticate user and update State."""
    # Perform authentication (simplified)
    if password == "correct":
        # Write to State: mark as authenticated using Command
        return Command(
            update={"authenticated": True},
        )
    else:
        return Command(update={"authenticated": False})

agent = create_agent(
    model="gpt-5.5",
    tools=[authenticate_user]
)
```

**Store（存储）**

写入 Store 以跨会话持久化数据：

```python
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
from langchain.agents import create_agent
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

@tool
def save_preference(
    preference_key: str,
    preference_value: str,
    runtime: ToolRuntime[Context]
) -> str:
    """Save user preference to Store."""
    user_id = runtime.context.user_id

    # Read existing preferences
    store = runtime.store
    existing_prefs = store.get(("preferences",), user_id)

    # Merge with new preference
    prefs = existing_prefs.value if existing_prefs else {}
    prefs[preference_key] = preference_value

    # Write to Store: save updated preferences
    store.put(("preferences",), user_id, prefs)

    return f"Saved preference: {preference_key} = {preference_value}"

agent = create_agent(
    model="gpt-5.5",
    tools=[save_preference],
    context_schema=Context,
    store=InMemoryStore()
)
```

关于在工具中访问 state、store 和运行时上下文的完整示例，参见[工具](/oss/python/langchain/tools)。

## 生命周期上下文

控制核心代理步骤**之间**发生的事情——拦截数据流以实现摘要、护栏和日志等横切关注点。

正如你在[模型上下文](#模型上下文)和[工具上下文](#工具上下文)中所见，[中间件](/oss/python/langchain/middleware) 是让上下文工程切实可行的机制。中间件允许你挂接到代理生命周期的任何步骤，并且可以：

1. **更新上下文** —— 修改 state 和 store 以持久化更改、更新对话历史或保存见解
2. **在生命周期中跳转** —— 根据上下文移动到代理循环中的不同步骤（例如，满足条件时跳过工具执行，用修改后的上下文重复模型调用）

（图示：中间件钩子挂在代理循环的各步骤之间。）

### 示例：摘要

最常见的生命周期模式之一是在对话历史过长时自动精简。与[模型上下文](#消息)中展示的瞬时消息裁剪不同，摘要是对 state 的**持久更新**——永久地用摘要替换旧消息，该摘要会保存到所有未来的轮次中。

LangChain 为此提供内置中间件：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger={"tokens": 4000},
            keep=("messages", 20),
        ),
    ],
)
```

当对话超过 token 限制时，`SummarizationMiddleware` 会自动：

1. 使用单独的 LLM 调用总结旧消息
2. 用 State 中的摘要消息替换它们（永久地）
3. 保留最近的消息以维持上下文

精简后的对话历史会永久更新——未来的轮次将看到摘要而不是原始消息。

> 注意：有关内置中间件的完整列表、可用钩子以及如何创建自定义中间件，参见[中间件文档](/oss/python/langchain/middleware)。

## 最佳实践

1. **从简单开始** —— 从静态提示词和工具开始，仅在需要时添加动态性
2. **增量测试** —— 一次只添加一个上下文工程功能
3. **监控性能** —— 跟踪模型调用、token 使用和延迟
4. **使用内置中间件** —— 利用 [`SummarizationMiddleware`](/oss/python/langchain/middleware#summarization)、[`LLMToolSelectorMiddleware`](/oss/python/langchain/middleware#llm-tool-selector) 等
5. **记录你的上下文策略** —— 明确传递了什么上下文以及为什么
6. **理解瞬时与持久的区别**：模型上下文的更改是瞬时的（每次调用），而生命周期上下文的更改会持久化到 state

## 相关资源

* [上下文概念概述](/oss/python/concepts/context) —— 理解上下文类型以及何时使用它们
* [中间件](/oss/python/langchain/middleware) —— 完整的中间件指南
* [工具](/oss/python/langchain/tools) —— 工具创建与上下文访问
* [记忆](/oss/python/concepts/memory) —— 短期记忆与长期记忆模式
* [代理](/oss/python/langchain/agents) —— 核心代理概念

# 快速开始

> 几分钟内构建你的第一个代理

本快速入门教程将向你展示如何在几分钟内创建一个功能完备的 AI 代理。

> 提示：**正在使用 AI 编程助手？**
>
> * 安装 [LangChain Docs MCP server](/use-these-docs)，让你的代理能够访问最新的 LangChain 文档和示例。
> * 安装 [LangChain Skills](https://github.com/langchain-ai/langchain-skills)，以提高你的代理在 LangChain 生态任务上的表现。

## 安装依赖

安装以下软件包以跟随本教程：

**uv**
```bash
uv init
uv add langchain
uv sync
```

**pip**
```bash
pip install -U langchain
```

**venv**
```bash
python3 -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -U langchain
```

## 设置 API 密钥

从[任何受支持的模型提供商](/oss/python/integrations/providers/overview)获取 API 密钥（例如 Google Gemini 或 OpenAI）。

设置 API 密钥，例如：

**OpenAI**
```bash
export OPENAI_API_KEY="your-api-key"
```

**Google Gemini**
```bash
export GOOGLE_API_KEY="your-api-key"
```

**Claude (Anthropic)**
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

**OpenRouter**
```bash
export OPENROUTER_API_KEY="your-api-key"
```

**Fireworks**
```bash
export FIREWORKS_API_KEY="your-api-key"
```

**Baseten**
```bash
export BASETEN_API_KEY="your-api-key"
```

**Ollama**
```bash
# Local: Ollama must be running (https://ollama.com)
# Cloud: Set your Ollama API key for hosted inference
export OLLAMA_API_KEY="your-api-key"
```

**Azure**
```bash
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT_NAME="your-deployment"
```

**AWS Bedrock**
```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-east-1"
```

**HuggingFace**
```bash
export HUGGINGFACEHUB_API_TOKEN="hf_..."
```

其他：查看受支持的[聊天模型集成](/oss/python/integrations/chat)的完整列表。

> 提示：**使用 LangSmith Gateway**
>
> [LangSmith Gateway](/langsmith/llm-gateway) 通过 LangSmith 路由大多数主流提供商。你可以[自带提供商密钥](/langsmith/llm-gateway-quickstart#2-make-a-call)，或使用 [Gateway Credits](/langsmith/llm-gateway-credits) 在无需提供商密钥的情况下访问模型。

## 构建一个基础代理

首先创建一个能够回答问题并调用工具的简单代理。此示例中的代理使用所选语言模型、一个基本的天气函数作为工具，以及一个简单的提示词来指导其行为：

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。Azure、AWS Bedrock 与 HuggingFace 的代码略有不同，单独保留。）

**Google Gemini**
```python
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="google_genai:gemini-2.5-flash-lite",
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]}
)
print(result["messages"][-1].content_blocks)
```

**Azure**
```python
import os
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

model = init_chat_model(
    "azure_openai:gpt-5.5",
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
)
agent = create_agent(
    model=model,
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]}
)
print(result["messages"][-1].content_blocks)
```

**AWS Bedrock**
```python
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="bedrock_converse:us.anthropic.claude-sonnet-4-6",
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]}
)
print(result["messages"][-1].content_blocks)
```

**HuggingFace**
```python
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="huggingface:microsoft/Phi-3-mini-4k-instruct",
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]}
)
print(result["messages"][-1].content_blocks)
```

当你运行代码并提示代理告诉你旧金山的天气时，代理会使用该输入及其可用的上下文。代理理解你是在询问旧金山市的天气，因此会以提供的城市名称调用天气工具。

> 提示：你可以通过更改模型名称并设置相应的 API 密钥来使用[任何受支持的模型](/oss/python/integrations/providers/overview)。使用 [LangSmith](https://smith.langchain.com) 追踪代理内部发生的情况。按照[追踪快速入门](/langsmith/trace-with-langchain)进行设置。
>
> 我们还建议你设置 [LangSmith Engine](/langsmith/engine)，它会监控你的追踪、检测问题并提出修复建议。

## 构建一个真实世界的代理

在下面的示例中，你将构建一个能够回答有关文本文件问题的研究代理。在此过程中，你将探索以下概念：

1. **详细的系统提示词**，以获得更好的代理行为
2. **创建工具**，与外部数据集成
3. **模型配置**，以获得一致的响应
4. **对话记忆**，用于类似聊天的交互
5. **Deep Agents**，获得内置功能
6. **测试**你的代理

### 步骤 1：定义系统提示词

系统提示词定义你的代理的角色和行为。保持具体且可操作：

```python
SYSTEM_PROMPT = """You are a literary data assistant.

## Capabilities

- `fetch_text_from_url`: loads document text from a URL into the conversation.
Do not guess line counts or positions—ground them in tool results from the saved file."""
```

### 步骤 2：创建工具

[工具](/oss/python/langchain/tools)允许模型通过调用你定义的函数与外部系统交互。工具可以依赖[运行时上下文](/oss/python/langchain/runtime)，也可以与[代理记忆](/oss/python/langchain/short-term-memory)交互。

本示例使用一个工具从给定的 URL 加载文档：

```python
import urllib.error
import urllib.request

from langchain.tools import tool

@tool
def fetch_text_from_url(url: str) -> str:
    """Fetch the document from a URL.
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; quickstart-research/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
    except urllib.error.URLError as e:
        return f"Fetch failed: {e}"
    text = raw.decode("utf-8", errors="replace")
    return text
```

> 提示：工具应有良好的文档说明：它们的名称、描述和参数名称会成为模型提示词的一部分。LangChain 的 [`@tool` 装饰器](https://reference.langchain.com/python/langchain-core/tools/convert/tool)会添加元数据，并通过 `ToolRuntime` 参数实现运行时注入。在[工具指南](/oss/python/langchain/tools)中了解更多。

### 步骤 3：配置你的模型

根据你的用例，为你的[语言模型](/oss/python/langchain/models)设置正确的参数。例如：

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。Azure、AWS Bedrock 与 HuggingFace 的代码略有不同，单独保留。）

**Google Gemini**
```python
from langchain.chat_models import init_chat_model

model = init_chat_model(
    "gemini-3.1-pro-preview",
    model_provider="google-genai",
    temperature=0.5,
    timeout=600,
    max_tokens=25000,
    streaming=True,
)
```

**Azure**
```python
import os
from langchain.chat_models import init_chat_model

model = init_chat_model(
    "azure_openai:gpt-5.5",
    temperature=0.5,
    timeout=300,
    max_tokens=25000,
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
)
```

**AWS Bedrock**
```python
from langchain.chat_models import init_chat_model

model = init_chat_model(
    "us.anthropic.claude-sonnet-4-6",
    model_provider="bedrock_converse",
    temperature=0.5,
    timeout=300,
    max_tokens=25000,
)
```

**HuggingFace**
```python
from langchain.chat_models import init_chat_model

model = init_chat_model(
    "microsoft/Phi-3-mini-4k-instruct",
    model_provider="huggingface",
    temperature=0.5,
    timeout=300,
    max_tokens=25000,
)
```

根据所选模型和提供商的不同，初始化参数可能会有所差异；详情请参阅它们的参考页面。

### 步骤 4：添加记忆

为你的代理添加[记忆](/oss/python/langchain/short-term-memory)，以在交互之间保持状态。这允许代理记住之前的对话和上下文。

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
```

> 信息：在生产环境中，请使用持久化的检查点保存器，将消息历史保存到数据库中。有关更多详情，请参阅[添加和管理记忆](/oss/python/langgraph/add-memory#manage-short-term-memory)。

### 步骤 5：创建并运行代理

现在，将你的代理与所有组件组装起来并运行它。

创建代理有两种不同的框架：LangChain agents 和 deep agents。LangChain agents 和 deep agents 都能让你对工具、记忆等拥有细粒度的控制。两者之间的主要区别在于，deep agents 内置了一系列常用的实用功能，例如规划、文件系统工具和子代理。

当你希望以最少的设置获得最大的能力时，请使用 deep agents；当你需要细粒度控制时，请选择 LangChain agents。

要在本步骤中比较两者，请安装 `deepagents` 包：

**uv**
```bash
uv add deepagents
```

**pip**
```bash
pip install -U deepagents
```

> 警告：由于代码会使用《了不起的盖茨比》（The Great Gatsby）的全文调用模型，因此会消耗大量的 token。
>
> 你可以在下一步查看示例输出。

让我们两种都试一下：

```python
from langchain.agents import create_agent
from deepagents import create_deep_agent

agent = create_agent(
    model=model,
    tools=[fetch_text_from_url],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)

deep_agent = create_deep_agent(
    model=model,
    tools=[fetch_text_from_url],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)

content = f"""Project Gutenberg hosts a full plain-text copy of F. Scott Fitzgerald's The Great Gatsby.
URL: https://www.gutenberg.org/files/64317/64317-0.txt

Answer as much as you can:

1) How many lines in the complete Gutenberg file contain the substring `Gatsby` (count lines, not occurrences within a line, each line ends with a line break).
2) The 1-based line number of the first line in the file that contains `Daisy`.
3) A two-sentence neutral synopsis.

Do your best on (1) and (2). If at any point you realize you cannot **verify** an exact answer with
your available tools and reasoning, do not fabricate numbers: use `null` for that field and spell out
the limitation in `how_you_computed_counts`. If you encounter any errors please report what the error was and what the error message was."""

agent_result = agent.invoke(
    {"messages": [{"role": "user", "content": content}]},
    config={"configurable": {"thread_id": "great-gatsby-lc"}},
)
deep_agent_result = deep_agent.invoke(
    {"messages": [{"role": "user", "content": content}]},
    config={"configurable": {"thread_id": "great-gatsby-da"}},
)
print(agent_result["messages"][-1].content_blocks)
print("\n")
print(deep_agent_result["messages"][-1].content_blocks)
```

#### 完整示例代码

```python
import urllib.error
import urllib.request

from langchain.agents import create_agent
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

SYSTEM_PROMPT = """You are a literary data assistant.

## Capabilities

- `fetch_text_from_url`: loads document text from a URL into the conversation.
Do not guess line counts or positions—ground them in tool results from the saved file."""

@tool
def fetch_text_from_url(url: str) -> str:
    """Fetch the document from a URL.
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; quickstart-research/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
    except urllib.error.URLError as e:
        return f"Fetch failed: {e}"
    text = raw.decode("utf-8", errors="replace")
    return text

model = init_chat_model(
    "gemini-3.1-pro-preview",
    model_provider="google-genai",
    temperature=0.5,
    timeout=600,
    max_tokens=25000,
    streaming=True,
)

checkpointer = InMemorySaver()

agent = create_agent(
    model=model,
    tools=[fetch_text_from_url],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)

deep_agent = create_deep_agent(
    model=model,
    tools=[fetch_text_from_url],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)

content = f"""Project Gutenberg hosts a full plain-text copy of F. Scott Fitzgerald's The Great Gatsby.
URL: https://www.gutenberg.org/files/64317/64317-0.txt

Answer as much as you can:

1) How many lines in the complete Gutenberg file contain the substring `Gatsby` (count lines, not occurrences within a line, each line ends with a line break).
2) The 1-based line number of the first line in the file that contains `Daisy`.
3) A two-sentence neutral synopsis.

Do your best on (1) and (2). If at any point you realize you cannot **verify** an exact answer with
your available tools and reasoning, do not fabricate numbers: use `null` for that field and spell out
the limitation in `how_you_computed_counts`. If you encounter any errors please report what the error was and what the error message was."""

agent_result = agent.invoke(
    {"messages": [{"role": "user", "content": content}]},
    config={"configurable": {"thread_id": "great-gatsby-lc"}},
)
deep_agent_result = deep_agent.invoke(
    {"messages": [{"role": "user", "content": content}]},
    config={"configurable": {"thread_id": "great-gatsby-da"}},
)
print(agent_result["messages"][-1].content_blocks)
print("\n")
print(deep_agent_result["messages"][-1].content_blocks)
```

### 步骤 6：查看结果

结果将根据模型和执行情况的不同而有所差异。

**LangChain agents 的结果：**

```txt
**1) Number of lines containing `Gatsby`:** `null`

**2) First line containing `Daisy`:** `null`

**3) Synopsis:**
The Great Gatsby follows the mysterious millionaire Jay Gatsby and his obsession with reuniting with his former lover, Daisy Buchanan, as narrated by his neighbor Nick Carraway. Set against the backdrop of the Roaring Twenties on Long Island, the novel explores themes of wealth, class, and the elusive nature of the American Dream.

**how_you_computed_counts:**
I successfully fetched the full text of the eBook using the `fetch_text_from_url` tool. However, because I do not have access to a code execution environment (like Python) or text-processing tools (like `grep`), I cannot deterministically split the text by line breaks, iterate through the thousands of lines, and verify the exact line numbers or match counts. LLMs cannot reliably perform exact line-counting or indexing over massive texts within their context window without external computational tools. As instructed, rather than fabricating or guessing a number, I have output `null` for the exact counts and positions.
```

**Deep agents 的结果：**

```txt
Based on the text fetched directly from the Gutenberg URL and analyzed using filesystem search tools, here are the answers to your questions:

**1) Lines containing the substring `Gatsby`**
**258** lines contain the exact substring `Gatsby`.

**2) First line containing `Daisy`**
Line **181** is the first line in the file that contains the exact substring `Daisy`.
*(For context, the line reads: "Buchanans. Daisy was my second cousin once removed, and I'd known Tom")*

**3) Two-sentence neutral synopsis**
*The Great Gatsby* follows the mysterious millionaire Jay Gatsby and his obsessive pursuit to reunite with his former lover, Daisy Buchanan, in 1920s Long Island. The story is narrated by Nick Carraway, who observes the tragic consequences of Gatsby's relentless ambition and the shallow materialism of the era's wealthy elite.

***

**How counts were computed:**
When fetching the document from the URL, the file was too large for the standard output and was automatically saved to the local filesystem by the system (`/large_tool_results/x246ax2x`). I then used the `grep` tool to search the saved file for the exact literal substrings `Gatsby` and `Daisy`. The `grep` tool returned every matching line along with its 1-based line number. I manually counted the exact number of lines returned for `Gatsby` (which totaled 258) and identified the first line number returned for `Daisy` (which was 181). I also verified there were no uppercase variations (`GATSBY` or `DAISY`) that would have been missed. No errors were encountered during this process.
```

如果你查看两个选项卡的输出，会注意到 LangChain agent 提供了答案，但那些只是估计值。该代理缺乏回答此问题所需的工具。你还可能会遇到提示词过长的错误。

另一方面，deep agent 可以：

1. 使用内置的 [`write_todos`](/oss/python/deepagents/harness#task-planning) 工具**规划其方法**，将研究任务分解为多个步骤。
2. 通过调用 `fetch_text_from_url` 工具**加载文件**以收集信息。
3. 通过使用文件系统工具（[`grep`](/oss/python/deepagents/harness#virtual-filesystem-access) 和 [`read_file`](/oss/python/deepagents/harness#virtual-filesystem-access)）**管理上下文**。
4. 根据需要**生成子代理**，将复杂的子任务委托给专门的子代理。

对于 LangChain agents，你必须实现更多功能才能获得类似的服务水平，并可以在过程中根据需要自定义它们。

## 追踪代理调用

你用 LangChain 构建的大多数有趣应用都会对 LLM 进行多次调用。随着这些应用变得越来越复杂，能够检查代理内部到底发生了什么就变得很重要。最好的方法是使用 [LangSmith](https://smith.langchain.com)。

注册一个 [LangSmith](https://smith.langchain.com) 帐户，并设置以下内容以开始记录追踪：

```shell
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="..."
```

设置完成后，再次运行你的脚本，然后在 [LangSmith](https://smith.langchain.com) 上检查代理调用期间发生的情况。

> 提示：要了解有关使用 LangSmith 追踪代理的更多信息，请参阅 [LangSmith 文档](/langsmith/trace-with-langchain)。
>
> 我们还建议你设置 [LangSmith Engine](/langsmith/engine)，它会监控你的追踪、检测问题并提出修复建议。

## 后续步骤

你现在拥有的代理可以：

* **理解上下文**并记住对话
* **智能地使用工具**
* **以一致的格式提供结构化响应**
* **通过上下文处理特定于用户的信息**
* **在交互之间维护对话状态**
* **规划、研究和综合**（仅限 deep agents）

接下来可以继续：

* **LangChain agents**：[添加和管理记忆](/oss/python/langgraph/add-memory#manage-short-term-memory)、[部署到生产环境](/oss/python/langgraph/deploy)
* **Deep Agents**：[自定义选项](/oss/python/deepagents/customization)、[持久化记忆](/oss/python/deepagents/memory)、[部署到生产环境](/oss/python/langgraph/deploy)

# 构建语义搜索引擎

> 信息：获取完整的文档索引：https://docs.langchain.com/llms.txt
> 在深入探索之前，可先使用该文件发现所有可用页面。

## 概述

使用 LangChain 的[嵌入模型](/oss/python/integrations/embeddings)和[向量存储](/oss/python/integrations/vectorstores)在 PDF 之上构建语义搜索引擎。用它检索与查询相似的文本片段，然后将检索器接入[检索增强生成（RAG）](/oss/python/deepagents/retrieval)或其他 LLM 工作流。

本教程涵盖：

1. 从 PDF 创建 `Document` 对象。
2. 生成嵌入向量。
3. 加载并拆分 PDF。
4. 将分块索引到向量存储中，并按相似度查询。
5. 将存储包装为检索器。

本指南还包含一个基于该搜索引擎的极简 RAG 实现。

### 概念

本教程专注于文本检索，涵盖以下概念：

* [`Document`](https://reference.langchain.com/python/langchain-core/documents/base/Document)
* [文本拆分器](/oss/python/integrations/splitters)
* [嵌入模型](/oss/python/integrations/embeddings)
* [向量存储](/oss/python/integrations/vectorstores)与[检索器](/oss/python/integrations/retrievers)

## 准备工作

### 安装依赖

本教程使用 `pypdf` 包读取 PDF：

**pip**

```bash
pip install pypdf
```

**conda**

```bash
conda install pypdf -c conda-forge
```

**uv**

```bash
uv add pypdf
```

更多细节参见[安装指南](/oss/python/langchain/install)。

### 配置 LangSmith

你使用 LangChain 构建的许多应用都会包含多个步骤、多次调用 LLM。随着这些应用越来越复杂，能够检查链或代理内部到底发生了什么变得至关重要。做到这一点的最佳方式是使用 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-knowledge-base)。

在上面链接注册之后，请务必设置环境变量以开始记录 trace：

```shell
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="..."
```

在 notebook 中，可以这样设置：

```python
import getpass
import os

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = getpass.getpass()
```

## 创建文档

LangChain 为文本单元及其关联元数据实现了 [`Document`](https://reference.langchain.com/python/langchain-core/documents/base/Document) 抽象。它有三个属性：

* `page_content`：表示内容的字符串。
* `metadata`：包含任意元数据的字典。
* `id`：（可选）文档的字符串标识符。

`metadata` 可以记录文档的来源、它与其他文档的关系以及其他信息。单个 [`Document`](https://reference.langchain.com/python/langchain-core/documents/base/Document) 通常表示更大文档的一个分块。

以下代码创建示例文档：

```python
from langchain_core.documents import Document

documents = [
    Document(
        page_content="Dogs are great companions, known for their loyalty and friendliness.",
        metadata={"source": "mammal-pets-doc"},
    ),
    Document(
        page_content="Cats are independent pets that often enjoy their own space.",
        metadata={"source": "mammal-pets-doc"},
    ),
]
```

## 生成嵌入向量

向量搜索存储与文本关联的数值向量。将查询嵌入为同维度的向量，然后使用相似度度量（如余弦相似度）查找相关文本。

LangChain 支持[许多提供商](/oss/python/integrations/embeddings/)的嵌入模型。选择一个模型来指定文本应如何转换为数值向量：

**OpenAI**

```shell
pip install -U "langchain-openai"
```

```python
import getpass
import os

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")

from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
```

**Azure**

```shell
pip install -U "langchain-openai"
```

```python
import getpass
import os

if not os.environ.get("AZURE_OPENAI_API_KEY"):
    os.environ["AZURE_OPENAI_API_KEY"] = getpass.getpass("Enter API key for Azure: ")

from langchain_openai import AzureOpenAIEmbeddings

embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
)
```

**Google Gemini**

```shell
pip install -qU langchain-google-genai
```

```python
import getpass
import os

if not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter API key for Google Gemini: ")

from langchain_google_genai import GoogleGenerativeAIEmbeddings

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
```

**Google Vertex**

```shell
pip install -qU langchain-google-vertexai
```

```python
from langchain_google_vertexai import VertexAIEmbeddings

embeddings = VertexAIEmbeddings(model="text-embedding-005")
```

**AWS**

```shell
pip install -qU langchain-aws
```

```python
from langchain_aws import BedrockEmbeddings

embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0")
```

**HuggingFace**

```shell
pip install -qU langchain-huggingface
```

```python
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2",
    encode_kwargs={"normalize_embeddings": True},
)
```

**Ollama**

```shell
pip install -qU langchain-ollama
```

```python
from langchain_ollama import OllamaEmbeddings

embeddings = OllamaEmbeddings(model="llama3")
```

**Cohere**

```shell
pip install -qU langchain-cohere
```

```python
import getpass
import os

if not os.environ.get("COHERE_API_KEY"):
    os.environ["COHERE_API_KEY"] = getpass.getpass("Enter API key for Cohere: ")

from langchain_cohere import CohereEmbeddings

embeddings = CohereEmbeddings(model="embed-english-v3.0")
```

**MistralAI**

```shell
pip install -qU langchain-mistralai
```

```python
import getpass
import os

if not os.environ.get("MISTRALAI_API_KEY"):
    os.environ["MISTRALAI_API_KEY"] = getpass.getpass("Enter API key for MistralAI: ")

from langchain_mistralai import MistralAIEmbeddings

embeddings = MistralAIEmbeddings(model="mistral-embed")
```

**Nomic**

```shell
pip install -qU langchain-nomic
```

```python
import getpass
import os

if not os.environ.get("NOMIC_API_KEY"):
    os.environ["NOMIC_API_KEY"] = getpass.getpass("Enter API key for Nomic: ")

from langchain_nomic import NomicEmbeddings

embeddings = NomicEmbeddings(model="nomic-embed-text-v1.5")
```

**NVIDIA**

```shell
pip install -qU langchain-nvidia-ai-endpoints
```

```python
import getpass
import os

if not os.environ.get("NVIDIA_API_KEY"):
    os.environ["NVIDIA_API_KEY"] = getpass.getpass("Enter API key for NVIDIA: ")

from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

embeddings = NVIDIAEmbeddings(model="NV-Embed-QA")
```

**Voyage AI**

```shell
pip install -qU langchain-voyageai
```

```python
import getpass
import os

if not os.environ.get("VOYAGE_API_KEY"):
    os.environ["VOYAGE_API_KEY"] = getpass.getpass("Enter API key for Voyage AI: ")

from langchain-voyageai import VoyageAIEmbeddings

embeddings = VoyageAIEmbeddings(model="voyage-3")
```

**IBM watsonx**

```shell
pip install -qU langchain-ibm
```

```python
import getpass
import os

if not os.environ.get("WATSONX_APIKEY"):
    os.environ["WATSONX_APIKEY"] = getpass.getpass("Enter API key for IBM watsonx: ")

from langchain_ibm import WatsonxEmbeddings

embeddings = WatsonxEmbeddings(
    model_id="ibm/slate-125m-english-rtrvr",
    url="https://us-south.ml.cloud.ibm.com",
    project_id="<WATSONX PROJECT_ID>",
)
```

**Fake**

```shell
pip install -qU langchain-core
```

```python
from langchain_core.embeddings import DeterministicFakeEmbedding

embeddings = DeterministicFakeEmbedding(size=4096)
```

**Isaacus**

```shell
pip install -qU langchain-isaacus
```

```python
import getpass
import os

if not os.environ.get("ISAACUS_API_KEY"):
os.environ["ISAACUS_API_KEY"] = getpass.getpass("Enter API key for Isaacus: ")

from langchain_isaacus import IsaacusEmbeddings

embeddings = IsaacusEmbeddings(model="kanon-2-embedder")
```

```python
vector_1 = embeddings.embed_query(documents[0].page_content)
vector_2 = embeddings.embed_query(documents[1].page_content)

assert len(vector_1) == len(vector_2)
print(f"Generated vectors of length {len(vector_1)}\n")
print(vector_1[:10])
```

```text
Generated vectors of length 1536

[-0.008586574345827103, -0.03341241180896759, -0.008936782367527485, -0.0036674530711025, 0.010564599186182022, 0.009598285891115665, -0.028587326407432556, -0.015824200585484505, 0.0030416189692914486, -0.012899317778646946]
```

接下来，将嵌入向量存储在支持高效相似度搜索的向量存储中。

## 选择向量存储

LangChain 的 [`VectorStore`](https://reference.langchain.com/python/langchain-core/vectorstores/base/VectorStore) 对象将文本和 [`Document`](https://reference.langchain.com/python/langchain-core/documents/base/Document) 对象添加到存储中，并使用相似度度量进行查询。它们通常使用将文本转换为数值向量的[嵌入模型](/oss/python/integrations/embeddings)进行初始化。

LangChain 包含与许多向量存储技术的[集成](/oss/python/integrations/vectorstores)。有些是托管服务，需要凭证；有些在独立基础设施（本地或第三方）中运行；另一些则在内存中运行，适合轻量级工作负载。选择一个向量存储：

**内存存储（In-memory）**

```shell
pip install -U "langchain-core"
```

```python
from langchain_core.vectorstores import InMemoryVectorStore

vector_store = InMemoryVectorStore(embeddings)
```

**Amazon OpenSearch**

```shell
pip install -qU  boto3
```

```python
from opensearchpy import RequestsHttpConnection

service = "es"  # must set the service as 'es'
region = "us-east-2"
credentials = boto3.Session(
    aws_access_key_id="xxxxxx", aws_secret_access_key="xxxxx"
).get_credentials()
awsauth = AWS4Auth("xxxxx", "xxxxxx", region, service, session_token=credentials.token)

vector_store = OpenSearchVectorSearch.from_documents(
    docs,
    embeddings,
    opensearch_url="host url",
    http_auth=awsauth,
    timeout=300,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    index_name="test-index",
)
```

**AstraDB**

```shell
pip install -U "langchain-astradb"
```

```python
from langchain_astradb import AstraDBVectorStore

vector_store = AstraDBVectorStore(
    embedding=embeddings,
    api_endpoint=ASTRA_DB_API_ENDPOINT,
    collection_name="astra_vector_langchain",
    token=ASTRA_DB_APPLICATION_TOKEN,
    namespace=ASTRA_DB_NAMESPACE,
)
```

**Chroma**

```shell
pip install -qU langchain-chroma
```

```python
from langchain_chroma import Chroma

vector_store = Chroma(
    collection_name="example_collection",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db",  # Where to save data locally, remove if not necessary
)
```

**Milvus**

```shell
pip install -qU langchain-milvus
```

```python
from langchain_milvus import Milvus

URI = "./milvus_example.db"

vector_store = Milvus(
    embedding_function=embeddings,
    connection_args={"uri": URI},
    index_params={"index_type": "FLAT", "metric_type": "L2"},
)
```

**MongoDB**

```shell
pip install -qU langchain-mongodb
```

```python
from langchain_mongodb import MongoDBAtlasVectorSearch

vector_store = MongoDBAtlasVectorSearch(
    embedding=embeddings,
    collection=MONGODB_COLLECTION,
    index_name=ATLAS_VECTOR_SEARCH_INDEX_NAME,
    relevance_score_fn="cosine",
)
```

**PGVector**

```shell
pip install -qU langchain-postgres
```

```python
from langchain_postgres import PGVector

vector_store = PGVector(
    embeddings=embeddings,
    collection_name="my_docs",
    connection="postgresql+psycopg://...",
)
```

**PGVectorStore**

```shell
pip install -qU langchain-postgres
```

```python
from langchain_postgres import PGEngine, PGVectorStore

pg_engine = PGEngine.from_connection_string(
    url="postgresql+psycopg://..."
)

vector_store = PGVectorStore.create_sync(
    engine=pg_engine,
    table_name='test_table',
    embedding_service=embeddings
)
```

**Pinecone**

```shell
pip install -qU langchain-pinecone
```

```python
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

pc = Pinecone(api_key=...)
index = pc.Index(index_name)

vector_store = PineconeVectorStore(embedding=embeddings, index=index)
```

**Qdrant**

```shell
pip install -qU langchain-qdrant
```

```python
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

client = QdrantClient(":memory:")

vector_size = len(embeddings.embed_query("sample text"))

if not client.collection_exists("test"):
    client.create_collection(
        collection_name="test",
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
    )
vector_store = QdrantVectorStore(
    client=client,
    collection_name="test",
    embedding=embeddings,
)
```

## 加载并拆分 PDF

从 PDF 加载内容，然后在索引之前将其拆分为更小的分块。本示例使用[一份 2023 年 Nike 10-K 年报样本](https://github.com/langchain-ai/langchain/blob/v0.3/docs/docs/example_data/nke-10k-2023.pdf)。

```python
import pypdf
from langchain_core.documents import Document

# Below is a minimal helper for demonstration purposes.
def load_pdf_pages(file_path: str) -> list[Document]:
    reader = pypdf.PdfReader(file_path)
    return [
        Document(
            page_content=page.extract_text() or "",
            metadata={"source": file_path, "page": i},
        )
        for i, page in enumerate(reader.pages)
    ]

file_path = "../example_data/nke-10k-2023.pdf"
docs = load_pdf_pages(file_path)
print(len(docs))
```

```text
107
```

单个页面对于检索来说往往过于粗糙。需要进一步拆分页面，以免相关段落被周围文本稀释。[`RecursiveCharacterTextSplitter`](https://reference.langchain.com/python/langchain-text-splitters/character/RecursiveCharacterTextSplitter) 会递归地在常见分隔符（如换行符）处拆分，直到每个分块达到目标大小。这是通用文本用例的推荐文本拆分器。

设置 `add_start_index=True`，使每个分块保留一个 `start_index` 元数据字段，记录其在原始文档中的字符偏移量。

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, chunk_overlap=200, add_start_index=True
)
all_splits = text_splitter.split_documents(docs)

print(len(all_splits))
```

```text
516
```

## 为文档建立索引

将分块索引到向量存储中：

```python
ids = vector_store.add_documents(documents=all_splits)
```

大多数向量存储集成还支持连接到现有存储（例如通过客户端或索引名称）。详细信息请参阅具体[集成](/oss/python/integrations/vectorstores)的文档。

## 查询向量存储

将文档添加到 [`VectorStore`](https://reference.langchain.com/python/langchain-core/vectorstores/base/VectorStore) 之后，就可以查询它：

* 同步和异步
* 按字符串查询和按向量查询
* 带相似度分数和不带相似度分数
* 按相似度和[最大边际相关性](https://reference.langchain.com/python/langchain-core/vectorstores/base/VectorStore/max_marginal_relevance_search)（在相似度与多样性之间取得平衡）

这些方法通常返回 [`Document`](https://reference.langchain.com/python/langchain-core/documents/base/Document) 对象列表。

### 按字符串搜索

嵌入模型将文本映射为稠密向量，使相似的含义在几何上彼此接近。这意味着你可以通过传入自然语言问题来检索相关段落：

```python
results = vector_store.similarity_search(
    "How many distribution centers does Nike have in the US?"
)

print(results[0])
```

```python
page_content='direct to consumer operations sell products through the following number of retail stores in the United States:
U.S. RETAIL STORES NUMBER
NIKE Brand factory stores 213
NIKE Brand in-line stores (including employee-only stores) 74
Converse stores (including factory stores) 82
TOTAL 369
In the United States, NIKE has eight significant distribution centers. Refer to Item 2. Properties for further information.
2023 FORM 10-K 2' metadata={'page': 4, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 3125}
```

异步查询：

```python
results = await vector_store.asimilarity_search("When was Nike incorporated?")

print(results[0])
```

```python
page_content='Table of Contents
PART I
ITEM 1. BUSINESS
GENERAL
NIKE, Inc. was incorporated in 1967 under the laws of the State of Oregon. As used in this Annual Report on Form 10-K (this "Annual Report"), the terms "we," "us," "our,"
"NIKE" and the "Company" refer to NIKE, Inc. and its predecessors, subsidiaries and affiliates, collectively, unless the context indicates otherwise.
Our principal business activity is the design, development and worldwide marketing and selling of athletic footwear, apparel, equipment, accessories and services. NIKE is
the largest seller of athletic footwear and apparel in the world. We sell our products through NIKE Direct operations, which are comprised of both NIKE-owned retail stores
and sales through our digital platforms (also referred to as "NIKE Brand Digital"), to retail accounts and to a mix of independent distributors, licensees and sales' metadata={'page': 3, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 0}
```

### 返回分数

你可以连同文档一起返回相似度分数。分数的含义因提供商而异。在本例中，分数是一个距离度量，与相似度成反比：

```python
# Note that providers implement different scores; the score here
# is a distance metric that varies inversely with similarity.

results = vector_store.similarity_search_with_score("What was Nike's revenue in 2023?")
doc, score = results[0]
print(f"Score: {score}\n")
print(doc)
```

```python
Score: 0.23699893057346344

page_content='Table of Contents
FISCAL 2023 NIKE BRAND REVENUE HIGHLIGHTS
The following tables present NIKE Brand revenues disaggregated by reportable operating segment, distribution channel and major product line:
FISCAL 2023 COMPARED TO FISCAL 2022
•NIKE, Inc. Revenues were $51.2 billion in fiscal 2023, which increased 10% and 16% compared to fiscal 2022 on a reported and currency-neutral basis, respectively.
The increase was due to higher revenues in North America, Europe, Middle East & Africa ("EMEA"), APLA and Greater China, which contributed approximately 7, 6,
2 and 1 percentage points to NIKE, Inc. Revenues, respectively.
•NIKE Brand revenues, which represented over 90% of NIKE, Inc. Revenues, increased 10% and 16% on a reported and currency-neutral basis, respectively. This
increase was primarily due to higher revenues in Men's, the Jordan Brand, Women's and Kids' which grew 17%, 35%,11% and 10%, respectively, on a wholesale
equivalent basis.' metadata={'page': 35, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 0}
```

### 按向量搜索

自行嵌入查询，然后用得到的向量进行搜索：

```python
embedding = embeddings.embed_query("How were Nike's margins impacted in 2023?")

results = vector_store.similarity_search_by_vector(embedding)
print(results[0])
```

```python
page_content='Table of Contents
GROSS MARGIN
FISCAL 2023 COMPARED TO FISCAL 2022
For fiscal 2023, our consolidated gross profit increased 4% to $22,292 million compared to $21,479 million for fiscal 2022. Gross margin decreased 250 basis points to
43.5% for fiscal 2023 compared to 46.0% for fiscal 2022 due to the following:
*Wholesale equivalent
The decrease in gross margin for fiscal 2023 was primarily due to:
•Higher NIKE Brand product costs, on a wholesale equivalent basis, primarily due to higher input costs and elevated inbound freight and logistics costs as well as
product mix;
•Lower margin in our NIKE Direct business, driven by higher promotional activity to liquidate inventory in the current period compared to lower promotional activity in
the prior period resulting from lower available inventory supply;
•Unfavorable changes in net foreign currency exchange rates, including hedges; and
•Lower off-price margin, on a wholesale equivalent basis.
This was partially offset by:' metadata={'page': 36, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 0}
```

了解更多：

* [API 参考](https://reference.langchain.com/python/langchain-core/vectorstores/base/VectorStore)
* [集成专属文档](/oss/python/integrations/vectorstores)

## 使用检索器

LangChain 的 [`VectorStore`](https://reference.langchain.com/python/langchain-core/vectorstores/base/VectorStore) 对象并不继承自 [`Runnable`](https://reference.langchain.com/python/langchain-core/runnables/base/Runnable)。[检索器](https://reference.langchain.com/python/langchain-core/retrievers/BaseRetriever)是 Runnable，因此支持同步和异步的 `invoke`、`batch` 等标准方法。

你还可以从向量存储构建检索器，检索器也可以包装非向量来源（例如外部 API）。

在本例中，通过包装 `similarity_search` 创建一个简单的检索器，而无需继承 `Retriever`：

```python
from typing import List

from langchain_core.documents import Document
from langchain_core.runnables import chain

@chain
def retriever(query: str) -> List[Document]:
    return vector_store.similarity_search(query, k=1)

retriever.batch(
    [
        "How many distribution centers does Nike have in the US?",
        "When was Nike incorporated?",
    ],
)
```

```text
[[Document(metadata={'page': 4, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 3125}, page_content='direct to consumer operations sell products through the following number of retail stores in the United States:\nU.S. RETAIL STORES NUMBER\nNIKE Brand factory stores 213 \nNIKE Brand in-line stores (including employee-only stores) 74 \nConverse stores (including factory stores) 82 \nTOTAL 369 \nIn the United States, NIKE has eight significant distribution centers. Refer to Item 2. Properties for further information.\n2023 FORM 10-K 2')],
 [Document(metadata={'page': 3, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 0}, page_content='Table of Contents\nPART I\nITEM 1. BUSINESS\nGENERAL\nNIKE, Inc. was incorporated in 1967 under the laws of the State of Oregon. As used in this Annual Report on Form 10-K (this "Annual Report"), the terms "we," "us," "our,"\n"NIKE" and the "Company" refer to NIKE, Inc. and its predecessors, subsidiaries and affiliates, collectively, unless the context indicates otherwise.\nOur principal business activity is the design, development and worldwide marketing and selling of athletic footwear, apparel, equipment, accessories and services. NIKE is\nthe largest seller of athletic footwear and apparel in the world. We sell our products through NIKE Direct operations, which are comprised of both NIKE-owned retail stores\nand sales through our digital platforms (also referred to as "NIKE Brand Digital"), to retail accounts and to a mix of independent distributors, licensees and sales')]]
```

向量存储实现了 `as_retriever` 方法，返回一个 [`VectorStoreRetriever`](https://reference.langchain.com/python/langchain-core/vectorstores/base/VectorStoreRetriever)。这些检索器暴露了 `search_type` 和 `search_kwargs`，用于选择和参数化底层存储方法。用以下方式复现上面的示例：

```python
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 1},
)

retriever.batch(
    [
        "How many distribution centers does Nike have in the US?",
        "When was Nike incorporated?",
    ],
)
```

```text
[[Document(metadata={'page': 4, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 3125}, page_content='direct to consumer operations sell products through the following number of retail stores in the United States:\nU.S. RETAIL STORES NUMBER\nNIKE Brand factory stores 213 \nNIKE Brand in-line stores (including employee-only stores) 74 \nConverse stores (including factory stores) 82 \nTOTAL 369 \nIn the United States, NIKE has eight significant distribution centers. Refer to Item 2. Properties for further information.\n2023 FORM 10-K 2')],
 [Document(metadata={'page': 3, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 0}, page_content='Table of Contents\nPART I\nITEM 1. BUSINESS\nGENERAL\nNIKE, Inc. was incorporated in 1967 under the laws of the State of Oregon. As used in this Annual Report on Form 10-K (this "Annual Report"), the terms "we," "us," "our,"\n"NIKE" and the "Company" refer to NIKE, Inc. and its predecessors, subsidiaries and affiliates, collectively, unless the context indicates otherwise.\nOur principal business activity is the design, development and worldwide marketing and selling of athletic footwear, apparel, equipment, accessories and services. NIKE is\nthe largest seller of athletic footwear and apparel in the world. We sell our products through NIKE Direct operations, which are comprised of both NIKE-owned retail stores\nand sales through our digital platforms (also referred to as "NIKE Brand Digital"), to retail accounts and to a mix of independent distributors, licensees and sales')]]
```

`VectorStoreRetriever` 支持 `"similarity"`（默认）、`"mmr"`（最大边际相关性）和 `"similarity_score_threshold"` 三种搜索类型。使用最后一种选项可按相似度分数过滤文档。

你可以在更复杂的应用中使用检索器，例如[检索增强生成（RAG）](/oss/python/deepagents/retrieval)，它将问题与检索到的上下文组合到提示词中交给 LLM。要了解更多构建此类应用的信息，请查看 [RAG 教程](/oss/python/deepagents/rag)。

## 后续步骤

现在你已经了解了如何在 PDF 文档之上构建语义搜索引擎。

更多信息参见：

* [可用的嵌入模型集成](/oss/python/integrations/embeddings)
* [可用的向量存储集成](/oss/python/integrations/vectorstores)

关于 RAG 的更多内容：

* [检索概述](/oss/python/deepagents/retrieval)
* [使用 Deep Agents 进行 RAG](/oss/python/deepagents/rag)
* [评估 RAG 应用](/langsmith/evaluate-rag-tutorial)

# 构建 SQL 代理

## 概述

在本教程中，你将学习如何使用 LangChain [代理](/oss/python/langchain/agents) 构建一个能够回答 SQL 数据库相关问题的代理。

在高层面上，该代理将：

1. 从数据库中获取可用的表和模式
2. 判断哪些表与问题相关
3. 获取相关表的模式
4. 根据问题以及模式中的信息生成查询
5. 使用 LLM 复查查询中的常见错误
6. 执行查询并返回结果
7. 纠正数据库引擎暴露出的错误，直到查询成功
8. 根据结果组织回答

> 警告：构建 SQL 数据库的问答系统需要执行模型生成的 SQL 查询。这样做存在固有风险。请确保你的数据库连接权限始终尽可能窄地限定在你的代理所需范围内。这可以降低（但无法消除）构建模型驱动系统的风险。

### 概念

以下教程涵盖以下概念：

* [工具](/oss/python/langchain/tools)：用于从 SQL 数据库读取数据
* LangChain [代理](/oss/python/langchain/agents)
* [人机协同](/oss/python/langchain/human-in-the-loop) 流程

## 环境搭建

### 安装依赖

**pip**
```bash
pip install langchain langgraph
```

### 设置 LangSmith

设置 [LangSmith](https://smith.langchain.com?utm_source=docs&utm_medium=cta&utm_campaign=langsmith-signup&utm_content=oss-langchain-sql-agent) 以检视你的链或代理内部发生的情况。然后设置以下环境变量：

```shell
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="..."
```

## 构建你的 SQL 代理

### 选择 LLM

选择一个支持 [工具调用](/oss/python/integrations/providers/overview) 的模型：

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

👉 阅读 [Google GenAI 聊天模型集成文档](/oss/python/integrations/chat/google_generative_ai/)

**pip**
```bash
pip install -U "langchain[google-genai]"
```

**uv**
```bash
uv add "langchain[google-genai]"
```

**init_chat_model**
```python
import os
from langchain.chat_models import init_chat_model

os.environ["GOOGLE_API_KEY"] = "..."

model = init_chat_model("google_genai:gemini-3.6-flash")
```

**Model Class**
```python
import os
from langchain_google_genai import ChatGoogleGenerativeAI

os.environ["GOOGLE_API_KEY"] = "..."

model = ChatGoogleGenerativeAI(model="gemini-3.6-flash")
```

下文示例中展示的输出使用的是 OpenAI。

### 配置数据库

你将为本教程创建一个 [SQLite 数据库](https://www.sqlitetutorial.net/sqlite-sample-database/)。SQLite 是一种轻量级数据库，易于设置和使用。我们将加载 `chinook` 数据库，这是一个代表数字媒体商店的示例数据库。

为方便起见，我们已将数据库（`Chinook.db`）托管在一个公共 GCS 存储桶上。

```python
import pathlib
import requests

url = "https://storage.googleapis.com/benchmarks-artifacts/chinook/Chinook.db"
local_path = pathlib.Path("Chinook.db")

if local_path.exists():
    print(f"{local_path} already exists, skipping download.")
else:
    response = requests.get(url, timeout=60)
    if response.status_code == 200:
        local_path.write_bytes(response.content)
        print(f"File downloaded and saved as {local_path}")
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")
```

我们将使用 Python 内置的 `sqlite3` 模块与数据库交互：

```python
import sqlite3

con = sqlite3.connect("Chinook.db")
cursor = con.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]

print("Dialect: sqlite")
print(f"Available tables: {tables}")

cursor.execute("SELECT * FROM Artist LIMIT 5;")
print(f"Sample output: {cursor.fetchall()}")
con.close()
```

```
Dialect: sqlite
Available tables: ['Album', 'Artist', 'Customer', 'Employee', 'Genre', 'Invoice', 'InvoiceLine', 'MediaType', 'Playlist', 'PlaylistTrack', 'Track']
Sample output: [(1, 'AC/DC'), (2, 'Accept'), (3, 'Aerosmith'), (4, 'Alanis Morissette'), (5, 'Alice In Chains')]
```

### 添加数据库交互工具

> 警告：以下数据库工具仅为演示目的的最小包装器。它们并非为安全环境或生产环境而设计。请使用范围受限的数据库权限，并在执行模型生成的 SQL 之前添加特定于应用的验证。

我们可以使用 `langchain.tools` 中的 `@tool` 装饰器将数据库 [工具](/oss/python/langchain/tools) 实现为薄包装器：

```python
import sqlite3
from langchain.tools import tool

# Below are minimal tools for demonstration purposes.
# They are not intended to be secure or for production use.

@tool
def sql_db_list_tables() -> str:
    """Input is an empty string, output is a comma-separated list of tables in the database."""
    con = sqlite3.connect("Chinook.db")
    try:
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]
        return ", ".join(tables)
    finally:
        con.close()

@tool
def sql_db_schema(table_names: str) -> str:
    """Input to this tool is a comma-separated list of tables, output is the schema and sample rows for those tables.
    Be sure that the tables actually exist by calling sql_db_list_tables first!
    Example Input: table1, table2, table3"""
    con = sqlite3.connect("Chinook.db")
    try:
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        valid_tables = {row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")}
        results = []
        for table in table_names.split(","):
            table = table.strip()
            if table not in valid_tables:
                results.append(f"Error: table_names {{{table!r}}} not found in database")
                continue
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?;", (table,))
            schema_row = cursor.fetchone()
            if schema_row:
                results.append(schema_row[0])
                try:
                    quoted_table = '"' + table.replace('"', '""') + '"'
                    cursor.execute(f"SELECT * FROM {quoted_table} LIMIT 3;")
                    rows = cursor.fetchall()
                    if rows:
                        col_names = [description[0] for description in cursor.description]
                        results.append(
                            f"/*\n3 rows from {table} table:\n"
                            + "\t".join(col_names)
                            + "\n"
                            + "\n".join("\t".join(str(x) for x in row) for row in rows)
                            + "\n*/"
                        )
                except Exception as e:
                    results.append(f"Error fetching sample rows: {e}")
        return "\n\n".join(results)
    finally:
        con.close()

@tool
def sql_db_query(query: str) -> str:
    """Input to this tool is a detailed and correct SQL query, output is a result from the database.
    If the query is not correct, an error message will be returned.
    If an error is returned, rewrite the query, check the query, and try again.
    If you encounter an issue with Unknown column 'xxxx' in 'field list', use sql_db_schema to query the correct table fields."""
    con = sqlite3.connect("Chinook.db")
    try:
        cursor = con.cursor()
        cursor.execute(query)
        res = cursor.fetchall()
        return str(res)
    except Exception as e:
        return f"Error: {e}"
    finally:
        con.close()

@tool
def sql_db_query_checker(query: str) -> str:
    """Use this tool to double check if your query is correct before executing it.
    Always use this tool before executing a query with sql_db_query!"""
    trigger_prompt = """{query}
Double check the sqlite query above for common mistakes, including:
- Using NOT IN with NULL values
- Using UNION when UNION ALL should have been used
- Using BETWEEN for exclusive ranges
- Data type mismatch in predicates
- Properly quoting identifiers
- Using the correct number of arguments for functions
- Casting to the correct data type
- Using the proper columns for joins

If there are any of the above mistakes, rewrite the query. If there are no mistakes, just reproduce the original query.

Output the final SQL query only.

SQL Query: """.format(query=query)

    response = model.invoke(trigger_prompt)
    return response.text.strip()

tools = [sql_db_list_tables, sql_db_schema, sql_db_query, sql_db_query_checker]

# Use a distinct loop variable so it does not shadow the `tool` decorator.
for t in tools:
    print(f"{t.name}: {t.description}\n")
```

```
sql_db_query: Input to this tool is a detailed and correct SQL query, output is a result from the database.
    If the query is not correct, an error message will be returned.
    If an error is returned, rewrite the query, check the query, and try again.
    If you encounter an issue with Unknown column 'xxxx' in 'field list', use sql_db_schema to query the correct table fields.

sql_db_schema: Input to this tool is a comma-separated list of tables, output is the schema and sample rows for those tables.
    Be sure that the tables actually exist by calling sql_db_list_tables first!
    Example Input: table1, table2, table3

sql_db_list_tables: Input is an empty string, output is a comma-separated list of tables in the database.

sql_db_query_checker: Use this tool to double check if your query is correct before executing it.
    Always use this tool before executing a query with sql_db_query!
```

### 创建代理

使用 [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 以最少的代码构建一个 [ReAct 代理](https://arxiv.org/pdf/2210.03629)。代理将解释请求并生成 SQL 命令，由工具执行。如果命令出错，错误消息会返回给模型。模型随后可以检查原始请求和新的错误消息，并生成新命令。这一过程会一直持续，直到 LLM 成功生成命令或达到结束计数。这种向模型提供反馈（本例中为错误消息）的模式非常强大。

使用描述性的系统提示初始化代理，以自定义其行为：

```python
system_prompt = """
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.

You can order the results by a relevant column to return the most interesting
examples in the database. Never query for all the columns from a specific table,
only ask for the relevant columns given the question.

You MUST double check your query before executing it. If you get an error while
executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.

To start you should ALWAYS look at the tables in the database to see what you
can query. Do NOT skip this step.

Then you should query the schema of the most relevant tables.
""".format(
    dialect="sqlite",
    top_k=5,
)
```

现在，使用模型、工具和提示创建代理：

```python
from langchain.agents import create_agent

agent = create_agent(
    model,
    tools,
    system_prompt=system_prompt,
)
```

### 运行代理

在示例查询上运行代理并观察其行为：

```python
question = "Which genre on average has the longest tracks?"

stream = agent.stream_events(
    {"messages": [{"role": "user", "content": question}]},
    version="v3",
)
for kind, item in stream.interleave("messages", "tool_calls"):
    if kind == "messages":
        for token in item.text:
            print(token, end="", flush=True)
    elif kind == "tool_calls":
        print(f"\nTool call: {item.tool_name}({item.input})")
        for delta in item.output_deltas:
            print(delta, end="", flush=True)
        print(f"\nTool result: {item.output}")

final_state = stream.output
```

```
================================ Human Message =================================

Which genre on average has the longest tracks?
================================== Ai Message ==================================
Tool Calls:
  sql_db_list_tables (call_BQsWg8P65apHc8BTJ1NPDvnM)
 Call ID: call_BQsWg8P65apHc8BTJ1NPDvnM
  Args:
================================= Tool Message =================================
Name: sql_db_list_tables

Album, Artist, Customer, Employee, Genre, Invoice, InvoiceLine, MediaType, Playlist, PlaylistTrack, Track
================================== Ai Message ==================================
Tool Calls:
  sql_db_schema (call_i89tjKECFSeERbuACYm4w0cU)
 Call ID: call_i89tjKECFSeERbuACYm4w0cU
  Args:
    table_names: Track, Genre
================================= Tool Message =================================
Name: sql_db_schema

CREATE TABLE "Genre" (
	"GenreId" INTEGER NOT NULL,
	"Name" NVARCHAR(120),
	PRIMARY KEY ("GenreId")
)

/*
3 rows from Genre table:
GenreId	Name
1	Rock
2	Jazz
3	Metal
*/

CREATE TABLE "Track" (
	"TrackId" INTEGER NOT NULL,
	"Name" NVARCHAR(200) NOT NULL,
	"AlbumId" INTEGER,
	"MediaTypeId" INTEGER NOT NULL,
	"GenreId" INTEGER,
	"Composer" NVARCHAR(220),
	"Milliseconds" INTEGER NOT NULL,
	"Bytes" INTEGER,
	"UnitPrice" NUMERIC(10, 2) NOT NULL,
	PRIMARY KEY ("TrackId"),
	FOREIGN KEY("MediaTypeId") REFERENCES "MediaType" ("MediaTypeId"),
	FOREIGN KEY("GenreId") REFERENCES "Genre" ("GenreId"),
	FOREIGN KEY("AlbumId") REFERENCES "Album" ("AlbumId")
)

/*
3 rows from Track table:
TrackId	Name	AlbumId	MediaTypeId	GenreId	Composer	Milliseconds	Bytes	UnitPrice
1	For Those About To Rock (We Salute You)	1	1	1	Angus Young, Malcolm Young, Brian Johnson	343719	11170334	0.99
2	Balls to the Wall	2	2	1	U. Dirkschneider, W. Hoffmann, H. Frank, P. Baltes, S. Kaufmann, G. Hoffmann	342562	5510424	0.99
3	Fast As a Shark	3	2	1	F. Baltes, S. Kaufman, U. Dirkscneider & W. Hoffman	230619	3990994	0.99
*/
================================== Ai Message ==================================
Tool Calls:
  sql_db_query_checker (call_G64yYm6R6UauiVPCXJZMA49b)
 Call ID: call_G64yYm6R6UauiVPCXJZMA49b
  Args:
    query: SELECT Genre.Name, AVG(Track.Milliseconds) AS AverageLength FROM Track INNER JOIN Genre ON Track.GenreId = Genre.GenreId GROUP BY Genre.Name ORDER BY AverageLength DESC LIMIT 5;
================================= Tool Message =================================
Name: sql_db_query_checker

SELECT Genre.Name, AVG(Track.Milliseconds) AS AverageLength FROM Track INNER JOIN Genre ON Track.GenreId = Genre.GenreId GROUP BY Genre.Name ORDER BY AverageLength DESC LIMIT 5;
================================== Ai Message ==================================
Tool Calls:
  sql_db_query (call_AnO3SrhD0ODJBxh6dHMwvHwZ)
 Call ID: call_AnO3SrhD0ODJBxh6dHMwvHwZ
  Args:
    query: SELECT Genre.Name, AVG(Track.Milliseconds) AS AverageLength FROM Track INNER JOIN Genre ON Track.GenreId = Genre.GenreId GROUP BY Genre.Name ORDER BY AverageLength DESC LIMIT 5;
================================= Tool Message =================================
Name: sql_db_query

[('Sci Fi & Fantasy', 2911783.0384615385), ('Science Fiction', 2625549.076923077), ('Drama', 2575283.78125), ('TV Shows', 2145041.0215053763), ('Comedy', 1585263.705882353)]
================================== Ai Message ==================================

On average, the genre with the longest tracks is "Sci Fi & Fantasy" with an average track length of approximately 2,911,783 milliseconds. This is followed by "Science Fiction," "Drama," "TV Shows," and "Comedy."
```

该代理正确地编写了查询、检查了查询并执行了查询，从而得出最终回答。

> 注意：你可以在 [LangSmith trace](https://smith.langchain.com/public/cd2ce887-388a-4bb1-a29d-48208ce50d15/r) 中检查上述运行的所有方面，包括执行的步骤、调用的工具、LLM 看到的提示等。

### （可选）使用 Studio

[Studio](/langsmith/studio) 提供了"客户端侧"循环以及记忆功能，因此你可以将其作为聊天界面运行并查询数据库。你可以提出诸如"告诉我数据库的模式"或"显示前 5 大客户的发票"之类的问题。你将看到生成的 SQL 命令以及相应的输出。以下是启动它的详细步骤。

#### 在 Studio 中运行你的代理

除了前面提到的包之外，你还需要：

```shell
pip install -U langgraph-cli[inmem]>=0.4.0
```

在你将要运行的目录中，需要一个包含以下内容的 `langgraph.json` 文件：

```json
{
  "dependencies": ["."],
  "graphs": {
      "agent": "./sql_agent.py:agent",
      "graph": "./sql_agent_langgraph.py:graph"
  },
  "env": ".env"
}
```

创建一个文件 `sql_agent.py` 并插入以下内容：

```python
# sql_agent.py for studio
import pathlib
import sqlite3

import requests
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool

# Initialize an LLM
model = init_chat_model("gpt-5.5")

# Get the database, store it locally
url = "https://storage.googleapis.com/benchmarks-artifacts/chinook/Chinook.db"
local_path = pathlib.Path("Chinook.db")

if local_path.exists():
    print(f"{local_path} already exists, skipping download.")
else:
    response = requests.get(url, timeout=60)
    if response.status_code == 200:
        local_path.write_bytes(response.content)
        print(f"File downloaded and saved as {local_path}")
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")

# Below are minimal tools for demonstration purposes.

@tool
def sql_db_list_tables() -> str:
    """Input is an empty string, output is a comma-separated list of tables in the database."""
    con = sqlite3.connect("Chinook.db")
    try:
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]
        return ", ".join(tables)
    finally:
        con.close()

@tool
def sql_db_schema(table_names: str) -> str:
    """Input to this tool is a comma-separated list of tables, output is the schema and sample rows for those tables.
    Be sure that the tables actually exist by calling sql_db_list_tables first!
    Example Input: table1, table2, table3"""
    con = sqlite3.connect("Chinook.db")
    try:
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        valid_tables = {row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")}
        results = []
        for table in table_names.split(","):
            table = table.strip()
            if table not in valid_tables:
                results.append(f"Error: table_names {{{table!r}}} not found in database")
                continue
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?;", (table,))
            schema_row = cursor.fetchone()
            if schema_row:
                results.append(schema_row[0])
                try:
                    quoted_table = '"' + table.replace('"', '""') + '"'
                    cursor.execute(f"SELECT * FROM {quoted_table} LIMIT 3;")
                    rows = cursor.fetchall()
                    if rows:
                        col_names = [description[0] for description in cursor.description]
                        results.append(
                            f"/*\n3 rows from {table} table:\n"
                            + "\t".join(col_names)
                            + "\n"
                            + "\n".join("\t".join(str(x) for x in row) for row in rows)
                            + "\n*/"
                        )
                except Exception as e:
                    results.append(f"Error fetching sample rows: {e}")
        return "\n\n".join(results)
    finally:
        con.close()

@tool
def sql_db_query(query: str) -> str:
    """Input to this tool is a detailed and correct SQL query, output is a result from the database.
    If the query is not correct, an error message will be returned.
    If an error is returned, rewrite the query, check the query, and try again.
    If you encounter an issue with Unknown column 'xxxx' in 'field list', use sql_db_schema to query the correct table fields."""
    con = sqlite3.connect("Chinook.db")
    try:
        cursor = con.cursor()
        cursor.execute(query)
        res = cursor.fetchall()
        return str(res)
    except Exception as e:
        return f"Error: {e}"
    finally:
        con.close()

@tool
def sql_db_query_checker(query: str) -> str:
    """Use this tool to double check if your query is correct before executing it.
    Always use this tool before executing a query with sql_db_query!"""
    trigger_prompt = """{query}
Double check the sqlite query above for common mistakes, including:
- Using NOT IN with NULL values
- Using UNION when UNION ALL should have been used
- Using BETWEEN for exclusive ranges
- Data type mismatch in predicates
- Properly quoting identifiers
- Using the correct number of arguments for functions
- Casting to the correct data type
- Using the proper columns for joins

If there are any of the above mistakes, rewrite the query. If there are no mistakes, just reproduce the original query.

Output the final SQL query only.

SQL Query: """.format(query=query)

    response = model.invoke(trigger_prompt)
    return response.text.strip()

tools = [sql_db_list_tables, sql_db_schema, sql_db_query, sql_db_query_checker]

# Use a distinct loop variable so it does not shadow the `tool` decorator.
for t in tools:
    print(f"{t.name}: {t.description}\n")

# Use create_agent
system_prompt = """
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.

You can order the results by a relevant column to return the most interesting
examples in the database. Never query for all the columns from a specific table,
only ask for the relevant columns given the question.

You MUST double check your query before executing it. If you get an error while
executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.

To start you should ALWAYS look at the tables in the database to see what you
can query. Do NOT skip this step.

Then you should query the schema of the most relevant tables.
""".format(
    dialect="sqlite",
    top_k=5,
)

agent = create_agent(
    model,
    tools,
    system_prompt=system_prompt,
)
```

### 实现人机协同审查

在执行代理的 SQL 查询之前对其进行检查，以防止任何意外操作或低效情况，这是明智的做法。

LangChain 代理支持内置的 [人机协同中间件](/oss/python/langchain/human-in-the-loop)，可为代理的工具调用添加监督。让我们配置代理，使其在调用 `sql_db_query` 工具时暂停等待人工审查：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model,
    tools,
    system_prompt=system_prompt,
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={"sql_db_query": True},
            description_prefix="Tool execution pending approval",
        ),
    ],
    checkpointer=InMemorySaver(),
)
```

> 注意：我们为代理添加了 [检查点](/oss/python/langchain/short-term-memory)，以便允许执行暂停和恢复。有关详细信息以及可用的中间件配置，请参阅 [人机协同指南](/oss/python/langchain/human-in-the-loop)。

运行代理时，它现在会在执行 `sql_db_query` 工具之前暂停等待审查：

```python
question = "Which genre on average has the longest tracks?"
config = {"configurable": {"thread_id": "1"}}

stream = agent.stream_events(
    {"messages": [{"role": "user", "content": question}]},
    config,
    version="v3",
)
for kind, item in stream.interleave("messages", "tool_calls"):
    if kind == "messages":
        for token in item.text:
            print(token, end="", flush=True)
    elif kind == "tool_calls":
        print(f"\nTool call: {item.tool_name}({item.input})")
if stream.interrupted:
    print("INTERRUPTED:")
    interrupt = stream.interrupts[0]
    for request in interrupt.value["action_requests"]:
        print(request["description"])
```

```
...

INTERRUPTED:
Tool execution pending approval

Tool: sql_db_query
Args: {'query': 'SELECT g.Name AS Genre, AVG(t.Milliseconds) AS AvgTrackLength FROM Track t JOIN Genre g ON t.GenreId = g.GenreId GROUP BY g.Name ORDER BY AvgTrackLength DESC LIMIT 1;'}
```

我们可以使用 [Command](/oss/python/langgraph/use-graph-api#combine-control-flow-and-state-updates-with-command) 恢复执行，本例中为接受查询：

```python
from langgraph.types import Command

stream = agent.stream_events(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config,
    version="v3",
)
for kind, item in stream.interleave("messages", "tool_calls"):
    if kind == "messages":
        for token in item.text:
            print(token, end="", flush=True)
    elif kind == "tool_calls":
        print(f"\nTool call: {item.tool_name}({item.input})")
if stream.interrupted:
    print("INTERRUPTED:")
    interrupt = stream.interrupts[0]
    for request in interrupt.value["action_requests"]:
        print(request["description"])
```

```
================================== Ai Message ==================================
Tool Calls:
  sql_db_query (call_7oz86Epg7lYRqi9rQHbZPS1U)
 Call ID: call_7oz86Epg7lYRqi9rQHbZPS1U
  Args:
    query: SELECT Genre.Name, AVG(Track.Milliseconds) AS AvgDuration FROM Track JOIN Genre ON Track.GenreId = Genre.GenreId GROUP BY Genre.Name ORDER BY AvgDuration DESC LIMIT 5;
================================= Tool Message =================================
Name: sql_db_query

[('Sci Fi & Fantasy', 2911783.0384615385), ('Science Fiction', 2625549.076923077), ('Drama', 2575283.78125), ('TV Shows', 2145041.0215053763), ('Comedy', 1585263.705882353)]
================================== Ai Message ==================================

The genre with the longest average track length is "Sci Fi & Fantasy" with an average duration of about 2,911,783 milliseconds, followed by "Science Fiction" and "Drama."
```

详情请参阅 [人机协同指南](/oss/python/langchain/human-in-the-loop)。

## 后续步骤

如需更深入的定制，请查看[本教程](/oss/python/langgraph/sql-agent)，了解如何直接使用 LangGraph 原语实现 SQL 代理。

# 构建语音代理

## 概述

聊天界面一直主导着我们与 AI 的交互方式，但多模态 AI 的最新突破正在开辟令人兴奋的新可能性。高质量的生成模型和富有表现力的文本转语音（TTS）系统，如今使得构建的代理感觉更像对话伙伴而不是工具成为可能。

语音代理就是其中一个例子。无需依赖键盘和鼠标向代理输入内容，你可以用语音与它交互。这是一种更自然、更具参与感的 AI 交互方式，并且在某些场景下尤其有用。

### 什么是语音代理？

语音代理是可以与用户进行自然语音对话的[代理](/oss/python/langchain/agents)。这些代理结合了语音识别、自然语言处理、生成式 AI 和文本转语音技术，从而创造出无缝、自然的对话体验。

它们适用于多种用例，包括：

* 客户支持
* 个人助理
* 免提界面
* 辅导与培训

### 语音代理如何工作？

从高层来看，每个语音代理都需要处理三项任务：

1. **听** —— 捕获音频并转录
2. **思考** —— 解读意图、推理、规划
3. **说** —— 生成音频并流式返回给用户

区别在于这些步骤如何排序和耦合。在实践中，生产级代理遵循两种主要架构之一：

#### 1. STT > Agent > TTS 架构（"三明治"架构）

三明治架构由三个独立组件组成：语音转文本（STT）、基于文本的 LangChain 代理和文本转语音（TTS）。

（架构流程图：用户音频 → 语音转文本 → LangChain 代理 → 文本转语音 → 音频输出。）

**优点：**

* 对每个组件拥有完全控制权（可按需更换 STT/TTS 提供商）
* 可使用现代文本模态模型的最新能力
* 行为透明，各组件之间边界清晰

**缺点：**

* 需要编排多个服务
* 管理流水线增加额外复杂性
* 从语音到文本的转换会丢失信息（例如语调、情绪）

#### 2. 语音到语音架构（S2S）

语音到语音使用多模态模型，原生处理音频输入并生成音频输出。

（架构流程图：用户音频 → 多模态模型 → 音频输出。）

**优点：**

* 架构更简单，活动部件更少
* 简单交互通常延迟更低
* 直接处理音频可捕获语调等语音细节

**缺点：**

* 模型选择有限，提供商锁定风险更高
* 功能可能落后于文本模态模型
* 音频处理方式的透明度较低
* 可控性和定制选项减少

本指南演示**三明治架构**，以平衡性能、可控性以及对现代模型能力的访问。三明治架构搭配某些 STT 和 TTS 提供商可达到 700ms 以下的延迟，同时保持对模块化组件的控制。

### 演示应用概述

我们将逐步构建一个基于三明治架构的语音代理。该代理将管理一家三明治店的订单。应用将演示三明治架构的全部三个组件，使用 [AssemblyAI](https://www.assemblyai.com/) 进行 STT，使用 [Cartesia](https://cartesia.ai/) 进行 TTS（尽管可以为大多数提供商构建适配器）。

完整的端到端参考应用位于 [voice-sandwich-demo](https://github.com/langchain-ai/voice-sandwich-demo) 仓库中。我们将在此处逐步讲解该应用。

该演示使用 WebSockets 实现浏览器与服务器之间的实时双向通信。同样的架构也可以适配其他传输方式，例如电话系统（Twilio、Vonage）或 WebRTC 连接。

### 架构

该演示实现了一个流式流水线，每个阶段异步处理数据：

**客户端（浏览器）**

* 捕获麦克风音频并将其编码为 PCM
* 与后端服务器建立 WebSocket 连接
* 实时向服务器流式传输音频块
* 接收并播放合成的语音音频

**服务器（Python）**

* 接受来自客户端的 WebSocket 连接
* 编排三步流水线：
  * [语音转文本（STT）](#1-speech-to-text)：将音频转发给 STT 提供商（例如 AssemblyAI），接收转录事件
  * [代理](#2-langchain-agent)：使用 LangChain 代理处理转录文本，流式输出响应令牌
  * [文本转语音（TTS）](#3-text-to-speech)：将代理响应发送给 TTS 提供商（例如 Cartesia），接收音频块
* 将合成的音频返回给客户端播放

流水线使用异步生成器在每个阶段实现流式处理。这使得下游组件可以在上游阶段完成之前就开始处理，从而最大限度地降低端到端延迟。

## 安装设置

有关详细的安装说明和设置，请参阅[仓库 README](https://github.com/langchain-ai/voice-sandwich-demo#readme)。

## 1. 语音转文本

STT 阶段将传入的音频流转换为文本转录。该实现使用生产者-消费者模式，并发处理音频流和转录接收。

### 关键概念

**生产者-消费者模式**：音频块被发送到 STT 服务，同时并发接收转录事件。这使得转录可以在所有音频到达之前就开始。

**事件类型**：

* `stt_chunk`：STT 服务处理音频时提供的部分转录
* `stt_output`：触发代理处理的最终格式化转录

**WebSocket 连接**：保持与 AssemblyAI 实时 STT API 的持久连接，配置为 16kHz PCM 音频并带有自动话轮格式化。

### 实现

```python
from typing import AsyncIterator
import asyncio
from assemblyai_stt import AssemblyAISTT
from events import VoiceAgentEvent

async def stt_stream(
    audio_stream: AsyncIterator[bytes],
) -> AsyncIterator[VoiceAgentEvent]:
    """
    Transform stream: Audio (Bytes) → Voice Events (VoiceAgentEvent)

    Uses a producer-consumer pattern where:
    - Producer: Reads audio chunks and sends them to AssemblyAI
    - Consumer: Receives transcription events from AssemblyAI
    """
    stt = AssemblyAISTT(sample_rate=16000)

    async def send_audio():
        """Background task that pumps audio chunks to AssemblyAI."""
        try:
            async for audio_chunk in audio_stream:
                await stt.send_audio(audio_chunk)
        finally:
            # Signal completion when audio stream ends
            await stt.close()

    # Launch audio sending in background
    send_task = asyncio.create_task(send_audio())

    try:
        # Receive and yield transcription events as they arrive
        async for event in stt.receive_events():
            yield event
    finally:
        # Cleanup
        with contextlib.suppress(asyncio.CancelledError):
            send_task.cancel()
            await send_task
        await stt.close()
```

该应用实现了一个 AssemblyAI 客户端来管理 WebSocket 连接和消息解析。实现见下文；可以为其他 STT 提供商构建类似的适配器。

> 信息：AssemblyAI 客户端

```python
class AssemblyAISTT:
    def __init__(self, api_key: str | None = None, sample_rate: int = 16000):
        self.api_key = api_key or os.getenv("ASSEMBLYAI_API_KEY")
        self.sample_rate = sample_rate
        self._ws: WebSocketClientProtocol | None = None

    async def send_audio(self, audio_chunk: bytes) -> None:
        """Send PCM audio bytes to AssemblyAI."""
        ws = await self._ensure_connection()
        await ws.send(audio_chunk)

    async def receive_events(self) -> AsyncIterator[STTEvent]:
        """Yield STT events as they arrive from AssemblyAI."""
        async for raw_message in self._ws:
            message = json.loads(raw_message)

            if message["type"] == "Turn":
                # Final formatted transcript
                if message.get("turn_is_formatted"):
                    yield STTOutputEvent.create(message["transcript"])
                # Partial transcript
                else:
                    yield STTChunkEvent.create(message["transcript"])

    async def _ensure_connection(self) -> WebSocketClientProtocol:
        """Establish WebSocket connection if not already connected."""
        if self._ws is None:
            url = f"wss://streaming.assemblyai.com/v3/ws?sample_rate={self.sample_rate}&format_turns=true"
            self._ws = await websockets.connect(
                url,
                additional_headers={"Authorization": self.api_key}
            )
        return self._ws
```

## 2. LangChain 代理

代理阶段通过 LangChain [代理](/oss/python/langchain/agents)处理文本转录，并流式输出响应令牌。在本例中，我们流式输出代理生成的所有[文本内容块](/oss/python/langchain/messages#content-block-reference)。

### 关键概念

**流式响应**：代理使用带 `stream.messages` 的 [`stream_events(version="v3")`](/oss/python/langchain/streaming) 在生成响应令牌时即时发出，而不是等待完整响应。这使得 TTS 阶段可以立即开始合成。

**对话记忆**：[检查点器](/oss/python/langchain/short-term-memory)使用唯一的 thread ID 在多个话轮之间维护对话状态。这使得代理可以引用对话中之前的交流内容。

### 实现

```python
from langchain_core.utils.uuid import uuid7
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

# Define agent tools
def add_to_order(item: str, quantity: int) -> str:
    """Add an item to the customer's sandwich order."""
    return f"Added {quantity} x {item} to the order."

def confirm_order(order_summary: str) -> str:
    """Confirm the final order with the customer."""
    return f"Order confirmed: {order_summary}. Sending to kitchen."

# Create agent with tools and memory
agent = create_agent(
    model="google_genai:gemini-3.6-flash",  # Select your model
    tools=[add_to_order, confirm_order],
    system_prompt="""You are a helpful sandwich shop assistant.
    Your goal is to take the user's order. Be concise and friendly.
    Do NOT use emojis, special characters, or markdown.
    Your responses will be read by a text-to-speech engine.""",
    checkpointer=InMemorySaver(),
)

async def agent_stream(
    event_stream: AsyncIterator[VoiceAgentEvent],
) -> AsyncIterator[VoiceAgentEvent]:
    """
    Transform stream: Voice Events → Voice Events (with Agent Responses)

    Passes through all upstream events and adds agent_chunk events
    when processing STT transcripts.
    """
    # Generate unique thread ID for conversation memory
    thread_id = str(uuid7())

    async for event in event_stream:
        # Pass through all upstream events
        yield event

        # Process final transcripts through the agent
        if event.type == "stt_output":
            # Stream agent response with conversation context
            stream = await agent.astream_events(
                {"messages": [HumanMessage(content=event.transcript)]},
                {"configurable": {"thread_id": thread_id}},
                version="v3",
            )

            # Yield agent response chunks as they arrive
            async for message in stream.messages:
                async for token in message.text:
                    yield AgentChunkEvent.create(token)
```

## 3. 文本转语音

TTS 阶段将代理响应文本合成为音频并流式返回给客户端。与 STT 阶段一样，它使用生产者-消费者模式并发处理文本发送和音频接收。

### 关键概念

**并发处理**：该实现合并两个异步流：

* **上游处理**：透传所有事件，并将代理文本块发送给 TTS 提供商
* **音频接收**：从 TTS 提供商接收合成的音频块

**流式 TTS**：某些提供商（如 [Cartesia](https://cartesia.ai/)）在收到文本后立即开始合成音频，使音频播放可以在代理生成完整响应之前就开始。

**事件透传**：所有上游事件原样流过，使客户端或其他观察者能够跟踪完整的流水线状态。

### 实现

```python
from cartesia_tts import CartesiaTTS
from utils import merge_async_iters

async def tts_stream(
    event_stream: AsyncIterator[VoiceAgentEvent],
) -> AsyncIterator[VoiceAgentEvent]:
    """
    Transform stream: Voice Events → Voice Events (with Audio)

    Merges two concurrent streams:
    1. process_upstream(): passes through events and sends text to Cartesia
    2. tts.receive_events(): yields audio chunks from Cartesia
    """
    tts = CartesiaTTS()

    async def process_upstream() -> AsyncIterator[VoiceAgentEvent]:
        """Process upstream events and send agent text to Cartesia."""
        async for event in event_stream:
            # Pass through all events
            yield event
            # Send agent text to Cartesia for synthesis
            if event.type == "agent_chunk":
                await tts.send_text(event.text)

    try:
        # Merge upstream events with TTS audio events
        # Both streams run concurrently
        async for event in merge_async_iters(
            process_upstream(),
            tts.receive_events()
        ):
            yield event
    finally:
        await tts.close()
```

该应用实现了一个 Cartesia 客户端来管理 WebSocket 连接和音频流。实现见下文；可以为其他 TTS 提供商构建类似的适配器。

> 信息：Cartesia 客户端

```python
import base64
import json
import websockets

class CartesiaTTS:
    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: str = "f6ff7c0c-e396-40a9-a70b-f7607edb6937",
        model_id: str = "sonic-3",
        sample_rate: int = 24000,
        encoding: str = "pcm_s16le",
    ):
        self.api_key = api_key or os.getenv("CARTESIA_API_KEY")
        self.voice_id = voice_id
        self.model_id = model_id
        self.sample_rate = sample_rate
        self.encoding = encoding
        self._ws: WebSocketClientProtocol | None = None

    def _generate_context_id(self) -> str:
        """Generate a valid context_id for Cartesia."""
        timestamp = int(time.time() * 1000)
        counter = self._context_counter
        self._context_counter += 1
        return f"ctx_{timestamp}_{counter}"

    async def send_text(self, text: str | None) -> None:
        """Send text to Cartesia for synthesis."""
        if not text or not text.strip():
            return

        ws = await self._ensure_connection()
        payload = {
            "model_id": self.model_id,
            "transcript": text,
            "voice": {
                "mode": "id",
                "id": self.voice_id,
            },
            "output_format": {
                "container": "raw",
                "encoding": self.encoding,
                "sample_rate": self.sample_rate,
            },
            "language": self.language,
            "context_id": self._generate_context_id(),
        }
        await ws.send(json.dumps(payload))

    async def receive_events(self) -> AsyncIterator[TTSChunkEvent]:
        """Yield audio chunks as they arrive from Cartesia."""
        async for raw_message in self._ws:
            message = json.loads(raw_message)

            # Decode and yield audio chunks
            if "data" in message and message["data"]:
                audio_chunk = base64.b64decode(message["data"])
                if audio_chunk:
                    yield TTSChunkEvent.create(audio_chunk)

    async def _ensure_connection(self) -> WebSocketClientProtocol:
        """Establish WebSocket connection if not already connected."""
        if self._ws is None:
            url = (
                f"wss://api.cartesia.ai/tts/websocket"
                f"?api_key={self.api_key}&cartesia_version={self.cartesia_version}"
            )
            self._ws = await websockets.connect(url)

        return self._ws
```

### LangSmith

你用 LangChain 构建的许多应用都会包含多个步骤、多次 LLM 调用。随着这些应用变得越来越复杂，能够检查链或代理内部到底发生了什么变得至关重要。做到这一点的最佳方式是使用 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-voice-agent)。

在上面的链接注册之后，请确保设置环境变量以开始记录追踪：

```shell
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="..."
```

或者在 Python 中设置：

```python
import getpass
import os

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = getpass.getpass()
```

## 整合所有部分

完整流水线将三个阶段串联起来：

```python
from langchain_core.runnables import RunnableGenerator

pipeline = (
    RunnableGenerator(stt_stream)      # Audio → STT events
    | RunnableGenerator(agent_stream)  # STT events → Agent events
    | RunnableGenerator(tts_stream)    # Agent events → TTS audio
)

# Use in WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async def websocket_audio_stream():
        """Yield audio bytes from WebSocket."""
        while True:
            data = await websocket.receive_bytes()
            yield data

    # Transform audio through pipeline
    output_stream = pipeline.atransform(websocket_audio_stream())

    # Send TTS audio back to client
    async for event in output_stream:
        if event.type == "tts_chunk":
            await websocket.send_bytes(event.audio)
```

我们使用 [RunnableGenerators](https://reference.langchain.com/python/langchain_core/runnables/#langchain_core.runnables.base.RunnableGenerator) 来组合流水线的每一步。这是 LangChain 内部用于管理[跨组件流式传输](https://reference.langchain.com/python/langchain_core/runnables/)的抽象。

每个阶段独立且并发地处理事件：音频一旦到达就开始转录，转录文本一旦可用代理就开始推理，代理文本一旦生成就开始语音合成。这种架构可以达到 700ms 以下的延迟，以支持自然对话。

关于使用 LangChain 构建代理的更多内容，请参阅[代理指南](/oss/python/langchain/agents)。

# 从零构建数据分析代理

> 使用 `create_agent` 和 Deep Agents 中间件，一步步构建一个数据分析代理。

本指南从第一性原理出发，使用 `create_agent` 和 Deep Agents 中间件构建一个数据分析代理。

`create_agent` 和 `create_deep_agent` 都能让你对工具、记忆等拥有细粒度的控制。两者主要的区别在于：Deep Agents 内置了一系列常用的能力，例如规划、文件系统工具和子代理。如果 Deep Agents 的默认框架（harness）不适合你的需求，本指南会展示如何从 `create_agent` 开始，一块一块地组装这个框架，让你清楚地看到每个组件带来了什么，并且只替换你的用例所需的部分。

按照本指南，你将构建一个能够：

1. 接收 CSV 文件进行分析
2. 在隔离的沙箱中编写并执行 Python 代码
3. 将可视化工作委托给专门的子代理
4. 从技能文件中加载数据分析模式

最终的完整技术栈与 `create_deep_agent` 默认组装的内容一致。

## 你将学到什么

每一步都为同一个数据分析代理添加一项能力：

| 步骤             | 缺少它的代价                                  | 你将添加的内容                                                                                             |
| ---------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| 最小化代理       | —                                             | 基础循环：模型 + 工具，无框架                                                                             |
| 沙箱 + 文件系统  | 代理无法读取 CSV 或运行 Python                | 隔离的 [backend](/oss/python/deepagents/backends) + 文件和执行工具                                        |
| 摘要总结         | 长会话触及上下文限制                          | 自动压缩历史记录                                                                                          |
| 技能             | 领域规则撑爆系统提示词                        | 通过 [渐进式披露](/oss/python/langchain/multi-agent/skills-sql-assistant) 按需获取专业知识                  |
| 子代理           | 图表迭代挤占主线程                            | 隔离的工作代理 + 并行委托                                                                                |

## 环境搭建

1. **安装软件包**

   安装本教程所需的软件包：

   ```bash
   pip install deepagents langsmith
   ```

2. **设置 LangSmith API 密钥**

   本教程使用 [`LangSmithSandbox`](https://reference.langchain.com/python/deepagents/backends/langsmith/LangSmithSandbox)，它通过 `SandboxClient` 来配置沙箱。该客户端使用环境变量中的 `LANGSMITH_API_KEY` 向 LangSmith 进行身份验证，因此运行本教程需要 API 密钥。设置 LangSmith 还可以让你查看代理运行时发生的追踪（trace）。

   1. [注册一个免费账户](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-deep-agent-from-scratch)。你可以使用 Google、GitHub 或邮箱登录。
   2. 在 **Settings → API Keys** 中[创建 API 密钥](/langsmith/create-account-api-key)。
   3. 导出 LangSmith API 密钥：

   ```bash
   export LANGSMITH_API_KEY=...
   ```

   4. 启用追踪，以便在逐步添加每个组件时检查工具调用、中间件步骤和子代理委托：

   ```bash
   export LANGSMITH_TRACING=true
   ```

3. **添加模型提供商 API 密钥**

   为代码示例中使用的模型提供商导出 API 密钥：

   ```bash
   export GOOGLE_API_KEY=...
   ```

   ```bash
   export OPENAI_API_KEY=...
   ```

   ```bash
   export ANTHROPIC_API_KEY=...
   ```

   ```bash
   export OPENROUTER_API_KEY=...
   ```

   ```bash
   export FIREWORKS_API_KEY=...
   ```

   ```bash
   export BASETEN_API_KEY=...
   ```

   ```bash
   # Local: Ollama must be running on your machine
   # Cloud: Set your Ollama API key for hosted inference
   export OLLAMA_API_KEY=...
   ```

## 构建代理

### 创建最小化代理

数据分析代理需要的不仅仅是聊天循环，但作为开始，先从基线入手：只有模型和一个循环。

使用 [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 并指定你想要使用的模型：

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
from langchain.agents import create_agent

agent = create_agent(model="google_genai:gemini-3.6-flash", tools=[])
```

这可以运行，但代理没有文件系统，也无法执行代码。如果你让它分析一个 CSV，它只能根据提示词猜测。接下来的步骤会添加真正的文件访问和代码执行能力。

### 添加沙箱后端

为了高效地分析数据，代理需要在文件上运行代码。这需要两样东西：

* 一个隔离的 [沙箱](/oss/python/deepagents/sandboxes)，代理可以在其中放置文件并在文件上运行代码，而不会让代理接触到你的宿主机。

* 一个 [backend](/oss/python/deepagents/backends)，通过 [`FilesystemMiddleware`](https://reference.langchain.com/python/deepagents/middleware/filesystem/FilesystemMiddleware) 提供与沙箱协作的文件系统工具（`read_file`、`write_file`、`edit_file`、`delete`、`glob`、`grep`）。由于 `LangSmithSandbox` 后端实现了沙箱协议，[`FilesystemMiddleware`](https://reference.langchain.com/python/deepagents/middleware/filesystem/FilesystemMiddleware) 还会添加 `execute` 工具，允许代理运行 shell 命令。

[`LangSmithSandbox`](https://reference.langchain.com/python/deepagents/backends/langsmith/LangSmithSandbox) 是文件存放和命令运行的地方。[`FilesystemMiddleware`](https://reference.langchain.com/python/deepagents/middleware/filesystem/FilesystemMiddleware) 则是把该环境以工具的形式暴露给模型。如果你之后更换后端，同一个中间件也可以与其他后端配合使用。

[`LangSmithSandbox`](https://reference.langchain.com/python/deepagents/backends/langsmith/LangSmithSandbox) 为代理提供了一个隔离的环境，包含文件系统和一个用于运行 shell 命令的 `execute` 工具。有了它，代理可以安装软件包、编写脚本并运行它们，而不会触及宿主机。要从自定义镜像而不是默认运行时启动，请向 `create_sandbox()` 传入 `snapshot_name` 或 `snapshot_id`；参见 [Sandbox snapshots](/langsmith/sandbox-snapshots)。

用包含 [`FilesystemMiddleware`](https://reference.langchain.com/python/deepagents/middleware/filesystem/FilesystemMiddleware) 的代理替换上一步的代理：

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
from langchain.agents import create_agent
from deepagents.backends.langsmith import LangSmithSandbox
from deepagents.middleware import FilesystemMiddleware
from langsmith.sandbox import SandboxClient

client = SandboxClient()
sandbox = None
sandbox = client.create_sandbox(name="langchain-docs", snapshot_name="docs-test-ci")
backend = LangSmithSandbox(sandbox=sandbox)

agent = create_agent(
    model="google_genai:gemini-3.6-flash",
    tools=[],
    middleware=[FilesystemMiddleware(backend=backend)],
)
```

沙箱文件系统与你的笔记本电脑是分离的。你必须在调用代理之前，把需要的文件上传到沙箱中：

```python
import csv
import io

rows = [
    ["Date", "Product", "Units", "Revenue"],
    ["2025-08-01", "Widget A", 10, 250],
    ["2025-08-02", "Widget B", 5, 125],
    ["2025-08-03", "Widget A", 7, 175],
    ["2025-08-04", "Widget C", 3, 90],
]
buf = io.StringIO()
csv.writer(buf).writerows(rows)
backend.upload_files([("/sales.csv", buf.getvalue().encode())])

upload_stream = agent.stream_events(
    {
        "messages": [
            {
                "role": "user",
                "content": (
                    "Read /sales.csv and summarize total revenue by product in one "
                    "sentence. Do not run shell commands."
                ),
            }
        ]
    },
    version="v3",
    config={"recursion_limit": 8},
)
for item in upload_stream.messages:
    print(item.text)
upload_stream.output
```

> 注意：使用 [`LangSmithSandbox`](https://reference.langchain.com/python/deepagents/backends/langsmith/LangSmithSandbox) 时，上传路径必须是绝对的 POSIX 路径（例如 `/sales.csv`）。诸如 `sales.csv` 这样的相对路径会被以 `invalid_path` 拒绝，文件不会被写入沙箱。

把前面几步的代码合并到一个脚本中并运行它：

```bash
python analyze_sales.py
```

首次运行时，LangSmith 会配置一个沙箱（这可能需要几秒钟）。脚本会上传 `sales.csv`，流式输出代理的运行过程，并在消息到达时打印助手消息。你应该会看到对示例销售数据的分析：按产品统计的收入、哪个小部件卖得最多，以及简要的趋势说明。具体措辞会因模型而异。

在 [LangSmith](https://smith.langchain.com/?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-deep-agent-from-scratch) 中打开该运行，观察代理在回复之前使用文件系统工具（`read_file`，以及如果它在沙箱中运行 Python 则会用到 `execute`）。

### 添加上下文管理

在第 2 步之后，每次工具结果都会保留在消息历史中。一次真实的分析会话（多个图表、失败的脚本、大量的 `read_file` 输出）很快就会填满上下文窗口。

[`SummarizationMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/SummarizationMiddleware) 会在历史记录变得过大时压缩较早的轮次，因此代理可以继续工作，而无需你手动裁剪消息。这在回答第一个 `sales.csv` 问题时关系不大，但在后续追问（例如"现在按产品分组并绘制月度趋势图"）时更为重要。

通过在第 2 步的中间件列表中添加 [`SummarizationMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/SummarizationMiddleware) 来更新你的代理：

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
from deepagents.middleware import FilesystemMiddleware, SummarizationMiddleware

model = "google_genai:gemini-3.6-flash"

agent = create_agent(
    model=model,
    tools=[],
    middleware=[
        FilesystemMiddleware(backend=backend),
        SummarizationMiddleware(model=model, backend=backend),
    ],
)
```

运行一个多轮会话，看看摘要总结的实际效果。在初始分析之后，提出一些会触发更多文件读取或脚本运行的追问。在 LangSmith 中，注意在后续模型调用之前会出现一个摘要总结步骤。更多信息，参见 [Context engineering](/oss/python/langchain/context-engineering)。

### 添加技能

[技能](/oss/python/langchain/multi-agent/skills-sql-assistant) 提供了一种方式，让代理在需要时通过渐进式披露按需获取领域知识。技能可以包含多步骤工作流、规则和约定。通过把这些信息放在技能中，它默认不会被加入系统提示词，从而确保只有在任务需要用到技能中的信息时才会消耗 token。

当代理启动时，它只会看到每个技能的轻量级元数据。当任务需要某个技能时，代理会按需加载完整的技能文件。

在技能目录中创建一个技能文件：

```
skills/
  pandas-patterns/
    SKILL.md
```

```markdown
---
name: pandas-patterns
description: Common pandas and matplotlib patterns for data analysis and visualization
---

## Data loading
Use `pd.read_csv()` for CSV files. Always check `df.info()` and `df.describe()` first.

## Visualization
Use `matplotlib` for bar charts, `seaborn` for statistical plots.
Save figures with `plt.savefig("output.png", dpi=150, bbox_inches="tight")`.

## Reporting
Write a markdown summary to `report.md` alongside any generated charts.
```

这个技能包含关于如何进行可视化的信息。

使用 [`LangSmithSandbox`](https://reference.langchain.com/python/deepagents/backends/langsmith/LangSmithSandbox) 时，技能路径会在沙箱文件系统上解析，而不是在你的本地机器上。在配置 [`SkillsMiddleware`](https://reference.langchain.com/python/deepagents/middleware/skills/SkillsMiddleware) 之前，先上传你的本地 `skills/` 目录：

```python
from pathlib import Path

skills_dir = (Path(__file__).resolve().parent / "skills").resolve()
skill_files: list[tuple[str, bytes]] = []
for path in sorted(skills_dir.rglob("*")):
    if not path.is_file():
        continue
    rel = path.resolve().relative_to(skills_dir)
    skill_files.append((f"/skills/{rel.as_posix()}", path.read_bytes()))
backend.upload_files(skill_files)
```

然后，通过添加 [`SkillsMiddleware`](https://reference.langchain.com/python/deepagents/middleware/skills/SkillsMiddleware) 来创建带有你的技能的代理：

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
from deepagents.middleware import FilesystemMiddleware, SkillsMiddleware, SummarizationMiddleware

model = "google_genai:gemini-3.6-flash"

agent = create_agent(
    model=model,
    tools=[],
    middleware=[
        FilesystemMiddleware(backend=backend),
        SummarizationMiddleware(model=model, backend=backend),
        SkillsMiddleware(backend=backend, sources=["/skills/"]),
    ],
)
```

你可以尝试这样的提示词："使用我们的 pandas 模式分析 sales.csv。" 当代理需要绘图或报告指导时，它会加载技能。如果你提出一个不需要该技能的不同问题，代理就不会加载它。

### 添加可视化子代理

有些任务会产生大量中间输出（脚本草稿、失败的运行、文件读取），如果放在同一个线程中，会挤占主代理的上下文。[子代理](/oss/python/deepagents/subagents) 在自己的上下文窗口中运行，因此主代理（supervisor）只会看到最终结果，而不会看到过程中的每一次工具调用。这样可以让主分析保持专注，并为后续提问留出空间。

使用子代理的一个典型场景是图表生成。绘图通常意味着反复迭代 Python 脚本、安装软件包、阅读错误输出，然后才能得到一张图。下面的 `visualizer` 子代理可以在隔离环境中处理这些工作，而主代理则继续规划和分析。借助 [`TodoListMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/todo/TodoListMiddleware)，主代理还可以并行委托图表工作，而不必在每张图上阻塞等待。

通过在第 4 步的代理中添加 [`TodoListMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/todo/TodoListMiddleware) 和 [`SubAgentMiddleware`](https://reference.langchain.com/python/deepagents/middleware/subagents/SubAgentMiddleware) 来更新你的代理：

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

```python
from deepagents import SubAgent
from deepagents.middleware import (
    FilesystemMiddleware,
    SkillsMiddleware,
    SubAgentMiddleware,
    SummarizationMiddleware,
)
from langchain.agents.middleware import TodoListMiddleware

model = "google_genai:gemini-3.6-flash"

visualizer: SubAgent = {
    "name": "visualizer",
    "description": "Generates charts and visualizations from data files in the sandbox.",
    "system_prompt": "You are a data visualization specialist. Write Python scripts using matplotlib and seaborn. Save all figures as PNG files.",
    "tools": [],
    "model": model,
}

agent = create_agent(
    model=model,
    tools=[],
    middleware=[
        FilesystemMiddleware(backend=backend),
        SummarizationMiddleware(model=model, backend=backend),
        SkillsMiddleware(backend=backend, sources=["/skills/"]),
        TodoListMiddleware(),
        SubAgentMiddleware(backend=backend, subagents=[visualizer]),
    ],
)
```

你可以尝试这样的提示词："分析 sales.csv，然后创建一张按产品统计收入的柱状图。" 主代理负责分析和规划，并通过 `task` 工具把图表生成委托给 `visualizer` 子代理。

如果你在 [Setup](#setup) 中启用了追踪，请在 [LangSmith](https://smith.langchain.com/?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-deep-agent-from-scratch) 中打开该运行。你应该会看到一次对 `visualizer` 的 `task` 调用、一个带有自己工具循环的独立子运行，以及返回给主代理的一段简短结果。

## 你构建了什么

你构建了一个包含以下中间件的定制代理：

| 中间件                                                                                                                                                                                                                             | 它带来的能力                         |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| [`FilesystemMiddleware`](https://reference.langchain.com/python/deepagents/middleware/filesystem/FilesystemMiddleware) + `LangSmithSandbox`                                                                                            | 隔离的文件系统 + `execute` 工具      |
| [`SummarizationMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/SummarizationMiddleware)                                                                                                  | 自动上下文压缩                       |
| [`SkillsMiddleware`](https://reference.langchain.com/python/deepagents/middleware/skills/SkillsMiddleware)                                                                                                                             | 按需加载的领域知识                   |
| [`TodoListMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/todo/TodoListMiddleware) + [`SubAgentMiddleware`](https://reference.langchain.com/python/deepagents/middleware/subagents/SubAgentMiddleware) | 并行可视化子代理                     |

这与 [`create_deep_agent`](https://reference.langchain.com/python/deepagents/graph/create_deep_agent) 的基础相同：手动组装，以便你精确控制包含哪些内容。

可能性不止于此：参见[预构建中间件](/oss/python/langchain/middleware/built-in)获取全部可组合能力的列表，以及 [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 参考文档了解所有配置选项。

要使用预组装版本，参见 [Customize Deep Agents](/oss/python/deepagents/customization)。要查看使用 `create_deep_agent` 的完整数据分析示例，参见 [Data analysis](/oss/python/deepagents/data-analysis)。

# 用交接构建客服系统

[状态机模式](/oss/python/langchain/multi-agent/handoffs)描述的是这样一种工作流：代理在任务的不同状态间移动时，其行为也随之改变。本教程展示如何通过工具调用动态地改变单个代理的配置——根据当前状态更新其可用工具和指令——来实现一个状态机。状态可以从多个来源确定：代理过去的动作（工具调用）、外部状态（如 API 调用结果），甚至最初的用户输入（例如，通过运行分类器来确定用户意图）。

在本教程中，你将构建一个客服代理，它可以完成以下工作：

* 在继续处理前收集保修信息。
* 将问题分类为硬件或软件。
* 提供解决方案或将问题升级给人工支持。
* 跨多个回合维持对话状态。

与[子代理模式](/oss/python/langchain/multi-agent/subagents-personal-assistant)（将子代理作为工具调用）不同，**状态机模式**使用单个代理，其配置会随工作流进展而变化。每个"步骤"只是同一个底层代理的不同配置（系统提示词 + 工具），根据状态动态选择。

以下是我们将要构建的工作流：

> 流程图：用户报告问题 → 判断设备是否在保修期内 → 无论是否在保都继续判断问题类型（硬件/软件）；保修内硬件问题提供保修维修指导，脱保硬件问题升级人工提供付费维修选项；软件问题提供排障步骤 → 问题解决。

## 设置

### 安装

本教程需要 `langchain` 包：

**pip**
```bash
pip install langchain
```

**uv**
```bash
uv add langchain
```

**conda**
```bash
conda install langchain -c conda-forge
```

更多详情请参阅[安装指南](/oss/python/langchain/install)。

### LangSmith

设置 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-multi-agent-handoffs-customer-support) 以查看代理内部发生的情况。然后设置以下环境变量：

**Shell**
```bash
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="..."
```

**Python**
```python
import getpass
import os

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = getpass.getpass()
```

### 选择 LLM

从 LangChain 的集成套件中选择一个聊天模型：

👉 阅读 [Google GenAI 聊天模型集成文档](/oss/python/integrations/chat/google_generative_ai/)

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

**pip**
```bash
pip install -U "langchain[google-genai]"
```

**uv**
```bash
uv add "langchain[google-genai]"
```

**init_chat_model**
```python
import os
from langchain.chat_models import init_chat_model

os.environ["GOOGLE_API_KEY"] = "..."

model = init_chat_model("google_genai:gemini-3.6-flash")
```

**Model Class**
```python
import os
from langchain_google_genai import ChatGoogleGenerativeAI

os.environ["GOOGLE_API_KEY"] = "..."

model = ChatGoogleGenerativeAI(model="gemini-3.6-flash")
```

## 1. 定义自定义状态

首先，定义一个自定义状态模式（state schema），用于跟踪当前处于哪个步骤：

```python
from langchain.agents import AgentState
from typing_extensions import NotRequired
from typing import Literal

# Define the possible workflow steps
SupportStep = Literal["warranty_collector", "issue_classifier", "resolution_specialist"]

class SupportState(AgentState):
    """State for customer support workflow."""
    current_step: NotRequired[SupportStep]
    warranty_status: NotRequired[Literal["in_warranty", "out_of_warranty"]]
    issue_type: NotRequired[Literal["hardware", "software"]]
```

`current_step` 字段是状态机模式的核心——它决定每一轮加载哪个配置（提示词 + 工具）。

## 2. 创建管理工作流状态的工具

创建用于更新工作流状态的工具。这些工具让代理能够记录信息并转换到下一步。

关键在于使用 `Command` 更新状态，包括 `current_step` 字段：

```python
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langgraph.types import Command

@tool
def record_warranty_status(
    status: Literal["in_warranty", "out_of_warranty"],
    runtime: ToolRuntime[None, SupportState],
) -> Command:
    """Record the customer's warranty status and transition to issue classification."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Warranty status recorded as: {status}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "warranty_status": status,
            "current_step": "issue_classifier",
        }
    )

@tool
def record_issue_type(
    issue_type: Literal["hardware", "software"],
    runtime: ToolRuntime[None, SupportState],
) -> Command:
    """Record the type of issue and transition to resolution specialist."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Issue type recorded as: {issue_type}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "issue_type": issue_type,
            "current_step": "resolution_specialist",
        }
    )

@tool
def escalate_to_human(reason: str) -> str:
    """Escalate the case to a human support specialist."""
    # In a real system, this would create a ticket, notify staff, etc.
    return f"Escalating to human support. Reason: {reason}"

@tool
def provide_solution(solution: str) -> str:
    """Provide a solution to the customer's issue."""
    return f"Solution provided: {solution}"
```

注意 `record_warranty_status` 和 `record_issue_type` 如何返回更新了数据（`warranty_status`、`issue_type`）以及 `current_step` 的 `Command` 对象。这就是状态机的工作原理——由工具控制工作流的推进。

## 3. 定义步骤配置

为每个步骤定义提示词和工具。首先定义每个步骤的提示词：

**展开查看完整的提示词定义**

```python
# Define prompts as constants for easy reference
WARRANTY_COLLECTOR_PROMPT = """You are a customer support agent helping with device issues.

CURRENT STAGE: Warranty verification

At this step, you need to:
1. Greet the customer warmly
2. Ask if their device is under warranty
3. Use record_warranty_status to record their response and move to the next step

Be conversational and friendly. Don't ask multiple questions at once."""

ISSUE_CLASSIFIER_PROMPT = """You are a customer support agent helping with device issues.

CURRENT STAGE: Issue classification
CUSTOMER INFO: Warranty status is {warranty_status}

At this step, you need to:
1. Ask the customer to describe their issue
2. Determine if it's a hardware issue (physical damage, broken parts) or software issue (app crashes, performance)
3. Use record_issue_type to record the classification and move to the next step

If unclear, ask clarifying questions before classifying."""

RESOLUTION_SPECIALIST_PROMPT = """You are a customer support agent helping with device issues.

CURRENT STAGE: Resolution
CUSTOMER INFO: Warranty status is {warranty_status}, issue type is {issue_type}

At this step, you need to:
1. For SOFTWARE issues: provide troubleshooting steps using provide_solution
2. For HARDWARE issues:
   - If IN WARRANTY: explain warranty repair process using provide_solution
   - If OUT OF WARRANTY: escalate_to_human for paid repair options

Be specific and helpful in your solutions."""
```

然后用字典把步骤名称映射到其配置：

```python
# Step configuration: maps step name to (prompt, tools, required_state)
STEP_CONFIG = {
    "warranty_collector": {
        "prompt": WARRANTY_COLLECTOR_PROMPT,
        "tools": [record_warranty_status],
        "requires": [],
    },
    "issue_classifier": {
        "prompt": ISSUE_CLASSIFIER_PROMPT,
        "tools": [record_issue_type],
        "requires": ["warranty_status"],
    },
    "resolution_specialist": {
        "prompt": RESOLUTION_SPECIALIST_PROMPT,
        "tools": [provide_solution, escalate_to_human],
        "requires": ["warranty_status", "issue_type"],
    },
}
```

这种基于字典的配置易于：

* 一目了然地看到所有步骤
* 添加新步骤（只需增加一条记录）
* 理解工作流依赖关系（`requires` 字段）
* 使用带状态变量的提示词模板（例如 `{warranty_status}`）

## 4. 创建基于步骤的中间件

创建从状态中读取 `current_step` 并应用相应配置的中间件。我们将使用 `@wrap_model_call` 装饰器实现简洁的方案：

```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@wrap_model_call
def apply_step_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """Configure agent behavior based on the current step."""
    # Get current step (defaults to warranty_collector for first interaction)
    current_step = request.state.get("current_step", "warranty_collector")

    # Look up step configuration
    stage_config = STEP_CONFIG[current_step]

    # Validate required state exists
    for key in stage_config["requires"]:
        if request.state.get(key) is None:
            raise ValueError(f"{key} must be set before reaching {current_step}")

    # Format prompt with state values (supports {warranty_status}, {issue_type}, etc.)
    system_prompt = stage_config["prompt"].format(**request.state)

    # Inject system prompt and step-specific tools
    request = request.override(
        system_prompt=system_prompt,
        tools=stage_config["tools"],
    )

    return handler(request)
```

这个中间件：

1. **读取当前步骤**：从状态中获取 `current_step`（首次交互默认 `warranty_collector`）。
2. **查找配置**：在 `STEP_CONFIG` 中找到对应的条目。
3. **校验依赖**：确保所需的状态字段存在。
4. **格式化提示词**：把状态值注入提示词模板。
5. **应用配置**：覆盖系统提示词和可用工具。

`request.override()` 方法很关键——它让我们无需创建多个代理实例，就能基于状态动态改变代理的行为。

## 5. 创建代理

现在创建带基于步骤的中间件和检查点（checkpointer）的代理，以实现状态持久化：

```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

# Collect all tools from all step configurations
all_tools = [
    record_warranty_status,
    record_issue_type,
    provide_solution,
    escalate_to_human,
]

# Create the agent with step-based configuration
agent = create_agent(
    model,
    tools=all_tools,
    state_schema=SupportState,
    middleware=[apply_step_config],
    checkpointer=InMemorySaver(),
)
```

> 注意：**为什么要检查点？** 检查点（checkpointer）在多个对话回合之间维持状态。没有它，`current_step` 状态会在用户消息之间丢失，从而破坏工作流。

## 6. 测试工作流

测试完整的工作流：

```python
from langchain.messages import HumanMessage
from langchain_core.utils.uuid import uuid7

# Configuration for this conversation thread
thread_id = str(uuid7())
config = {"configurable": {"thread_id": thread_id}}

# Turn 1: Initial message - starts with warranty_collector step
print("=== Turn 1: Warranty Collection ===")
result = agent.invoke(
    {"messages": [HumanMessage("Hi, my phone screen is cracked")]},
    config
)
for msg in result['messages']:
    msg.pretty_print()

# Turn 2: User responds about warranty
print("\n=== Turn 2: Warranty Response ===")
result = agent.invoke(
    {"messages": [HumanMessage("Yes, it's still under warranty")]},
    config
)
for msg in result['messages']:
    msg.pretty_print()
print(f"Current step: {result.get('current_step')}")

# Turn 3: User describes the issue
print("\n=== Turn 3: Issue Description ===")
result = agent.invoke(
    {"messages": [HumanMessage("The screen is physically cracked from dropping it")]},
    config
)
for msg in result['messages']:
    msg.pretty_print()
print(f"Current step: {result.get('current_step')}")

# Turn 4: Resolution
print("\n=== Turn 4: Resolution ===")
result = agent.invoke(
    {"messages": [HumanMessage("What should I do?")]},
    config
)
for msg in result['messages']:
    msg.pretty_print()
```

预期的流程：

1. **保修验证步骤**：询问保修状态
2. **问题分类步骤**：询问问题详情，判断为硬件问题
3. **解决方案步骤**：提供保修维修指导

## 7. 理解状态转换

让我们跟踪每一轮发生的情况：

### 第 1 轮：初始消息

```python
{
    "messages": [HumanMessage("Hi, my phone screen is cracked")],
    "current_step": "warranty_collector"  # Default value
}
```

中间件应用：

* 系统提示词：`WARRANTY_COLLECTOR_PROMPT`
* 工具：`[record_warranty_status]`

### 第 2 轮：保修状态记录后

工具调用：`record_warranty_status("in_warranty")` 返回：

```python
Command(update={
    "warranty_status": "in_warranty",
    "current_step": "issue_classifier"  # State transition!
})
```

下一轮，中间件应用：

* 系统提示词：`ISSUE_CLASSIFIER_PROMPT`（以 `warranty_status="in_warranty"` 格式化）
* 工具：`[record_issue_type]`

### 第 3 轮：问题分类后

工具调用：`record_issue_type("hardware")` 返回：

```python
Command(update={
    "issue_type": "hardware",
    "current_step": "resolution_specialist"  # State transition!
})
```

下一轮，中间件应用：

* 系统提示词：`RESOLUTION_SPECIALIST_PROMPT`（以 `warranty_status` 和 `issue_type` 格式化）
* 工具：`[provide_solution, escalate_to_human]`

关键洞察：**工具通过更新 `current_step` 驱动工作流**，**中间件通过在下轮应用相应配置作出响应**。

## 8. 管理消息历史

随着代理在步骤间推进，消息历史会不断增长。使用[摘要中间件](/oss/python/langchain/short-term-memory#summarize-messages)压缩较早的消息，同时保留对话上下文：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model,
    tools=all_tools,
    state_schema=SupportState,
    middleware=[
        apply_step_config,
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger=("tokens", 4000),
            keep=("messages", 10)
        )
    ],
    checkpointer=InMemorySaver(),
)
```

有关其他内存管理技术，请参阅[短期记忆指南](/oss/python/langchain/short-term-memory)。

## 9. 增加灵活性：回退

有些工作流需要允许用户返回之前的步骤来更正信息（例如修改保修状态或问题分类）。但并非所有转换都合理——例如，退款一旦处理完毕，通常就无法回退。对于这个客服工作流，我们将添加工具以返回保修验证和问题分类步骤。

> 提示：如果你的工作流需要在大多数步骤之间任意转换，请考虑是否真的需要结构化工作流。此模式最适合步骤遵循清晰的顺序推进、仅偶尔为更正而向后回退的场景。

为解决方案步骤添加"回退"工具：

```python
@tool
def go_back_to_warranty() -> Command:
    """Go back to warranty verification step."""
    return Command(update={"current_step": "warranty_collector"})

@tool
def go_back_to_classification() -> Command:
    """Go back to issue classification step."""
    return Command(update={"current_step": "issue_classifier"})

# Update the resolution_specialist configuration to include these tools
STEP_CONFIG["resolution_specialist"]["tools"].extend([
    go_back_to_warranty,
    go_back_to_classification
])
```

更新解决方案专家的提示词以提及这些工具：

```python
RESOLUTION_SPECIALIST_PROMPT = """You are a customer support agent helping with device issues.

CURRENT STAGE: Resolution
CUSTOMER INFO: Warranty status is {warranty_status}, issue type is {issue_type}

At this step, you need to:
1. For SOFTWARE issues: provide troubleshooting steps using provide_solution
2. For HARDWARE issues:
   - If IN WARRANTY: explain warranty repair process using provide_solution
   - If OUT OF WARRANTY: escalate_to_human for paid repair options

If the customer indicates any information was wrong, use:
- go_back_to_warranty to correct warranty status
- go_back_to_classification to correct issue type

Be specific and helpful in your solutions."""
```

现在代理可以处理更正了：

```python
result = agent.invoke(
    {"messages": [HumanMessage("Actually, I made a mistake - my device is out of warranty")]},
    config
)
# Agent will call go_back_to_warranty and restart the warranty verification step
```

## 完整示例

以下是一个可直接运行的完整脚本：

**完整代码**

```python
"""
Customer Support State Machine Example

This example demonstrates the state machine pattern.
A single agent dynamically changes its behavior based on the current_step state,
creating a state machine for sequential information collection.
"""

from langchain_core.utils.uuid import uuid7

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from typing import Callable, Literal
from typing_extensions import NotRequired

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse, SummarizationMiddleware
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, ToolMessage
from langchain.tools import tool, ToolRuntime

model = init_chat_model("google_genai:gemini-3.6-flash")

# Define the possible workflow steps
SupportStep = Literal["warranty_collector", "issue_classifier", "resolution_specialist"]

class SupportState(AgentState):
    """State for customer support workflow."""

    current_step: NotRequired[SupportStep]
    warranty_status: NotRequired[Literal["in_warranty", "out_of_warranty"]]
    issue_type: NotRequired[Literal["hardware", "software"]]

@tool
def record_warranty_status(
    status: Literal["in_warranty", "out_of_warranty"],
    runtime: ToolRuntime[None, SupportState],
) -> Command:
    """Record the customer's warranty status and transition to issue classification."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Warranty status recorded as: {status}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "warranty_status": status,
            "current_step": "issue_classifier",
        }
    )

@tool
def record_issue_type(
    issue_type: Literal["hardware", "software"],
    runtime: ToolRuntime[None, SupportState],
) -> Command:
    """Record the type of issue and transition to resolution specialist."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Issue type recorded as: {issue_type}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "issue_type": issue_type,
            "current_step": "resolution_specialist",
        }
    )

@tool
def escalate_to_human(reason: str) -> str:
    """Escalate the case to a human support specialist."""
    # In a real system, this would create a ticket, notify staff, etc.
    return f"Escalating to human support. Reason: {reason}"

@tool
def provide_solution(solution: str) -> str:
    """Provide a solution to the customer's issue."""
    return f"Solution provided: {solution}"

# Define prompts as constants
WARRANTY_COLLECTOR_PROMPT = """You are a customer support agent helping with device issues.

CURRENT STEP: Warranty verification

At this step, you need to:
1. Greet the customer warmly
2. Ask if their device is under warranty
3. Use record_warranty_status to record their response and move to the next step

Be conversational and friendly. Don't ask multiple questions at once."""

ISSUE_CLASSIFIER_PROMPT = """You are a customer support agent helping with device issues.

CURRENT STEP: Issue classification
CUSTOMER INFO: Warranty status is {warranty_status}

At this step, you need to:
1. Ask the customer to describe their issue
2. Determine if it's a hardware issue (physical damage, broken parts) or software issue (app crashes, performance)
3. Use record_issue_type to record the classification and move to the next step

If unclear, ask clarifying questions before classifying."""

RESOLUTION_SPECIALIST_PROMPT = """You are a customer support agent helping with device issues.

CURRENT STEP: Resolution
CUSTOMER INFO: Warranty status is {warranty_status}, issue type is {issue_type}

At this step, you need to:
1. For SOFTWARE issues: provide troubleshooting steps using provide_solution
2. For HARDWARE issues:
   - If IN WARRANTY: explain warranty repair process using provide_solution
   - If OUT OF WARRANTY: escalate_to_human for paid repair options

Be specific and helpful in your solutions."""

# Step configuration: maps step name to (prompt, tools, required_state)
STEP_CONFIG = {
    "warranty_collector": {
        "prompt": WARRANTY_COLLECTOR_PROMPT,
        "tools": [record_warranty_status],
        "requires": [],
    },
    "issue_classifier": {
        "prompt": ISSUE_CLASSIFIER_PROMPT,
        "tools": [record_issue_type],
        "requires": ["warranty_status"],
    },
    "resolution_specialist": {
        "prompt": RESOLUTION_SPECIALIST_PROMPT,
        "tools": [provide_solution, escalate_to_human],
        "requires": ["warranty_status", "issue_type"],
    },
}

@wrap_model_call
def apply_step_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """Configure agent behavior based on the current step."""
    # Get current step (defaults to warranty_collector for first interaction)
    current_step = request.state.get("current_step", "warranty_collector")

    # Look up step configuration
    step_config = STEP_CONFIG[current_step]

    # Validate required state exists
    for key in step_config["requires"]:
        if request.state.get(key) is None:
            raise ValueError(f"{key} must be set before reaching {current_step}")

    # Format prompt with state values
    system_prompt = step_config["prompt"].format(**request.state)

    # Inject system prompt and step-specific tools
    request = request.override(
        system_prompt=system_prompt,
        tools=step_config["tools"],
    )

    return handler(request)

# Collect all tools from all step configurations
all_tools = [
    record_warranty_status,
    record_issue_type,
    provide_solution,
    escalate_to_human,
]

# Create the agent with step-based configuration and summarization
agent = create_agent(
    model,
    tools=all_tools,
    state_schema=SupportState,
    middleware=[
        apply_step_config,
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger=("tokens", 4000),
            keep=("messages", 10)
        )
    ],
    checkpointer=InMemorySaver(),
)

# ============================================================================
# Test the workflow
# ============================================================================

if __name__ == "__main__":
    thread_id = str(uuid7())
    config = {"configurable": {"thread_id": thread_id}}

    result = agent.invoke(
        {"messages": [HumanMessage("Hi, my phone screen is cracked")]},
        config
    )

    result = agent.invoke(
        {"messages": [HumanMessage("Yes, it's still under warranty")]},
        config
    )

    result = agent.invoke(
        {"messages": [HumanMessage("The screen is physically cracked from dropping it")]},
        config
    )

    result = agent.invoke(
        {"messages": [HumanMessage("What should I do?")]},
        config
    )
    for msg in result['messages']:
        msg.pretty_print()
```

## 后续步骤

* 了解[子代理模式](/oss/python/langchain/multi-agent/subagents-personal-assistant)以实现集中式编排
* 探索[中间件](/oss/python/langchain/middleware)以获得更多动态行为
* 阅读[多代理概览](/oss/python/langchain/multi-agent)以比较各种模式
* 使用 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-multi-agent-handoffs-customer-support) 调试和监控你的多代理系统

---

# 用路由构建多源知识库

## 概述

**路由模式（router pattern）** 是一种[多代理](/oss/python/langchain/multi-agent)架构：路由步骤对输入进行分类，并将其导向专用代理，最终把结果综合成一个合并后的响应。当你的组织知识分散在多个不同的**垂直域**（separate knowledge domains，即各自需要拥有专用工具和提示词的独立知识领域）时，这种模式最为适用。

在本教程中，你将构建一个多源知识库路由，通过一个真实的企业场景展示这些优势。系统将协调三个专家：

* 一个 **GitHub 代理**，负责搜索代码、issue 和 pull request。
* 一个 **Notion 代理**，负责搜索内部文档和 wiki。
* 一个 **Slack 代理**，负责搜索相关线程和讨论。

当用户询问"How do I authenticate API requests?"时，路由会把查询分解为针对各来源的子问题，并行路由到相关代理，并将结果综合成一个连贯的答案。

> 流程图：查询 → 分类 → 并行分发到 GitHub/Notion/Slack 代理 → 综合 → 合并后的答案。

### 为什么使用路由？

路由模式提供若干优势：

* **并行执行**：同时查询多个来源，相比顺序方式降低延迟。
* **专用代理**：每个垂直域拥有针对其领域优化的聚焦工具和提示词。
* **选择性路由**：并非每个查询都需要所有来源——路由会智能地选择相关的垂直域。
* **针对性的子问题**：每个代理收到为其领域量身定制的问题，提升结果质量。
* **干净的综合**：来自多个来源的结果被合并为单一连贯的响应。

### 概念

我们将涵盖以下概念：

* [多代理系统](/oss/python/langchain/multi-agent)
* 用于工作流编排的 [StateGraph](/oss/python/langgraph/graph-api)
* 用于并行执行的 [Send API](/oss/python/langgraph/graph-api#send)

> 提示：**路由 vs 子代理**：[子代理模式](/oss/python/langchain/multi-agent/subagents)也可以路由到多个代理。当你需要专门的预处理、自定义路由逻辑，或希望对并行执行有显式控制时，使用路由模式。当你希望让 LLM 动态决定调用哪些代理时，使用子代理模式。

## 设置

### 安装

本教程需要 `langchain` 和 `langgraph` 包：

**pip**
```bash
pip install langchain langgraph
```

**uv**
```bash
uv add langchain langgraph
```

**conda**
```bash
conda install langchain langgraph -c conda-forge
```

更多详情请参阅[安装指南](/oss/python/langchain/install)。

### LangSmith

设置 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-multi-agent-router-knowledge-base) 以查看代理内部发生的情况。然后设置以下环境变量：

**Shell**
```bash
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="..."
```

**Python**
```python
import getpass
import os

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = getpass.getpass()
```

### 选择 LLM

从 LangChain 的集成套件中选择一个聊天模型：

👉 阅读 [Google GenAI 聊天模型集成文档](/oss/python/integrations/chat/google_generative_ai/)

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

**pip**
```bash
pip install -U "langchain[google-genai]"
```

**uv**
```bash
uv add "langchain[google-genai]"
```

**init_chat_model**
```python
import os
from langchain.chat_models import init_chat_model

os.environ["GOOGLE_API_KEY"] = "..."

model = init_chat_model("google_genai:gemini-3.6-flash")
```

**Model Class**
```python
import os
from langchain_google_genai import ChatGoogleGenerativeAI

os.environ["GOOGLE_API_KEY"] = "..."

model = ChatGoogleGenerativeAI(model="gemini-3.6-flash")
```

## 1. 定义状态

首先，定义状态模式（state schema）。我们使用三种类型：

* **`AgentInput`**：传递给每个子代理的简单状态（只是一个查询）
* **`AgentOutput`**：每个子代理返回的结果（来源名称 + 结果）
* **`RouterState`**：主工作流状态，跟踪查询、分类、结果和最终答案

```python
from typing import Annotated, Literal, TypedDict
import operator

class AgentInput(TypedDict):
    """Simple input state for each subagent."""
    query: str

class AgentOutput(TypedDict):
    """Output from each subagent."""
    source: str
    result: str

class Classification(TypedDict):
    """A single routing decision: which agent to call with what query."""
    source: Literal["github", "notion", "slack"]
    query: str

class RouterState(TypedDict):
    query: str
    classifications: list[Classification]
    results: Annotated[list[AgentOutput], operator.add]  # Reducer collects parallel results
    final_answer: str
```

`results` 字段使用**reducer**（Python 中是 `operator.add`，JS 中是 concat 函数）把并行代理执行的结果收集到单个列表中。

## 2. 为每个垂直域定义工具

为每个知识领域创建工具。在生产系统中，这些工具会调用真实的 API。在本教程中，我们使用返回模拟数据的桩实现。我们在 3 个垂直域中定义了 7 个工具：GitHub（搜索代码、issue、PR）、Notion（搜索文档、获取页面）和 Slack（搜索消息、获取线程）。

```python
from langchain.tools import tool

@tool
def search_code(query: str, repo: str = "main") -> str:
    """Search code in GitHub repositories."""
    return f"Found code matching '{query}' in {repo}: authentication middleware in src/auth.py"

@tool
def search_issues(query: str) -> str:
    """Search GitHub issues and pull requests."""
    return f"Found 3 issues matching '{query}': #142 (API auth docs), #89 (OAuth flow), #203 (token refresh)"

@tool
def search_prs(query: str) -> str:
    """Search pull requests for implementation details."""
    return f"PR #156 added JWT authentication, PR #178 updated OAuth scopes"

@tool
def search_notion(query: str) -> str:
    """Search Notion workspace for documentation."""
    return f"Found documentation: 'API Authentication Guide' - covers OAuth2 flow, API keys, and JWT tokens"

@tool
def get_page(page_id: str) -> str:
    """Get a specific Notion page by ID."""
    return f"Page content: Step-by-step authentication setup instructions"

@tool
def search_slack(query: str) -> str:
    """Search Slack messages and threads."""
    return f"Found discussion in #engineering: 'Use Bearer tokens for API auth, see docs for refresh flow'"

@tool
def get_thread(thread_id: str) -> str:
    """Get a specific Slack thread."""
    return f"Thread discusses best practices for API key rotation"
```

## 3. 创建专用代理

为每个垂直域创建一个代理。每个代理都有领域专用的工具和针对其知识来源优化的提示词。三个代理遵循相同的模式——只有工具和系统提示词不同。

```python
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

model = init_chat_model("openai:gpt-5.5")

github_agent = create_agent(
    model,
    tools=[search_code, search_issues, search_prs],
    system_prompt=(
        "You are a GitHub expert. Answer questions about code, "
        "API references, and implementation details by searching "
        "repositories, issues, and pull requests."
    ),
)

notion_agent = create_agent(
    model,
    tools=[search_notion, get_page],
    system_prompt=(
        "You are a Notion expert. Answer questions about internal "
        "processes, policies, and team documentation by searching "
        "the organization's Notion workspace."
    ),
)

slack_agent = create_agent(
    model,
    tools=[search_slack, get_thread],
    system_prompt=(
        "You are a Slack expert. Answer questions by searching "
        "relevant threads and discussions where team members have "
        "shared knowledge and solutions."
    ),
)
```

## 4. 构建路由工作流

现在使用 StateGraph 构建路由工作流。工作流有四个主要步骤：

1. **分类（Classify）**：分析查询并确定调用哪些代理、带什么子问题
2. **路由（Route）**：使用 `Send` 并行分发到选定的代理
3. **查询代理（Query agents）**：每个代理接收简单的 `AgentInput` 并返回 `AgentOutput`
4. **综合（Synthesize）**：把收集到的结果合并为连贯的响应

```python
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

router_llm = init_chat_model("openai:gpt-5.4-mini")

# Define structured output schema for the classifier
class ClassificationResult(BaseModel):
    """Result of classifying a user query into agent-specific sub-questions."""
    classifications: list[Classification] = Field(
        description="List of agents to invoke with their targeted sub-questions"
    )

def classify_query(state: RouterState) -> dict:
    """Classify query and determine which agents to invoke."""
    structured_llm = router_llm.with_structured_output(ClassificationResult)

    result = structured_llm.invoke([
        {
            "role": "system",
            "content": """Analyze this query and determine which knowledge bases to consult.
For each relevant source, generate a targeted sub-question optimized for that source.

Available sources:
- github: Code, API references, implementation details, issues, pull requests
- notion: Internal documentation, processes, policies, team wikis
- slack: Team discussions, informal knowledge sharing, recent conversations

Return ONLY the sources that are relevant to the query. Each source should have
a targeted sub-question optimized for that specific knowledge domain.

Example for "How do I authenticate API requests?":
- github: "What authentication code exists? Search for auth middleware, JWT handling"
- notion: "What authentication documentation exists? Look for API auth guides"
(slack omitted because it's not relevant for this technical question)"""
        },
        {"role": "user", "content": state["query"]}
    ])

    return {"classifications": result.classifications}

def route_to_agents(state: RouterState) -> list[Send]:
    """Fan out to agents based on classifications."""
    return [
        Send(c["source"], {"query": c["query"]})
        for c in state["classifications"]
    ]

def query_github(state: AgentInput) -> dict:
    """Query the GitHub agent."""
    result = github_agent.invoke({
        "messages": [{"role": "user", "content": state["query"]}]
    })
    return {"results": [{"source": "github", "result": result["messages"][-1].content}]}

def query_notion(state: AgentInput) -> dict:
    """Query the Notion agent."""
    result = notion_agent.invoke({
        "messages": [{"role": "user", "content": state["query"]}]
    })
    return {"results": [{"source": "notion", "result": result["messages"][-1].content}]}

def query_slack(state: AgentInput) -> dict:
    """Query the Slack agent."""
    result = slack_agent.invoke({
        "messages": [{"role": "user", "content": state["query"]}]
    })
    return {"results": [{"source": "slack", "result": result["messages"][-1].content}]}

def synthesize_results(state: RouterState) -> dict:
    """Combine results from all agents into a coherent answer."""
    if not state["results"]:
        return {"final_answer": "No results found from any knowledge source."}

    # Format results for synthesis
    formatted = [
        f"**From {r['source'].title()}:**\n{r['result']}"
        for r in state["results"]
    ]

    synthesis_response = router_llm.invoke([
        {
            "role": "system",
            "content": f"""Synthesize these search results to answer the original question: "{state['query']}"

- Combine information from multiple sources without redundancy
- Highlight the most relevant and actionable information
- Note any discrepancies between sources
- Keep the response concise and well-organized"""
        },
        {"role": "user", "content": "\n\n".join(formatted)}
    ])

    return {"final_answer": synthesis_response.content}
```

## 5. 编译工作流

现在通过连接节点和边来组装工作流。关键在于使用 `add_conditional_edges` 配合路由函数来实现并行执行：

```python
workflow = (
    StateGraph(RouterState)
    .add_node("classify", classify_query)
    .add_node("github", query_github)
    .add_node("notion", query_notion)
    .add_node("slack", query_slack)
    .add_node("synthesize", synthesize_results)
    .add_edge(START, "classify")
    .add_conditional_edges("classify", route_to_agents, ["github", "notion", "slack"])
    .add_edge("github", "synthesize")
    .add_edge("notion", "synthesize")
    .add_edge("slack", "synthesize")
    .add_edge("synthesize", END)
    .compile()
)
```

`add_conditional_edges` 调用通过 `route_to_agents` 函数把 classify 节点连接到各代理节点。当 `route_to_agents` 返回多个 `Send` 对象时，这些节点会并行执行。

## 6. 使用路由

用跨越多个知识领域的查询测试你的路由：

```python
result = workflow.invoke({
    "query": "How do I authenticate API requests?"
})

print("Original query:", result["query"])
print("\nClassifications:")
for c in result["classifications"]:
    print(f"  {c['source']}: {c['query']}")
print("\n" + "=" * 60 + "\n")
print("Final Answer:")
print(result["final_answer"])
```

预期输出：

```
Original query: How do I authenticate API requests?

Classifications:
  github: What authentication code exists? Search for auth middleware, JWT handling
  notion: What authentication documentation exists? Look for API auth guides

============================================================

Final Answer:
To authenticate API requests, you have several options:

1. **JWT Tokens**: The recommended approach for most use cases.
   Implementation details are in `src/auth.py` (PR #156).

2. **OAuth2 Flow**: For third-party integrations, follow the OAuth2
   flow documented in Notion's 'API Authentication Guide'.

3. **API Keys**: For server-to-server communication, use Bearer tokens
   in the Authorization header.

For token refresh handling, see issue #203 and PR #178 for the latest
OAuth scope updates.
```

路由分析了查询，将其分类以确定调用哪些代理（GitHub 和 Notion，但这个技术问题不涉及 Slack），并行查询了两个代理，并把结果综合成一个连贯的答案。

## 7. 理解架构

路由工作流遵循清晰的模式：

### 分类阶段

`classify_query` 函数使用**结构化输出**分析用户查询并确定调用哪些代理。路由智能就在这里：

* 使用 Pydantic 模型（Python）或 Zod 模式（JS）确保输出有效
* 返回 `Classification` 对象列表，每个对象包含 `source` 和针对性的 `query`
* 只包含相关的来源——不相关的直接省略

这种结构化方法比自由形式的 JSON 解析更可靠，也让路由逻辑显式化。

### 使用 Send 并行执行

`route_to_agents` 函数把分类结果映射为 `Send` 对象。每个 `Send` 指定目标节点和要传递的状态：

```python
# Classifications: [{"source": "github", "query": "..."}, {"source": "notion", "query": "..."}]
# Becomes:
[Send("github", {"query": "..."}), Send("notion", {"query": "..."})]
# Both agents execute simultaneously, each receiving only the query it needs
```

每个代理节点接收一个简单的 `AgentInput`，只包含 `query` 字段——而不是完整的路由状态。这让接口保持干净和显式。

### 使用 reducer 收集结果

代理结果通过**reducer**回流到主状态。每个代理返回：

```python
{"results": [{"source": "github", "result": "..."}]}
```

reducer（Python 中的 `operator.add`）会连接这些列表，把所有并行结果收集到 `state["results"]`。

### 综合阶段

所有代理完成后，`synthesize_results` 函数遍历收集到的结果：

* 等待所有并行分支完成（LangGraph 自动处理）
* 引用原始查询，确保答案回应了用户的提问
* 合并所有来源的信息而不冗余

> 注意：**部分结果**：在本教程中，所有选定的代理都必须完成之后才进行综合。

## 8. 完整可运行示例

以下是一个可直接运行的完整脚本：

**查看完整代码**

```python
"""
Multi-Source Knowledge Router Example

This example demonstrates the router pattern for multi-agent systems.
A router classifies queries, routes them to specialized agents in parallel,
and synthesizes results into a combined response.
"""

import operator
from typing import Annotated, Literal, TypedDict

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from pydantic import BaseModel, Field

# State definitions
class AgentInput(TypedDict):
    """Simple input state for each subagent."""
    query: str

class AgentOutput(TypedDict):
    """Output from each subagent."""
    source: str
    result: str

class Classification(TypedDict):
    """A single routing decision: which agent to call with what query."""
    source: Literal["github", "notion", "slack"]
    query: str

class RouterState(TypedDict):
    query: str
    classifications: list[Classification]
    results: Annotated[list[AgentOutput], operator.add]
    final_answer: str

# Structured output schema for classifier
class ClassificationResult(BaseModel):
    """Result of classifying a user query into agent-specific sub-questions."""
    classifications: list[Classification] = Field(
        description="List of agents to invoke with their targeted sub-questions"
    )

# Tools
@tool
def search_code(query: str, repo: str = "main") -> str:
    """Search code in GitHub repositories."""
    return f"Found code matching '{query}' in {repo}: authentication middleware in src/auth.py"

@tool
def search_issues(query: str) -> str:
    """Search GitHub issues and pull requests."""
    return f"Found 3 issues matching '{query}': #142 (API auth docs), #89 (OAuth flow), #203 (token refresh)"

@tool
def search_prs(query: str) -> str:
    """Search pull requests for implementation details."""
    return f"PR #156 added JWT authentication, PR #178 updated OAuth scopes"

@tool
def search_notion(query: str) -> str:
    """Search Notion workspace for documentation."""
    return f"Found documentation: 'API Authentication Guide' - covers OAuth2 flow, API keys, and JWT tokens"

@tool
def get_page(page_id: str) -> str:
    """Get a specific Notion page by ID."""
    return f"Page content: Step-by-step authentication setup instructions"

@tool
def search_slack(query: str) -> str:
    """Search Slack messages and threads."""
    return f"Found discussion in #engineering: 'Use Bearer tokens for API auth, see docs for refresh flow'"

@tool
def get_thread(thread_id: str) -> str:
    """Get a specific Slack thread."""
    return f"Thread discusses best practices for API key rotation"

# Models and agents
model = init_chat_model("openai:gpt-5.5")
router_llm = init_chat_model("openai:gpt-5.4-mini")

github_agent = create_agent(
    model,
    tools=[search_code, search_issues, search_prs],
    system_prompt=(
        "You are a GitHub expert. Answer questions about code, "
        "API references, and implementation details by searching "
        "repositories, issues, and pull requests."
    ),
)

notion_agent = create_agent(
    model,
    tools=[search_notion, get_page],
    system_prompt=(
        "You are a Notion expert. Answer questions about internal "
        "processes, policies, and team documentation by searching "
        "the organization's Notion workspace."
    ),
)

slack_agent = create_agent(
    model,
    tools=[search_slack, get_thread],
    system_prompt=(
        "You are a Slack expert. Answer questions by searching "
        "relevant threads and discussions where team members have "
        "shared knowledge and solutions."
    ),
)

# Workflow nodes
def classify_query(state: RouterState) -> dict:
    """Classify query and determine which agents to invoke."""
    structured_llm = router_llm.with_structured_output(ClassificationResult)

    result = structured_llm.invoke([
        {
            "role": "system",
            "content": """Analyze this query and determine which knowledge bases to consult.
For each relevant source, generate a targeted sub-question optimized for that source.

Available sources:
- github: Code, API references, implementation details, issues, pull requests
- notion: Internal documentation, processes, policies, team wikis
- slack: Team discussions, informal knowledge sharing, recent conversations

Return ONLY the sources that are relevant to the query."""
        },
        {"role": "user", "content": state["query"]}
    ])

    return {"classifications": result.classifications}

def route_to_agents(state: RouterState) -> list[Send]:
    """Fan out to agents based on classifications."""
    return [
        Send(c["source"], {"query": c["query"]})
        for c in state["classifications"]
    ]

def query_github(state: AgentInput) -> dict:
    """Query the GitHub agent."""
    result = github_agent.invoke({
        "messages": [{"role": "user", "content": state["query"]}]
    })
    return {"results": [{"source": "github", "result": result["messages"][-1].content}]}

def query_notion(state: AgentInput) -> dict:
    """Query the Notion agent."""
    result = notion_agent.invoke({
        "messages": [{"role": "user", "content": state["query"]}]
    })
    return {"results": [{"source": "notion", "result": result["messages"][-1].content}]}

def query_slack(state: AgentInput) -> dict:
    """Query the Slack agent."""
    result = slack_agent.invoke({
        "messages": [{"role": "user", "content": state["query"]}]
    })
    return {"results": [{"source": "slack", "result": result["messages"][-1].content}]}

def synthesize_results(state: RouterState) -> dict:
    """Combine results from all agents into a coherent answer."""
    if not state["results"]:
        return {"final_answer": "No results found from any knowledge source."}

    formatted = [
        f"**From {r['source'].title()}:**\n{r['result']}"
        for r in state["results"]
    ]

    synthesis_response = router_llm.invoke([
        {
            "role": "system",
            "content": f"""Synthesize these search results to answer the original question: "{state['query']}"

- Combine information from multiple sources without redundancy
- Highlight the most relevant and actionable information
- Note any discrepancies between sources
- Keep the response concise and well-organized"""
        },
        {"role": "user", "content": "\n\n".join(formatted)}
    ])

    return {"final_answer": synthesis_response.content}

# Build workflow
workflow = (
    StateGraph(RouterState)
    .add_node("classify", classify_query)
    .add_node("github", query_github)
    .add_node("notion", query_notion)
    .add_node("slack", query_slack)
    .add_node("synthesize", synthesize_results)
    .add_edge(START, "classify")
    .add_conditional_edges("classify", route_to_agents, ["github", "notion", "slack"])
    .add_edge("github", "synthesize")
    .add_edge("notion", "synthesize")
    .add_edge("slack", "synthesize")
    .add_edge("synthesize", END)
    .compile()
)

if __name__ == "__main__":
    result = workflow.invoke({
        "query": "How do I authenticate API requests?"
    })

    print("Original query:", result["query"])
    print("\nClassifications:")
    for c in result["classifications"]:
        print(f"  {c['source']}: {c['query']}")
    print("\n" + "=" * 60 + "\n")
    print("Final Answer:")
    print(result["final_answer"])
```

## 9. 进阶：有状态路由

我们目前构建的路由是**无状态的**（每个请求独立处理，调用之间没有记忆）。对于多轮对话，你需要**有状态**的方法。

### 工具包装器方法

为对话添加记忆的最简单方法，是把无状态的路由包装成一个工具，供对话代理调用：

```python
from langgraph.checkpoint.memory import InMemorySaver

@tool
def search_knowledge_base(query: str) -> str:
    """Search across multiple knowledge sources (GitHub, Notion, Slack).

    Use this to find information about code, documentation, or team discussions.
    """
    result = workflow.invoke({"query": query})
    return result["final_answer"]

conversational_agent = create_agent(
    model,
    tools=[search_knowledge_base],
    system_prompt=(
        "You are a helpful assistant that answers questions about our organization. "
        "Use the search_knowledge_base tool to find information across our code, "
        "documentation, and team discussions."
    ),
    checkpointer=InMemorySaver(),
)
```

这种方法让路由保持无状态，而对话代理负责记忆和上下文。用户可以进行多轮对话，代理会在需要时调用路由工具。

```python
config = {"configurable": {"thread_id": "user-123"}}

result = conversational_agent.invoke(
    {"messages": [{"role": "user", "content": "How do I authenticate API requests?"}]},
    config
)
print(result["messages"][-1].content)

result = conversational_agent.invoke(
    {"messages": [{"role": "user", "content": "What about rate limiting for those endpoints?"}]},
    config
)
print(result["messages"][-1].content)
```

> 提示：大多数用例推荐使用工具包装器方法。它提供了干净的分离：路由负责多源查询，而对话代理负责上下文和记忆。

### 完整持久化方法

如果你需要路由本身维持状态——例如在路由决策中使用之前的搜索结果——可以使用[持久化](/oss/python/langchain/short-term-memory)在路由层面存储消息历史。

> 警告：**有状态路由会增加复杂性。** 当跨回合路由到不同代理时，如果各代理的语气或提示词不同，对话可能会显得不一致。请考虑改用[交接模式](/oss/python/langchain/multi-agent/handoffs)或[子代理模式](/oss/python/langchain/multi-agent/subagents)——两者都为涉及不同代理的多轮对话提供了更清晰的语义。

## 10. 关键要点

当以下条件成立时，路由模式表现出色：

* **不同的垂直域**：各自需要专用工具和提示词的独立知识领域
* **并行查询需求**：同时查询多个来源有益的问题
* **综合需求**：来自多个来源的结果需要合并为连贯的响应

该模式有三个阶段：**分解**（分析查询并生成针对性的子问题）、**路由**（并行执行查询）和**综合**（合并结果）。

> 提示：**何时使用路由模式**
>
> 当你拥有多个独立的知识来源、需要低延迟的并行查询，并希望对路由逻辑有显式控制时，使用路由模式。
>
> 对于需要动态选择工具的简单场景，请考虑[子代理模式](/oss/python/langchain/multi-agent/subagents)。对于需要代理与用户顺序对话的工作流，请考虑[交接](/oss/python/langchain/multi-agent/handoffs)。

## 后续步骤

* 了解[交接](/oss/python/langchain/multi-agent/handoffs)以实现代理间对话
* 探索[子代理模式](/oss/python/langchain/multi-agent/subagents-personal-assistant)以实现集中式编排
* 阅读[多代理概览](/oss/python/langchain/multi-agent)以比较不同模式
* 使用 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-multi-agent-router-knowledge-base) 调试和监控你的路由

---

# 用按需技能构建 SQL 助手

本教程展示如何使用**渐进式披露（progressive disclosure）**——一种按需而非预先加载信息的上下文管理技术——来实现**技能（skills）**（基于提示词的专业指令单元）。代理通过工具调用加载技能，而不是动态更改系统提示词，只发现并加载每个任务所需的技能。

**用例：** 想象构建一个代理，帮助大型企业内不同业务线编写 SQL 查询。你的组织可能为每条业务线设置独立的数据存储，也可能是一个包含数千张表的单体数据库。无论哪种方式，预先加载所有模式都会压垮上下文窗口。渐进式披露通过在需要时只加载相关模式来解决这个问题。这种架构还使不同的产品负责人和利益相关者能够独立地为其业务线贡献和维护技能。

**你将构建的内容：** 一个带有两个技能（销售分析 sales analytics 和库存管理 inventory management）的 SQL 查询助手。代理在其系统提示词中看到轻量的技能描述，然后仅在相关时才通过工具调用加载完整的数据库模式和业务逻辑。

> 注意：有关带查询执行、错误纠正和验证的 SQL 代理完整示例，请参阅我们的 [SQL 代理教程](/oss/python/langchain/sql-agent)。本教程聚焦于可应用于任何领域的渐进式披露模式。

> 提示：渐进式披露由 Anthropic 推广，作为构建可扩展代理技能系统的一种技术。这种方法使用三级架构（元数据 → 核心内容 → 详细资源），代理只在需要时加载信息。有关该技术的更多信息，请参阅 [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)。

## 工作原理

以下是用户请求 SQL 查询时的流程：

> 流程图：用户请求编写 SQL 查询 → 代理看到技能描述（sales_analytics、inventory_management）→ 判断需要销售模式 → 调用 load_skill 加载 'sales_analytics' → 模式已加载（customers、orders 表 + 业务逻辑）→ 代理根据模式知识编写 SQL 查询 → 返回符合业务规则的有效 SQL。

**为什么用渐进式披露：**

* **减少上下文使用** —— 只加载任务所需的 2-3 个技能，而不是所有可用技能
* **支持团队自治** —— 不同团队可以独立开发专业技能（类似于其他多代理架构）
* **高效扩展** —— 添加数十或数百个技能而不会压垮上下文
* **简化对话历史** —— 单个代理、单个对话线程

**什么是技能：** 技能由 Claude Code 推广，主要是基于提示词的：针对特定业务任务的、自包含的专业指令单元。在 Claude Code 中，技能以文件系统中的目录形式暴露，通过文件操作发现。技能通过提示词引导行为，可以提供工具使用信息，或为编码代理包含可执行的示例代码。

> 提示：带渐进式披露的技能可以被视为一种 [RAG（检索增强生成）](/oss/python/deepagents/rag) 形式，每个技能是一个检索单元——尽管不一定由嵌入或关键词搜索支持，而是由浏览内容的工具支持（如文件操作，或本教程中的直接查找）。

**权衡：**

* **延迟**：按需加载技能需要额外的工具调用，这会给首次需要该技能的请求增加延迟
* **工作流控制**：基础实现依赖提示词来引导技能使用——没有自定义逻辑，你无法强制诸如"总是先尝试技能 A 再尝试技能 B"的硬约束

> 提示：**实现你自己的技能系统**
>
> 在构建自己的技能实现时（如本教程所做），核心概念是渐进式披露——按需加载信息。除此之外，你在实现上拥有充分的灵活性：
>
> * **存储**：数据库、S3、内存数据结构，或任何后端
> * **发现**：直接查找（本教程）、面向大型技能集合的 RAG、文件系统扫描，或 API 调用
> * **加载逻辑**：定制延迟特性，并添加在技能内容中搜索或对相关性排序的逻辑
> * **副作用**：定义技能加载时发生什么，例如暴露与该技能关联的工具（第 8 节会讲到）
>
> 这种灵活性让你可以针对性能、存储和工作流控制的具体需求进行优化。

## 设置

### 安装

本教程需要 `langchain` 包：

**pip**
```bash
pip install langchain
```

**uv**
```bash
uv add langchain
```

**conda**
```bash
conda install langchain -c conda-forge
```

更多详情请参阅[安装指南](/oss/python/langchain/install)。

### LangSmith

设置 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-multi-agent-skills-sql-assistant) 以查看代理内部发生的情况。然后设置以下环境变量：

**Shell**
```bash
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="..."
```

**Python**
```python
import getpass
import os

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = getpass.getpass()
```

### 选择 LLM

从 LangChain 的集成套件中选择一个聊天模型：

👉 阅读 [Google GenAI 聊天模型集成文档](/oss/python/integrations/chat/google_generative_ai/)

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

**pip**
```bash
pip install -U "langchain[google-genai]"
```

**uv**
```bash
uv add "langchain[google-genai]"
```

**init_chat_model**
```python
import os
from langchain.chat_models import init_chat_model

os.environ["GOOGLE_API_KEY"] = "..."

model = init_chat_model("google_genai:gemini-3.6-flash")
```

**Model Class**
```python
import os
from langchain_google_genai import ChatGoogleGenerativeAI

os.environ["GOOGLE_API_KEY"] = "..."

model = ChatGoogleGenerativeAI(model="gemini-3.6-flash")
```

## 1. 定义技能

首先，定义技能的结构。每个技能有一个名称、一段简短描述（显示在系统提示词中）和完整内容（按需加载）：

```python
from typing import TypedDict

class Skill(TypedDict):
    """A skill that can be progressively disclosed to the agent."""
    name: str  # Unique identifier for the skill
    description: str  # 1-2 sentence description to show in system prompt
    content: str  # Full skill content with detailed instructions
```

现在为 SQL 查询助手定义示例技能。这些技能的设计是**描述轻量**（预先展示给代理）但**内容详细**（仅在需要时加载）：

**展开查看完整的技能定义**

```python
SKILLS: list[Skill] = [
    {
        "name": "sales_analytics",
        "description": "Database schema and business logic for sales data analysis including customers, orders, and revenue.",
        "content": """# Sales Analytics Schema

## Tables

### customers
- customer_id (PRIMARY KEY)
- name
- email
- signup_date
- status (active/inactive)
- customer_tier (bronze/silver/gold/platinum)

### orders
- order_id (PRIMARY KEY)
- customer_id (FOREIGN KEY -> customers)
- order_date
- status (pending/completed/cancelled/refunded)
- total_amount
- sales_region (north/south/east/west)

### order_items
- item_id (PRIMARY KEY)
- order_id (FOREIGN KEY -> orders)
- product_id
- quantity
- unit_price
- discount_percent

## Business Logic

**Active customers**: status = 'active' AND signup_date <= CURRENT_DATE - INTERVAL '90 days'

**Revenue calculation**: Only count orders with status = 'completed'. Use total_amount from orders table, which already accounts for discounts.

**Customer lifetime value (CLV)**: Sum of all completed order amounts for a customer.

**High-value orders**: Orders with total_amount > 1000

## Example Query

-- Get top 10 customers by revenue in the last quarter
SELECT
    c.customer_id,
    c.name,
    c.customer_tier,
    SUM(o.total_amount) as total_revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'completed'
  AND o.order_date >= CURRENT_DATE - INTERVAL '3 months'
GROUP BY c.customer_id, c.name, c.customer_tier
ORDER BY total_revenue DESC
LIMIT 10;
""",
    },
    {
        "name": "inventory_management",
        "description": "Database schema and business logic for inventory tracking including products, warehouses, and stock levels.",
        "content": """# Inventory Management Schema

## Tables

### products
- product_id (PRIMARY KEY)
- product_name
- sku
- category
- unit_cost
- reorder_point (minimum stock level before reordering)
- discontinued (boolean)

### warehouses
- warehouse_id (PRIMARY KEY)
- warehouse_name
- location
- capacity

### inventory
- inventory_id (PRIMARY KEY)
- product_id (FOREIGN KEY -> products)
- warehouse_id (FOREIGN KEY -> warehouses)
- quantity_on_hand
- last_updated

### stock_movements
- movement_id (PRIMARY KEY)
- product_id (FOREIGN KEY -> products)
- warehouse_id (FOREIGN KEY -> warehouses)
- movement_type (inbound/outbound/transfer/adjustment)
- quantity (positive for inbound, negative for outbound)
- movement_date
- reference_number

## Business Logic

**Available stock**: quantity_on_hand from inventory table where quantity_on_hand > 0

**Products needing reorder**: Products where total quantity_on_hand across all warehouses is less than or equal to the product's reorder_point

**Active products only**: Exclude products where discontinued = true unless specifically analyzing discontinued items

**Stock valuation**: quantity_on_hand * unit_cost for each product

## Example Query

-- Find products below reorder point across all warehouses
SELECT
    p.product_id,
    p.product_name,
    p.reorder_point,
    SUM(i.quantity_on_hand) as total_stock,
    p.unit_cost,
    (p.reorder_point - SUM(i.quantity_on_hand)) as units_to_reorder
FROM products p
JOIN inventory i ON p.product_id = i.product_id
WHERE p.discontinued = false
GROUP BY p.product_id, p.product_name, p.reorder_point, p.unit_cost
HAVING SUM(i.quantity_on_hand) <= p.reorder_point
ORDER BY units_to_reorder DESC;
""",
    },
]
```

## 2. 创建技能加载工具

创建一个按需加载完整技能内容的工具：

```python
from langchain.tools import tool

@tool
def load_skill(skill_name: str) -> str:
    """Load the full content of a skill into the agent's context.

    Use this when you need detailed information about how to handle a specific
    type of request. This will provide you with comprehensive instructions,
    policies, and guidelines for the skill area.

    Args:
        skill_name: The name of the skill to load (e.g., "expense_reporting", "travel_booking")
    """
    # Find and return the requested skill
    for skill in SKILLS:
        if skill["name"] == skill_name:
            return f"Loaded skill: {skill_name}\n\n{skill['content']}"

    # Skill not found
    available = ", ".join(s["name"] for s in SKILLS)
    return f"Skill '{skill_name}' not found. Available skills: {available}"
```

`load_skill` 工具把完整技能内容作为字符串返回，该内容以 ToolMessage 的形式成为对话的一部分。有关创建和使用工具的更多细节，请参阅[工具指南](/oss/python/langchain/tools)。

## 3. 构建技能中间件

创建把技能描述注入系统提示词的自定义中间件。这个中间件让技能可被发现，而无需预先加载其完整内容。

> 注意：本指南演示了创建自定义中间件。有关中间件概念和模式的完整指南，请参阅[自定义中间件文档](/oss/python/langchain/middleware/custom)。

```python
from langchain.agents.middleware import ModelRequest, ModelResponse, AgentMiddleware
from langchain.messages import SystemMessage
from typing import Callable

class SkillMiddleware(AgentMiddleware):
    """Middleware that injects skill descriptions into the system prompt."""

    # Register the load_skill tool as a class variable
    tools = [load_skill]

    def __init__(self):
        """Initialize and generate the skills prompt from SKILLS."""
        # Build skills prompt from the SKILLS list
        skills_list = []
        for skill in SKILLS:
            skills_list.append(
                f"- **{skill['name']}**: {skill['description']}"
            )
        self.skills_prompt = "\n".join(skills_list)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Sync: Inject skill descriptions into system prompt."""
        # Build the skills addendum
        skills_addendum = (
            f"\n\n## Available Skills\n\n{self.skills_prompt}\n\n"
            "Use the load_skill tool when you need detailed information "
            "about handling a specific type of request."
        )

        # Append to system message content blocks
        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": skills_addendum}
        ]
        new_system_message = SystemMessage(content=new_content)
        modified_request = request.override(system_message=new_system_message)
        return handler(modified_request)
```

中间件把技能描述追加到系统提示词中，让代理知晓可用技能而无需加载其完整内容。`load_skill` 工具作为类变量注册，对代理可用。

> 注意：**生产环境考虑**：本教程为简单起见在 `__init__` 中加载技能列表。在生产系统中，你可能希望在 `before_agent` 钩子中加载技能，以便定期刷新以反映最新变化（例如添加新技能或修改现有技能时）。详见 [before_agent 钩子文档](/oss/python/langchain/middleware/custom#node-style-hooks)。

## 4. 创建支持技能的代理

现在创建带技能中间件和检查点（用于状态持久化）的代理：

```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

# Create the agent with skill support
agent = create_agent(
    model,
    system_prompt=(
        "You are a SQL query assistant that helps users "
        "write queries against business databases."
    ),
    middleware=[SkillMiddleware()],
    checkpointer=InMemorySaver(),
)
```

代理现在可以在系统提示词中看到技能描述，并可以在需要时调用 `load_skill` 获取完整的技能内容。检查点在多轮对话之间维持对话历史。

## 5. 测试渐进式披露

用一个需要特定技能知识的问题来测试代理：

```python
from langchain_core.utils.uuid import uuid7

# Configuration for this conversation thread
thread_id = str(uuid7())
config = {"configurable": {"thread_id": thread_id}}

# Ask for a SQL query
result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": (
                    "Write a SQL query to find all customers "
                    "who made orders over $1000 in the last month"
                ),
            }
        ]
    },
    config
)

# Print the conversation
for message in result["messages"]:
    if hasattr(message, 'pretty_print'):
        message.pretty_print()
    else:
        print(f"{message.type}: {message.content}")
```

预期输出：

```
================================ Human Message =================================

Write a SQL query to find all customers who made orders over $1000 in the last month
================================== Ai Message ==================================
Tool Calls:
  load_skill (call_abc123)
 Call ID: call_abc123
  Args:
    skill_name: sales_analytics
================================= Tool Message =================================
Name: load_skill

Loaded skill: sales_analytics

# Sales Analytics Schema

## Tables

### customers
- customer_id (PRIMARY KEY)
- name
- email
- signup_date
- status (active/inactive)
- customer_tier (bronze/silver/gold/platinum)

### orders
- order_id (PRIMARY KEY)
- customer_id (FOREIGN KEY -> customers)
- order_date
- status (pending/completed/cancelled/refunded)
- total_amount
- sales_region (north/south/east/west)

[... rest of schema ...]

## Business Logic

**High-value orders**: Orders with `total_amount > 1000`
**Revenue calculation**: Only count orders with `status = 'completed'`

================================== Ai Message ==================================

Here's a SQL query to find all customers who made orders over $1000 in the last month:

\`\`\`sql
SELECT DISTINCT
    c.customer_id,
    c.name,
    c.email,
    c.customer_tier
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.total_amount > 1000
  AND o.status = 'completed'
  AND o.order_date >= CURRENT_DATE - INTERVAL '1 month'
ORDER BY c.customer_id;
\`\`\`

This query:
- Joins customers with their orders
- Filters for high-value orders (>$1000) using the total_amount field
- Only includes completed orders (as per the business logic)
- Restricts to orders from the last month
- Returns distinct customers to avoid duplicates if they made multiple qualifying orders
```

代理在系统提示词中看到轻量的技能描述，识别出该问题需要销售数据库知识，调用 `load_skill("sales_analytics")` 获取完整的模式和业务逻辑，然后利用这些信息按照数据库约定写出了正确的查询。

## 6. 进阶：用自定义状态添加约束

**可选：跟踪已加载的技能并强制工具约束**

你可以添加约束，强制某些工具只在特定技能加载后才可用。这需要在自定义代理状态中跟踪已加载的技能。

#### 定义自定义状态

首先，扩展代理状态以跟踪已加载的技能：

```python
from langchain.agents.middleware import AgentState

class CustomState(AgentState):
    skills_loaded: NotRequired[list[str]]  # Track which skills have been loaded
```

#### 更新 load_skill 以修改状态

修改 `load_skill` 工具，使其在技能加载时更新状态：

```python
from langgraph.types import Command
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage

@tool
def load_skill(skill_name: str, runtime: ToolRuntime) -> Command:
    """Load the full content of a skill into the agent's context.

    Use this when you need detailed information about how to handle a specific
    type of request. This will provide you with comprehensive instructions,
    policies, and guidelines for the skill area.

    Args:
        skill_name: The name of the skill to load
    """
    # Find and return the requested skill
    for skill in SKILLS:
        if skill["name"] == skill_name:
            skill_content = f"Loaded skill: {skill_name}\n\n{skill['content']}"

            # Update state to track loaded skill
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            content=skill_content,
                            tool_call_id=runtime.tool_call_id,
                        )
                    ],
                    "skills_loaded": [skill_name],
                }
            )

    # Skill not found
    available = ", ".join(s["name"] for s in SKILLS)
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Skill '{skill_name}' not found. Available skills: {available}",
                    tool_call_id=runtime.tool_call_id,
                )
            ]
        }
    )
```

#### 创建受限工具

创建一个只有在特定技能加载后才能使用的工具：

````python
@tool
def write_sql_query(
    query: str,
    vertical: str,
    runtime: ToolRuntime,
) -> str:
    """Write and validate a SQL query for a specific business vertical.

    This tool helps format and validate SQL queries. You must load the
    appropriate skill first to understand the database schema.

    Args:
        query: The SQL query to write
        vertical: The business vertical (sales_analytics or inventory_management)
    """
    # Check if the required skill has been loaded
    skills_loaded = runtime.state.get("skills_loaded", [])

    if vertical not in skills_loaded:
        return (
            f"Error: You must load the '{vertical}' skill first "
            f"to understand the database schema before writing queries. "
            f"Use load_skill('{vertical}') to load the schema."
        )

    # Validate and format the query
    return (
        f"SQL Query for {vertical}:\n\n"
        f"```sql\n{query}\n```\n\n"
        f"✓ Query validated against {vertical} schema\n"
        f"Ready to execute against the database."
    )
````

#### 更新中间件和代理

更新中间件以使用自定义状态模式：

```python
class SkillMiddleware(AgentMiddleware[CustomState]):
    """Middleware that injects skill descriptions into the system prompt."""

    state_schema = CustomState
    tools = [load_skill, write_sql_query]

    # ... rest of the middleware implementation stays the same
```

创建注册了受限工具的代理：

```python
agent = create_agent(
    model,
    system_prompt=(
        "You are a SQL query assistant that helps users "
        "write queries against business databases."
    ),
    middleware=[SkillMiddleware()],
    checkpointer=InMemorySaver(),
)
```

现在，如果代理在加载所需技能之前尝试使用 `write_sql_query`，它将收到一条错误消息，提示先加载相应的技能（例如 `sales_analytics` 或 `inventory_management`）。这确保代理在尝试验证查询之前拥有必要的模式知识。

## 完整示例

**查看完整的可运行脚本**

以下是一个完整、可运行的实现，结合了本教程的所有部分：

```python
from langchain_core.utils.uuid import uuid7
from typing import TypedDict, NotRequired
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, ModelResponse, AgentMiddleware
from langchain.messages import SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from typing import Callable

# Define skill structure
class Skill(TypedDict):
    """A skill that can be progressively disclosed to the agent."""
    name: str
    description: str
    content: str

# Define skills with schemas and business logic
SKILLS: list[Skill] = [
    {
        "name": "sales_analytics",
        "description": "Database schema and business logic for sales data analysis including customers, orders, and revenue.",
        "content": """# Sales Analytics Schema

## Tables

### customers
- customer_id (PRIMARY KEY)
- name
- email
- signup_date
- status (active/inactive)
- customer_tier (bronze/silver/gold/platinum)

### orders
- order_id (PRIMARY KEY)
- customer_id (FOREIGN KEY -> customers)
- order_date
- status (pending/completed/cancelled/refunded)
- total_amount
- sales_region (north/south/east/west)

### order_items
- item_id (PRIMARY KEY)
- order_id (FOREIGN KEY -> orders)
- product_id
- quantity
- unit_price
- discount_percent

## Business Logic

**Active customers**: status = 'active' AND signup_date <= CURRENT_DATE - INTERVAL '90 days'

**Revenue calculation**: Only count orders with status = 'completed'. Use total_amount from orders table, which already accounts for discounts.

**Customer lifetime value (CLV)**: Sum of all completed order amounts for a customer.

**High-value orders**: Orders with total_amount > 1000

## Example Query

-- Get top 10 customers by revenue in the last quarter
SELECT
    c.customer_id,
    c.name,
    c.customer_tier,
    SUM(o.total_amount) as total_revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'completed'
  AND o.order_date >= CURRENT_DATE - INTERVAL '3 months'
GROUP BY c.customer_id, c.name, c.customer_tier
ORDER BY total_revenue DESC
LIMIT 10;
""",
    },
    {
        "name": "inventory_management",
        "description": "Database schema and business logic for inventory tracking including products, warehouses, and stock levels.",
        "content": """# Inventory Management Schema

## Tables

### products
- product_id (PRIMARY KEY)
- product_name
- sku
- category
- unit_cost
- reorder_point (minimum stock level before reordering)
- discontinued (boolean)

### warehouses
- warehouse_id (PRIMARY KEY)
- warehouse_name
- location
- capacity

### inventory
- inventory_id (PRIMARY KEY)
- product_id (FOREIGN KEY -> products)
- warehouse_id (FOREIGN KEY -> warehouses)
- quantity_on_hand
- last_updated

### stock_movements
- movement_id (PRIMARY KEY)
- product_id (FOREIGN KEY -> products)
- warehouse_id (FOREIGN KEY -> warehouses)
- movement_type (inbound/outbound/transfer/adjustment)
- quantity (positive for inbound, negative for outbound)
- movement_date
- reference_number

## Business Logic

**Available stock**: quantity_on_hand from inventory table where quantity_on_hand > 0

**Products needing reorder**: Products where total quantity_on_hand across all warehouses is less than or equal to the product's reorder_point

**Active products only**: Exclude products where discontinued = true unless specifically analyzing discontinued items

**Stock valuation**: quantity_on_hand * unit_cost for each product

## Example Query

-- Find products below reorder point across all warehouses
SELECT
    p.product_id,
    p.product_name,
    p.reorder_point,
    SUM(i.quantity_on_hand) as total_stock,
    p.unit_cost,
    (p.reorder_point - SUM(i.quantity_on_hand)) as units_to_reorder
FROM products p
JOIN inventory i ON p.product_id = i.product_id
WHERE p.discontinued = false
GROUP BY p.product_id, p.product_name, p.reorder_point, p.unit_cost
HAVING SUM(i.quantity_on_hand) <= p.reorder_point
ORDER BY units_to_reorder DESC;
""",
    },
]

# Create skill loading tool
@tool
def load_skill(skill_name: str) -> str:
    """Load the full content of a skill into the agent's context.

    Use this when you need detailed information about how to handle a specific
    type of request. This will provide you with comprehensive instructions,
    policies, and guidelines for the skill area.

    Args:
        skill_name: The name of the skill to load (e.g., "sales_analytics", "inventory_management")
    """
    # Find and return the requested skill
    for skill in SKILLS:
        if skill["name"] == skill_name:
            return f"Loaded skill: {skill_name}\n\n{skill['content']}"

    # Skill not found
    available = ", ".join(s["name"] for s in SKILLS)
    return f"Skill '{skill_name}' not found. Available skills: {available}"

# Create skill middleware
class SkillMiddleware(AgentMiddleware):
    """Middleware that injects skill descriptions into the system prompt."""

    # Register the load_skill tool as a class variable
    tools = [load_skill]

    def __init__(self):
        """Initialize and generate the skills prompt from SKILLS."""
        # Build skills prompt from the SKILLS list
        skills_list = []
        for skill in SKILLS:
            skills_list.append(
                f"- **{skill['name']}**: {skill['description']}"
            )
        self.skills_prompt = "\n".join(skills_list)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Sync: Inject skill descriptions into system prompt."""
        # Build the skills addendum
        skills_addendum = (
            f"\n\n## Available Skills\n\n{self.skills_prompt}\n\n"
            "Use the load_skill tool when you need detailed information "
            "about handling a specific type of request."
        )

        # Append to system message content blocks
        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": skills_addendum}
        ]
        new_system_message = SystemMessage(content=new_content)
        modified_request = request.override(system_message=new_system_message)
        return handler(modified_request)

# Initialize your chat model (replace with your model)
# Example: from langchain_anthropic import ChatAnthropic
# model = ChatAnthropic(model="claude-3-5-sonnet-20241022")
from langchain_openai import ChatOpenAI
model = ChatOpenAI(model="gpt-5.5")

# Create the agent with skill support
agent = create_agent(
    model,
    system_prompt=(
        "You are a SQL query assistant that helps users "
        "write queries against business databases."
    ),
    middleware=[SkillMiddleware()],
    checkpointer=InMemorySaver(),
)

# Example usage
if __name__ == "__main__":
    # Configuration for this conversation thread
    thread_id = str(uuid7())
    config = {"configurable": {"thread_id": thread_id}}

    # Ask for a SQL query
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Write a SQL query to find all customers "
                        "who made orders over $1000 in the last month"
                    ),
                }
            ]
        },
        config
    )

    # Print the conversation
    for message in result["messages"]:
        if hasattr(message, 'pretty_print'):
            message.pretty_print()
        else:
            print(f"{message.type}: {message.content}")
```

这个完整示例包括：

* 带完整数据库模式的技能定义
* 用于按需加载的 `load_skill` 工具
* 把技能描述注入系统提示词的 `SkillMiddleware`
* 带中间件和检查点的代理创建
* 展示代理如何加载技能并编写 SQL 查询的示例用法

要运行它，你需要：

1. 安装所需包：`pip install langchain langchain-openai langgraph`
2. 设置 API 密钥（例如 `export OPENAI_API_KEY=...`）
3. 将模型初始化替换为你偏好的 LLM 提供商

## 实现变体

**查看实现选项与权衡**

本教程把技能实现为通过工具调用加载的内存 Python 字典。然而，有几种实现渐进式披露技能的方式：

**存储后端：**

* **内存**（本教程）：技能定义为 Python 数据结构，访问快速，无 I/O 开销
* **文件系统**（Claude Code 方式）：技能为目录加文件，通过 `read_file` 等文件操作发现
* **远程存储**：技能存储在 S3、数据库、Notion 或 API 中，按需获取

**技能发现**（代理如何得知存在哪些技能）：

* **系统提示词列出**：系统提示词中的技能描述（本教程使用）
* **基于文件**：通过扫描目录发现技能（Claude Code 方式）
* **基于注册表**：查询技能注册表服务或 API 获取可用技能
* **动态查找**：通过工具调用列出可用技能

**渐进式披露策略**（技能内容如何加载）：

* **单次加载**：一次工具调用加载完整技能内容（本教程使用）
* **分页**：对大型技能，以多页/分块加载技能内容
* **基于搜索**：在特定技能内容中搜索相关部分（例如对技能文件使用 grep/read 操作）
* **分层**：先加载技能概览，再深入特定子部分

**规模考量**（未经校准的心智模型——请为你的系统优化）：

* **小型技能**（< 1K tokens / ~750 词）：可直接包含在系统提示词中，并结合提示词缓存节省成本、加快响应
* **中型技能**（1-10K tokens / ~750-7.5K 词）：受益于按需加载以避免上下文开销（本教程）
* **大型技能**（> 10K tokens / ~7.5K 词，或超过上下文窗口的 5-10%）：应使用分页、基于搜索的加载或分层探索等渐进式披露技术，避免消耗过多上下文

选择取决于你的需求：内存方式最快，但技能更新需要重新部署，而基于文件或远程的存储支持无需代码更改的动态技能管理。

## 渐进式披露与上下文工程

**结合少样本提示与其他技术**

渐进式披露从根本上说是一种**[上下文工程](/oss/python/langchain/context-engineering)技术**——你在管理代理可用的信息以及何时可用。本教程聚焦于加载数据库模式，但同样的原理适用于其他类型的上下文。

#### 结合少样本提示

对于 SQL 查询用例，你可以扩展渐进式披露，动态加载与用户查询匹配的**少样本示例**：

**示例方法：**

1. 用户问："查找 6 个月未下单的客户"
2. 代理加载 `sales_analytics` 模式（如本教程所示）
3. 代理还加载 2-3 个相关的示例查询（通过语义搜索或基于标签的查找）：
   * 查找非活跃客户的查询
   * 带日期过滤的查询
   * 连接 customers 和 orders 表的查询
4. 代理结合模式知识和示例模式编写查询

这种渐进式披露（按需加载模式）与动态少样本提示（加载相关示例）的组合，创造了一个强大的上下文工程模式，可扩展到大型知识库，同时提供高质量、有依据的输出。

## 后续步骤

* 了解[中间件](/oss/python/langchain/middleware)以获得更多动态代理行为
* 探索[上下文工程](/oss/python/langchain/context-engineering)技术以管理代理上下文
* 探索[交接模式](/oss/python/langchain/multi-agent/handoffs-customer-support)以实现顺序工作流
* 阅读[子代理模式](/oss/python/langchain/multi-agent/subagents-personal-assistant)以实现并行任务路由
* 参阅[多代理模式](/oss/python/langchain/multi-agent)了解其他专用代理方案
* 使用 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-multi-agent-skills-sql-assistant) 调试和监控技能加载

---

# 用子代理构建个人助理

## 概述

**监督者模式（supervisor pattern）** 是一种[多代理](/oss/python/langchain/multi-agent)架构：一个中央监督者代理协调专门的工人代理。当任务需要不同类型的专业知识时，这种方法最为适用。与其构建一个跨领域管理工具选择的代理，不如创建由理解整体工作流的监督者协调的聚焦专家。

在本教程中，你将通过一个真实的工作流构建个人助理系统，展示这些优势。系统将协调两个职责根本不同的专家：

* 一个**日历代理**，负责日程安排、可用性检查和事件管理。
* 一个**电子邮件代理**，负责沟通管理、草拟消息和发送通知。

我们还将融入[人机协同审查](/oss/python/langchain/human-in-the-loop)，让用户能够按需批准、编辑和拒绝操作（如外发邮件）。

> 注意：如果你正从 [`langgraph-supervisor`](https://github.com/langchain-ai/langgraph-supervisor-py) 包迁移，请参阅 [Migrate from langgraph-supervisor](/oss/python/migrate/langgraph-supervisor) 了解迁移前后的模式，包括中断（interrupt）和恢复（resume）流程。

### 为什么使用监督者？

多代理架构让你可以把[工具](/oss/python/langchain/tools)划分到各个工人代理，每个代理有自己的提示词或指令。设想一个可以直接访问所有日历和电子邮件 API 的代理：它必须从许多相似的工具中选择、理解每个 API 的确切格式，并同时处理多个领域。如果性能下降，把相关工具及其提示词分组成逻辑单元（部分是为了管理迭代改进）可能会有所帮助。

### 概念

我们将涵盖以下概念：

* [多代理系统](/oss/python/langchain/multi-agent)
* [人机协同审查](/oss/python/langchain/human-in-the-loop)

## 设置

### 安装

本教程需要 `langchain` 包：

**pip**
```bash
pip install langchain
```

**conda**
```bash
conda install langchain -c conda-forge
```

更多详情请参阅[安装指南](/oss/python/langchain/install)。

### LangSmith

设置 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-multi-agent-subagents-personal-assistant) 以查看代理内部发生的情况。然后设置以下环境变量：

**Shell**
```bash
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="..."
```

**Python**
```python
import getpass
import os

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = getpass.getpass()
```

### 组件

我们需要从 LangChain 的集成套件中选择一个聊天模型：

👉 阅读 [Google GenAI 聊天模型集成文档](/oss/python/integrations/chat/google_generative_ai/)

（官方文档对 Google/OpenAI/Anthropic/OpenRouter/Fireworks/Baseten/Ollama 提供了相同示例，仅模型字符串不同；此处保留 Google 版本。）

**pip**
```bash
pip install -U "langchain[google-genai]"
```

**uv**
```bash
uv add "langchain[google-genai]"
```

**init_chat_model**
```python
import os
from langchain.chat_models import init_chat_model

os.environ["GOOGLE_API_KEY"] = "..."

model = init_chat_model("google_genai:gemini-3.6-flash")
```

**Model Class**
```python
import os
from langchain_google_genai import ChatGoogleGenerativeAI

os.environ["GOOGLE_API_KEY"] = "..."

model = ChatGoogleGenerativeAI(model="gemini-3.6-flash")
```

## 1. 定义工具

首先定义需要结构化输入的工具。在实际应用中，它们会调用真实的 API（Google Calendar、SendGrid 等）。在本教程中，你将使用桩实现来演示该模式。

```python
from langchain.tools import tool

@tool
def create_calendar_event(
    title: str,
    start_time: str,       # ISO format: "2024-01-15T14:00:00"
    end_time: str,         # ISO format: "2024-01-15T15:00:00"
    attendees: list[str],  # email addresses
    location: str = ""
) -> str:
    """Create a calendar event. Requires exact ISO datetime format."""
    # Stub: In practice, this would call Google Calendar API, Outlook API, etc.
    return f"Event created: {title} from {start_time} to {end_time} with {len(attendees)} attendees"

@tool
def send_email(
    to: list[str],  # email addresses
    subject: str,
    body: str,
    cc: list[str] = []
) -> str:
    """Send an email via email API. Requires properly formatted addresses."""
    # Stub: In practice, this would call SendGrid, Gmail API, etc.
    return f"Email sent to {', '.join(to)} - Subject: {subject}"

@tool
def get_available_time_slots(
    attendees: list[str],
    date: str,  # ISO format: "2024-01-15"
    duration_minutes: int
) -> list[str]:
    """Check calendar availability for given attendees on a specific date."""
    # Stub: In practice, this would query calendar APIs
    return ["09:00", "14:00", "16:00"]
```

## 2. 创建专用子代理

接下来，我们将创建处理每个领域的专用子代理。

### 创建日历代理

日历代理理解自然语言的日程请求，并把它们翻译成精确的 API 调用。它处理日期解析、可用性检查和事件创建。

```python
from datetime import date

from langchain.agents import create_agent

CALENDAR_AGENT_PROMPT = (
    f"Today's date is {date.today().isoformat()}. "
    "You are a calendar scheduling assistant. "
    "Parse natural language scheduling requests (e.g., 'next Tuesday at 2pm') "
    "into proper ISO datetime formats. "
    "Use get_available_time_slots to check availability when needed. "
    "If there is no suitable time slot, stop and confirm unavailability in your response. "
    "Use create_calendar_event to schedule events. "
    "Always confirm what was scheduled in your final response."
)

calendar_agent = create_agent(
    model,
    tools=[create_calendar_event, get_available_time_slots],
    system_prompt=CALENDAR_AGENT_PROMPT,
)
```

测试日历代理如何处理自然语言的日程请求：

```python
query = "Schedule a team meeting next Tuesday at 2pm for 1 hour"

stream = calendar_agent.stream_events(
    {"messages": [{"role": "user", "content": query}]},
    version="v3",
)
for kind, item in stream.interleave("messages", "tool_calls"):
    if kind == "messages":
        for token in item.text:
            print(token, end="", flush=True)
    elif kind == "tool_calls":
        print(f"\nTool call: {item.tool_name}({item.input})")
        print(f"Tool result: {item.output}")
```

```
================================== Ai Message ==================================
Tool Calls:
  get_available_time_slots (call_EIeoeIi1hE2VmwZSfHStGmXp)
 Call ID: call_EIeoeIi1hE2VmwZSfHStGmXp
  Args:
    attendees: []
    date: 2024-06-18
    duration_minutes: 60
================================= Tool Message =================================
Name: get_available_time_slots

["09:00", "14:00", "16:00"]
================================== Ai Message ==================================
Tool Calls:
  create_calendar_event (call_zgx3iJA66Ut0W8S3NpT93kEB)
 Call ID: call_zgx3iJA66Ut0W8S3NpT93kEB
  Args:
    title: Team Meeting
    start_time: 2024-06-18T14:00:00
    end_time: 2024-06-18T15:00:00
    attendees: []
================================= Tool Message =================================
Name: create_calendar_event

Event created: Team Meeting from 2024-06-18T14:00:00 to 2024-06-18T15:00:00 with 0 attendees
================================== Ai Message ==================================

The team meeting has been scheduled for next Tuesday, June 18th, at 2:00 PM and will last for 1 hour. If you need to add attendees or a location, please let me know!
```

代理把"next Tuesday at 2pm"解析为 ISO 格式（"2024-01-16T14:00:00"），计算结束时间，调用 `create_calendar_event`，并返回自然语言的确认。

### 创建电子邮件代理

电子邮件代理处理消息的撰写和发送。它专注于提取收件人信息、构思合适的主题行和正文，以及管理电子邮件沟通。

```python
EMAIL_AGENT_PROMPT = (
    "You are an email assistant. "
    "Compose professional emails based on natural language requests. "
    "Extract recipient information and craft appropriate subject lines and body text. "
    "Use send_email to send the message. "
    "Always confirm what was sent in your final response."
)

email_agent = create_agent(
    model,
    tools=[send_email],
    system_prompt=EMAIL_AGENT_PROMPT,
)
```

用自然语言请求测试电子邮件代理：

```python
query = "Send the design team a reminder about reviewing the new mockups"

stream = email_agent.stream_events(
    {"messages": [{"role": "user", "content": query}]},
    version="v3",
)
for kind, item in stream.interleave("messages", "tool_calls"):
    if kind == "messages":
        for token in item.text:
            print(token, end="", flush=True)
    elif kind == "tool_calls":
        print(f"\nTool call: {item.tool_name}({item.input})")
        print(f"Tool result: {item.output}")
```

```
================================== Ai Message ==================================
Tool Calls:
  send_email (call_OMl51FziTVY6CRZvzYfjYOZr)
 Call ID: call_OMl51FziTVY6CRZvzYfjYOZr
  Args:
    to: ['design-team@example.com']
    subject: Reminder: Please Review the New Mockups
    body: Hi Design Team,

This is a friendly reminder to review the new mockups at your earliest convenience. Your feedback is important to ensure that we stay on track with our project timeline.

Please let me know if you have any questions or need additional information.

Thank you!

Best regards,
================================= Tool Message =================================
Name: send_email

Email sent to design-team@example.com - Subject: Reminder: Please Review the New Mockups
================================== Ai Message ==================================

I've sent a reminder to the design team asking them to review the new mockups. If you need any further communication on this topic, just let me know!
```

代理从非正式请求中推断出收件人，构思出专业的主题行和正文，调用 `send_email`，并返回确认。每个子代理都专注于狭窄的范围，拥有领域专用的工具和提示词，从而能在其特定任务上表现出色。

## 3. 将子代理包装为工具

现在把每个子代理包装成监督者可以调用的工具。这是创建分层系统的关键架构步骤。监督者将看到"schedule_event"这样的高级工具，而不是"create_calendar_event"这样的低级工具。

```python
@tool
def schedule_event(request: str) -> str:
    """Schedule calendar events using natural language.

    Use this when the user wants to create, modify, or check calendar appointments.
    Handles date/time parsing, availability checking, and event creation.

    Input: Natural language scheduling request (e.g., 'meeting with design team
    next Tuesday at 2pm')
    """
    result = calendar_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text

@tool
def manage_email(request: str) -> str:
    """Send emails using natural language.

    Use this when the user wants to send notifications, reminders, or any email
    communication. Handles recipient extraction, subject generation, and email
    composition.

    Input: Natural language email request (e.g., 'send them a reminder about
    the meeting')
    """
    result = email_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text
```

工具描述帮助监督者决定何时使用每个工具，所以要让它们清晰而具体。我们只返回子代理的最终响应，因为监督者不需要看到中间推理或工具调用。

## 4. 创建监督者代理

现在创建编排子代理的监督者。监督者只看到高级工具，在领域层面而非单个 API 层面做出路由决策。

```python
SUPERVISOR_PROMPT = (
    "You are a helpful personal assistant. "
    "You can schedule calendar events and send emails. "
    "Break down user requests into appropriate tool calls and coordinate the results. "
    "When a request involves multiple actions, use multiple tools in sequence or in parallel as appropriate."
)

supervisor_agent = create_agent(
    model,
    tools=[schedule_event, manage_email],
    system_prompt=SUPERVISOR_PROMPT,
)
```

## 5. 使用监督者

现在用需要跨多个领域协调的复杂请求测试你的完整系统：

### 示例 1：简单的单域请求

```python
query = "Schedule a team standup for tomorrow at 9am"

stream = supervisor_agent.stream_events(
    {"messages": [{"role": "user", "content": query}]},
    version="v3",
)
for kind, item in stream.interleave("messages", "tool_calls"):
    if kind == "messages":
        for token in item.text:
            print(token, end="", flush=True)
    elif kind == "tool_calls":
        print(f"\nTool call: {item.tool_name}({item.input})")
        print(f"Tool result: {item.output}")
```

```
================================== Ai Message ==================================
Tool Calls:
  schedule_event (call_mXFJJDU8bKZadNUZPaag8Lct)
 Call ID: call_mXFJJDU8bKZadNUZPaag8Lct
  Args:
    request: Schedule a team standup for tomorrow at 9am with Alice and Bob.
================================= Tool Message =================================
Name: schedule_event

The team standup has been scheduled for tomorrow at 9:00 AM with Alice and Bob. If you need to make any changes or add more details, just let me know!
================================== Ai Message ==================================

The team standup with Alice and Bob is scheduled for tomorrow at 9:00 AM. If you need any further arrangements or adjustments, please let me know!
```

监督者识别出这是一个日历任务，调用 `schedule_event`，日历代理处理日期解析和事件创建。

> 提示：要全面了解信息流（包括每次聊天模型调用的提示词和响应），请查看上述运行对应的 [LangSmith trace](https://smith.langchain.com/public/91a9a95f-fba9-4e84-aff0-371861ad2f4a/r)。

### 示例 2：复杂的多域请求

```python
query = (
    "Schedule a meeting with the design team next Tuesday at 2pm for 1 hour, "
    "and send them an email reminder about reviewing the new mockups."
)

stream = supervisor_agent.stream_events(
    {"messages": [{"role": "user", "content": query}]},
    version="v3",
)
for kind, item in stream.interleave("messages", "tool_calls"):
    if kind == "messages":
        for token in item.text:
            print(token, end="", flush=True)
    elif kind == "tool_calls":
        print(f"\nTool call: {item.tool_name}({item.input})")
        print(f"Tool result: {item.output}")
```

```
================================== Ai Message ==================================
Tool Calls:
  schedule_event (call_YA68mqF0koZItCFPx0kGQfZi)
 Call ID: call_YA68mqF0koZItCFPx0kGQfZi
  Args:
    request: meeting with the design team next Tuesday at 2pm for 1 hour
  manage_email (call_XxqcJBvVIuKuRK794ZIzlLxx)
 Call ID: call_XxqcJBvVIuKuRK794ZIzlLxx
  Args:
    request: send the design team an email reminder about reviewing the new mockups
================================= Tool Message =================================
Name: schedule_event

Your meeting with the design team is scheduled for next Tuesday, June 18th, from 2:00pm to 3:00pm. Let me know if you need to add more details or make any changes!
================================= Tool Message =================================
Name: manage_email

I've sent an email reminder to the design team requesting them to review the new mockups. If you need to include more information or recipients, just let me know!
================================== Ai Message ==================================

Your meeting with the design team is scheduled for next Tuesday, June 18th, from 2:00pm to 3:00pm.

I've also sent an email reminder to the design team, asking them to review the new mockups.

Let me know if you'd like to add more details to the meeting or include additional information in the email!
```

监督者识别出这需要日历和电子邮件两类操作，为会议调用 `schedule_event`，然后为提醒调用 `manage_email`。每个子代理完成自己的任务，监督者把两个结果综合成连贯的响应。

> 注意：监督者默认按顺序向子代理派发任务。每个工具调用完成后才开始下一个。然而，许多 LLM 会在单次响应中发出多个工具调用（如上面的 trace 所示，`schedule_event` 和 `manage_email` 被一起调用），运行时将并行执行它们。你也可以配置显式的并行派发。详见 [`create_supervisor` 参考文档](https://reference.langchain.com/python/langgraph-supervisor/supervisor/create_supervisor)。

> 提示：参阅 [LangSmith trace](https://smith.langchain.com/public/95cd00a3-d1f9-4dba-9731-7bf733fb6a3c/r) 查看上述运行的详细信息流，包括各个聊天模型提示词和响应。

### 完整可运行示例

以下是一个可直接运行的完整脚本：

**查看完整代码**

```python
"""
Personal Assistant Supervisor Example

This example demonstrates the tool calling pattern for multi-agent systems.
A supervisor agent coordinates specialized sub-agents (calendar and email)
that are wrapped as tools.
"""

from datetime import date

from langchain.tools import tool
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

# ============================================================================
# Step 1: Define low-level API tools (stubbed)
# ============================================================================

@tool
def create_calendar_event(
    title: str,
    start_time: str,  # ISO format: "2024-01-15T14:00:00"
    end_time: str,    # ISO format: "2024-01-15T15:00:00"
    attendees: list[str],  # email addresses
    location: str = ""
) -> str:
    """Create a calendar event. Requires exact ISO datetime format."""
    return f"Event created: {title} from {start_time} to {end_time} with {len(attendees)} attendees"

@tool
def send_email(
    to: list[str],      # email addresses
    subject: str,
    body: str,
    cc: list[str] = []
) -> str:
    """Send an email via email API. Requires properly formatted addresses."""
    return f"Email sent to {', '.join(to)} - Subject: {subject}"

@tool
def get_available_time_slots(
    attendees: list[str],
    date: str,  # ISO format: "2024-01-15"
    duration_minutes: int
) -> list[str]:
    """Check calendar availability for given attendees on a specific date."""
    return ["09:00", "14:00", "16:00"]

# ============================================================================
# Step 2: Create specialized sub-agents
# ============================================================================

model = init_chat_model("gpt-5.5")  # for example

calendar_agent = create_agent(
    model,
    tools=[create_calendar_event, get_available_time_slots],
    system_prompt=(
        f"Today's date is {date.today().isoformat()}. "
        "You are a calendar scheduling assistant. "
        "Parse natural language scheduling requests (e.g., 'next Tuesday at 2pm') "
        "into proper ISO datetime formats. "
        "Use get_available_time_slots to check availability when needed. "
        "If there is no suitable time slot, stop and confirm unavailability in your response. "
        "Use create_calendar_event to schedule events. "
        "Always confirm what was scheduled in your final response."
    )
)

email_agent = create_agent(
    model,
    tools=[send_email],
    system_prompt=(
        "You are an email assistant. "
        "Compose professional emails based on natural language requests. "
        "Extract recipient information and craft appropriate subject lines and body text. "
        "Use send_email to send the message. "
        "Always confirm what was sent in your final response."
    )
)

# ============================================================================
# Step 3: Wrap sub-agents as tools for the supervisor
# ============================================================================

@tool
def schedule_event(request: str) -> str:
    """Schedule calendar events using natural language.

    Use this when the user wants to create, modify, or check calendar appointments.
    Handles date/time parsing, availability checking, and event creation.

    Input: Natural language scheduling request (e.g., 'meeting with design team
    next Tuesday at 2pm')
    """
    result = calendar_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text

@tool
def manage_email(request: str) -> str:
    """Send emails using natural language.

    Use this when the user wants to send notifications, reminders, or any email
    communication. Handles recipient extraction, subject generation, and email
    composition.

    Input: Natural language email request (e.g., 'send them a reminder about
    the meeting')
    """
    result = email_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text

# ============================================================================
# Step 4: Create the supervisor agent
# ============================================================================

supervisor_agent = create_agent(
    model,
    tools=[schedule_event, manage_email],
    system_prompt=(
        "You are a helpful personal assistant. "
        "You can schedule calendar events and send emails. "
        "Break down user requests into appropriate tool calls and coordinate the results. "
        "When a request involves multiple actions, use multiple tools in sequence or in parallel as appropriate."
    )
)

# ============================================================================
# Step 5: Use the supervisor
# ============================================================================

if __name__ == "__main__":
    # Example: User request requiring both calendar and email coordination
    user_request = (
        "Schedule a meeting with the design team next Tuesday at 2pm for 1 hour, "
        "and send them an email reminder about reviewing the new mockups."
    )

    print("User Request:", user_request)
    print("\n" + "="*80 + "\n")

    stream = supervisor_agent.stream_events(
        {"messages": [{"role": "user", "content": user_request}]},
        version="v3",
    )
    for kind, item in stream.interleave("messages", "tool_calls"):
        if kind == "messages":
            for token in item.text:
                print(token, end="", flush=True)
        elif kind == "tool_calls":
            print(f"\nTool call: {item.tool_name}({item.input})")
            print(f"Tool result: {item.output}")
```

### 理解架构

你的系统有三层。底层包含需要精确格式的刚性 API 工具。中间层包含接受自然语言、将其翻译为结构化 API 调用并返回自然语言确认的子代理。顶层是路由到高级能力并综合结果的监督者。

这种关注点分离带来几个好处：每层有聚焦的职责，你可以在不影响现有层的情况下添加新领域，并且可以独立测试和迭代每一层。

## 6. 添加人机协同审查

对敏感操作加入[人机协同审查](/oss/python/langchain/human-in-the-loop)是明智的。LangChain 包含[内置中间件](/oss/python/langchain/human-in-the-loop#configuring-interrupts)来审查工具调用，本例中是子代理调用的工具。

让我们为两个子代理都添加人机协同审查：

* 我们配置 `create_calendar_event` 和 `send_email` 工具触发中断，允许所有[响应类型](/oss/python/langchain/human-in-the-loop)（`approve` 批准、`edit` 编辑、`reject` 拒绝）
* 我们**只给顶层代理**添加[检查点](/oss/python/langchain/short-term-memory)。这是暂停和恢复执行所必需的。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver

calendar_agent = create_agent(
    model,
    tools=[create_calendar_event, get_available_time_slots],
    system_prompt=CALENDAR_AGENT_PROMPT,
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={"create_calendar_event": True},
            description_prefix="Calendar event pending approval",
        ),
    ],
)

email_agent = create_agent(
    model,
    tools=[send_email],
    system_prompt=EMAIL_AGENT_PROMPT,
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={"send_email": True},
            description_prefix="Outbound email pending approval",
        ),
    ],
)

supervisor_agent = create_agent(
    model,
    tools=[schedule_event, manage_email],
    system_prompt=SUPERVISOR_PROMPT,
    checkpointer=InMemorySaver(),
)
```

让我们重放该查询。注意我们为了访问下游内容，把中断事件收集到列表中：

```python
query = (
    "Schedule a meeting with the design team next Tuesday at 2pm for 1 hour, "
    "and send them an email reminder about reviewing the new mockups."
)

config = {"configurable": {"thread_id": "6"}}

interrupts = []
stream = supervisor_agent.stream_events(
    {"messages": [{"role": "user", "content": query}]},
    config,
    version="v3",
)
for kind, item in stream.interleave("messages", "tool_calls"):
    if kind == "messages":
        for token in item.text:
            print(token, end="", flush=True)
    elif kind == "tool_calls":
        print(f"\nTool call: {item.tool_name}({item.input})")
if stream.interrupted:
    for interrupt_ in stream.interrupts:
        interrupts.append(interrupt_)
        print(f"\nINTERRUPTED: {interrupt_.id}")
```

```
================================== Ai Message ==================================
Tool Calls:
  schedule_event (call_t4Wyn32ohaShpEZKuzZbl83z)
 Call ID: call_t4Wyn32ohaShpEZKuzZbl83z
  Args:
    request: Schedule a meeting with the design team next Tuesday at 2pm for 1 hour.
  manage_email (call_JWj4vDJ5VMnvkySymhCBm4IR)
 Call ID: call_JWj4vDJ5VMnvkySymhCBm4IR
  Args:
    request: Send an email reminder to the design team about reviewing the new mockups before our meeting next Tuesday at 2pm.

INTERRUPTED: 4f994c9721682a292af303ec1a46abb7

INTERRUPTED: 2b56f299be313ad8bc689eff02973f16
```

这次我们中断了执行。让我们检查中断事件：

```python
for interrupt_ in interrupts:
    for request in interrupt_.value["action_requests"]:
        print(f"INTERRUPTED: {interrupt_.id}")
        print(f"{request['description']}\n")
```

```
INTERRUPTED: 4f994c9721682a292af303ec1a46abb7
Calendar event pending approval

Tool: create_calendar_event
Args: {'title': 'Meeting with the Design Team', 'start_time': '2024-06-18T14:00:00', 'end_time': '2024-06-18T15:00:00', 'attendees': ['design team']}

INTERRUPTED: 2b56f299be313ad8bc689eff02973f16
Outbound email pending approval

Tool: send_email
Args: {'to': ['designteam@example.com'], 'subject': 'Reminder: Review New Mockups Before Meeting Next Tuesday at 2pm', 'body': "Hello Team,\n\nThis is a reminder to review the new mockups ahead of our meeting scheduled for next Tuesday at 2pm. Your feedback and insights will be valuable for our discussion and next steps.\n\nPlease ensure you've gone through the designs and are ready to share your thoughts during the meeting.\n\nThank you!\n\nBest regards,\n[Your Name]"}
```

我们可以通过引用中断 ID，用 [`Command`](https://reference.langchain.com/python/langgraph/types/Command) 为每个中断指定决策。更多细节请参阅[人机协同指南](/oss/python/langchain/human-in-the-loop)。出于演示目的，这里我们将批准日历事件，但编辑外发邮件的主题：

```python
from langgraph.types import Command

resume = {}
for interrupt_ in interrupts:
    if interrupt_.id == "2b56f299be313ad8bc689eff02973f16":
        # Edit email
        edited_action = interrupt_.value["action_requests"][0].copy()
        edited_action["args"]["subject"] = "Mockups reminder"
        resume[interrupt_.id] = {
            "decisions": [{"type": "edit", "edited_action": edited_action}]
        }
    else:
        resume[interrupt_.id] = {"decisions": [{"type": "approve"}]}

interrupts = []
stream = supervisor_agent.stream_events(
    Command(resume=resume),
    config,
    version="v3",
)
for kind, item in stream.interleave("messages", "tool_calls"):
    if kind == "messages":
        for token in item.text:
            print(token, end="", flush=True)
    elif kind == "tool_calls":
        print(f"\nTool call: {item.tool_name}({item.input})")
if stream.interrupted:
    for interrupt_ in stream.interrupts:
        interrupts.append(interrupt_)
        print(f"\nINTERRUPTED: {interrupt_.id}")
```

```
================================= Tool Message =================================
Name: schedule_event

Your meeting with the design team has been scheduled for next Tuesday, June 18th, from 2:00 pm to 3:00 pm.
================================= Tool Message =================================
Name: manage_email

Your email reminder to the design team has been sent. Here's what was sent:

- Recipient: designteam@example.com
- Subject: Mockups reminder
- Body: A reminder to review the new mockups before the meeting next Tuesday at 2pm, with a request for feedback and readiness for discussion.

Let me know if you need any further assistance!
================================== Ai Message ==================================

- Your meeting with the design team has been scheduled for next Tuesday, June 18th, from 2:00 pm to 3:00 pm.
- An email reminder has been sent to the design team about reviewing the new mockups before the meeting.

Let me know if you need any further assistance!
```

运行在我们的输入下继续进行。

## 7. 进阶：控制信息流

默认情况下，子代理只从监督者那里收到请求字符串。你可能希望传递额外的上下文，例如对话历史或用户偏好。

### 向子代理传递额外的对话上下文

```python
from langchain.tools import tool, ToolRuntime

@tool
def schedule_event(
    request: str,
    runtime: ToolRuntime
) -> str:
    """Schedule calendar events using natural language."""
    # Customize context received by sub-agent
    original_user_message = next(
        message for message in runtime.state["messages"]
        if message.type == "human"
    )
    prompt = (
        "You are assisting with the following user inquiry:\n\n"
        f"{original_user_message.text}\n\n"
        "You are tasked with the following sub-request:\n\n"
        f"{request}"
    )
    result = calendar_agent.invoke({
        "messages": [{"role": "user", "content": prompt}],
    })
    return result["messages"][-1].text
```

这允许子代理看到完整的对话上下文，这对于解决"schedule it for the same time tomorrow"（引用之前的对话）这类歧义很有用。

> 提示：你可以在 LangSmith trace 的[聊天模型调用](https://smith.langchain.com/public/c7d54882-afb8-4039-9c5a-4112d0f458b0/r/6803571e-af78-4c68-904a-ecf55771084d)中看到子代理收到的完整上下文。

### 控制监督者接收的内容

你也可以自定义流回监督者的信息：

```python
import json

@tool
def schedule_event(request: str) -> str:
    """Schedule calendar events using natural language."""
    result = calendar_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })

    # Option 1: Return just the confirmation message
    return result["messages"][-1].text

    # Option 2: Return structured data
    # return json.dumps({
    #     "status": "success",
    #     "event_id": "evt_123",
    #     "summary": result["messages"][-1].text
    # })
```

**重要提示：** 确保子代理提示词强调其最终消息应包含所有相关信息。一个常见的失败模式是子代理执行了工具调用，但没有把结果包含在最终响应中。

## 8. 关键要点

监督者模式创建了抽象层次，每一层都有明确的职责。在设计监督者系统时，从清晰的领域边界开始，给每个子代理聚焦的工具和提示词。为监督者编写清晰的工具描述，在集成前独立测试每一层，并根据你的具体需求控制信息流。

> 提示：**何时使用监督者模式**
>
> 当你拥有多个不同的领域（日历、电子邮件、CRM、数据库）、每个领域有多个工具或复杂逻辑、需要集中的工作流控制，且子代理不需要直接与用户对话时，使用监督者模式。
>
> 对于只有几个工具的简单场景，使用单个代理。当代理需要与用户对话时，改用[交接](/oss/python/langchain/multi-agent/handoffs)。对于代理之间的对等协作，请考虑其他多代理模式。

## 后续步骤

了解[交接](/oss/python/langchain/multi-agent/handoffs)以实现代理间对话，探索[上下文工程](/oss/python/langchain/context-engineering)以微调信息流，阅读[多代理概览](/oss/python/langchain/multi-agent)以比较不同模式，并使用 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-multi-agent-subagents-personal-assistant) 调试和监控你的多代理系统。

