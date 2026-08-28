
# 单头

```python
import torch
import torch.nn.functional as F


def self_attention_single_head(
    X: torch.Tensor,  # 输入序列特征 (batch, seq_len, d_model) 或 (seq_len, d_model)
    W_q: torch.Tensor,  # Query 权重矩阵 (d_model, d_k)
    W_k: torch.Tensor,  # Key 权重矩阵 (d_model, d_k)
    W_v: torch.Tensor,  # Value 权重矩阵 (d_model, d_v)
) -> tuple[torch.Tensor, torch.Tensor]:
    r"""单头自注意力（手写实现）。

    自注意力的核心公式：

    $$
    \text{Attention}(Q, K, V) =
    \text{softmax}\left(\frac{QK^\top}{\sqrt{d_k}}\right) V
    $$

    其中三个线性投影为：

    $$
    Q = XW_q,\qquad K = XW_k,\qquad V = XW_v
    $$

    计算步骤：
    1. 用三个权重矩阵把输入 $X$ 投影为 Query / Key / Value；
    2. 计算缩放点积分数 $\text{scores} = QK^\top / \sqrt{d_k}$，
       除以 $\sqrt{d_k}$ 是为了防止点积过大导致 softmax 梯度消失；
    3. 对分数在 key 维度（dim=-1）做 softmax，得到注意力权重；
    4. 用注意力权重对 Value 加权求和得到输出。

    参数：
        X: 输入张量，形状 (batch, seq_len, d_model) 或 (seq_len, d_model)。
        W_q, W_k, W_v: 投影权重，形状均为 (d_model, d_k)（此处取 d_v = d_k）。

    返回：
        output: 注意力输出，形状与输入序列维度一致 (batch, seq_len, d_k)。
        attn_weights: 注意力权重 (batch, seq_len, seq_len)，每行和为 1。
    """

    # --- 1. 线性投影：Q = XW_q, K = XW_k, V = XW_v ---
    Q = X @ W_q  # (…, seq_len, d_k)
    K = X @ W_k  # (…, seq_len, d_k)
    V = X @ W_v  # (…, seq_len, d_k)

    # --- 2. 缩放点积分数 scores = QK^T / sqrt(d_k) ---
    d_k = Q.size(-1)  # 特征维度，用于缩放
    # 注意：用 mT 只转置最后两维，(…, seq_len, d_k) -> (…, d_k, seq_len)
    scores = Q @ K.mT / (d_k**0.5)  # (…, seq_len, seq_len)

    # --- 3. 对最后一维（key 方向）做 softmax 归一化 ---
    attn_weights = F.softmax(scores, dim=-1)  # (…, seq_len, seq_len)，每行和为 1

    # --- 4. 注意力权重加权求和 Value ---
    output = attn_weights @ V  # (…, seq_len, d_k)

    return output, attn_weights


if __name__ == "__main__":
    # ========== 测试输入 ==========
    torch.manual_seed(0)  # 固定随机种子，保证结果可复现

    seq_len, d_model, d_k = 4, 8, 8  # 序列长度 / 输入维度 / 注意力维度

    # 测试 1：单序列输入（无 batch 维）
    X = torch.randn(seq_len, d_model)  # (4, 8)
    W = torch.randn(d_model, d_k)  # (8, 8)，三个投影用同一个权重简化演示
    output, attn = self_attention_single_head(X, W, W, W)
    print(f"单序列: X{X.shape} -> output{output.shape}, attn{attn.shape}")
    print(f"attn 每行和（应为 1）: {attn.sum(dim=-1).tolist()}")

    # 测试 2：带 batch 的输入（深度学习常用形状）
    batch = 2
    X_batch = torch.randn(batch, seq_len, d_model)  # (2, 4, 8)
    output_b, attn_b = self_attention_single_head(X_batch, W, W, W)
    print(f"batch: X{X_batch.shape} -> output{output_b.shape}, attn{attn_b.shape}")
    print(f"attn 每行和（应为 1）: {attn_b.sum(dim=-1).tolist()}")

    # 测试 3：断言检查，验证注意力权重确实归一化
    assert torch.allclose(attn.sum(dim=-1), torch.ones(seq_len), atol=1e-5)
    assert torch.allclose(attn_b.sum(dim=-1), torch.ones(batch, seq_len), atol=1e-5)
    print("全部断言通过 ✓")

```

# 带 Mask 的通用版本

增加一个内容

```

def self_attention_batch(X, W_q, W_k, W_v, mask=None):
...

if mask is not None:
    # 将 mask 中为 0 的位置设为 -inf
    scores = scores.masked_fill(mask == 0, float('-inf'))
...

```

## 多头注意力

$$
\text{scores}_{ij} = \frac{Q_i K_j^\top}{\sqrt{d_k}} +
\begin{cases}
	0 & \text{mask}_{ij} = 1 \\
	-\infty & \text{mask}_{ij} = 0
\end{cases}
$$

