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

对每个 query 行 $i$，取 $\tilde{K}$ 中行索引属于 $\mathcal{S}_i$ 的子矩阵 $\tilde{K}_{\mathcal{S}_i}\in \mathbb{R}^{|\mathcal{S}_i|\times D}$

$$
P_h[i,j]=(Q_h\tilde{K}_{\mathcal{S}_i}^\top)[i,\cdot], j\in \mathcal{S}_i
$$

```dataviewjs
// ===== Sparse MQA 实例: P_h = Q_h · K_{S_i}^T =====
const H = 1;
const Sq = 3, D = 2, Skv = 6;

const S = [
  [0, 2, 5],
  [1, 2, 3, 4],
  [0, 5],
];

const Q = [[1, 0], [0, 1], [1, 1]];
const K = [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10], [11, 12]];

const cell = (txt, bg, title) => {
  const td = document.createElement("td");
  td.textContent = txt;
  td.title = title || "";
  td.style.cssText = `
    border:1px solid #888; padding:6px 10px; text-align:center;
    font-family:monospace; font-size:13px; background:${bg};
    min-width:46px; border-radius:4px; cursor:default;`;
  return td;
};

const makeTable = (rows, cols, label, bg, getCell) => {
  const wrap = document.createElement("div");
  wrap.style.cssText = "display:inline-block; margin:4px 8px; vertical-align:middle;";
  const cap = document.createElement("div");
  cap.textContent = label;
  cap.style.cssText = "font-weight:bold; margin-bottom:4px; font-size:12px; color:#444;";
  wrap.appendChild(cap);

  const table = document.createElement("table");
  table.style.cssText = "border-collapse:separate; border-spacing:2px;";
  const tb = document.createElement("tbody");
  for (let i = 0; i < rows; i++) {
    const tr = document.createElement("tr");
    for (let j = 0; j < cols; j++) {
      const r = getCell(i, j);
      tr.appendChild(cell(r.txt, r.bg, r.title));
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

function opSym(s) {
  const d = document.createElement("div");
  d.textContent = s;
  d.style.cssText = "font-size:22px; padding:0 6px; display:inline-block; vertical-align:middle;";
  return d;
}

const container = document.createElement("div");
container.style.cssText = "padding:14px; border:1px solid #ccc; border-radius:8px; overflow-x:auto;";

const title = document.createElement("div");
title.textContent = `Sparse MQA 实例：Q_h (3×2) · K_{S_i}^T ，每行 query 的 S_i 不同`;
title.style.cssText = "font-size:16px; font-weight:bold; margin-bottom:12px;";
container.appendChild(title);

// ---- 顶部：全量 Q_h 与 K ----
const top = document.createElement("div");
top.style.cssText = "display:flex; align-items:flex-start; flex-wrap:wrap; padding-bottom:10px; border-bottom:1px dashed #bbb;";

top.appendChild(makeTable(Sq, D, "Q_h (3×2)", "#e3f2fd", (i, j) => ({
  txt: `q${sub(i)}${sub(j)}=${Q[i][j]}`,
  bg: "#e3f2fd",
  title: `q_${i}${j} = ${Q[i][j]}`
})));

top.appendChild(makeTable(Skv, D, "K (6×2，全量)", "#e8f5e9", (i, j) => ({
  txt: `k${sub(i)}${sub(j)}=${K[i][j]}`,
  bg: "#e8f5e9",
  title: `k_${i}${j} = ${K[i][j]}  (全局 KV 索引 ${i})`
})));

container.appendChild(top);

// ---- 每个 query 行：Q_h[i] × K_{S_i}^T = P_h[i,ℓ] ----
for (let i = 0; i < Sq; i++) {
  const Si = S[i];

  const rowWrap = document.createElement("div");
  rowWrap.style.cssText = "margin-top:14px; padding:8px 0;";

  const rowTitle = document.createElement("div");
  rowTitle.textContent = `query 行 i=${i}   （S_${i} = {${Si.join(", ")}}）`;
  rowTitle.style.cssText = "font-weight:bold; font-size:13px; margin-bottom:6px; color:#333;";
  rowWrap.appendChild(rowTitle);

  const line = document.createElement("div");
  line.style.cssText = "display:flex; align-items:center; flex-wrap:wrap;";

  // Q_h[i] : 1×D
  line.appendChild(makeTable(1, D, `Q_h[i=${i}] (1×2)`, "#e3f2fd", (r, c) => ({
    txt: `q${sub(i)}${sub(c)}=${Q[i][c]}`,
    bg: "#e3f2fd",
    title: `Q_h 第 ${i} 行第 ${c} 列`
  })));

  line.appendChild(opSym("×"));

  // K_{S_i}^T : D×|S_i|，转置后每列是一个选中 KV
  line.appendChild(makeTable(D, Si.length, `K_{S_i}^T (2×${Si.length})`, "#e8f5e9", (r, c) => {
    const j = Si[c]; // 第 c 列 -> 全局 j
    return {
      txt: `k${sub(j)}${sub(r)}=${K[j][r]}`,
      bg: "#e8f5e9",
      title: `第 ${c} 列 -> 全局 KV ${j}；分量 ${r}`
    };
  }));

  line.appendChild(opSym("="));

  // P_h[i,ℓ] : 1×|S_i|
  const pRow = Si.map(j => {
    let s = 0;
    for (let d = 0; d < D; d++) s += Q[i][d] * K[j][d];
    return s;
  });
  line.appendChild(makeTable(1, Si.length, `P_h[i=${i},ℓ] (1×${Si.length})`, "#fce4ec", (r, c) => ({
    txt: `ℓ${sub(c)}=${pRow[c]}`,
    bg: "#fce4ec",
    title: `P_h[${i},ℓ=${c}] = ${pRow[c]}，对应全局 KV j=${Si[c]}`
  })));

  rowWrap.appendChild(line);

  // 映射说明
  const mapDiv = document.createElement("div");
  mapDiv.style.cssText = "font-size:12px; color:#555; margin:6px 0 0 0; font-family:monospace;";
  mapDiv.innerHTML = `ℓ → j : ` + Si.map((j, l) => `${l}→${j}`).join(", ");
  rowWrap.appendChild(mapDiv);

  container.appendChild(rowWrap);
}

// ---- score（ReLU + 头加权，H=1 时 w=1 简化）----
const row3 = document.createElement("div");
row3.style.cssText = "margin-top:14px; padding-top:10px; border-top:1px dashed #bbb;";

const sTitle = document.createElement("div");
sTitle.textContent = "score = ReLU(P_h)  （H=1, w=1 简化）";
sTitle.style.cssText = "font-weight:bold; font-size:13px; margin-bottom:6px; color:#333;";
row3.appendChild(sTitle);

for (let i = 0; i < Sq; i++) {
  const Si = S[i];
  const pRow = Si.map(j => {
    let s = 0;
    for (let d = 0; d < D; d++) s += Q[i][d] * K[j][d];
    return s;
  });
  const score = pRow.map(v => Math.max(0, v));
  const div = document.createElement("div");
  div.style.cssText = "font-family:monospace; font-size:13px; margin:3px 0;";
  div.innerHTML = `行 ${i}: score_{${i},j} = [` +
    Si.map((j, l) => `j=${j}:${score[l]}`).join(", ") + `]`;
  row3.appendChild(div);
}
container.appendChild(row3);

dv.container.appendChild(container);
```

