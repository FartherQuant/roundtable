// 圆桌会议 Prompt 生成器主逻辑

// 默认前 N 个人格
const DEFAULT_PRESELECT = 3;

// 初始化人格列表（前 N 个默认勾选）
function initPersonaList() {
  const list = document.getElementById("personaList");
  list.innerHTML = "";

  const keys = Object.keys(PERSONAS);
  keys.forEach((key, idx) => {
    const p = PERSONAS[key];
    const checked = idx < DEFAULT_PRESELECT;
    const item = document.createElement("label");
    item.className = "persona-item" + (checked ? " selected" : "");
    item.dataset.key = key;
    item.innerHTML = `
      <input type="checkbox" value="${key}"${checked ? " checked" : ""}>
      <div class="info">
        <div class="name">${p.name}</div>
        <div class="desc">${p.desc}</div>
      </div>
    `;
    list.appendChild(item);
  });

  // 监听选择
  list.addEventListener("change", e => {
    if (e.target.type === "checkbox") {
      e.target.closest(".persona-item").classList.toggle("selected", e.target.checked);
      update();
    }
  });
}

// 随机选 N 个推荐人格
function pickRandom(n) {
  const allKeys = Object.keys(PERSONAS);
  const shuffled = [...allKeys].sort(() => Math.random() - 0.5);
  return new Set(shuffled.slice(0, n));
}

// 全不选 / 推荐3个 / 推荐5个
function selectNone() {
  document.querySelectorAll("#personaList input").forEach(cb => {
    cb.checked = false;
    cb.closest(".persona-item").classList.remove("selected");
  });
  update();
}

function selectDefault() {
  const picked = pickRandom(3);
  document.querySelectorAll("#personaList input").forEach(cb => {
    const isPicked = picked.has(cb.value);
    cb.checked = isPicked;
    cb.closest(".persona-item").classList.toggle("selected", isPicked);
  });
  update();
}

function selectFive() {
  const picked = pickRandom(5);
  document.querySelectorAll("#personaList input").forEach(cb => {
    const isPicked = picked.has(cb.value);
    cb.checked = isPicked;
    cb.closest(".persona-item").classList.toggle("selected", isPicked);
  });
  update();
}

// 获取当前选中的 persona 对象
function getSelectedPersonas() {
  const keys = Array.from(document.querySelectorAll("#personaList input:checked")).map(cb => cb.value);
  return keys.map(k => ({ key: k, ...PERSONAS[k] }));
}

// 获取当前模式（默认快速共识）
function getMode() {
  return "quick";
}

// 渲染单个人格
function renderPersona(p) {
  const anchorLines = p.anchors.map((a, i) => `  ${i + 1}. ${a}`).join("\n");
  return `### ${p.name} — ${p.desc}

- **说话风格**：${p.style}
- **追问方向**：
${anchorLines}
- **诚实规则**：${p.honesty}
- **反套路**：${p.antiPattern}`;
}

// 生成完整 prompt
function buildPrompt() {
  const topic = document.getElementById("topic").value.trim();
  if (!topic) return null;
  const personas = getSelectedPersonas();
  if (personas.length === 0) return null;
  const mode = getMode();

  const personasSection = personas.map(renderPersona).join("\n\n");

  if (mode === "quick") {
    return `# 圆桌会议（快速共识模式）

## 议题

${topic}

## 参与者

${personasSection}

## 要求

请一次性完成以下5步，输出结构化结论。每步尽量精简，重点在Step 5的结构化产出。

**Step 1：各抒己见** — 每位参与者100字左右回应议题，以[身份：人格名]开头。

**Step 2：交叉反驳** — 每位参与者用1-2句话反驳一位其他参与者的核心论点，显式称呼对方。

**Step 3：推理综合** — 列出共识点和分歧点。

**Step 4：共识裁决** — 一句话结论。分歧标记"待定"。

**Step 5：结构化产出** — 按以下格式输出：

## 结论
[一段话]

## 可操作信号
| # | 行动 | 预期效果 | 负责视角 |
|---|------|---------|---------|

## 共识矩阵
| 议题点 | 共识度 | 共识方向 | 分歧原因 |
|--------|--------|---------|---------|

## 盲点
1. ...
2. ...

## 置信度
[高/中/低] — [理由]
`;
  } else {
    return `# 圆桌会议（深度圆桌模式 · 5步执行）

## 议题

${topic}

## 参与者

${personasSection}

## 讨论规则

1. **身份标注**：每条发言必须以 \`[身份：人格名]\` 开头
2. **交叉质疑**：至少一位参与者必须质疑另一位参与者的核心论点
3. **结论可操作**：最终结论必须包含具体可执行的行动项
4. **盲点显式化**：必须列出本次讨论未覆盖的重要视角

## 讨论流程

请严格按以下5步执行：

### Step 1：各抒己见

每位参与者从自己的视角回应议题，200字左右。

### Step 2：交叉反驳

每位参与者至少反驳一位其他参与者的核心论点。反驳时必须显式称呼对方：\`"我不同意{{对方名}}的观点，因为……"\`

### Step 3：推理综合

基于各方观点和反驳，综合出共识与分歧：
- 列出各方一致同意的结论
- 列出各方仍然分歧的观点及分歧原因

### Step 4：共识裁决

输出最终结论。共识优先，裁决次之。分歧点标记为"待定"而非强行统一。

### Step 5：结构化产出

按以下格式输出：

\`\`\`
## 结论

[一段话总结最终结论]

## 可操作信号

| # | 行动 | 预期效果 | 负责视角 |
|---|------|---------|---------|
| 1 | ... | ... | ... |

## 共识矩阵

| 议题点 | 共识度 | 共识方向 | 分歧原因 |
|--------|--------|---------|---------|
| ... | 高/中/低 | ... | ... |

## 盲点

1. [本次讨论未覆盖的重要视角]
2. [...]

## 置信度

[高/中/低] — [理由]
\`\`\`
`;
  }
}

// 更新预览
function update() {
  const preview = document.getElementById("preview");
  const prompt = buildPrompt();

  if (!prompt) {
    const topic = document.getElementById("topic").value.trim();
    if (!topic) {
      preview.innerHTML = '<div class="empty-state">请先输入议题</div>';
    } else {
      preview.innerHTML = '<div class="empty-state">请至少选择一位参与人格</div>';
    }
    return;
  }

  preview.textContent = prompt;
}

// 复制到剪贴板
async function copyPrompt() {
  const prompt = buildPrompt();
  if (!prompt) {
    showToast("请先填写议题并选择参与人格", true);
    return;
  }

  try {
    await navigator.clipboard.writeText(prompt);
    showToast("✓ 已复制到剪贴板");
  } catch (err) {
    // 降级方案
    const ta = document.createElement("textarea");
    ta.value = prompt;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    showToast("✓ 已复制到剪贴板");
  }
}

// 下载为 .md
function downloadPrompt() {
  const prompt = buildPrompt();
  if (!prompt) {
    showToast("请先填写议题并选择参与人格", true);
    return;
  }
  const blob = new Blob([prompt], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `roundtable-${Date.now()}.md`;
  a.click();
  URL.revokeObjectURL(url);
  showToast("✓ 已下载");
}

// Toast 提示
function showToast(msg, isError = false) {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.style.background = isError ? "#c53030" : "#2d3748";
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2000);
}

// 议题输入监听
document.addEventListener("input", e => {
  if (e.target.id === "topic") update();
});

// 启动
initPersonaList();
update();
