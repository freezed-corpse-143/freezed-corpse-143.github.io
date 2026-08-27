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

# 正确请求资源（验证逻辑）

```mermaid
sequenceDiagram
    participant C as 客户端
    participant S as 业务服务
    participant A as 认证服务（可选）

    C->>S: 1. 请求API + Header: Authorization: Bearer <access_token>
    S->>S: 2. 拆分Token，取签名部分
    Note over S: 3. 验证签名（用服务端公钥/密钥）<br/>- 检查头部+载荷是否被篡改<br/>- 验签通过则解码载荷
    S->>S: 4. 校验过期时间（exp）<br/>- 若 exp < 当前时间 → 失效
    S->>S: 5. 可选：校验签发者（iss）/受众（aud）等
    S-->>C: 6. 验签+过期均通过 → 返回资源
```

# Access Token 过期 → 用 Refresh Token 刷新

```mermaid
sequenceDiagram
    participant C as 客户端
    participant A as 认证服务
    participant DB as 黑名单/刷新表（可选）

    C->>A: 1. 请求刷新: grant_type=refresh_token<br/>+ refresh_token
    A->>A: 2. 验证refresh_token签名+有效期
    A->>A: 3. 校验refresh_token是否被撤销（如DB黑名单）
    alt 有效
        A->>A: 4. 生成新access_token（有效期重置）<br/>可选：轮换refresh_token
        A-->>C: 5. 返回 新access_token（+ 新refresh_token）
    else 无效/过期
        A-->>C: 6. 401 Unauthorized，要求重新登录
    end
```

# 主动登出/强制失效（黑名单机制）

```mermaid
sequenceDiagram
    participant C as 客户端
    participant A as 认证服务
    participant R as Redis/黑名单

    C->>A: 1. 登出请求（携带access_token）
    A->>A: 2. 解析Token，获取jti（唯一ID）+ 过期剩余时间
    A->>R: 3. 将jti加入黑名单，TTL=剩余过期时间
    A-->>C: 4. 登出成功
    Note over A,R: 后续任何携带此Token的请求<br/>→ 先查黑名单 → 命中则拒绝
```

# JWT 结构回顾

JWT 由三部分组成，用 `.` 连接

```
base64UrlEncode(Header).base64UrlEncode(payload).签名(Signature)
```

- Header：定义算法和类型，比如

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

- Payload：存放用户信息，比如

```json
{
  "sub": "zhangsan",      // 用户标识
  "userId": 10086,
  "role": "admin",
  "iat": 1750000000,      // 签发时间（Unix秒）
  "exp": 1750007200       // 过期时间（2小时后）
}
```

签名：

1. 服务端准备密钥 Secret
2. 拼接待签名字符串

```
待签名内容=base64UrlEncode(Header).base64UrlEncode(payload)
```
3. 使用密钥加密
4. 将密文使用 Base64 进行编码
5. 将最后的编码拼接到待签名内容即可。
