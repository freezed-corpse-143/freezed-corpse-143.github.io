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

HyperConnection：把 token 的隐状态展成 $R$ 条「路由」（route），在层间做**混合 → 归一化 → 归一化输出**。DeepGEMM 的 `mega_mhc` 把下一层的混合系数生成、路由重组合、RMSNorm 与 FP8 量化融进一个 kernel。

## 记号

| 符号 | 含义 | 代码/形状 |
|---|---|---|
| $T$ | token 数 | `num_tokens` |
| $H$ | 隐维 | `kHidden` |
| $R$ | 路由数，默认 **4** | `hc_mult` / `kNumRoutes` |
| $x_{i,h}$ | 第 $i$ 个 token 的隐向量 | `x [T,H]` BF16 |
| $\tilde R_{i,r,h}$ | 路由残差栈 | `residual [T,R,H]` BF16 |
| $W=\mathrm{fn}$ | 生成混合系数的权重 | `fn [R(R+2), R·H]` FP32 |
| $s_{0,1,2}$ | 三组缩放 | `mix_scales [3]` FP32 |
| $b_\ell$ | 通道偏置 | `mix_bases [R(R+2)]` FP32 |
| $\varepsilon_{\text{hc}},\varepsilon_{\text{pre}},\varepsilon_{\text{sk}},\varepsilon_{\text{rms}}$ | 各处 eps | `hc_norm_eps` / `hc_pre_eps` / `sinkhorn_eps` / `rmsnorm_eps` |
| $\gamma_{\text{post}}$ | post 缩放 | `hc_post_scale` |
| $\kappa$ | Sinkhorn 迭代次数 | `num_sinkhorn_iters` |

## 数据流（先看顺序）

一次 kernel 调用同时做两件事：

1. **消费**上一层传入的 $(p,q,M)$，把 $x$ 与残差栈 $\tilde R$ 组合成本层的路由栈 $u$；
2. **生产**下一层的 $(p,q,M)$：用 $u$ 做 GEMM 与 Sinkhorn。

所以 $(p,q,M)$ 在"组合"里是**输入**，在"Sinkhorn"里是**输出**。

## 第 1 步：组合路由栈

$$
u_{i,o,h}=q_{i,o}\,x_{i,h}+\sum_{r=1}^{R}M_{i,r,o}\,\tilde R_{i,r,h}
$$

结果先**舍入到 BF16** 再往下走——代码注释明确这是所有消费者的公共数值边界：

> "this BF16 round is the shared numerical boundary for all consumers"

## 第 2 步：u 的 RMS 缩放与混合 logits

$$
\sigma_i=\Big(\frac{1}{R H}\sum_{r=1}^{R}\sum_{h=1}^{H}u_{i,r,h}^{2}+\varepsilon_{\text{hc}}\Big)^{-1/2},
\qquad
z_{i,\ell}=\sum_{r=1}^{R}\sum_{h=1}^{H}\mathrm{fn}_{\ell,\,(r-1)H+h}\;u_{i,r,h}
$$

对应 `hc_rms_scale = rsqrtf(hc_norm_sqr_sum / (kNumRoutes*kHidden) + hc_norm_eps)`。GEMM 的 K 维长度是 $R\cdot H$，沿 K 切成 `kNumSplits` 段（默认 16）并行；`gemm_partials [num_m_blocks, kNumSplits, BLOCK_M, R(R+2)]` 与 `hc_norm_sqr_sum_partials` 都是跨 split 的部分和。

## 第 3 步：仿射

$$
\alpha_{i,\ell}=z_{i,\ell}\cdot\sigma_i\cdot s_{g(\ell)}+b_\ell,
\qquad
g(\ell)=
\begin{cases}
0, & \ell<R \quad(\text{Pre})\\
1, & R\le\ell<2R \quad(\text{Post})\\
2, & 2R\le\ell<R(R+2) \quad(\text{Comb})
\end{cases}
$$

## 第 4 步：Pre / Post 系数

$$
p_{i,o}=\mathrm{sigmoid}(\alpha_{i,o})+\varepsilon_{\text{pre}},
\qquad
q_{i,o}=\mathrm{sigmoid}(\alpha_{i,R+o})\cdot\gamma_{\text{post}},
\qquad o=1,\dots,R
$$

注意 Post 是**乘** `hc_post_scale`，Pre 是**加** `hc_pre_eps`——两者不对称，代码里就是这样分的。

## 第 5 步：Comb 矩阵的 Sinkhorn 归一化

把后 $R^2$ 个通道排成 $R\times R$ 矩阵 $A$：

$$
A_{i,r,o}=\alpha_{i,\,2R+(r-1)R+o}
$$

先按**输出路由 $o$** 逐行 softmax，再做交替的行/列归一化（让矩阵近似双随机）：