# Mega MoE

## 路由（门控打分与 TopK）

对 token $x_i$、专家 $e$：

$$
g_{i,e}=\text{norm}(x_i \cdot w_e^g),\ \ \ \  \mathcal{T}_i = \text{TopK}_e \{g_{i,e}\}_{e=1}^E
$$
- $x_i\in\mathbb{R}^{d}$：第 $i$ 个 token 的隐向量
- $w^{g}_e\in\mathbb{R}^{d}$：专家 $e$ 的门控权重
- $g_{i,e}\in\mathbb{R}$：token $i$ 对专家 $e$ 的门控分数
- $\mathcal{T}_i$：token $i$ 选中的 TopK 专家集合，$|\mathcal{T}_i|=K$
- `norm` 是门控归一化（如 softmax 或 top-k 归一化），文档未展开具体形式

## 专家计算（SwiGLU）

每个专家 $e$ 内部是一个 SwiGLU 前馈：

$$
\mathrm{SwiGLU}_e(x)=(xW_{e,1})\odot\mathrm{SiLU}(xW_{e,3}),
\qquad
\mathrm{SiLU}(u)=u\,\sigma(u)
$$

- $W_{e,1}\in\mathbb{R}^{d\times d_{ff}}$：上投影（gate 分支）
- $W_{e,3}\in\mathbb{R}^{d\times d_{ff}}$：上投影（value 分支）
- $W_{e,2}\in\mathbb{R}^{d_{ff}\times d}$：下投影（在 MoE 求和里乘上，见下）
- $\odot$：逐元素乘
- $\sigma$：sigmoid

严格说 $\mathrm{SwiGLU}_e(x)\in\mathbb{R}^{d_{ff}}$ 是中间激活，完整专家输出还要乘 $W_{e,2}$ 回到 $d$ 维。文档把 `linear1 → linear2 → SwiGLU` 融进一个 kernel，所以公式里通常写成：
$$
\mathrm{Expert}_e(x)=\big[(xW_{e,1})\odot\mathrm{SiLU}(xW_{e,3})\big]\,W_{e,2}
$$

## MoE 输出

$$
\mathrm{MoE}(x_i)=\sum_{e\in\mathcal{T}_i}g_{i,e}\,\mathrm{SwiGLU}_e(x_i)
$$

展开为完整形式：

$$
\mathrm{MoE}(x_i)=\sum_{e\in\mathcal{T}_i}g_{i,e}\cdot\Big(\big[(x_iW_{e,1})\odot\mathrm{SiLU}(x_iW_{e,3})\big]W_{e,2}\Big)
$$
