# web-access (OpenClaw adaptation)

把 upstream `web-access` 的设计哲学迁到 **OpenClaw**：不是生搬硬套 Claude Code 的 CDP proxy，而是改造成 **OpenClaw 原生工具优先** 的联网 skill。

这版保留作者的核心思想：

- **Skill = 联网策略哲学 + 最小完备工具集 + 必要事实说明**
- 目标导向，而不是固定步骤导向
- 让 Agent 在「搜 / 读 / 做」之间自己切换，而不是一条路撞到底
- 为常见站点沉淀可复用经验，而不是把经验全塞进长期记忆

同时把实现改成更适合 OpenClaw 的形态：

- **读公开页面**：优先 `web_fetch` 或 `scripts/read_url.py`（Jina → Scrapling + html2text）
- **读 PDF**：优先 OpenClaw `pdf` 工具
- **搜索信息源**：优先 OpenClaw 搜索能力 / 已安装 search skill
- **动态页面 / 登录态 / 表单操作**：优先 OpenClaw `browser` 工具
- **视觉内容**：配合 `image` 工具分析截图
- **并行独立任务**：鼓励 OpenClaw 子 agent / isolated session 分治

## 为什么要融合 web-reader

原版 `web-access` 很强，但它把「读页面」主要放在 `WebFetch / curl / CDP` 的框架里。

在 OpenClaw 里，公开页面正文提取其实有一条非常实用的低成本路径：

1. 先试 **Jina Reader**
2. 不行就抓 HTML
3. 提取正文区块
4. 再转成 Markdown 给模型读

这正是 `web-reader` 的长处。

所以这次融合的重点是：

- 保留 `web-access` 的**策略哲学**
- 用 `web-reader` 的 **Jina-first readable extraction** 补强“读”这件事
- 把浏览器层改写为 **OpenClaw browser tool first**，而不是本地自起 CDP proxy

## 目录

- `SKILL.md` — OpenClaw 版核心 skill 指引
- `scripts/read_url.py` — 公共网页正文读取器（Jina → Scrapling fallback）
- `scripts/init_env.sh` — 安装 fallback Python 依赖
- `references/openclaw-browser.md` — OpenClaw browser 工具的使用模式与决策边界
- `references/site-patterns/` — 站点经验沉淀

## 设计结论（来自作者文章）

我对原文的提炼是：作者真正想解决的，不是“没有浏览器工具”，而是 **Agent 在联网时不会像人一样切换策略**。

所以 skill 不应只是一份 API 说明，而应同时做到：

1. **校准思维方式**：先定义成功标准，再选起点，再根据证据换路
2. **补齐最小完备工具集**：搜、读、做 三类能力缺一不可
3. **补惰性知识**：例如 Jina 适合正文页，动态站/登录页直接进浏览器，平台错误文案不一定可信
4. **允许经验沉淀**：站点模式、坑点、有效入口可以按域名复用

## 快速使用

### 读取公共网页正文

```bash
python3 scripts/read_url.py "https://example.com/article"
```

强制指定路径：

```bash
python3 scripts/read_url.py "https://example.com/article" --mode jina
python3 scripts/read_url.py "https://example.com/article" --mode scrapling
```

首次安装 fallback 依赖：

```bash
bash scripts/init_env.sh
```

### 在 OpenClaw 中的推荐路由

- **已知 URL，目标是读正文** → `web_fetch` / `scripts/read_url.py`
- **PDF / 扫描 PDF** → `pdf`
- **需要登录、点击、上传、滚动、动态渲染** → `browser`
- **图片/视频内容是关键信息** → `browser` 截图 + `image`
- **多个独立目标** → 子 agent 并行，每个 agent 自己维护页面上下文

## 与 upstream 的主要差异

| 主题 | upstream web-access | 本改造版 |
|---|---|---|
| 浏览器执行层 | 本地 CDP proxy + curl API | OpenClaw `browser` 工具 |
| 公共页面读取 | WebFetch / curl / Jina（概念层） | 增加可直接落地的 `read_url.py` |
| 运行环境 | Claude Code / 泛 skill 环境 | OpenClaw-first |
| 登录态策略 | 复用用户 Chrome CDP | 按 OpenClaw browser profile 选择（isolated / user / chrome-relay） |
| 经验沉淀 | 域名经验文件 | 保留，并适配 OpenClaw 工作流 |

## 说明

这个分支更像是 **OpenClaw 版 web-access fork 草案**。

重点不是 1:1 复刻原项目，而是把作者最值钱的那部分——**联网决策方法论**——落到 OpenClaw 的原生能力上。