$$
M^{(0)}_{i,r,o}=\operatorname*{softmax}_{o'}\big(A_{i,r,o'}\big)+\varepsilon_{\text{sk}},
\qquad
M\leftarrow\frac{M}{\sum_{r'}M_{i,r',o}+\varepsilon_{\text{sk}}}
$$

$$
\text{for } t=1,\dots,\kappa-1:\quad
M\leftarrow\frac{M}{\sum_{o'}M_{i,r,o'}+\varepsilon_{\text{sk}}},
\quad
M\leftarrow\frac{M}{\sum_{r'}M_{i,r',o}+\varepsilon_{\text{sk}}}
$$

即「1 次行 softmax → 1 次列归一 → $(\kappa-1)$ 次（行、列）归一」。列求和在 warp 内用两次 `shfl_xor`（先翻转行号低位、再翻转次低位）合成 4 行的列和。

## 第 6 步：token 输出

$$
\tilde y_{i,h}=\sum_{o=1}^{R}p_{i,o}\,u_{i,o,h}
$$

两条路径的式子相同，差别在 $p$ 从哪来：

| | shifted | normal |
|---|---|---|
| $p$ 来源 | 上一层传入的 `shifted_prev_mix` | 本次由 $u$ 现场算（sigmoid $+\varepsilon_{\text{pre}}$） |
| $q$、$M$ 来源 | 上一层传入 | 上一层传入 |
| 归一化时机 | Post worker 先把 $x_1$ 落盘，Norm worker 再读回来做 RMSNorm | Norm worker 直接读 $u$ 组合后做 RMSNorm |
| `new_prev_mix` | 写 | 不写 |

## 第 7 步：RMSNorm + 量化

$$
\hat y_{i,h}=\tilde y_{i,h}\cdot
\underbrace{\Big(\frac{1}{H}\sum_{h'=1}^{H}\tilde y_{i,h'}^{2}+\varepsilon_{\text{rms}}\Big)^{-1/2}s_{\text{rms}}}_{\text{rms scale}}\cdot w_h
$$

- normal 路径的 RMS 用**已舍入到 BF16** 的值算；shifted 路径用 BF16 的 $x_1$ 算，保证与下游消费者看到的一致。
- 输出可同时给 BF16 与 FP8 E4M3；FP8 用 `gran_k=32`、4 个 UE8M0 打包进一个 `int32`，并支持三种 SF 布局（`y_gemm_sf` 列主 TMA 对齐 / `y_routed_sf` 行主连续 / `y_shared_sf` Mega MoE 共享专家布局）。

## 输出张量

| 输出 | 公式 |
|---|---|
| `new_residual [T,R,H]` | $u$（BF16） |
| `new_prev_mix [T,R,1]` | $p$（仅 shifted 写） |
| `new_post_mix [T,R,1]` | $q$ |
| `new_comb_res_mix [T,R,R]` | $M$ |
| `y_bf16` / `y_fp8` | $\hat y$ |

## 为什么是 $R(R+2)=24$

$R(R+2)$ 就是三类系数的总数：

$$
\underbrace{R}_{\text{Pre}}+\underbrace{R}_{\text{Post}}+\underbrace{R\times R}_{\text{Comb}}=4+4+16=24
$$

这正是 `kNumHCOutputs = kNumRoutes * (kNumRoutes + 2)`，也是 GEMM 的 `BLOCK_N`。

## 实现落点

| 位置 | 内容 |
|---|---|
| `layout/mega_mhc.cuh` | $R=4$、$R(R+2)=24$、`BLOCK_M=64/BLOCK_K=64`、split-K workspace 布局 |
| `epilogue/sm100_mega_mhc.cuh:17` | `run_mix_task`：跨 split 归约 logits 与平方和、sigmoid、Sinkhorn |
| `epilogue/sm100_mega_mhc.cuh:332` | shifted 路径的 RMS scale |
| `epilogue/sm100_mega_mhc.cuh:220` | normal 路径的 RMS scale（先 BF16 舍入） |
| `impls/sm100_mega_mhc.cuh:489-523` | 第 1/6 步：$u$ 与 $x_1$ 的累加、BF16 舍入、平方和 |
| `scheduler/mega_mhc.cuh` | `Norm` / `Mix` 两道 split barrier + epoch 标记 |

> 补充：`sinkhorn_eps` 同时出现在初始 softmax（`+ε`）和后续归一化（除以 `sum+ε`）里，作用不同——前者避免 logits 为常数时除零，后者避免行列和为零。

---

## 流程图（一图看懂）

