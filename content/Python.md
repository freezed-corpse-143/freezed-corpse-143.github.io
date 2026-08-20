
# MRO

```python
# DFS 的问题示例
class A: pass
class B(A): pass
class C(A): pass
class D(B, C): pass

# DFS 顺序：D → B → A → C → A（重复）
# C3 顺序：D → B → C → A（正确）
```

---
