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

> 分工：路由由独立的 gate kernel（`bf16_mega_gate`）完成，Mega MoE 主 kernel 只消费它的输出 `topk_idx` / `topk_weights`，自己不做门控。

对 token $x_i$、专家 $e$：

$$
s_{i,e}=\sqrt{\operatorname{softplus}(x_i\cdot w_e^g)},\qquad
\mathcal{T}_i=\operatorname{TopK}_e\{s_{i,e}+b_e\}_{e=1}^{E},\qquad
g_{i,e}=\frac{s_{i,e}}{\sum_{e'\in\mathcal{T}_i}s_{i,e'}+10^{-20}}\,\gamma
$$
- $x_i\in\mathbb{R}^{d}$：第 $i$ 个 token 的隐向量
- $w^{g}_e\in\mathbb{R}^{d}$：专家 $e$ 的门控权重
- $s_{i,e}$：**sqrt-softplus** 激活后的门控分数，$\operatorname{softplus}(u)=\log(1+e^{u})$（实现取数值稳定分支：$u>20$ 时直接取 $u$，否则 `log1p(exp(u))`）
- $b_e$：可选的打分偏置（图像 token 用另一套 `image_bias`），**只参与排序、不进入权重**；无效/填充专家置 $-\infty$
- $\mathcal{T}_i$：按 $s_{i,e}+b_e$ 选出的 TopK 专家集合，$|\mathcal{T}_i|=K$。无偏置时因 sqrt-softplus 单调，等价于直接按原始打分排序，且只对选中的专家做激活
- $g_{i,e}$：对**未加偏置**的 $s_{i,e}$ 在 TopK 内归一化，再乘全局缩放 $\gamma$（`routed_scaling_factor`）；分母的 $10^{-20}$ 用于防零除
- `RoutingArgs` 里另有逻辑→物理专家映射（`to_physical_map`）、重复专家（`num_duplicate_experts`，按 `(rank_idx + token_idx*23333) % num_duplicates` 分散）与共享专家旁路（`num_shared_experts`）

## 专家计算（SwiGLU）

每个专家 $e$ 内部是一个 SwiGLU 前馈：

$$
\mathrm{SwiGLU}_e(x)=(xW_{e,1})\odot\mathrm{SiLU}(xW_{e,3}),
\qquad
\mathrm{SiLU}(u)=u\,\sigma(u)
$$

- $W_{e,1}\in\mathbb{R}^{d\times d_{ff}}$：上投影（gate 分支）
- $W_{e,3}\in\mathbb{R}^{d\times d_{ff}}$：上投影（up 分支，与 gate 分支逐元素相乘）
- $W_{e,2}\in\mathbb{R}^{d_{ff}\times d}$：下投影（在 MoE 求和里乘上，见下）
- $\odot$：逐元素乘
- $\sigma$：sigmoid

严格说 $\mathrm{SwiGLU}_e(x)\in\mathbb{R}^{d_{ff}}$ 是中间激活，完整专家输出还要乘 $W_{e,2}$ 回到 $d$ 维。文档把 `linear1 → SwiGLU → linear2` 融进一个 kernel，所以公式里通常写成：
$$
\mathrm{Expert}_e(x)=\big[(xW_{e,1})\odot\mathrm{SiLU}(xW_{e,3})\big]\,W_{e,2}
$$

## MoE 输出

$$
\mathrm{MoE}(x_i)=\sum_{e\in\mathcal{T}_i}g_{i,e}\,\mathrm{Expert}_e(x_i)
$$

展开为完整形式：

