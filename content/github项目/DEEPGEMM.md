# GEMM

$$
D=C+AB
$$

GEMM = 分块矩阵乘 + 量化缩放 + 让相邻块共享缓存 + 一个 CTA 连续吃多个块（持久化）

```dataviewjs
// ===== GEMM 格子图: BᵀAᵀ + Cᵀ = Dᵀ =====
// 原 A: m×k, B: k×n, C/D: m×n
// 转置后 Bᵀ: n×k, Aᵀ: k×m, Cᵀ/Dᵀ: n×m
const m = 2, k = 3, n = 4;

const cell = (txt, bg, title) => {
  const td = document.createElement("td");
  td.textContent = txt;
  td.title = title || "";
  td.style.cssText = `
    border:1px solid #888; padding:8px 12px; text-align:center;
    font-family:monospace; font-size:14px; background:${bg};
    min-width:52px; border-radius:4px; cursor:default;`;
  return td;
};

const makeTable = (rows, cols, label, bg, isResult) => {
  const wrap = document.createElement("div");
  wrap.style.cssText = "display:inline-block; margin:10px 18px; vertical-align:top;";
  const cap = document.createElement("div");
  cap.textContent = label;
  cap.style.cssText = "font-weight:bold; margin-bottom:6px; font-size:15px;";
  wrap.appendChild(cap);

  const table = document.createElement("table");
  table.style.cssText = "border-collapse:separate; border-spacing:2px;";
  const tb = document.createElement("tbody");

  for (let i = 0; i < rows; i++) {
    const tr = document.createElement("tr");
    for (let j = 0; j < cols; j++) {
      let txt, title;
      if (isResult) {
        // Dᵀ 的 (i,j) 对应原 D 的 (j,i)
        txt = `Dᵀ${sub(i+1)}${sub(j+1)}`;
        let terms = [];
        for (let p = 1; p <= k; p++) terms.push(`Bᵀ${sub(i+1)}${sub(p)}·Aᵀ${sub(p)}${sub(j+1)}`);
        title = `Dᵀ${sub(i+1)}${sub(j+1)} = Cᵀ${sub(i+1)}${sub(j+1)} + ` + terms.join(" + ");
      } else {
        txt = `${label[0]}${sub(i+1)}${sub(j+1)}`;
        title = txt;
      }
      tr.appendChild(cell(txt, bg, title));
    }
    tb.appendChild(tr);
  }
  table.appendChild(tb);
  wrap.appendChild(table);
  return wrap;
};

function sub(num) {
  const map = {0:"₀",1:"₁",2:"₂",3:"₃",4:"₄",5:"₅",6:"₆",7:"₇",8:"₈",9:"₉"};
  return String(num).split("").map(d => map[d] || d).join("");
}

function opSym(s, css) {
  const d = document.createElement("div");
  d.textContent = s;
  d.style.cssText = css;
  return d;
}

const container = document.createElement("div");
container.style.cssText = "padding:14px; border:1px solid #ccc; border-radius:8px; overflow-x:auto;";

const title = document.createElement("div");
title.textContent = `转置后的 GEMM:  Bᵀ·Aᵀ + Cᵀ = Dᵀ   （Bᵀ: ${n}×${k},  Aᵀ: ${k}×${m}  ⇒  Dᵀ, Cᵀ: ${n}×${m}）`;
title.style.cssText = "font-size:16px; font-weight:bold; margin-bottom:12px;";
container.appendChild(title);

const row = document.createElement("div");
row.style.cssText = "display:flex; align-items:center; flex-wrap:nowrap;";

row.appendChild(makeTable(n, k, "Bᵀ", "#e8f5e9", false));
row.appendChild(opSym("×", "font-size:26px; padding:0 10px;"));
row.appendChild(makeTable(k, m, "Aᵀ", "#e3f2fd", false));
row.appendChild(opSym("+", "font-size:26px; padding:0 10px;"));
row.appendChild(makeTable(n, m, "Cᵀ", "#fff3e0", false));
row.appendChild(opSym("=", "font-size:26px; padding:0 10px;"));
row.appendChild(makeTable(n, m, "Dᵀ", "#fce4ec", true));

container.appendChild(row);
dv.container.appendChild(container);
```

<b>怎么看这张图：</b><br>
-  每格是一个标量。悬停 D 的格子可看到完整的展开式，例如
  D₁₁ = C₁₁ + A₁₁·B₁₁ + A₁₂·B₂₁ + A₁₃·B₃₁。
- 结果 D 的第 (i,j) 格 = C 的同位置格 + A 第 i 行 与 <b>B 第 j 列</b> 的逐项乘积和（K= ${k}$ 项）
- 行数关系：A 的行数(${m}$) = D 的行数；B 的列数(${n}$) = D 的列数；中间维度 K(${k}$) 在相乘时被"消掉"。
- 在 GPU 里，这些格子会被切成 tile（如 BLOCK_M×BLOCK_N），分给不同 SM 并行算，A/B 的 tile 通过 TMA 搬进 shared memory 的环里。

# MQA

1. KV 缩放（逐渐 Token 还原）
$$
\tilde{K} = \text{diag}(2^{s^{kv}})K
$$
其中 $K,\tilde{K}\in \mathbb{R}^{S_{kv}\times D}$

2. 每个头的点积

对第 $h$ 个头，query 矩阵 $Q_h\in \mathbb{R}^{S_q\times D}$：

$$
P_h = Q_h \tilde{K}^\top \in \mathbb{R}^{S_q\times S_{kv}}
$$
经过 ReLU

$$
P_h^+ = \text{ReLU}(P_h) \in \mathbb{R}^{S_q\times S_{kv}}
$$
头加权求和

$$
\text{score}= \sum_{h=1}^H P_h^+ \odot (1_{S_{kv}} w^\top_{:,h})
$$

其中 $w_{:,h}\in\mathbb{R}^{S_q}$ 是第 $h$ 个头的权重列，$1_{S_{kv}}$ 是全 1 列向量，$\odot$ 是逐元素乘，结果 $\text{score} \in \mathbb{R}^{S_q \times S_{kv}}$

# Sparse MQA


与 MQA 的区别只在第 $h$ 个头的点积（只在选中的 KV 上）

对每个 query 行 