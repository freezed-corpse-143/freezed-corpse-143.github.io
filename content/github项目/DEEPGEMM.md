# GEMM

$$
D=C+AB
$$

GEMM = 分块矩阵乘 + 量化缩放 + 让相邻块共享缓存 + 一个 CTA 连续吃多个块（持久化）

```dataviewjs
// ===== GEMM 格子图: D = C + A B =====
// A: 2x3, B: 3x4  =>  D, C: 2x4
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
        txt = `D${sub(i+1)}${sub(j+1)}`;
        let terms = [];
        for (let p = 1; p <= k; p++) terms.push(`A${sub(i+1)}${sub(p)}·B${sub(p)}${sub(j+1)}`);
        title = `D${sub(i+1)}${sub(j+1)} = C${sub(i+1)}${sub(j+1)} + ` + terms.join(" + ");
      } else {
        // 输入矩阵用字母+下标
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

// 下标数字转 Unicode 小写（1-9 够用）
function sub(num) {
  const map = {0:"₀",1:"₁",2:"₂",3:"₃",4:"₄",5:"₅",6:"₆",7:"₇",8:"₈",9:"₉"};
  return String(num).split("").map(d => map[d] || d).join("");
}

const container = document.createElement("div");
container.style.cssText = "padding:14px; border:1px solid #ccc; border-radius:8px; overflow-x:auto;";

const title = document.createElement("div");
title.textContent = `GEMM:  D = C + A·B   （A: ${m}×${k},  B: ${k}×${n}  ⇒  D, C: ${m}×${n}）`;
title.style.cssText = "font-size:16px; font-weight:bold; margin-bottom:12px;";
container.appendChild(title);

const row = document.createElement("div");
row.style.cssText = "display:flex; align-items:center; flex-wrap:nowrap;";

row.appendChild(makeTable(m, k, "A", "#e3f2fd", false));
row.appendChild(opSym("×", "font-size:26px; padding:0 10px;"));
row.appendChild(makeTable(k, n, "B", "#e8f5e9", false));
row.appendChild(opSym("+", "font-size:26px; padding:0 10px;"));
row.appendChild(makeTable(m, n, "C", "#fff3e0", false));
row.appendChild(opSym("=", "font-size:26px; padding:0 10px;"));
row.appendChild(makeTable(m, n, "D", "#fce4ec", true));

container.appendChild(row);

// 说明
const note = document.createElement("div");
note.style.cssText = "margin-top:12px; font-size:13px; color:#555; line-height:1.7;";
note.innerHTML = `
<b>怎么看这张图：</b><br>
• 每格是一个标量。<b>悬停 D 的格子</b>可看到完整的展开式，例如
  D₁₁ = C₁₁ + A₁₁·B₁₁ + A₁₂·B₂₁ + A₁₃·B₃₁。<br>
• 结果 D 的第 (i,j) 格 = C 的同位置格 + <b>A 第 i 行</b> 与 <b>B 第 j 列</b> 的逐项乘积和（K=${k} 项）。<br>
• 行数关系：A 的行数(${m}) = D 的行数；B 的列数(${n}) = D 的列数；中间维度 K(${k}) 在相乘时被"消掉"。<br>
• 在 GPU 里，这些格子会被切成 tile（如 BLOCK_M×BLOCK_N），分给不同 SM 并行算，A/B 的 tile 通过 TMA 搬进 shared memory 的环里。
`;
container.appendChild(note);

// 操作符元素
function opSym(s, css) {
  const d = document.createElement("div");
  d.textContent = s;
  d.style.cssText = css;
  return d;
}

dv.container.appendChild(container);
```