$$
\mathrm{MoE}(x_i)=\sum_{e\in\mathcal{T}_i}g_{i,e}\cdot\Big(\big[(x_iW_{e,1})\odot\mathrm{SiLU}(x_iW_{e,3})\big]W_{e,2}\Big)
$$
```dataviewjs
// ===== Mega MoE 流水线格子图 =====
// 展示: L1 (linear1，产出 gate/up) 与 L2 (linear2/down) 按 N 方向切 cluster 交错
// 用格子表示每个 SM 在时间轴上执行的阶段

// 真实形状由 hidden / intermediate 推得：L1 ∝ 2*intermediate，L2 ∝ hidden
// （DeepSeek-V3: intermediate=2048, hidden=7168 → L1=16, L2=28，即 L1 < L2）
const numL1N = 16;       // L1 (gate+up 两路) 的 N cluster 数
const numL2N = 28;       // L2 (down) 的 N cluster 数
const numMBlocks = 5;    // M block 数
const numSMs = 8;        // 展示用的 SM 数（= 4 个 cluster）
const numClusters = numSMs / 2;  // 2-CTA cluster
const timeSteps = 18;    // 时间轴步数

// 与 get_num_l1_warmup_waves() 一致：两个候选取 max
const warmupWaves = Math.max(
  Math.ceil(Math.ceil(numClusters / numL2N) * numL1N / numClusters),   // 第一波 L2 开始前必须先发的 L1
  Math.ceil((numL1N + (numMBlocks - 1) * Math.max(0, numL1N - numL2N)) / numClusters) + 1
);

// 阶段颜色
const PHASE = {
  IDLE:      { txt: "·",   bg: "#f5f5f5", color: "#aaa" },
  L1:        { txt: "L1",  bg: "#e3f2fd", color: "#1565c0" },
  L2:        { txt: "L2",  bg: "#fce4ec", color: "#c2185b" },
  SHARED_L1: { txt: "sL1", bg: "#e8f5e9", color: "#2e7d32" },
  SHARED_L2: { txt: "sL2", bg: "#fff3e0", color: "#e65100" },
  SYNC:      { txt: "⇄",   bg: "#ede7f6", color: "#4527a0" },
  WARMUP:    { txt: "W",   bg: "#fff9c4", color: "#f57f17" },
};

// 构造一个【示意图】: [sm][t] -> phase key
// 注意：真实派活由 cluster 与 (m_block, n_cluster) 决定，不按 SM 奇偶；
//      这里只示意"warmup 后 L1/L2 按 N 方向交错推进"的节奏。
const grid = [];
for (let sm = 0; sm < numSMs; sm++) grid.push(new Array(timeSteps).fill("IDLE"));

// warmup 阶段: 先集中发 L1
for (let sm = 0; sm < numSMs; sm++) {
  for (let t = 0; t < warmupWaves; t++) grid[sm][t] = "WARMUP";
}

// 交错阶段: L1:L2 ≈ numL1N:numL2N（16:28 = 4:7），按 cluster 偏移错开
const pattern = ["L1", "L2", "L2", "L1", "L2", "L2", "L1", "L2", "L2", "L1", "L2"];
for (let sm = 0; sm < numSMs; sm++) {
  const cluster = Math.floor(sm / 2);
  for (let t = warmupWaves; t < timeSteps; t++) {
    const k = t - warmupWaves;
    grid[sm][t] = pattern[(k + cluster) % pattern.length];
  }
}

const cell = (phase, sm, t) => {
  const p = PHASE[phase];
  const td = document.createElement("td");
  td.textContent = p.txt;
  td.title = `SM ${sm}, t=${t}: ${phase}`;
  td.style.cssText = `
    border:1px solid #ccc; padding:4px 6px; text-align:center;
    font-family:monospace; font-size:11px; background:${p.bg};
    color:${p.color}; min-width:28px; border-radius:3px;`;
  return td;
};

const container = document.createElement("div");
container.style.cssText = "padding:14px; border:1px solid #ccc; border-radius:8px; overflow-x:auto;";

const title = document.createElement("div");
title.textContent = `Mega MoE 流水线（示意）：L1 (linear1，产出 gate/up) ⇄ L2 (linear2/down) 两级交错，前 ${warmupWaves} 步为 warmup`;
title.style.cssText = "font-size:15px; font-weight:bold; margin-bottom:10px;";
container.appendChild(title);

const table = document.createElement("table");
table.style.cssText = "border-collapse:separate; border-spacing:2px;";

// 表头: 时间轴
const thead = document.createElement("thead");
const htr = document.createElement("tr");
const corner = document.createElement("th");
corner.textContent = "SM\\t";
corner.style.cssText = "font-size:11px; padding:4px; color:#555;";
htr.appendChild(corner);
for (let t = 0; t < timeSteps; t++) {
  const th = document.createElement("th");
  th.textContent = t;
  th.style.cssText = "font-size:10px; padding:3px; color:#777; font-weight:normal;";
  htr.appendChild(th);
}
thead.appendChild(htr);
table.appendChild(thead);

// 表体
const tb = document.createElement("tbody");
for (let sm = 0; sm < numSMs; sm++) {
  const tr = document.createElement("tr");
  const smTh = document.createElement("td");
  smTh.textContent = `SM${sm}`;
  smTh.style.cssText = "font-size:11px; padding:3px 6px; color:#555; font-family:monospace;";
  tr.appendChild(smTh);
  for (let t = 0; t < timeSteps; t++) {
    tr.appendChild(cell(grid[sm][t], sm, t));
  }
  tb.appendChild(tr);
}
table.appendChild(tb);
container.appendChild(table);

// 图例
const legend = document.createElement("div");
legend.style.cssText = "margin-top:12px; font-size:12px; display:flex; flex-wrap:wrap; gap:12px;";
for (const [key, p] of Object.entries(PHASE)) {
  if (key === "IDLE") continue;
  const item = document.createElement("div");
  item.style.cssText = "display:flex; align-items:center; gap:4px;";
  const sw = document.createElement("span");
  sw.textContent = p.txt;
  sw.style.cssText = `display:inline-block; padding:2px 6px; background:${p.bg}; color:${p.color};
    border:1px solid #ccc; border-radius:3px; font-family:monospace; font-size:11px;`;
  const lb = document.createElement("span");
  lb.textContent = key;
  item.appendChild(sw);
  item.appendChild(lb);
  legend.appendChild(item);
}
container.appendChild(legend);

// 说明: warmup 防死锁
const note = document.createElement("div");
note.style.cssText = "margin-top:10px; font-size:12px; color:#555; line-height:1.6;";
note.innerHTML = `
<b>为什么需要 warmup 波次：</b><code>get_num_l1_warmup_waves()</code> 取两个候选的最大值——
<code>first = ceil(ceil(num_clusters/num_l2_n) * num_l1_n / num_clusters)</code>（第一波 L2 开始前必须先发出的 L1），
<code>second = ceil((num_l1_n + (M-1)*max(0, num_l1_n - num_l2_n)) / num_clusters) + 1</code>。
L2 的最后一个 M block 需要自己 <code>num_l1_pair_n_blocks</code> 个 L1 任务；前面 ${numMBlocks-1} 个 M block 累计了
<code>max(0, num_l1_n - num_l2_n) = ${Math.max(0, numL1N-numL2N)}</code> 个待发 L1 任务。
DeepSeek-V3 形状下 L1=16 &lt; L2=28，第二项退化为 0，主因是第一项。
若不先把这批 L1 冲出去，L1 会等 L2 释放 ring、L2 又等 L1 产出 → 死锁。
图中前 ${warmupWaves} 步全为 <b>W</b>（warmup），之后按 L1:L2 ≈ ${numL1N}:${numL2N} 交错推进。
<b>图中 sL1 / sL2 / ⇄ 仅在有共享专家等配置时出现，本示意未画。</b>
`;
container.appendChild(note);

dv.container.appendChild(container);
```

# mHC

HyperConnection