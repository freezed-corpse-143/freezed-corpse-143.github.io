
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

# MLA 多头潜在注意力

标准 MHA 每个 token 要缓存所有头的 K 和 V（$2 \times n_h \times d_h$
个浮点数），序列一长 KV cache 就爆炸。MLA 的核心思路：
把 K 和 V 联合压缩成一个低维潜在向量，只缓存它。

对第 $t$ 个 token：

$$
c_t^{KV} = W^{DKV} h_t \qquad
k_t^C = W^{UK} c_t^{KV}, \quad
v_t^C = W^{UV} c_t^{KV}
$$

Query 同样先压缩再升维：

$$
c_t^Q = W^{DQ} h_t \qquad
q_t^C = W^{UQ} c_t^Q
$$

RoPE 依赖位置、无法折进低秩压缩，所以 MLA 把旋转位置编码解耦出来：

$$
q_t^R = \text{RoPE}(W^{QR} c_t^Q), \qquad
k_t^R = \text{RoPE}(W^{KR} h_t)
$$

最终拼接 content 与 rotary 两部分算注意力：

$$
q_t = [q_t^C;\, q_t^R], \quad k_t = [k_t^C;\, k_t^R], \qquad
o_t = \sum_{i \le t} \text{softmax}_i\!\left(
	\frac{q_t^\top k_i}{\sqrt{d_h + d_h^R}}
\right) v_i^C
$$

缓存对比（每 token）：标准 MHA 缓存 $2 n_h d_h$；MLA 只缓存
$c_t^{KV}$（$d_c$ 维）+ $k_t^R$（$n_h d_h^R$ 维），通常 $d_c \ll n_h d_h$。
推理时还可把 $W^{UK}$ 吸收进 $W^{UQ}$（$q^{C\top} k^C =
c^{Q\top}(W^{UQ\top}W^{UK})c^{KV}$），连升维都省掉。


