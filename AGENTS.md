# Mio AI Companion Agent Guide

## 项目概述

Mio AI Companion 是一个面向程序员的女友陪伴型 PersonaRAG Agent，也是用于求职展示的 AI 应用开发项目。

它的第一身份是具有稳定人设、情绪理解和关系连续性的陪伴者，同时具备：

- 长期记忆与短期对话上下文。
- LangGraph Agent 工作流。
- LangChain RAG 知识库。
- Persona Builder 人设生成器。
- 项目上下文检索。
- Tool Calling、Skill 和 MCP 扩展能力。
- 主动关怀、表情包和后续状态图能力。
- Agent Trace、学习审核和可回滚的自适应学习。

本项目借鉴现有 Hermes Companion 原型的使用经验，但不是 Hermes 的复刻。Hermes 继续作为个人体验原型，本项目负责展示完整的 Python AI 应用工程能力。

## 当前状态

- 项目目录已经建立，但尚未初始化代码工程。
- 现有主要产物是需求、设计和图表文档。
- 当前工作优先级应从 M1 开始，不要直接实现完整 Skill/MCP 或自治 Agent。

上游文档：

- `../docs/mio-ai-companion-design.md`
- `../docs/mio-ai-companion-diagrams.md`
- `../docs/ai-companion-prd.md`
- Hermes 原型说明：`../../2026-05-26/openclaw/agent.md`

## 产品原则

1. 女友陪伴是第一身份，知识回答仍需保持人设，不能变成客服腔。
2. RAG 提供事实依据，Persona Layer 决定表达方式和关系感。
3. 用户明显低落时先回应情绪，再解决技术或学习问题。
4. 长期记忆用于关系连续性，不能把临时情绪误写为长期事实。
5. 主动关怀应轻量、可关闭、有限频，避免像定时营业。
6. 自主学习必须可解释、可审核、可回滚。
7. 微信、Web、IDE 等均为渠道，核心 Agent 不依赖某个渠道实现。
8. 所有关键 AI 决策应记录 trace，便于调试和面试展示。

## 默认人设

默认 Companion 名为「澪」：

- 清冷慢热、认真克制。
- 害羞可爱、稳定陪伴。
- 短句优先，不像客服。
- 不油腻，不频繁动作描写。
- 不复刻已有角色或专有台词。

人设必须可配置，包括：

- 关系类型。
- 甜度、主动程度、情绪直接程度。
- 称呼和说话风格。
- 边界和公开演示模式。

Persona Builder 支持：

- 默认模板。
- 自定义表单。
- 粘贴资料后提取结构化人设。
- 后续从公开资料提取抽象风格，生成原创角色。

不得声称 Companion 就是某个动漫角色、网络人物或真实公众人物。

## V1 范围

V1 应形成可演示的最小闭环：

- Web Chat。
- 默认澪人设和 Persona Settings。
- Persona Builder 基础版。
- 情绪识别和意图分类。
- 长期记忆抽取、审核、检索和管理。
- Markdown/TXT 知识库。
- companion / learning / project 分类。
- embedding 和 pgvector 检索。
- Mock LLM、Mock Embedding。
- OpenAI-compatible LLM、Embedding Provider。
- 本地表情包工具。
- APScheduler 本地主动关怀。
- Agent Debug Console。
- 微信 Webhook 模拟接口和幂等处理。
- Docker Compose 和基础自动化测试。

V1 暂不实现：

- 真实微信长连接。
- 完整多用户 SaaS。
- 实时 WebRTC 语音通话。Avatar 与半实时语音作为 M7.5/M7.75/M8.5 扩展，在基础聊天闭环后实现。
- 复杂生图工作流。
- Skill 市场。
- 自动修改代码或不可控自治。
- 付费系统。

## Avatar 与语音扩展

已确认采用独立的全屏沉浸式语音通话：

