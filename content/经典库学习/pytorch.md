
# 单头，无 batch

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