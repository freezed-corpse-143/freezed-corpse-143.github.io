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

#