- 普通聊天页不常驻展示人物，不加载 Live2D 或 VRM 运行时。
- 用户主动点击语音入口后进入全屏通话页面。
- 人物位于右侧前景，字幕位于人物下方，结束后返回原 Conversation。
- 进入通话页面不等于自动开启麦克风，语音输入必须由用户主动授权。

完整设计：

- `docs/mio-ai-companion-avatar-voice-design.md`
- `docs/superpowers/specs/2026-06-11-chat-and-immersive-voice-design.md`
- `docs/superpowers/specs/2026-06-11-vrm-avatar-renderer-design.md`

实现顺序：

1. M7.5：全屏通话静态人物闭环、AvatarProfile、AvatarRenderer、Presentation Engine 和降级链。
2. M7.75：VRM Renderer、VRMA 动作、表情、眨眼、视线和音频嘴型。
3. M8.5：点击录音、Mock/真实 ASR、Mock/真实 TTS、字幕、嘴型和 VoiceTrace。
4. M9.5：WebRTC、VAD、可打断实时通话、TURN 和断线恢复。
5. M10.5：显式授权的可选视觉输入。
6. M11.5：桌面 Companion。

边界：

- 文字和语音共用同一个 Conversation、Persona、Memory、RAG、Safety 和 Agent Trace。
- Voice Gateway 只负责媒体会话、ASR、TTS 和打断控制，不维护独立人格或记忆。
- Presentation Layer 使用抽象表现语义，不让 LangGraph 直接操作 Live2D 或 VRM 参数。
- Avatar Renderer 可插拔支持 Static、Live2D 和 VRM；人物失败不得阻断语音和字幕。
- AgentResponse 区分 `display_text` 和可选 `speech_text`，后者缺省时回退前者。
- 分句 TTS 使用请求编号和片段序号保证顺序播放；用户打断后只记录实际听到的 `heard_text`。
- 主动关怀和系统事件可禁止写入正常历史或参与长期记忆提取。
- 默认不长期保存原始音频或视频帧。
- 使用原创或获得明确授权的模型、动作与音色。
- Amadeus System 只作为架构参考，不复制其源码和角色素材。
- `https://github.com/umikok7/roxy-agent` 是后期 VRM/VRMA、Three.js、嘴型和桌面角色实现的重要参考；只参考工程思路，不默认复用或分发其中的洛琪希模型、动作、语音、Persona 或其他 IP 素材。

## 推荐技术栈

- Backend：Python、FastAPI。
- Agent：LangGraph。
- RAG：LangChain。
- Database：PostgreSQL、pgvector。
- ORM/Migration：SQLAlchemy 2.x、Alembic。
- Scheduler：APScheduler。
- Frontend：React、Vite、TypeScript。
- Testing：pytest、httpx。
- Deployment：Docker Compose。

Redis 在 V1 中不是必需依赖。

## Agent 主流程

```text
用户消息
  -> 创建 trace_id
  -> 保存消息
  -> 情绪识别
  -> 意图分类
  -> 检索长期记忆
  -> 按意图检索知识库或项目上下文
  -> 可选工具调用
  -> 组装 Persona Prompt
  -> 调用 LLM
  -> 安全检查
  -> 可选表情包
  -> 提取候选记忆
  -> 保存回复、附件和 trace
```

意图至少包括：

- `companion`
- `knowledge_qa`
- `mixed`
- `reminder`
- `unsafe`

## 数据来源与项目上下文

所有知识来源统一抽象为 Project Source Adapter：

- `UploadSourceAdapter`：V1，网页上传 Markdown、TXT、log。
- `WorkspaceSourceAdapter`：后续，读取 allowlist 工作目录。
- `GitSourceAdapter`：后续，读取 branch、diff、commit、changed files。
- `GitHubSourceAdapter`：后续，读取 issue、PR 和 diff。
- `MCPFilesystemSourceAdapter`：后续，通过 MCP 读取外部文件。