```dataviewjs
const R = 4;
const total = R * (R + 2);
const uid = `mhc-${Math.random().toString(36).slice(2, 10)}`;
const colors = ["#60a5fa", "#34d399", "#fb923c", "#c084fc"];
const routeColor = i => colors[i % colors.length];

const esc = s => String(s)
  .replace(/&/g, "&amp;")
  .replace(/</g, "&lt;")
  .replace(/"/g, "&quot;");

const holder = document.createElement("div");
holder.className = uid;

holder.innerHTML = `
<style>
.${uid} {
  --fg: var(--text-normal, #263244);
  --muted: var(--text-muted, #738094);
  --surface: var(--background-primary, #fff);
  --panel: var(--background-secondary, #f5f7fa);
  --border: var(--background-modifier-border, #dde3eb);
  margin: 12px 0;
}
.${uid} .frame {
  overflow-x: auto;
  padding: 16px 12px;
  border: 1px solid var(--border);
  border-radius: 18px;
  background: var(--surface);
}
.${uid} svg {
  display: block;
  width: 100%;
  min-width: 780px;
  max-width: 1080px;
  height: auto;
  margin: auto;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
    "PingFang SC", "Microsoft YaHei", sans-serif;
}
.${uid} .cell {
  transition: fill-opacity .15s ease, stroke-opacity .15s ease;
}
.${uid} .cell:hover {
  fill-opacity: .3;
  stroke-opacity: 1;
}
</style>
<div class="frame"></div>
`;

let g = "";

const text = (
  x, y, value, size = 12,
  fill = "var(--fg)", anchor = "start", weight = 400
) => `<text x="${x}" y="${y}" fill="${fill}"
  font-size="${size}" text-anchor="${anchor}" font-weight="${weight}"
  >${esc(value)}</text>`;

const rect = (
  x, y, w, h,
  fill = "var(--surface)", stroke = "var(--border)", radius = 12
) => `<rect x="${x}" y="${y}" width="${w}" height="${h}"
  rx="${radius}" fill="${fill}" stroke="${stroke}"/>`;

const cell = (x, y, w, h, color, label, size = 12, title = label) => `
  <g>
    <title>${esc(title)}</title>
    <rect class="cell" x="${x}" y="${y}" width="${w}" height="${h}"
      rx="8" fill="${color}" fill-opacity=".12"
      stroke="${color}" stroke-opacity=".65"/>
    ${text(x + w / 2, y + h / 2 + 4, label, size, color, "middle", 600)}
  </g>`;

const path = (d, color = "var(--muted)", width = 1.6, arrow = true) =>
  `<path d="${d}" fill="none" stroke="${color}"
    stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round"
    ${arrow ? `marker-end="url(#${uid}-arrow)"` : ""}/>`;

const dashed = (d, color = "var(--muted)", width = 1.2) =>
  `<path d="${d}" fill="none" stroke="${color}"
    stroke-width="${width}" stroke-dasharray="4 5"
    marker-end="url(#${uid}-arrow)"/>`;

const panel = (x, y, w, h, step, title, subtitle, accent) => {
  g += rect(x, y, w, h, "var(--panel)", "var(--border)", 16);
  g += cell(x + 18, y + 18, 28, 28, accent, step, 12);
  g += text(x + 57, y + 37, title, 15, "var(--fg)", "start", 650);
  g += text(x + 18, y + 69, subtitle, 11, "var(--muted)");
};

// ---------- 标题 ----------
g += text(28, 34, "mHC · 路由与系数", 22, "var(--fg)", "start", 700);
g += text(28, 59, "Pre 作用于分流前，Post 汇合后加回，Comb 做路由间混合", 12, "var(--muted)");
g += cell(834, 18, 138, 34, "#a78bfa", `R = ${R}  ·  ${total} 个系数`, 12);

// ---------- 三个主面板 ----------
panel(28, 86, 246, 420, "01", "并行路由",
  `残差栈 R̃ · [T, ${R}, H]`, "#60a5fa");
panel(298, 86, 306, 420, "02", "路由间混合",
  "行：输入路由 r    列：输出路由 o", "#a78bfa");
panel(628, 86, 344, 420, "03", "系数分组",
  `${total} = ${R} Pre + ${R} Post + ${R * R} Comb`, "#2dd4bf");

// ---------- 左侧：输入 → Pre → 分流 ----------
g += cell(62, 160, 178, 38, "#94a3b8", "输入 x · [T, H]", 13);

// Pre 作用节点：p ⊙ x
g += cell(74, 208, 166, 32, "#14b8a6", "p ⊙ x", 13,
  "Pre 系数 p 逐通道作用于输入 x，结果再分流进 R 条路由");
g += path("M 151 198 V 208", "#14b8a6", 1.5);
g += text(246, 229, "Pre", 10, "#14b8a6", "start", 600);

// 从 p⊙x 分流
const routeStart = 268;
const routeStep = Math.min(41, 160 / Math.max(R - 1, 1));
const routeHeight = Math.min(32, routeStep - 6);
const lastCenter = routeStart + (R - 1) * routeStep + routeHeight / 2;

g += path("M 157 240 V 252 H 48", "#94a3b8", 1.5, false);
g += path(`M 48 252 V ${lastCenter}`, "#94a3b8", 1.5, false);

for (let r = 0; r < R; r++) {
  const y = routeStart + r * routeStep;
  const cy = y + routeHeight / 2;
  const color = routeColor(r);

  g += path(`M 48 ${cy} H 70`, color, 1.5);
  g += cell(74, y, 166, routeHeight, color, `路由 ${r + 1} · R̃[${r + 1}]`, 12);

  g += path(
    `M 240 ${cy} C 272 ${cy}, 282 ${225 + r * 41}, 320 ${225 + r * 41}`,
    color, 1.4
  );
}

// Pre 系数行 → p⊙x 节点的连线
g += dashed("M 704 196 H 660 V 228 H 244", "#14b8a6", 1.2);
g += text(452, 218, "p 来自右侧 Pre 行", 9, "#14b8a6", "middle", 500);

// ---------- 中间：矩阵 ----------
const mx = 354, my = 225;
const matrixSize = 164;
const pitch = matrixSize / R;
const box = pitch - 5;

g += text(436, 202, `M · ${R} × ${R}`, 15, "#a78bfa", "middle", 700);

for (let r = 0; r < R; r++) {
  const color = routeColor(r);

  g += text(mx - 12, my + r * pitch + box / 2 + 4,
    `r${r + 1}`, 11, color, "end", 600);

  for (let o = 0; o < R; o++) {
    g += cell(mx + o * pitch, my + r * pitch, box, box, color,
      `${r + 1},${o + 1}`, 11,
      `M[${r + 1}, ${o + 1}]：输入路由 ${r + 1} → 输出路由 ${o + 1}`);
  }
}

for (let o = 0; o < R; o++) {
  g += text(mx + o * pitch + box / 2, my + matrixSize + 16,
    `o${o + 1}`, 11, "var(--muted)", "middle");
}

g += text(451, 441, "每个输出路由汇合所有输入路由", 11,
  "var(--muted)", "middle");

// ---------- 右侧：系数 ----------
const sx = 704, sw = 236;
const gap = 7;
const cw = Math.min(48, (sw - (R - 1) * gap) / R);

function coefficientRow(y, label, symbol, color, note) {
  g += text(650, y + 23, label, 12, color, "start", 650);
  for (let i = 0; i < R; i++) {
    g += cell(sx + i * (cw + gap), y, cw, 34,
      color, `${symbol}${i + 1}`, 11);
  }
  if (note) g += text(650, y + 46, note, 9, "var(--muted)");
}

coefficientRow(176, "Pre", "p", "#14b8a6", "作用于分流前的 x：p ⊙ x");
coefficientRow(232, "Post", "q", "#f472b6", "汇合后乘回：+ q ⊙ x");

g += path("M 650 290 H 948", "var(--border)", 1, false);
g += text(650, 316, "Comb", 12, "#c49a6c", "start", 650);
g += text(948, 316, `${R} × ${R} = ${R * R}`, 11, "var(--muted)", "end");
g += text(650, 334, "经 Sinkhorn 得到 M", 9, "var(--muted)");

const combY = 344;
const combPitch = Math.min(27, 110 / R);

for (let r = 0; r < R; r++) {
  for (let o = 0; o < R; o++) {
    g += cell(sx + o * (cw + gap), combY + r * combPitch,
      cw, combPitch - 4, "#c49a6c",
      `${r + 1},${o + 1}`, 10,
      `Comb[${r + 1}, ${o + 1}] → M[${r + 1}, ${o + 1}]`);
  }
}

// Comb logits 与 M 的关系
g += dashed("M 700 396 H 614 V 267 H 526", "#a78bfa", 1.5);
g += text(565, 255, "Sinkhorn", 10, "#a78bfa", "middle", 600);

// ---------- 底部：组合示意 ----------
g += rect(28, 524, 576, 132, "var(--panel)", "var(--border)", 16);
g += text(48, 551, "组合示意", 12, "var(--muted)", "start", 600);

// 上：路由栈来自 p⊙x
g += cell(48, 566, 330, 32, "#14b8a6",
  "R̃ = Routes(p ⊙ x)   ← Pre 在此", 12);
// 下：组合式
g += cell(48, 608, 330, 36, "#a78bfa",
  "u = M · R̃ + q ⊙ x   ← Post 在此", 13);
g += path("M 390 620 H 430", "#94a3b8", 1.8);
g += cell(442, 600, 140, 44, "#34d399", "输出 ŷ", 14);

// ---------- 底部：数量分解 ----------
g += rect(628, 524, 344, 132, "var(--panel)", "var(--border)", 16);
g += text(648, 551, "系数数量", 12, "var(--muted)", "start", 600);

const terms = [
  { x: 674, n: R, label: "Pre", color: "#14b8a6" },
  { x: 754, n: R, label: "Post", color: "#f472b6" },
  { x: 834, n: R * R, label: "Comb", color: "#c49a6c" },
  { x: 933, n: total, label: "总计", color: "#a78bfa" },
];

for (const t of terms) {
  g += text(t.x, 589, t.n, 25, t.color, "middle", 700);
  g += text(t.x, 617, t.label, 11, "var(--muted)", "middle");
}

g += text(714, 588, "+", 17, "var(--muted)", "middle");
g += text(794, 588, "+", 17, "var(--muted)", "middle");
g += text(884, 588, "=", 17, "var(--muted)", "middle");

holder.querySelector(".frame").innerHTML = `
<svg xmlns="http://www.w3.org/2000/svg"
  viewBox="0 0 1000 678" role="img"
  aria-labelledby="${uid}-title ${uid}-desc">
  <title id="${uid}-title">mHC 路由与系数示意图</title>
  <desc id="${uid}-desc">
    Pre 系数 p 作用于分流前的输入 x，得到 p 乘 x 后再分流进 ${R} 条并行路由；
    ${R} 乘 ${R} 混合矩阵 M 由 Comb logits 经 Sinkhorn 得到；
    组合式为 u 等于 M 乘 R 波浪 + q 乘 x。
    系数分为 Pre、Post、Comb，共 ${total} 个。
  </desc>
  <defs>
    <marker id="${uid}-arrow" viewBox="0 0 10 10"
      refX="9" refY="5" markerWidth="5" markerHeight="5"
      orient="auto">
      <path d="M 1 1 L 9 5 L 1 9 Z" fill="context-stroke"/>
    </marker>
  </defs>
  ${g}
</svg>`;

dv.container.appendChild(holder);
```

## 有无 mHC 对比

```dataviewjs
// ===== 标准残差 vs mHC 对比图 =====
const P = { common: "#607d8b", std: "#1565c0", mhc: "#e65100" };
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");

function box(x, y, w, h, color, title, dashed = false) {
  let s = `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="10" fill="${color}" fill-opacity="0.13" stroke="${color}" stroke-opacity="0.85"${dashed ? ' stroke-dasharray="5 4"' : ""}/>`;
  s += `<text x="${x + w / 2}" y="${y + h / 2 + 5}" text-anchor="middle" font-size="14" font-weight="600" fill="currentColor">${esc(title)}</text>`;
  return s;
}
const arrow = (x1, y1, x2, y2, dashed = false) =>
  `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#888" stroke-width="1.6"${dashed ? ' stroke-dasharray="5 4"' : ""} marker-end="url(#ah2)"/>`;
const path = (d, marker = true, dashed = false) =>
  `<path d="${d}" fill="none" stroke="#888" stroke-width="1.6"${dashed ? ' stroke-dasharray="5 4"' : ""}${marker ? ' marker-end="url(#ah2)"' : ""}/>`;

let g = "";

// ---- 标题 + 分隔线 ----
g += `<text x="140" y="30" text-anchor="middle" font-size="14" font-weight="700" fill="currentColor">标准残差（无 mHC）</text>`;
g += `<text x="430" y="30" text-anchor="middle" font-size="14" font-weight="700" fill="currentColor">mHC（两列：H 维 / 路由）</text>`;
g += `<line x1="290" y1="40" x2="290" y2="390" stroke="currentColor" stroke-opacity="0.15" stroke-dasharray="4 6"/>`;

// ---- 左：标准残差 ----
g += box(40, 58, 200, 40, P.common, "h（H 维）");
g += arrow(140, 98, 140, 114);
g += box(40, 114, 200, 40, P.common, "Layer");
g += arrow(140, 154, 140, 170);
g += box(40, 170, 200, 40, P.std, "＋ 残差直加");
g += arrow(140, 210, 140, 226);
g += box(40, 226, 200, 40, P.common, "RMSNorm");
g += arrow(140, 266, 140, 282);
g += box(40, 282, 200, 40, P.common, "下一层");
g += path("M240,78 H265 V190 H240");               // 残差旁路

// ---- 右：mHC｜左列 = H 维链路 ----
g += box(300, 58, 190, 40, P.common, "上一层 x（H 维）");
g += box(300, 114, 190, 40, P.mhc, "Collapse  Σ p·u");
g += arrow(395, 154, 395, 170);
g += box(300, 170, 190, 40, P.common, "ỹ（H 维）");
g += arrow(395, 210, 395, 226);
g += box(300, 226, 190, 40, P.common, "RMSNorm");
g += arrow(395, 266, 395, 282);
g += box(300, 282, 190, 40, P.common, "Layer");
g += arrow(395, 322, 395, 338);
g += box(300, 338, 190, 40, P.common, "下一层 x'（H 维）");
g += `<text x="395" y="398" text-anchor="middle" font-size="11.5" fill="currentColor" opacity="0.6">→ 下一层</text>`;

// ---- 右：mHC｜右列 = 路由 / 系数（上移一格，与左列逐行对齐） ----
g += box(580, 4, 210, 40, P.mhc, "上一层 R̃, p, q, M", true);
g += arrow(685, 44, 685, 58, true);
g += box(580, 58, 210, 40, P.mhc, "Mix  q·x + M·R̃");
g += arrow(685, 98, 685, 114);
g += box(580, 114, 210, 40, P.mhc, "u（R×H）");
g += arrow(685, 154, 685, 170);
g += box(580, 170, 210, 40, P.mhc, "Sinkhorn → 新 p/q/M");
g += arrow(685, 210, 685, 226);
g += box(580, 226, 210, 40, P.mhc, "下一层 u, 新 p/q/M", true);
g += `<text x="685" y="286" text-anchor="middle" font-size="11.5" fill="currentColor" opacity="0.6">→ 下一层</text>`;

// ---- 跨列连线 ----
g += path("M490,78 H580");                          // x → Mix（水平对齐）
g += path("M580,134 H490");                         // u → Collapse（水平对齐）
g += path("M580,34 H545 V124 H490", true, true);    // 上一层的 p → Collapse

// ---- 图例 ----
function legend(x, color, label) {
  return `<rect x="${x}" y="418" width="16" height="16" rx="4" fill="${color}" fill-opacity="0.2" stroke="${color}"/>` +
    `<text x="${x + 24}" y="431" font-size="12.5" fill="currentColor" opacity="0.85">${esc(label)}</text>`;
}
g += legend(40, P.common, "两者共有");
g += legend(190, P.std, "仅标准残差（残差直加）");
g += legend(420, P.mhc, "仅 mHC（路由 / Mix / Collapse / Sinkhorn）");
g += `<text x="40" y="454" font-size="11.5" fill="currentColor" opacity="0.6">虚线 = 上一层传入 / 传给下一层的系数</text>`;

const svg = `<svg viewBox="0 0 830 460" width="100%" style="max-width:830px;height:auto;display:block;margin:0 auto"
  xmlns="http://www.w3.org/2000/svg"
  font-family="-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif">
  <defs><marker id="ah2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
    <path d="M0,0 L10,5 L0,10 z" fill="#888"/></marker></defs>
  <g>${g}</g></svg>`;

const holder2 = document.createElement("div");
holder2.style.cssText = "overflow-x:auto;padding:6px 0";
holder2.innerHTML = svg;
dv.container.appendChild(holder2);
```

# mega gate

> gate kernel（`bf16_mega_gate`）= **GEMM + 路由 epilogue**：矩阵乘算出每个 token 对每个专家的打分，再在片上做激活、TopK、归一化。输出的 `topk_idx` / `topk_weights` 直接喂给 Mega MoE 主 kernel。

## 第一步：打分矩阵乘

$$
\ell_i = W_g\,x_i,\qquad W_g\in\mathbb{R}^{E\times d},\quad \ell_i\in\mathbb{R}^{E}
$$

- $x_i\in\mathbb{R}^{d}$：第 $i$ 个 token 的隐向量（bf16）
- $W_g\in\mathbb{R}^{E\times d}$：全局门控权重，$E$ = 路由专家数
- $\ell_{i,e}$：token $i$ 对专家 $e$ 的**原始打分**（logit），fp32 累加
- 这一步就是普通 GEMM：$M=T$（token 数）、$N=E$、$K=d$，累加结果先落在 TMEM 里

## 第二步：sqrt-softplus 激活

$$
s_{i,e}=\sqrt{\operatorname{softplus}(\ell_{i,e})},\qquad
\operatorname{softplus}(u)=\log\!\left(1+e^{u}\right)
$$

实现取数值稳定分支（`epilogue/sm100_mega_gate.cuh:19-23`）：

$$
\operatorname{softplus}(u)=
\begin{cases}
u, & u>20\\[2pt]
\operatorname{log1p}\!\left(e^{u}\right), & u\le 20
\end{cases}
$$

- 为什么分支：$e^{20}\approx4.85\times10^{8}$，再大 `expf` 就溢出成 `inf`；而 $u>20$ 时 $\log(1+e^{u})\approx u$ 在 fp32 下已经相等
- 为什么开根号：softplus 只保证非负，分布仍是长尾；开方压缩动态范围，让 TopK 的相对差距更平滑（**推断**——源码只体现做法，未写动机）
- $s_{i,e}$ 非负、单调于 $\ell_{i,e}$，这是后面"无偏置时可省激活"的前提

## 第三步：TopK 选择（含偏置）

$$
r_{i,e}=s_{i,e}+b_e,\qquad
\mathcal{T}_i=\operatorname{TopK}_{K}\big\{r_{i,e}\big\}_{e=1}^{E}
$$

- $b_e$：可选打分偏置；图像 token 改用另一套 `image_bias`
- 偏置**只进排序**，不进入权重（见下一步）
- 平局取专家下标更小者（`compare_swap_best_first` 里显式比较 index）
- $E$ 不是 128 的整数倍时，尾部填充专家置 $r=-\infty$
- 无偏置时因 $s$ 单调，直接按 $\ell$ 排序即可，等价且更省

## 第四步：权重归一化

$$
g_{i,e}=\gamma\cdot\frac{s_{i,e}}{\displaystyle\sum_{e'\in\mathcal{T}_i}s_{i,e'}+10^{-20}},
\qquad e\in\mathcal{T}_i
$$

- 分子是**未加偏置**的 $s_{i,e}$：偏置决定"选谁"，不决定"权重多大"
- $10^{-20}$ 防零除（专家全 0 时）
- $\gamma$ = `routed_scaling_factor`，全局缩放，不参与除

## 第五步：写回（含共享专家）

$$
\operatorname{topk\_idx}[i,:]=\big[\,e_1,\dots,e_K,\ \underbrace{E,\,E+1,\,\dots}_{S\ \text{个共享专家}}\,\big]
$$

$$
\operatorname{topk\_weights}[i,:]=\big[\,g_{i,e_1},\dots,g_{i,e_K},\ \underbrace{1,\dots,1}_{S\ \text{个}}\,\big]
$$

共享专家固定权重 1，不进归一化分母。

## 合起来（单 split、无偏置）

$$
g_{i,e}=\gamma\cdot
\frac{\sqrt{\operatorname{softplus}\!\big(x_i w^{g}_{e}\big)}}
{\displaystyle\sum_{e'\in\mathcal{T}_i}\sqrt{\operatorname{softplus}\!\big(x_i w^{g}_{e'}\big)}+10^{-20}}
$$

## 实现细节

| 项 | 处理 | 原因 |
|---|---|---|
| split-K | 先把各 split 的部分和相加，再激活 | sqrt-softplus 非线性，不能先激活再相加 |
| 无偏置 + 单 split | 只对选中的 $K$ 个专家激活 | 排序可用原始 logit，省 $E-K$ 次 `exp/log/sqrt` |
| 有偏置 + 单 split | 在 TMEM 存回时就激活（`kScoreOnStore`） | 偏置要加在激活后的分数上 |
| masked token | `topk_idx = -1`，`weight = 0` | 直接跳过计算 |
| force_random | curand 随机抽 $K$ 个**不同**专家，权重是同一个随机数 | 压力测试路由 |
| 重复专家 | 逻辑→物理：$\text{dup}=(\text{rank\_idx}+i\cdot 23333)\bmod D$ | 各 rank 打散到不同副本 |
| 专家分波 | 每波 128 个专家（`kNumExpertsPerWave = 32 lane × 4`），每 lane 持 4 个 | warp 内一次排序即可覆盖 128 专家 |

## 示例：4 个路由 + 1 个共享，TopK = 2

```dataviewjs
// ===== Mega Gate 数值示例：方格 = 专家 =====
const C = { routed: "#607d8b", sel: "#e65100", shared: "#00897b" };
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");

const W = 72, H = 56;
const sq = (x, y, text, o = {}) => {
  const c = o.color || C.routed;
  const fo = o.muted ? 0.05 : (o.strong ? 0.22 : 0.12);
  const so = o.muted ? 0.3 : 0.85;
  return `<rect x="${x}" y="${y}" width="${W}" height="${H}" rx="8" fill="${c}" fill-opacity="${fo}" stroke="${c}" stroke-opacity="${so}"${o.dashed ? ' stroke-dasharray="5 4"' : ""}/>`
    + `<text x="${x + W / 2}" y="${y + H / 2 + 5}" text-anchor="middle" font-size="13.5" font-weight="${o.strong ? 700 : 500}" fill="currentColor" opacity="${o.muted ? 0.4 : 1}">${esc(text)}</text>`;
};

const COLS = [195, 287, 379, 471, 563];          // E1..E4 路由 / E5 共享
const CX = COLS.map(x => x + W / 2);
const ROWS = [76, 154, 232, 310];
const rowLabel = (y, t) =>
  `<text x="170" y="${y + 33}" text-anchor="end" font-size="12.5" fill="currentColor" opacity="0.75">${esc(t)}</text>`;

let g = "";
g += `<text x="415" y="30" text-anchor="middle" font-size="15" font-weight="700" fill="currentColor">Mega Gate 示例：4 个路由专家 + 1 个共享专家，TopK K = 2，γ = 2.5</text>`;

// 专家表头
["E1", "E2", "E3", "E4", "E5（共享）"].forEach((n, i) => {
  g += `<text x="${CX[i]}" y="66" text-anchor="middle" font-size="11.5" font-weight="600" fill="currentColor" opacity="0.7">${esc(n)}</text>`;
});

// ① logits
g += rowLabel(ROWS[0], "ℓ = Wg x");
["-1.20", "2.40", "0.80", "3.10", "—"].forEach((v, i) => {
  g += sq(COLS[i], ROWS[0], v, i === 4 ? { color: C.shared, dashed: true, muted: true } : {});
});

// ② sqrt-softplus
g += rowLabel(ROWS[1], "s = √softplus(ℓ)");
["0.513", "1.577", "1.082", "1.773", "—"].forEach((v, i) => {
  g += sq(COLS[i], ROWS[1], v, i === 4 ? { color: C.shared, dashed: true, muted: true } : {});
});

// ③ TopK
g += rowLabel(ROWS[2], "TopK K = 2");
["—", "②", "—", "①", "常开"].forEach((v, i) => {
  if (i === 4) g += sq(COLS[i], ROWS[2], v, { color: C.shared, dashed: true, strong: true });
  else if (i === 1 || i === 3) g += sq(COLS[i], ROWS[2], v, { color: C.sel, strong: true });
  else g += sq(COLS[i], ROWS[2], v, { muted: true });
});

// ④ 归一化权重
g += rowLabel(ROWS[3], "g = γ·s / Σs");
["—", "1.177", "—", "1.323", "1.000"].forEach((v, i) => {
  if (i === 4) g += sq(COLS[i], ROWS[3], v, { color: C.shared, dashed: true });
  else if (i === 1 || i === 3) g += sq(COLS[i], ROWS[3], v, { color: C.sel, strong: true });
  else g += sq(COLS[i], ROWS[3], v, { muted: true });
});

// 行间箭头
const ar = (x, y1, y2) =>
  `<line x1="${x}" y1="${y1}" x2="${x}" y2="${y2}" stroke="#888" stroke-width="1.6" marker-end="url(#ah3)"/>`;
g += ar(415, 136, 150) + ar(415, 214, 228) + ar(415, 292, 306) + ar(415, 370, 398);

// ⑤ 写回槽位
const SX = [219, 355, 491];
[["E4 · 1.323", C.sel], ["E2 · 1.177", C.sel], ["E5 · 1.000", C.shared]].forEach(([t, c], i) => {
  g += `<rect x="${SX[i]}" y="404" width="120" height="50" rx="8" fill="${c}" fill-opacity="0.15" stroke="${c}" stroke-opacity="0.85"/>`
    + `<text x="${SX[i] + 60}" y="435" text-anchor="middle" font-size="13" font-weight="600" fill="currentColor">${esc(t)}</text>`;
});

// 说明
g += `<text x="415" y="476" text-anchor="middle" font-size="11.5" fill="currentColor" opacity="0.7">Σs = 1.773 + 1.577 = 3.350，× γ = 2.5 得 g；最后 1 个槽位是共享专家，权重恒为 1</text>`;

// 图例
const legend = (x, color, label, dashed = false) =>
  `<rect x="${x}" y="500" width="16" height="16" rx="4" fill="${color}" fill-opacity="0.2" stroke="${color}"${dashed ? ' stroke-dasharray="4 3"' : ""}/>`
  + `<text x="${x + 24}" y="513" font-size="12" fill="currentColor" opacity="0.8">${esc(label)}</text>`;
g += legend(195, C.sel, "TopK 选中");
g += legend(340, C.routed, "未选中（不参与写回）");
g += legend(560, C.shared, "共享专家（不打分）", true);

const svg = `<svg viewBox="0 0 830 540" width="100%" style="max-width:830px;height:auto;display:block;margin:0 auto"
  xmlns="http://www.w3.org/2000/svg"
  font-family="-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif">
  <defs><marker id="ah3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
    <path d="M0,0 L10,5 L0,10 z" fill="#888"/></marker></defs>
  <g>${g}</g></svg>`;

const holder3 = document.createElement("div");
holder3.style.cssText = "overflow-x:auto;padding:6px 0";
holder3.innerHTML = svg;
dv.container.appendChild(holder3);
```

读法：同一列是同一个专家，从上往下走完 $\ell \to s \to \text{TopK} \to g$；$E_5$ 整列虚线，因为它不参与打分和排序，只在最后被追加一个固定权重 1 的槽位。

# Swap AB