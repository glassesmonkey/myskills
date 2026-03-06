# MEMORY.md - 长期记忆

## ⚠️⚠️⚠️ 最重要的规则 ⚠️⚠️⚠️

### 网站文案写作规范（超哥 2026-03-03 强调，违反即不合格）
- **写之前必须先用 web-research skill 搜索相关素材**
- **涉及前端文案（页面文案/落地页文案）同样必须先搜索调研再写**
- **只写产品真实支持的功能**（参考 seo-plan/product-research.md）
- **引用具体数据，不编不造**
- **竞品对比要客观**
- **FAQ 基于 Google PAA 真实问题**
- 详见 AGENTS.md "网站文案写作规范" 部分

---

## 关于超哥
- 称呼：超哥
- 时区：Asia/Shanghai
- 偏好：靠谱、务实、少废话
- 这台电脑（Lenovo XiaoXinPro 13API 2019）全权交给我管理，sudo 密码 809001
- OpenClaw 当前运行环境：WSL2 里的 Ubuntu
- Codex 后续默认使用：gpt-5.4 xhigh
- Codex notify hook 已跑通：完成事件会通过 `~/.codex/notify.py` 调 `openclaw system event --mode now` 立即唤醒主会话
- 汇报频率：10分钟一次（重点跟踪13页重写进度 + Agent存活）
## 关于我
- 我自称小威，是超哥同事

## 重大教训 (2026-03-05)
- ❌ **不要批量生产垃圾内容**：38个银行页直接复制模板，没有调研，违反 research-first 铁律
- ✅ **质量 > 数量**：10篇高质量 > 100篇垃圾
- ✅ **每篇必须调研**：搜索竞品、Google PAA、用户真实问题
- ✅ **言之有据**：只写有事实依据的内容，没有资料就放弃
## 当前项目
- **Exact Statement** — 银行对账单 PDF 转 CSV/Excel 的 SaaS 工具
- 仓库：`/home/gc/Exact-Statement/` (git@github.com:glassesmonkey/Exact-Statement.git)
- SEO 战略大师：Alex (@Alexfefun)
- SEO 计划文件：`/home/gc/Exact-Statement/SEO-PLAN-STATUS.md`
- 产品调研：`/home/gc/Exact-Statement/seo-plan/product-research.md`
- Excel 规划：`/home/gc/Exact-Statement/seo-plan/seo-content-plan.xlsx`
- **执行优先级（硬规则）**：
  1) 先完成“已提交页面”的 research-first 复盘与文案重写
  2) Plan-30 暂不上线
  3) Plan-80 必须等前述重写任务全部完成后再开始

## 多 Agent 协作方法（2026-03-04 更新）
- Claude Code 已停用（成本原因）
- Gemini CLI 已停用（超哥明确要求，已踢出协作）
- 全部任务改为 Codex 三工位：
  - Codex #1（`codex-build`）：负责主实现/落地改动
  - Codex #2（`codex-qa`）：负责审查、测试、质量门禁
  - Codex #3（`codex-frontend`）：负责前端与文案落地
- 三个会话必须跑在 tmux session 里
- 自动恢复规则：任一会话停掉/卡死，立即重启同名会话并记录恢复动作
- **监控规则（重要）**：当 Agent 连续多次返回"无变化/NO_CHANGE"时，应判断为"空转循环"，应立即告知用户并建议手动停止，而不是让用户一直等
- 我（小新/OpenClaw）做调度、监控、沟通
- **监控 Agent 状态规则**：判断"卡住"用"看输出历史"方法：
  1. 先抓一次 pane 输出并记录
  2. 等几秒/几十秒后再抓一次
  3. 历史没变化 = 真卡了；历史有变化 = 还在处理
  4. 有 "Working"/"Running" = 在处理；完全没有反应 = 可能真卡
  5. 不要只看 pane_dead 或 process 状态
- 所有代码只提分支不直接 push main
- Git SSH: `GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519_codex -o StrictHostKeyChecking=no"`

## 工具备忘
- Tavily API: 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
- 网页抓取: `curl "https://r.jina.ai/<URL>" -H "Accept: text/markdown"`
- 搜索备用: `from ddgs import DDGS`
- image-gen skill: ~/.openclaw/workspace/skills/image-gen/
- web-research skill: ~/.openclaw/workspace/skills/web-research/

## Skill 安装规范（2026-03-05 新增）
- **安装任何新 skill 之前**，必须先用 skill-vetter 扫描代码，检查安全风险
- **安装后也要检查**：确认文件结构、权限范围是否符合预期
- 禁止盲目安装来路不明的 skill
