# 圆桌会议 · Prompt 生成器

一个零依赖的纯静态网页，输入议题 → 选择人格 → 一键复制可用的 Prompt → 粘贴到任何 LLM 对话框即可。

## 特性

- 🚀 **零依赖**：纯 HTML + CSS + JavaScript，无需任何后端
- 🔓 **无 API Key**：用户不需要任何账号或 API
- 📋 **一键复制**：生成的 Prompt 一键复制到剪贴板
- 💾 **可下载**：支持下载为 .md 文件
- 📱 **响应式**：手机/平板/电脑均可使用
- 🌐 **LLM 无关**：兼容 ChatGPT / Claude / Gemini / 通义千问 / 智谱清言 / 文心一言 / DeepSeek 等所有 LLM

## 文件结构

```
roundtable-web/
├── index.html      # 主页面（HTML + CSS）
├── personas.js     # 5 个人格配方数据
└── app.js          # 主逻辑（事件处理 + Prompt 生成）
```

## 部署到 Vercel

### 方式 1：拖拽部署（最简单）
1. 访问 https://vercel.com/new
2. 把 `roundtable-web` 文件夹直接拖入页面
3. 等待几十秒，即可在 `xxx.vercel.app` 访问

### 方式 2：命令行
```bash
cd roundtable-web
npx vercel --prod
```

### 方式 3：Git 集成
1. 把 `roundtable-web` 推到 GitHub
2. 在 Vercel 导入仓库
3. 配置：`Output Directory` 留空（根目录就是静态文件）

## 本地预览

```bash
cd roundtable-web
python3 -m http.server 8000
# 浏览器访问 http://localhost:8000
```

## 使用方法

1. 打开页面
2. 在"议题"框输入要讨论的问题
3. 勾选参与讨论的人格（默认推荐3人：卡尼曼+芒格+邓小平）
4. 选择讨论模式（快速共识 / 深度圆桌）
5. 右侧自动生成完整 Prompt
6. 点击"复制到剪贴板"
7. 粘贴到任意 LLM 对话框
8. 等待 30 秒 ~ 2.5 分钟，查看多视角分析结果

## 自定义人格

编辑 `personas.js`，按以下结构添加：

```javascript
window.PERSONAS = {
  mypersona: {
    name: "我的角色",
    desc: "一句话定位",
    style: "说话风格",
    anchors: ["追问1", "追问2", "追问3"],
    honesty: "诚实规则",
    antiPattern: "反套路"
  }
};
```
