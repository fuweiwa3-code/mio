# 决策：聊天页移除常驻人物，语音采用全屏沉浸模式

日期：2026-06-11

## 决策

Mio 普通聊天页不再展示常驻人物，也不提供“显示澪”开关。聊天页恢复完整文字内容宽度，聚焦长期阅读和输入。

用户主动点击语音入口后，进入独立的全屏沉浸式通话页面：

- 使用暖灰、米白和暗梅色的“暖色静室”视觉。
- 人物位于右侧前景。
- 当前字幕位于人物下方。
- 顶部显示退出、通话状态和时长。
- 底部提供静音、结束和字幕控制。
- 结束后返回原聊天和原 `conversation_id`。

全屏通话只是独立 Experience Layer。文字和语音继续共享同一个 Conversation、Persona、Memory、RAG、Safety、Agent Trace 和 Presentation Layer。

人物表现采用可插拔 Avatar Renderer。Companion 可以配置静态立绘、Live2D 或 VRM；Web 端只在进入全屏通话后按需加载对应运行时和模型。具体 VRM/VRMA 方案见：

- `docs/superpowers/specs/2026-06-11-vrm-avatar-renderer-design.md`

## 原因

- 普通聊天页常驻人物会压缩正文宽度并持续争夺注意力。
- 人物只在语音通话中出现，可以提高进入语音模式的仪式感。
- 独立全屏空间更适合组织录音授权、字幕、人物、媒体状态和结束操作。
- 暖色静室比深色影院更符合 Mio 的品牌，也比展示项目桌面更少分心和隐私风险。

## 视觉尺度

- 保留现有暖梅主题，不改为蓝紫 AI 主色。
- 减少普通页面的阴影、渐变、玻璃和悬浮动效。
- 通话页允许局部环境光和字幕磨砂，但正文与控制保持高对比。

## 替代关系

本决策替代：

- `design/decisions/2026-06-07-single-page-companion.md`
- `design/decisions/2026-06-08-stitch-chat-structure.md` 中关于聊天页右下常驻人物的部分

历史文件保留，用于记录设计演进。

## 详细规格

见：

- `docs/superpowers/specs/2026-06-11-chat-and-immersive-voice-design.md`
