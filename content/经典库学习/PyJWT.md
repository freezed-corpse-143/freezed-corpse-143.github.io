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
