# OpenClaw Browser Notes

这份文件替代 upstream 里偏 Claude/CDP proxy 的浏览器说明，改为 **OpenClaw browser 工具优先** 的使用方式。

## 基本原则

- 默认用 OpenClaw 自带浏览器能力，不额外自起本地 proxy
- 同一页面的后续操作尽量复用同一个 `targetId`
- 先 `snapshot` 理解页面，再 `act`
- 优先 `refs="aria"`，比 role+name 更稳定
- 不要默认 `act:wait`；除非真的没有更稳定的可观察条件

## profile 选择

### 1. 默认隔离浏览器

适合：
- 公共页面
- 不需要登录态
- 不希望打扰用户自己的浏览器

### 2. `profile=user`

适合：
- 需要复用用户已有登录态
- 用户在场，可以批准浏览器 attach

注意：
- 这通常比 extension relay 更自然
- 如果用户不在场，不要盲目依赖这个路径

### 3. `profile=chrome-relay`

适合：
- 用户明确提到 Chrome extension / Browser Relay / toolbar icon / attach tab
- 必须附着到某个现有用户 tab

注意：
- 需要用户点 toolbar icon，使 badge 变成 ON
- 不是默认路径

## 推荐工作流

### 读页面结构

1. `snapshot` 页面
2. 看页面是否已经有目标内容
3. 再决定是否需要点击、输入、滚动或截图

### 点击 / 输入

- 能稳定定位时，用 `act(kind=click/type/fill/select)`
- 同一 tab 内连续动作时始终带上 `targetId`
- 输入表单时尽量一次性填完整，减少细碎操作

### 动态页面

- 先看是不是内容其实已经在 DOM / 网络响应里
- 真需要交互再做交互
- 需要懒加载时，滚动到相关区域后再重新 snapshot / screenshot

### 视觉内容

- 如果主体内容是图、图表、海报、视频帧：
  1. 浏览器截图
  2. 再交给 `image` 分析

## 错误处理

- browser 工具超时：不要在同一路径连打重试
- 若只是读公开页面：切回 `web_fetch` / `scripts/read_url.py`
- 若任务本质依赖登录态交互：告诉用户当前浏览器链路不可用，等待恢复或用户介入

## 安全边界

- 不主动操作用户现有 tab，除非任务确实要求
- 不关闭用户原本的 tab
- 登录态相关动作要最小侵入
- 涉及发布、提交、付款、删除等外部动作时，按更高标准确认
