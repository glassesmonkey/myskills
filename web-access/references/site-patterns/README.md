# Site patterns

Store one file per domain, for example:
- `mp.weixin.qq.com.md`
- `xiaohongshu.com.md`
- `github.com.md`

Use this format:

```markdown
---
domain: example.com
aliases: [示例, Example]
updated: 2026-03-23
---

## 平台特征
仅记录已验证的事实：登录要求、反爬特征、内容加载方式、是否适合静态读取。

## 有效模式
记录已验证有效的 URL 结构、页面入口、交互路径、提取方式。

## 已知陷阱
记录会失败的路径，以及为什么会失败。
```

Rules:
- only write verified facts
- prefer short, high-signal notes
- treat patterns as hints, not guarantees
- update the `updated` field when the pattern changes