Workspace 模式必须：

- 仅在 Personal Self-hosted Mode 开启。
- 使用目录 allowlist。
- 支持 include/exclude。
- 默认排除 `.env`、密钥、证书、`.git`、依赖和构建目录。
- 使用 content hash 增量索引。
- 记录 ProjectIndexTrace。

## Tool、Skill 与 MCP

V1 先实现内置工具：

- `search_memory`
- `write_memory_candidate`
- `search_knowledge_base`
- `create_reminder`
- `select_sticker`

后续演进：

```text
Built-in Tools
  -> Skill Manifest
  -> Skill Registry
  -> MCP Tool Adapter
```

Skill 适合项目内部强业务能力，例如表情包、状态图、学习计划。

MCP 适合连接外部系统，例如文件、日历、GitHub、浏览器和笔记服务。高风险 MCP 工具必须显式启用并记录调用审计。

## Adaptive Learning

“自主学习”不表示重新训练模型或允许 Agent 任意改代码。

支持的成长方式：

- 从对话提取候选长期记忆。
- 从上传资料扩展 RAG 知识。
- Reflection Job 总结偏好和策略候选。
- 用户审核后更新 CompanionState 或 Conversation Policy。
- 通过 Skill/MCP 扩展能力。

高影响变化必须经过：

```text
pending_review -> approved / rejected / archived
```

## 部署模式

### Personal Self-hosted

- V1 默认模式。
- 单 owner 用户。
- 数据保存在个人机器或个人服务器。
- 可读取配置过的 workspace。

### Public Demo

- 面试和作品集演示。
- 只使用演示用户、演示记忆和演示知识库。
- 禁止高风险 MCP、系统配置写入和敏感文件上传。
- 支持一键重置数据。

### Hosted Multi-user

- 后续方向。
- 需要多租户隔离、配额、限流、审核、数据导出删除和计费。
- 不属于当前 V1。

## 程序员生产力扩展

建议优先级：

1. Project Context RAG。
2. Coding Session Companion。
3. Git/GitHub MCP。
4. AI Code Review Companion。
5. Error Log / Stack Trace Debugger。
6. Dev Journal 自动复盘。
7. Safe Command Advisor。
8. IDE 插件或轻量 Coding Agent。

这些能力必须保留 Companion 特性：理解用户当前项目、进度和挫败感，而不是退化为普通代码问答工具。

## 开发里程碑

1. M1：FastAPI、React、PostgreSQL、Alembic、Mock LLM。
2. M2：Web Chat、Persona Prompt、消息和 Agent Trace。
3. M3：Persona Builder。
4. M4：长期记忆。
5. M5：RAG。
6. M6：Project Context。
7. M7：Sticker 和 Active Care。
8. M7.5：沉浸式通话静态人物、AvatarRenderer 与 Presentation Engine。
9. M7.75：VRM/VRMA Renderer。
10. M8：Debug、Webhook、测试和 Docker。
11. M8.5：半实时语音闭环。
12. M9：Skill 与 MCP。
13. M9.5：WebRTC 实时可打断通话。
14. M10：Adaptive Learning。
15. M10.5：可选视觉输入。
16. M11：Workspace 和 Git Source。
17. M11.5：桌面 Companion。
18. M12：网络参考人物 Persona Builder。

## 开发约束

- 优先完成可运行、可测试的垂直闭环。
- Mock Provider 必须可在无 API Key 环境运行测试。
- LLM 输出应使用结构化 schema 校验，不依赖脆弱的字符串解析。
- Prompt、Provider、Retriever、Tool 和 Channel 之间保持清晰边界。
- 不把渠道逻辑写进 Conversation Service。
- 不把 Persona 文本散落在业务代码中。
- 不在日志中记录 API Key 或完整敏感聊天内容。
- 新增重要 AI 决策时同步补充 trace 字段和测试。
- 涉及文件系统、Shell、Git 写操作时默认只读或要求明确确认。
- 不为未来功能提前搭建过重框架；按照里程碑逐步演进。

