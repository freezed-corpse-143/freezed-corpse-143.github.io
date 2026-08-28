Jinja 2 是 Python 里一个非常流行的模板引擎，常与 Flask 等 Web 框架搭配使用，也常被用于生成配置文件或代码。它的核心理念是允许你在静态模板中插入动态变量和逻辑，从而实现灵活的输出。
# 安装

```bash
uv pip install Jinja2
```

# 环境

在使用 Jinja 2 时，核心是创建一个“环境”（Environment），用它来管理模板的加载和配置。

1.  **准备模板文件**：比如，创建一个 `templates` 文件夹，在里面新建一个 `index.html` 文件。
2.  **编写模板**：在 `index.html` 中写入动态内容，用 `{{ ... }}` 来表示变量。

```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
</head>
<body>
    <h1>Hello, {{ name }}!</h1>
</body>
</html>
```

3.  **在 Python 中渲染**：加载模板并传入数据，就能得到最终的字符串结果。

```python
from jinja2 import Environment, FileSystemLoader

# 1. 创建环境，指定模板文件夹
env = Environment(loader=FileSystemLoader('templates'))

# 2. 加载模板文件
template = env.get_template('index.html')

# 3. 渲染模板，传入数据
output = template.render(title='我的网站', name='张三')
print(output)
```

# 三大语法界定符

Jinja2 的语法很清晰，主要通过三种定界符来区分不同的功能：

| 定界符      | 用途                                                       | 示例                      |
| :---------- | :--------------------------------------------------------- | :------------------------ |
| `{{ ... }}` | **表达式**：输出变量值或表达式结果，如 `{{ user.name }}`。 | `{{ user.name }}`         |
| `{% ... %}` | **语句**：执行控制逻辑，如 `for` 循环和 `if` 判断。        | `{% for item in items %}` |
| `{# ... #}` | **注释**：写注释，渲染时会被忽略，不会出现在最终输出中。   | `{# 这是一条注释 #}`      |

# 常用功能详解

*   **变量与属性访问**：在模板中，你可以通过 `{{ 变量名 }}` 来输出变量。如果变量是字典或对象，使用 `.` 来获取其属性或键值，比如 `{{ user.username }}`。

*   **过滤器 (Filters)**：过滤器可以修改变量的输出，使用管道符 `|` 连接。例如，`{{ name|upper }}` 会将 `name` 转换为大写。常用的过滤器包括：
    *   `safe`：渲染时**不转义**特殊字符，用于输出可信的 HTML 代码。
    *   `capitalize` / `upper` / `lower` / `title`：转换字母大小写。
    *   `trim`：去除字符串首尾的空白字符。
    *   `length`：返回列表、字符串或字典的长度。

*   **控制结构 (Control Structures)**：你可以在模板中使用 `if` 和 `for` 来控制输出逻辑。
    *   **条件判断**：`{% if ... %}` ... `{% elif ... %}` ... `{% else %}` ... `{% endif %}`。
    *   **循环遍历**：`{% for item in items %}` ... `{% endfor %}`，可以用来生成列表等重复结构。

*   **模板继承 (Template Inheritance)**：这是 Jinja 2 最强大的功能之一，能有效重用代码。你可以定义一个基础模板（base.html），其中用 `{% block 块名 %}` 标记出可被子模板替换的区域。子模板通过 `{% extends "base.html" %}` 继承后，就可以用 `{% block 块名 %}` ... `{% endblock %}` 来填充具体内容了。

*   **模板包含 (Includes)**：通过 `{% include "header.html" %}`，你可以将一个独立的模板片段（如页眉、页脚）嵌入到当前模板中，方便管理和复用代码片段。

*   **自动转义**：为了安全，在渲染 HTML 时，Jinja 2 默认会对变量中的特殊字符（如 `<`, `>`, `&`）进行转义，防止 XSS 攻击。如果你确信内容是安全的 HTML（例如来自富文本编辑器），记得使用 `{{ content|safe }}` 过滤器来避免它被错误转义。