```python
import torch
import torch.nn.functional as F

from multi_head_attention import build_causal_mask  # 复用上一文件的因果 mask


def rotary_embedding(x: torch.Tensor, theta: float = 10000.0) -> torch.Tensor:
    r"""旋转位置编码 RoPE（Rotary Position Embedding）。

    对最后一维按相邻两元素成对旋转。位置 $m$ 处、频率 $\theta_j$ 的旋转：

    $$
    \begin{pmatrix} x'_{2j} \\ x'_{2j+1} \end{pmatrix}
    = \begin{pmatrix}
        \cos(m\theta_j) & -\sin(m\theta_j) \\
        \sin(m\theta_j) & \cos(m\theta_j)
    \end{pmatrix}
    \begin{pmatrix} x_{2j} \\ x_{2j+1} \end{pmatrix},
    \qquad \theta_j = \theta^{-2j/d}
    $$

    关键性质：两个向量的内积只取决于**相对位置**，因此位置信息天然融入
    注意力分数，且不增加可学习参数。

    参数：
        x: 输入张量 (..., seq_len, d)，d 必须为偶数。
        theta: 基频（base），控制频率跨度。

    返回：
        旋转后的张量，形状不变。
    """

    d = x.size(-1)
    seq_len = x.size(-2)
    assert d % 2 == 0, "最后一维必须为偶数（按对旋转）"

    # 频率: (d/2,)，位置: (seq_len,)，外积得到每个位置每对维度的旋转角
    freqs = 1.0 / (theta ** (torch.arange(0, d, 2, dtype=torch.float32) / d))
    positions = torch.arange(seq_len, dtype=torch.float32)
    angles = positions[:, None] * freqs[None, :]  # (seq_len, d/2)
    cos = angles.cos()
    sin = angles.sin()

    # 拆成相邻对: (..., seq_len, d/2, 2)
    x_pairs = x.float().reshape(*x.shape[:-1], -1, 2)
    x0, x1 = x_pairs[..., 0], x_pairs[..., 1]

    # 旋转公式（cos/sin 自动广播到 batch/head 维）
    rotated = torch.stack(
        [x0 * cos - x1 * sin, x0 * sin + x1 * cos], dim=-1
    )
    return rotated.reshape_as(x).type_as(x)


def multi_head_latent_attention(
    X: torch.Tensor,  # 输入 (batch, seq_len, d_model)
    W_dkv: torch.Tensor,  # KV 下投影 (d_model, d_c)，把 K/V 压缩到 d_c 维潜在空间
    W_uk: torch.Tensor,  # Key 上投影 (d_c, n_h * d_h)
    W_uv: torch.Tensor,  # Value 上投影 (d_c, n_h * d_h)
    W_dq: torch.Tensor,  # Query 下投影 (d_model, d_c')
    W_uq: torch.Tensor,  # Query 上投影 (d_c', n_h * d_h)
    W_qr: torch.Tensor,  # 旋转 Query 投影 (d_c', n_h * d_h^R)
    W_kr: torch.Tensor,  # 旋转 Key 投影 (d_model, n_h * d_h^R)
    num_heads: int,  # 头数 n_h
    head_dim: int,  # 每头内容维度 d_h
    rotary_dim: int,  # 每头旋转位置编码维度 d_h^R
    rope_theta: float = 10000.0,  # RoPE 基频
    mask: torch.Tensor | None = None,  # 同前两个文件，1=允许 attend
    W_o: torch.Tensor | None = None,  # 输出投影 (n_h*d_h, d_model)，None 则不投影
) -> tuple[torch.Tensor, torch.Tensor]:
    r"""多头潜在注意力 MLA（DeepSeek-V2 提出，V3/R1 沿用）。

    标准 MHA 每个 token 要缓存所有头的 K 和 V（$2 \times n_h \times d_h$
    个浮点数），序列一长 KV cache 就爆炸。MLA 的核心思路：
    把 K 和 V 联合压缩成一个低维潜在向量，只缓存它。

    对第 $t$ 个 token：

    $$
    c_t^{KV} = W^{DKV} h_t \qquad
    k_t^C = W^{UK} c_t^{KV}, \quad
    v_t^C = W^{UV} c_t^{KV}
    $$

    Query 同样先压缩再升维：

    $$
    c_t^Q = W^{DQ} h_t \qquad
    q_t^C = W^{UQ} c_t^Q
    $$

    RoPE 依赖位置、无法折进低秩压缩，所以 MLA 把旋转位置编码解耦出来：

    $$
    q_t^R = \text{RoPE}(W^{QR} c_t^Q), \qquad
    k_t^R = \text{RoPE}(W^{KR} h_t)
    $$

    最终拼接 content 与 rotary 两部分算注意力：

    $$
    q_t = [q_t^C;\, q_t^R], \quad k_t = [k_t^C;\, k_t^R], \qquad
    o_t = \sum_{i \le t} \text{softmax}_i\!\left(
        \frac{q_t^\top k_i}{\sqrt{d_h + d_h^R}}
    \right) v_i^C
    $$

    缓存对比（每 token）：标准 MHA 缓存 $2 n_h d_h$；MLA 只缓存
    $c_t^{KV}$（$d_c$ 维）+ $k_t^R$（$n_h d_h^R$ 维），通常 $d_c \ll n_h d_h$。
    推理时还可把 $W^{UK}$ 吸收进 $W^{UQ}$（$q^{C\top} k^C =
    c^{Q\top}(W^{UQ\top}W^{UK})c^{KV}$），连升维都省掉。

    参数：
        X: 输入 (batch, seq_len, d_model)。
        W_dkv/W_uk/W_uv/W_dq/W_uq/W_qr/W_kr: 各投影权重，形状见签名注释。
        num_heads/head_dim/rotary_dim: 结构参数。
        rope_theta: RoPE 基频。
        mask: 同前，自动广播到所有头。
        W_o: 可选输出投影。

    返回：
        output: (batch, seq_len, n_h*d_h) 或投影后 (batch, seq_len, d_model)。
        attn_weights: (batch, n_h, seq_len, seq_len)，每头每行和为 1。
    """

    batch, seq_len, _ = X.shape
    n_h, d_h, d_h_r = num_heads, head_dim, rotary_dim
    d_c = W_dkv.size(-1)  # KV 潜在维度
    d_c_q = W_dq.size(-1)  # Query 潜在维度

    # --- 1. KV 联合压缩（MLA 的核心）---
    # c_t^KV 就是每个 token 需要缓存的潜在向量，后续 K/V 都由它升维还原
    C_kv = X @ W_dkv  # (b, s, d_c)  ← 缓存它
    K_c = (C_kv @ W_uk).view(batch, seq_len, n_h, d_h).transpose(1, 2)  # (b, n_h, s, d_h)
    V_c = (C_kv @ W_uv).view(batch, seq_len, n_h, d_h).transpose(1, 2)

    # --- 2. Query 压缩 ---
    C_q = X @ W_dq  # (b, s, d_c')
    Q_c = (C_q @ W_uq).view(batch, seq_len, n_h, d_h).transpose(1, 2)

    # --- 3. 解耦的旋转 query/key（RoPE 只作用在这部分）---
    Q_r = (C_q @ W_qr).view(batch, seq_len, n_h, d_h_r).transpose(1, 2)
    K_r = (X @ W_kr).view(batch, seq_len, n_h, d_h_r).transpose(1, 2)
    Q_r = rotary_embedding(Q_r, rope_theta)  # (b, n_h, s, d_h^R)
    K_r = rotary_embedding(K_r, rope_theta)  # ← K_r 也需要缓存（配合未来的 query 算分数）

    # --- 4. 拼接 content + rotary 两部分，计算注意力 ---
    Q = torch.cat([Q_c, Q_r], dim=-1)  # (b, n_h, s, d_h + d_h^R)
    K = torch.cat([K_c, K_r], dim=-1)
    scores = Q @ K.mT / ((d_h + d_h_r) ** 0.5)  # (b, n_h, s, s)，缩放用总维度

    if mask is not None:
        scores = scores.masked_fill(mask == 0, float("-inf"))

    attn_weights = F.softmax(scores, dim=-1)

    # --- 5. 加权求和：只对 content 部分 V 求加权（rotary 维度不参与输出）---
    heads = attn_weights @ V_c  # (b, n_h, s, d_h)

    # --- 6. 拼接多头 + 可选输出投影 ---
    concat = heads.transpose(1, 2).contiguous().view(batch, seq_len, n_h * d_h)
    output = concat @ W_o if W_o is not None else concat

    return output, attn_weights


if __name__ == "__main__":
    # ========== 测试输入 ==========
    torch.manual_seed(0)
    batch, seq_len, d_model = 2, 8, 32  # 输入形状
    n_h, d_h, d_h_r = 4, 8, 4  # 4 头，每头内容 8 维、旋转 4 维
    d_c, d_c_q = 16, 16  # KV/Query 潜在维度（远小于 n_h*d_h = 32，体现压缩）

    X = torch.randn(batch, seq_len, d_model)
    scale = 0.1  # 权重缩放，避免 softmax 过于尖锐
    W_dkv = torch.randn(d_model, d_c) * scale
    W_uk = torch.randn(d_c, n_h * d_h) * scale
    W_uv = torch.randn(d_c, n_h * d_h) * scale
    W_dq = torch.randn(d_model, d_c_q) * scale
    W_uq = torch.randn(d_c_q, n_h * d_h) * scale
    W_qr = torch.randn(d_c_q, n_h * d_h_r) * scale
    W_kr = torch.randn(d_model, n_h * d_h_r) * scale

    print("=" * 50)
    print("测试 1：MLA 前向 + 因果 mask")
    print("=" * 50)
    causal = build_causal_mask(seq_len)
    out, attn = multi_head_latent_attention(
        X, W_dkv, W_uk, W_uv, W_dq, W_uq, W_qr, W_kr,
        n_h, d_h, d_h_r, mask=causal,
    )
    print(f"output{out.shape}, attn{attn.shape}")
    assert out.shape == (batch, seq_len, n_h * d_h)
    assert attn.shape == (batch, n_h, seq_len, seq_len)
    assert (torch.triu(attn, diagonal=1) == 0).all(), "因果 mask 下不能 attend 未来"
    assert torch.allclose(attn.sum(-1), torch.ones(batch, n_h, seq_len), atol=1e-5)
    print("✓ 形状正确、因果性正确、每行和为 1")

    print("=" * 50)
    print("测试 2：RoPE 性质（相对位置不变性 + 范数保持）")
    print("=" * 50)
    # 固定一对向量 q、k，让它们分别出现在位置 (5,3) 和 (2,0)——相对位置差都是 2
    q_vec, k_vec = torch.randn(4), torch.randn(4)
    v = torch.zeros(1, 6, 1, 4)
    v[:, 5], v[:, 2] = q_vec, q_vec
    v[:, 3], v[:, 0] = k_vec, k_vec
    r = rotary_embedding(v)
    # 内积只依赖相对位置：<q@5, k@3> 应等于 <q@2, k@0>（相对位置差都是 2）
    rel_a = (r[:, 5] * r[:, 3]).sum()
    rel_b = (r[:, 2] * r[:, 0]).sum()
    assert torch.allclose(rel_a, rel_b, atol=1e-5)
    print(f"相对位置差 2 的两组内积: {rel_a.item():.4f} == {rel_b.item():.4f}")
    # 旋转不改变向量长度
    assert torch.allclose(r.norm(dim=-1), v.norm(dim=-1), atol=1e-5)
    print("✓ 内积仅依赖相对位置、旋转保持范数")

    print("=" * 50)
    print("测试 3：KV cache 对比")
    print("=" * 50)
    mha_cache = 2 * n_h * d_h
    mla_cache = d_c + n_h * d_h_r
    print(f"标准 MHA: 2×{n_h}×{d_h} = {mha_cache} floats/token")
    print(f"MLA: d_c({d_c}) + n_h×d_h^R({n_h}×{d_h_r}) = {mla_cache} floats/token")
    print(f"本示例节省 {mha_cache / mla_cache:.2f}×")
    # DeepSeek-V2 论文真实配置（n_h=128, d_h=128, d_c=512, d_h^R=64）
    real_mha = 2 * 128 * 128
    real_mla = 512 + 128 * 64
    print(f"DeepSeek-V2 真实配置: {real_mha} -> {real_mla} = {real_mha / real_mla:.2f}×")

    print("=" * 50)
    print("测试 4：输出投影 W_o")
    print("=" * 50)
    W_o = torch.randn(n_h * d_h, d_model) * scale
    out4, _ = multi_head_latent_attention(
        X, W_dkv, W_uk, W_uv, W_dq, W_uq, W_qr, W_kr,
        n_h, d_h, d_h_r, mask=causal, W_o=W_o,
    )
    assert out4.shape == (batch, seq_len, d_model)
    print(f"output{out4.shape}（投影回 {d_model} 维）✓")

    print("\n全部断言通过 ✓")

```