```python
import torch
import torch.nn.functional as F


def self_attention_batch(
    X: torch.Tensor,  # 输入 (batch, seq_len, d_model)
    W_q: torch.Tensor,  # Query 权重 (d_model, d_k)
    W_k: torch.Tensor,  # Key 权重 (d_model, d_k)
    W_v: torch.Tensor,  # Value 权重 (d_model, d_v)
    mask: torch.Tensor | None = None,  # (seq_len, seq_len) 或 (batch, seq_len, seq_len)；1=参与 attention，0=屏蔽
) -> tuple[torch.Tensor, torch.Tensor]:
    r"""带 batch 和 mask 的单头自注意力。

    公式与单序列版本相同，只是多了 batch 维：

    $$
    \text{Attention}(Q, K, V) =
    \text{softmax}\left(\frac{QK^\top}{\sqrt{d_k}} + \text{mask}\right) V
    $$

    mask 的作用：把不想 attend 的位置（padding 填充位、未来位置等）在
    softmax 之前设为 $-\infty$，使对应位置的概率变为 0。

    $$
    \text{scores}_{ij} = \frac{Q_i K_j^\top}{\sqrt{d_k}} +
    \begin{cases}
        0 & \text{mask}_{ij} = 1 \\
        -\infty & \text{mask}_{ij} = 0
    \end{cases}
    $$

    参数：
        X: 输入张量 (batch, seq_len, d_model)。
        W_q, W_k, W_v: 投影权重 (d_model, d_k)。
        mask: 注意力掩码，1 表示允许 attend，0 表示屏蔽。
            形状可为 (seq_len, seq_len)（所有 batch 共用）或
            (batch, seq_len, seq_len)（每个样本不同）。
            注意：某一行全为 0 时 softmax 会得到 NaN。

    返回：
        output: 注意力输出 (batch, seq_len, d_k)。
        attn_weights: 注意力权重 (batch, seq_len, seq_len)，每行和为 1。
    """

    # --- 1. 线性投影 ---
    Q = X @ W_q  # (batch, seq_len, d_k)
    K = X @ W_k
    V = X @ W_v

    # --- 2. 缩放点积分数 ---
    d_k = Q.size(-1)
    scores = Q @ K.mT / (d_k**0.5)  # (batch, seq_len, seq_len)

    # --- 3. 应用 mask：把 0 的位置填 -inf ---
    if mask is not None:
        scores = scores.masked_fill(mask == 0, float("-inf"))

    # --- 4. softmax + 加权求和 ---
    attn_weights = F.softmax(scores, dim=-1)  # (batch, seq_len, seq_len)
    output = attn_weights @ V  # (batch, seq_len, d_k)

    return output, attn_weights


def multi_head_attention(
    X: torch.Tensor,  # 输入 (batch, seq_len, d_model)
    W_q: torch.Tensor,  # Query 权重 (d_model, num_heads * head_dim)
    W_k: torch.Tensor,  # Key 权重 (d_model, num_heads * head_dim)
    W_v: torch.Tensor,  # Value 权重 (d_model, num_heads * head_dim)
    num_heads: int = 2,  # 注意力头数
    mask: torch.Tensor | None = None,  # 同 self_attention_batch
    W_o: torch.Tensor | None = None,  # 输出投影 (num_heads*head_dim, d_model)；None 则不投影
) -> tuple[torch.Tensor, torch.Tensor]:
    r"""多头自注意力（手写实现）。

    多头就是把 $d_k$ 维的特征切成 $h$ 份，每个头独立做一次注意力，
    最后拼接起来再做一次线性投影：

    $$
    \text{MultiHead}(Q, K, V) =
    \text{Concat}(\text{head}_1, \dots, \text{head}_h) W_o
    $$

    $$
    \text{head}_i = \text{softmax}\left(
        \frac{(XW_q^i)(XW_k^i)^\top}{\sqrt{d_k}} + \text{mask}
    \right) XW_v^i
    $$

    每个头关注不同的子空间（例如有的头关注局部依赖，有的关注长距离），
    这是 Transformer 里 attention 层的关键设计。

    参数：
        X: 输入张量 (batch, seq_len, d_model)。
        W_q, W_k, W_v: 投影权重 (d_model, num_heads * head_dim)。
        num_heads: 头数，必须整除 W_q 的最后一维。
        mask: 同 self_attention_batch，形状 (seq_len, seq_len) 或
            (batch, seq_len, seq_len)，自动广播到所有头。
        W_o: 输出投影 (num_heads*head_dim, d_model)；传 None 时直接返回拼接结果。

    返回：
        output: 注意力输出 (batch, seq_len, num_heads*head_dim) 或投影后 (batch, seq_len, d_model)。
        attn_weights: 每个头的注意力权重 (batch, num_heads, seq_len, seq_len)。
    """

    batch, seq_len, _ = X.shape
    # 每个头的维度 = 总维度 / 头数
    assert W_q.size(-1) % num_heads == 0, "num_heads 必须整除 W_q 最后一维"
    head_dim = W_q.size(-1) // num_heads

    # --- 1. 线性投影并拆成多头 ---
    # 先投影得到 (batch, seq_len, num_heads*head_dim)
    Q = X @ W_q
    K = X @ W_k
    V = X @ W_v
    # 拆头: (batch, seq_len, num_heads, head_dim) -> 转置 -> (batch, num_heads, seq_len, head_dim)
    # 这样每个头内部就是独立的 (batch, seq_len, head_dim) 矩阵，可并行批量计算
    Q = Q.view(batch, seq_len, num_heads, head_dim).transpose(1, 2)
    K = K.view(batch, seq_len, num_heads, head_dim).transpose(1, 2)
    V = V.view(batch, seq_len, num_heads, head_dim).transpose(1, 2)

    # --- 2. 缩放点积分数（所有头一起算）---
    scores = Q @ K.mT / (head_dim**0.5)  # (batch, num_heads, seq_len, seq_len)

    # --- 3. 应用 mask（自动广播到所有头）---
    if mask is not None:
        scores = scores.masked_fill(mask == 0, float("-inf"))

    # --- 4. 每个头独立 softmax + 加权求和 ---
    attn_weights = F.softmax(scores, dim=-1)  # (batch, num_heads, seq_len, seq_len)
    heads = attn_weights @ V  # (batch, num_heads, seq_len, head_dim)

    # --- 5. 拼接多头并做输出投影 ---
    # 还原维度: (batch, num_heads, seq_len, head_dim) -> (batch, seq_len, num_heads, head_dim)
    # -> view 展平为 (batch, seq_len, num_heads*head_dim)
    concat = heads.transpose(1, 2).contiguous().view(batch, seq_len, num_heads * head_dim)
    output = concat @ W_o if W_o is not None else concat

    return output, attn_weights


def build_causal_mask(seq_len: int) -> torch.Tensor:
    r"""构造因果 mask：只允许 attend 到当前位置及之前的位置。

    $$
    \text{mask}_{ij} = \begin{cases}
        1 & j \le i \quad (\text{当前位置或之前}) \\
        0 & j > i \quad (\text{未来位置，需屏蔽})
    \end{cases}
    $$

    用于自回归解码（GPT 类模型）：生成第 $i$ 个 token 时不能看到
    第 $i+1$ 个及之后的 token。
    """
    # tril 生成下三角全 1 矩阵，上三角为 0
    return torch.tril(torch.ones(seq_len, seq_len, dtype=torch.bool))


if __name__ == "__main__":
    # ========== 测试输入 ==========
    torch.manual_seed(0)
    batch, seq_len, d_model = 2, 6, 8
    d_k = 8

    X = torch.randn(batch, seq_len, d_model)  # (2, 6, 8)
    W = torch.randn(d_model, d_k)  # (8, 8)

    print("=" * 50)
    print("测试 1：batch 单头 + padding mask")
    print("=" * 50)
    # padding mask：屏蔽每个序列的最后一个 token（视为填充位）
    pad_mask = torch.ones(batch, seq_len, seq_len, dtype=torch.bool)
    pad_mask[:, :, -1] = False  # 任何位置都不能 attend 到最后一个 token
    out1, attn1 = self_attention_batch(X, W, W, W, mask=pad_mask)
    print(f"output{out1.shape}, attn{attn1.shape}")
    # 校验：最后一列的注意力权重全为 0（被屏蔽）
    assert (attn1[:, :, -1] == 0).all(), "被屏蔽的 token 不应被 attend"
    # 校验：未屏蔽的行和为 1
    assert torch.allclose(attn1.sum(dim=-1), torch.ones(batch, seq_len), atol=1e-5)
    print(f"✓ 被屏蔽列全为 0，其余行和为 1")

    print("=" * 50)
    print("测试 2：多头注意力 + 因果 mask")
    print("=" * 50)
    num_heads, head_dim = 2, 4
    W_mh = torch.randn(d_model, num_heads * head_dim)  # (8, 8)
    causal = build_causal_mask(seq_len)  # (6, 6) 下三角
    out2, attn2 = multi_head_attention(X, W_mh, W_mh, W_mh, num_heads=num_heads, mask=causal)
    print(f"output{out2.shape}, attn{attn2.shape}")
    # 校验：因果 mask 下注意力矩阵必须是下三角（上三角全为 0）
    upper = torch.triu(attn2, diagonal=1)
    assert (upper == 0).all(), "因果 mask 下不能 attend 未来位置"
    # 校验：每行和为 1（第 i 行至少能 attend 到自己）
    assert torch.allclose(attn2.sum(dim=-1), torch.ones(batch, num_heads, seq_len), atol=1e-5)
    print(f"✓ 上三角全为 0（因果），每行和为 1")
    print(f"  头 0 的注意力权重（batch 0，可看到每个 token 只 attend 自己及之前）:")
    print(attn2[0, 0].round(decimals=2))

    print("=" * 50)
    print("测试 3：多头 + 输出投影 W_o")
    print("=" * 50)
    W_o = torch.randn(num_heads * head_dim, d_model)
    out3, attn3 = multi_head_attention(X, W_mh, W_mh, W_mh, num_heads=num_heads, mask=causal, W_o=W_o)
    print(f"output{out3.shape}（投影回 {d_model} 维）")
    assert out3.shape == (batch, seq_len, d_model)

    print("\n全部断言通过 ✓")
```