## 后端开发与教学文档工作流

本项目同时用于帮助具有 Java / Spring Boot 后端经验的开发者系统学习 Python AI 应用开发。后端任务不能只交付代码；每次完成一个功能后，必须同步维护开发文档和学习文档。

### 开发文档

路径：

```text
docs/development/<模块名>.md
```

开发文档面向需要继续维护项目的工程师，必须以当前实际实现为准，至少包含：

1. 功能目标、范围和实际用户流程。
2. 模块架构、职责边界、目录和文件说明。
3. 核心类、函数、数据模型及重要代码位置。
4. API 请求、响应、统一错误结构。
5. 数据库表、字段、索引和迁移。
6. Agent、Prompt、Provider、Retriever、Tool 等 AI 模块边界。
7. 关键调用链、数据流和必要的 Mermaid 图。
8. 配置项、环境变量、启动、测试和调试方法。
9. Mock Provider 的使用方法。
10. 技术决策、已知限制和后续扩展点。

文档中的文件链接、行号、命令和预期结果必须在当前工作区中真实有效。不得把需求文档中的未来能力写成已经实现。

### 学习文档

路径：

```text
docs/learning/<序号>-<主题>.md
```

学习文档默认使用中文，面向熟悉 Java 后端但不熟悉 Python 和 AI 应用工程的读者。首次出现的术语必须解释，并结合项目真实代码讲解。

每章至少包含：

1. 学习目标和前置概念。
2. 本次涉及的 Python 语法与工程知识，例如类型标注、Pydantic 或 dataclass、async/await、装饰器、context manager、模块导入、异常处理和 pytest。
3. 与 Java / Spring Boot 的准确对照，包括 FastAPI Router、Depends、Pydantic、SQLAlchemy、pytest 和 Python async；需要说明语义差异，不能声称完全等同。
4. 本模块涉及的 AI 应用知识，例如 LLM、Prompt、结构化输出、Token、上下文窗口、流式响应、LangGraph、RAG、Embedding、Memory、Tool Calling、Skill 和 MCP。只详细讲解本次实际涉及的内容，其他概念可简要说明衔接关系。
5. 使用真实文件路径和行号进行代码讲解。
6. 关键调用链的逐步执行过程和 Mermaid 图。
7. 常见错误、调试方法、排查顺序和方案取舍。
8. 可以亲手完成的小练习。
9. 自测题、参考答案、章节总结和下一章衔接。

学习文档应足够完整，使用户能够脱离当前对话独立复习和复现功能。

### 后端任务执行顺序

每个后端任务按以下顺序执行：

1. 阅读 `AGENTS.md`、需求、已有开发文档和学习文档。
2. 分析功能边界和现有代码约定。
3. 先写或更新测试。
4. 实现最小可运行闭环。
5. 运行格式化、静态检查和测试。
6. 更新对应开发文档。
7. 编写或更新对应学习文档。
8. 验证文档中的路径、行号、命令和预期结果。
9. 最终汇报代码、测试、开发文档和学习文档的变化。

小型修复应更新已有模块的开发文档和学习文档，不为每个修复重复创建新文档。

后端功能只有同时满足以下条件才算完成：

- 代码可运行。
- 测试通过。
- 开发文档准确反映当前实现。
- 学习文档能够帮助 Java 开发者理解并复现实现。

## 尚未确定

代码工程初始化前仍需最终确认：

- Python 包管理器。
- React UI 组件方案。
- 首个真实 LLM/Embedding Provider。
- V1 是否直接使用 pgvector，或先以可替换检索接口启动。
- 管理员登录的具体实现。

在这些选择影响实现前，优先参考仓库已有约定；当前仓库尚无约定时，选择简单、主流、便于面试解释的方案。
