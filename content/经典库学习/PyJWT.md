# HS256

```python
import jwt
key = "secret"
encoded = jwt.encode(
	{"some": "payload"},
	key,
	algorithm="HS256"
)
print(jwt.decode(encoded, key, algorithms="HS265"))
```

# 登录与颁发 Token（首次获取）

```mermaid
sequenceDiagram
    participant C as 客户端
    participant A as 认证服务
    participant DB as 用户数据库

    C->>A: 1. 用户名+密码
    A->>DB: 2. 校验身份
    DB-->>A: 3. 身份有效
    Note over A: 4. 生成JWT（Payload含userId/role）<br/>设置过期时间（如2小时）
    A-->>C: 5. 返回 access_token + refresh_token
```

# 正确