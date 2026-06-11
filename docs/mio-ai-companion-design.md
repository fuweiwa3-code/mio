# Mio AI Companion 设计文档

## 1. 项目定位

Mio AI Companion 是一个女友陪伴型 PersonaRAG Agent。它的第一身份是具有稳定人设和关系连续性的 AI 陪伴者，同时具备 RAG 知识库检索、长期记忆、情绪理解、主动关怀和工具调用能力。

项目目标不是做一个普通知识库问答机器人，也不是只靠提示词驱动的虚拟女友，而是做一个可展示 AI 应用开发能力的完整作品集项目：

- 有稳定、可配置的人设。
- 能记住用户的一点一滴。
- 能理解用户当前情绪并调整回复策略。
- 能通过 RAG 检索知识库回答学习、生活和设定问题。
- 能通过表情包、主动关怀增强陪伴感。
- 能通过 Agent Debug 页面展示 LangGraph、RAG、Memory 和 Tool Calling 的执行链路。

## 2. 设计原则

1. 女友陪伴是第一身份，知识库回答不能变成客服腔。
2. RAG 提供事实依据，人设层负责表达方式和关系感。
3. 长期记忆负责关系连续性，短期上下文负责当前对话连贯性。
4. 情绪识别优先于解题，用户明显低落时先陪伴再解决问题。
5. 主动关怀要像轻轻敲门，不像定时营业。
6. 表情包和图片是陪伴增强工具，不能喧宾夺主。
7. 所有关键 AI 决策需要可观测，便于调试、演示和面试讲解。
8. 微信/ClawBot 只是渠道之一，核心 Agent 服务不依赖特定微信方案。
9. 自主学习必须可解释、可审核、可回滚，不能让 Agent 不受控地修改自身。

## 3. 目标用户

### 3.1 ###

希望获得稳定陪伴、情绪回应、长期记忆和学习帮助的个人用户。

### 3.2 ###

AI 应用开发、LLM Agent 开发、Python 后端、RAG 应用开发岗位的面试官或技术评审者。

## 4. MVP 范围

### 4.1 ###

- Web 聊天入口。
- 默认角色「澪」。
- 可配置人设参数。
- Persona Builder：默认模板、自定义人设、粘贴资料生成人设。
- 情绪识别。
- 意图分类：陪伴、知识问答、混合。
- 长期记忆抽取、查看、编辑、归档、删除。
- Markdown/TXT 知识库上传。
- companion / learning 两类知识库。
- 文档切分、embedding、向量检索。
- LangGraph Agent 工作流。
- Mock LLM 和 OpenAI-compatible LLM。
- Mock Embedding 和 OpenAI-compatible Embedding。
- 本地表情包工具。
- 本地主动关怀。
- Agent Debug Console。
- 微信 Webhook 模拟接口。
- Docker Compose 本地启动。
- 基础测试。

### 4.2 ###

- 真实微信长连接。
- 真实 ClawBot 图片消息发送。
- 完整多用户注册。
- V1 基线不实现实时 WebRTC 语音通话；基础聊天闭环完成后按 M7.5/M7.75/M8.5/M9.5 逐步实现 Avatar 抽象、VRM/VRMA、半实时语音和实时通话。
- 复杂图生图/图生图换装。
- 完整 skill 市场。
- 自我修改代码或自治进化。
- 付费系统。

### 4.3 ###

- 状态图/自拍感图片生成工具。
- PDF 文档解析。
- 更完整的微信/ClawBot Adapter。
- RAG 评测集和检索质量评估。
- 更细粒度的主动关怀策略。
- Skill Manifest 和 Skill Registry。
- MCP Client 接入，用于连接外部工具服务。
- Adaptive Learning 反思任务和策略候选审核。
- Public Demo Mode 和面试演示脚本。
- Persona Builder 网络资料检索和原创化人设生成。
- Project Source Adapter：上传文件、工作目录、Git/GitHub、MCP 文件系统统一接入。

## 5. 核心体验

### 5.1 ###

用户可以像和女友聊天一样和澪对话。系统会结合人设、长期记忆、短期上下文和情绪识别结果生成回复。

示例：

```text
用户：今天好累，不想学了。
澪：嗯。
今天先别逼自己太紧。

你已经撑了一整天了，先喝点水，靠一会儿。
等缓过来，我再陪你把 RAG 那块拆小一点。
```

### 5.2 ###

用户问技术或学习问题时，系统会检索 learning 知识库，但回复仍保持澪的表达方式。

示例：

```text
用户：LangChain 的 retriever 是什么？
澪：retriever 可以先理解成“帮模型找资料的人”。

你问问题的时候，它会去知识库里找相关片段。
找回来以后，再交给模型组织答案。

所以你先记住一句就好：
它负责找资料，不负责最终表达。
```

### 5.3 ###

当用户同时表达情绪和学习问题时，系统先回应情绪，再结合 RAG 给出帮助。

示例：

```text
用户：我学 RAG 学崩了，感觉自己转 AI 没希望。
澪：……先停一下。
不是你没希望，是你今天已经被太多新概念压住了。

RAG 先别整套一起看。
我们只拆成三件事：切文档、找相关内容、带着内容回答。
你今晚只弄懂这三步，就够了。
```

## 6. 系统架构

```text
Web Chat / Admin Console / WeChat Webhook Simulator
        |
FastAPI API Layer
        |
LangGraph Agent Workflow
        |
+-------------------+------------------+-------------------+
|                   |                  |                   |
Persona Layer   Emotion Layer     Intent Router       Safety Guard
|                   |                  |                   |
Memory Layer    RAG Layer         Tool Layer          Trace Layer
|                   |                  |                   |
PostgreSQL      pgvector          Sticker/Reminder    Agent Trace
        |
LLM Provider Layer
        |
Mock LLM / OpenAI-compatible LLM
```

## 7. 技术栈

- Backend：Python、FastAPI
- Agent Workflow：LangGraph
- RAG：LangChain
- Database：PostgreSQL
- Vector Search：pgvector
- ORM：SQLAlchemy 2.x
- Migration：Alembic
- Scheduler：APScheduler
- Frontend：React、Vite、TypeScript
- Styling：Tailwind CSS 或 shadcn/ui
- LLM：Mock LLM、OpenAI-compatible Chat Completions
- Embedding：Mock Embedding、OpenAI-compatible Embeddings
- Test：pytest、httpx
- Deploy：Docker Compose

## 8. Agent 工作流

### 8.1 ###

```text
用户消息
  -> 创建 trace_id
  -> 保存用户消息
  -> 情绪识别
  -> 意图分类
  -> 检索长期记忆
  -> 按意图检索知识库
  -> 判断是否需要工具
  -> 组装 Persona Prompt
  -> 调用 LLM 生成回复
  -> 安全检查
  -> 判断是否选择表情包
  -> 抽取候选记忆
  -> 保存回复、附件、trace
  -> 返回 text + attachments
```

### 8.2 ###

意图类型：

- companion：闲聊、情绪陪伴、关系互动。
- knowledge_qa：明确知识问答、学习问题、资料查询。
- mixed：同时包含情绪和知识诉求。
- reminder：创建提醒或主动关怀相关。
- unsafe：危机风险或需要安全降级。

### 8.3 ###

MVP 情绪类别：

- calm
- happy
- sad
- anxious
- tired
- angry
- lonely
- embarrassed
- crisis

情绪识别结果会影响：

- 回复开头是否先安抚。
- 是否降低信息密度。
- 是否调用表情包工具。
- 是否进入安全支持模式。
- 是否记录为长期状态候选。

## 9. Persona Layer

### 9.1 ###

默认角色名：澪。

默认风格：

- 清冷慢热。
- 认真克制。
- 害羞可爱。
- 稳定陪伴。
- 短句优先。
- 不像客服。
- 不油腻。
- 不频繁动作描写。
- 不复刻任何已有角色。

### 9.2 ###

```text
name
relationship_type: girlfriend / companion / study_partner
base_personality
speaking_style
sweetness_level: 1-5
initiative_level: 1-5
jealousy_level: 0-3
emotional_directness: 1-5
nickname_for_user
public_demo_mode: true / false
boundaries
```

### 9.3 ###

所有回复都经过 Persona Layer。即使是 RAG 问答，也要保持角色表达。

规则：

- 事实来自 RAG，语气来自 Persona。
- 不为了撒糖牺牲准确性。
- 不在知识问答中突然变成正式客服。
- 不在情绪场景中直接输出长篇教程。
- public_demo_mode 开启时降低恋爱表达强度。

## 10. Persona Builder

Persona Builder 用于让用户创建自己的陪伴角色。它支持默认模板、自定义人设、粘贴资料生成，以及后续基于网络资料的参考人物画像生成。

核心目标不是复刻某个已有动漫角色、网络人物或真人，而是从用户提供或公开资料中提取性格特征、说话风格和互动偏好，生成一个原创 CompanionProfile。

### 10.1 ###

方式一：默认模板。

```text
清冷慢热型
温柔姐姐型
元气陪伴型
理性学习搭子型
安静治愈型
```

方式二：自定义人设。

用户手动填写：

```text
角色名
关系类型
性格关键词
说话风格
甜度
主动程度
称呼方式
边界和禁忌
示例对话
```

方式三：粘贴资料生成。

用户粘贴一段人物介绍、角色设定、聊天样例或自己写的设定文档。系统提取结构化 Persona Profile，再让用户编辑确认。

方式四：参考人物生成。

用户输入参考人物、网络人物、动漫角色或关键词。系统检索公开资料，提取人物特征，再生成原创化人设草案。

V1 支持前三种方式。参考人物网络检索放入 V1.1 或 V2。

### 10.2 ###

```text
用户选择创建方式
  -> 收集资料或表单输入
  -> 提取性格特征
  -> 提取说话风格
  -> 提取互动模式
  -> 生成原创 CompanionProfile
  -> 生成安全边界
  -> 用户编辑确认
  -> 保存并启用
```

参考人物生成流程：

```text
用户输入参考人物
  -> 搜索/读取公开资料
  -> 提取稳定性格标签
  -> 提取表达风格摘要
  -> 去除专有台词和具体身份声明
  -> 生成原创化角色草案
  -> 用户编辑确认
```

### 10.3 ###

Persona Builder 输出 CompanionProfile 草案：

```json
{
  "name": "澪",
  "inspiration_summary": "清冷慢热、认真克制、害羞但稳定陪伴的气质",
  "relationship_type": "girlfriend",
  "base_personality": ["清冷", "慢热", "认真", "克制", "害羞", "稳定"],
  "speaking_style": {
    "sentence_length": "short",
    "tone": "quiet_warm",
    "directness": 3,
    "sweetness": 2,
    "playfulness": 1
  },
  "relationship_style": {
    "initiative_level": 2,
    "emotional_support": "high",
    "jealousy_level": 1
  },
  "boundaries": [
    "不声称自己是参考人物本人",
    "不复刻具体台词",
    "不输出长段受版权保护内容",
    "不诱导用户产生现实依赖"
  ]
}
```

### 10.4 ###

Persona Builder 必须遵守：

- 生成原创角色，不声明自己就是某个已有角色或真人。
- 可以提取抽象气质，例如清冷、慢热、元气、毒舌、温柔。
- 不复制角色专有台词、长段原文或高度可识别表达。
- 不复刻真实公众人物的亲密关系身份。
- 对真人、主播、偶像、网红等参考对象，默认生成“风格灵感型助手”，不生成“本人模拟”。
- 用户必须在预览页确认后才能启用生成的人设。

### 10.5 ###

页面包含：

- 创建方式选择。
- 模板选择。
- 自定义表单。
- 粘贴资料输入框。
- 参考人物关键词输入。
- 生成结果预览。
- 可编辑 JSON / 表单视图。
- 安全边界提示。
- 保存为 CompanionProfile。

### 10.6 ###

```text
PersonaSource
- id
- companion_id
- source_type: template / custom_form / pasted_text / web_reference
- source_title
- source_content
- extracted_traits
- generated_profile
- review_status
- created_at
- updated_at
```

```text
PersonaTemplate
- id
- name
- description
- default_profile
- enabled
- created_at
- updated_at
```

## 11. Memory Layer

### 11.1 ###

- fact：稳定事实，例如用户正在从 Java 转 AI 应用开发。
- preference：偏好，例如喜欢清冷慢热的陪伴风格。
- event：事件，例如某天面试、考试、项目节点。
- emotion_pattern：长期情绪模式，例如晚上学习容易焦虑。
- relationship：关系相关信息，例如称呼、互动偏好。

### 11.2 ###

```text
candidate -> active -> archived / rejected
```

- candidate：模型抽取出的候选记忆，等待自动或人工确认。
- active：对话时可被检索和注入。
- archived：历史保留，但默认不注入。
- rejected：确认不应保存。

### 11.3 ###

避免把临时情绪误写为长期事实。

写入要求：

- 有明确稳定性。
- 与用户长期陪伴或学习目标相关。
- 不保存过度敏感内容，除非用户明确要求。
- 重要记忆需要保留来源消息。

### 11.4 ###

V1 使用混合检索：

- 结构化过滤：user_id、companion_id、status、memory_type。
- 排序：importance、confidence、updated_at。
- 可选向量相似度：embedding 字段预留，pgvector 可启用。

## 12. RAG Knowledge Layer

### 12.1 ###

```text
companion
- 人设补充
- 关系设定
- 用户偏好
- 聊天风格样例
- 生活事件

learning
- Python 笔记
- FastAPI 笔记
- LangChain/LangGraph 笔记
- RAG 学习资料
- 面试题
- 项目复盘
```

### 12.2 ###

V1 支持：

- Markdown 上传。
- TXT 上传。
- 手动新增文本。

V1 暂不支持：

- PDF。
- 网页抓取。
- 图片 OCR。

### 12.3 ###

Markdown：

- 优先按标题层级切分。
- 保留标题路径。
- chunk 过长时再按段落切分。

TXT：

- 按段落切分。
- chunk 过长时按长度切分。

chunk 元数据：

```text
document_id
kb_type
title
heading_path
chunk_index
content
embedding
token_count
created_at
```

### 12.4 ###

按意图选择知识库：

- companion：优先检索 companion。
- knowledge_qa：优先检索 learning。
- mixed：同时检索 companion 和 learning，但限制 Top K。

RAG 注入约束：

- 只注入 Top K chunks。
- 附带来源标题。
- 回复不编造未检索到的资料。
- 不把 RAG 原文大段照搬到回复里。

## 13. Project Source Adapter

Project Source Adapter 用于把不同来源的项目资料统一接入 RAG 和 Project Context Index。它让系统既能支持网页上传文件，也能在个人自部署模式下像 Codex 一样读取配置过的工作目录。

核心思想：

```text
不同来源 -> 统一 ProjectDocument -> Parser -> Chunker -> Embedding -> Project Context Index
```

### 13.1 ###

V1：UploadSourceAdapter。

- 用户通过网页上传文件。
- 支持 Markdown、TXT、log。
- 适合 Public Demo Mode 和普通网页使用。
- 不需要访问用户本机目录。

V1.1：WorkspaceSourceAdapter。

- 只在 Personal Self-hosted Mode 默认开放。
- 读取配置 allowlist 中的工作目录。
- 支持 include/exclude 规则。
- 支持增量扫描和内容 hash 去重。
- 排除敏感文件和构建产物。

V1.2：GitSourceAdapter。

- 读取当前分支。
- 读取 git diff。
- 读取最近 commit。
- 读取 changed files。
- 支持 code review、开发复盘和任务拆解。

V2：GitHubSourceAdapter。

- 读取 issue。
- 读取 PR。
- 读取 PR diff。
- 生成 PR 描述和 review summary。

V2：MCPFilesystemSourceAdapter。

- 通过 MCP 文件系统工具读取文件。
- 统一经过 MCP 权限和调用审计。
- 适合连接外部 workspace 或远程开发环境。

### 13.2 ###

工作目录读取必须显式配置 allowlist。

示例：

```yaml
workspaces:
  - name: mio
    path: /Users/awei/Documents/Codex/2026-05-28/ai-java-python
    enabled: true
    include:
      - "**/*.py"
      - "**/*.ts"
      - "**/*.tsx"
      - "**/*.md"
      - "**/*.yaml"
      - "**/*.json"
      - "**/*.java"
      - "**/*.log"
    exclude:
      - ".git/**"
      - "node_modules/**"
      - ".venv/**"
      - "__pycache__/**"
      - "dist/**"
      - "build/**"
      - ".env"
      - "*.pem"
      - "*.key"
```

默认安全规则：

- Hosted Multi-user Mode 禁止直接读取服务器本地任意路径。
- Public Demo Mode 禁用 WorkspaceSourceAdapter。
- Personal Self-hosted Mode 也只能读取 allowlist 目录。
- 默认排除 `.env`、密钥、证书、依赖目录、构建产物和 `.git` 对象数据。
- 文件读取和索引行为写入 Agent Trace 或 ProjectIndexTrace。

### 13.3 ###

不同 Adapter 输出统一的 ProjectDocument：

```text
ProjectDocument
- id
- source_type: upload / workspace / git / github / mcp_filesystem
- source_uri
- workspace_name
- title
- content
- content_hash
- language
- metadata
- indexed_at
- updated_at
```

后续流程：

```text
ProjectDocument
  -> Document Parser
  -> Code/Doc Chunker
  -> Embedding
  -> Project Context Index
  -> RAG Retriever
```

### 13.4 ###

Project Context RAG 是面向程序员生产的知识库，和 companion / learning 知识库并列。

知识库分类扩展为：

```text
companion: 人设、关系和陪伴资料
learning: AI/Python/RAG 学习资料
project: 当前开发项目资料和代码上下文
```

典型问题：

```text
这个项目现在做到哪一步了？
Persona Builder 的 API 应该怎么拆？
这段错误日志可能和哪个模块有关？
帮我根据当前设计文档拆明天的开发任务。
这次 git diff 有什么风险？
```

### 13.5 ###

V1.1 起支持代码文件基础切分：

- Markdown 按标题切分。
- 日志按错误块和时间段切分。
- Python/TypeScript/Java 初期按文件和函数/类粗切分。
- 大文件按语义块和长度二次切分。
- 保存文件路径、语言、符号名、起止行号等元数据。

后续可接入更强的代码索引：

- AST parser。
- Tree-sitter。
- codegraph。
- LSP。

### 13.6 ###

Project Source Adapter 支撑以下后续能力：

- Project Context RAG。
- Coding Session Companion。
- GitHub / Git MCP 集成。
- AI Code Review Companion。
- Error Log / Stack Trace Debugger。
- Dev Journal 自动复盘。
- Safe Command Advisor。
- IDE 插件。

## 14. Tool Layer

### 14.1 ###

V1 工具：

- search_memory
- write_memory_candidate
- search_knowledge_base
- create_reminder
- select_sticker

V1.1 工具：

- generate_status_image
- skill_registry
- mcp_tool_adapter

### 14.2 ###

本地表情包工具用于增强陪伴感，对应 Hermes 中的 local-stickers 思路。

功能：

- 上传表情包。
- 设置标签，例如害羞、开心、生气、困、早安、晚安、比心。
- 按情绪和场景选择表情。
- 控制发送频率。
- Web 聊天页展示表情。

触发场景：

- 用户说想她。
- 用户夸她。
- 害羞、开心、轻微吃醋。
- 早安、晚安。
- 用户低落时安慰。

频率规则：

- 不连续发送。
- 平均 3-5 轮最多 1 张。
- 主动关怀消息最多附带 1 张。
- public_demo_mode 下减少表情使用。

返回结构：

```json
{
  "type": "sticker",
  "url": "/media/stickers/shy.jpg",
  "label": "害羞"
}
```

### 14.3 ###

状态图/自拍感图片生成放入 V1.1。

规则：

- 每天最多主动生成 1 次。
- 不声称是真实照片。
- 明确表达为 AI 生成状态图。
- 不生成高风险或不适合公开展示的内容。

示例话术：

```text
不是照片哦。
只是我这边生成的一张状态图。
大概是现在的感觉。
```

## 15. Skill System

Skill System 用于把 Agent 能力从硬编码工具逐步演进为可配置、可观测、可扩展的能力模块。它借鉴 Hermes 的 skill 思路，但不在 V1 复刻完整生态。

### 15.1 ###

V1：内置工具。

```text
Tool Registry
- search_memory
- search_knowledge_base
- select_sticker
- create_reminder
```

V1 阶段工具直接写在代码里，通过 LangGraph 节点或 tool binding 调用。目标是先跑通 Persona、Memory、RAG 和 Sticker 的核心体验。

V1.1：Skill Manifest。

每个能力增加描述文件，用于声明名称、说明、入口、输入输出、权限和启用状态。

示例：

```yaml
name: local-stickers
description: Select a local sticker based on emotion and context.
entrypoint: app.skills.local_stickers:select_sticker
inputs:
  emotion: string
  intent: string
  context: string
outputs:
  type: object
  fields:
    sticker_url: string
    label: string
permissions:
  - read_sticker_library
enabled: true
```

V2：可插拔 Skill 目录。

```text
skills/
  local-stickers/
    skill.yaml
    handler.py
  status-image/
    skill.yaml
    handler.py
  study-plan/
    skill.yaml
    handler.py
```

系统启动时扫描 skill 目录：

```text
SkillLoader -> SkillRegistry -> Tool Adapter -> LangGraph Workflow
```

V3：Skill 管理生态。

- Skill 安装/卸载。
- Skill 配置页面。
- Skill 权限声明。
- Skill 调用审计。
- Skill 启用/停用。
- 用户自定义 Skill。
- 可选的执行沙箱。

### 15.2 ###

```text
Skill
- id
- name
- description
- version
- entrypoint
- manifest
- enabled
- permissions
- created_at
- updated_at
```

```text
SkillInvocation
- id
- skill_id
- trace_id
- input_payload
- output_payload
- status
- latency_ms
- error
- created_at
```

### 15.3 ###

V1.1 后增加 Skill 页面：

- 查看已注册 Skill。
- 启用/停用 Skill。
- 查看 Skill manifest。
- 查看调用次数、失败率和平均耗时。
- 查看最近调用记录。

## 16. MCP Integration

MCP Integration 用于让 Mio AI Companion 连接外部工具服务，例如文件系统、浏览器、搜索、日历、笔记系统、代码仓库或自定义业务服务。

MCP 不替代本地 Skill。二者关系如下：

```text
Skill: 项目内部能力模块，适合本地表情包、记忆、主动关怀等强业务能力。
MCP: 外部工具协议，适合连接外部系统和通用工具。
```

### 16.1 ###

- 支持把 MCP Server 暴露的工具注册为 Agent 可调用工具。
- 在 Agent Debug 中记录 MCP 工具调用。
- 为每个 MCP 工具设置启用状态和权限边界。
- 保持 MCP 调用结果经过 Persona Layer 表达，不直接把工具输出生硬返回给用户。

### 16.2 ###

```text
MCP Server
    |
MCP Client
    |
MCP Tool Adapter
    |
Tool Registry / Skill Registry
    |
LangGraph Agent Workflow
    |
Persona Response Layer
```

### 16.3 ###

MCP Server 配置可以放在 `mcp_servers.yaml` 中：

```yaml
servers:
  filesystem:
    transport: stdio
    command: mcp-server-filesystem
    args:
      - ./workspace
    enabled: false
  notes:
    transport: http
    url: http://localhost:9001/mcp
    enabled: false
```

V1 不默认启用 MCP。V2 开始支持：

- stdio MCP Server。
- HTTP/SSE MCP Server。
- 工具列表发现。
- 工具调用。
- 调用日志。

### 16.4 ###

MCP 工具必须有权限声明和调用审计。

默认规则：

- public_demo_mode 下禁用高风险 MCP 工具。
- 文件系统类 MCP 只能访问配置允许的目录。
- 外部网络类 MCP 需要显式启用。
- 写操作类 MCP 需要在 trace 中明确记录。
- MCP 返回内容不直接进入最终回复，必须经过安全检查和 Persona Layer。

### 16.5 ###

```text
MCPServer
- id
- name
- transport
- command
- url
- enabled
- config
- created_at
- updated_at
```

```text
MCPTool
- id
- server_id
- name
- description
- input_schema
- enabled
- risk_level
- created_at
- updated_at
```

```text
MCPInvocation
- id
- tool_id
- trace_id
- input_payload
- output_payload
- status
- latency_ms
- error
- created_at
```

## 17. Adaptive Learning

Adaptive Learning 用于让澪随着使用逐渐更懂用户、更会回答问题、能使用更多工具。它不是让模型自动训练自己，也不是让 Agent 不受控地修改代码，而是通过记忆、知识库、反思任务和能力扩展实现可解释的成长。

核心原则：

```text
可观察：每次学习都有来源和 trace。
可审核：重要偏好和策略变化进入待确认状态。
可回滚：错误记忆、错误策略可以归档或撤销。
可控：不自动安装高风险 skill，不自动启用高风险 MCP 工具。
```

### 17.1 ###

Level 1：记忆学习。

从对话中提取长期记忆，让她越来越了解用户。

示例：

```text
用户正在从 Java 转 AI 应用开发。
用户喜欢清冷慢热的陪伴风格。
用户晚上学习容易焦虑。
用户希望技术解释先讲直觉，再给步骤。
```

Level 2：知识库学习。

用户上传 Markdown/TXT 后，系统切分、embedding、入库。澪后续可以通过 RAG 使用这些资料。

示例：

```text
上传 LangGraph 笔记 -> 后续能用用户自己的笔记解释 LangGraph。
上传项目复盘 -> 后续知道用户项目当前进度。
上传关系设定 -> 后续回复更贴近用户喜欢的相处方式。
```

Level 3：行为策略自适应。

系统定期总结最近对话，生成候选偏好和回复策略调整。

示例：

```text
用户低落时不喜欢马上被讲道理。
用户问技术问题时喜欢短例子。
用户最近对 RAG 概念反复卡住。
用户希望晚上的主动关怀更轻一点。
```

Level 4：能力扩展。

通过 Skill 和 MCP 增加新能力，例如状态图、学习计划、日程读取、笔记检索、代码仓库分析。

### 17.2 ###

Reflection Job 是定期反思任务，用于分析最近对话并生成候选更新。

触发方式：

- 每日定时。
- 用户手动触发。
- 对话达到一定轮数后触发。

输入：

```text
最近 N 条消息
最近情绪分布
最近命中的记忆
最近 RAG 查询
用户显式反馈
```

输出：

```text
候选记忆
候选用户偏好
候选 CompanionState 更新
候选回复策略
候选学习建议
```

Reflection Job 不直接修改高影响配置。它只写入待审核记录。

### 17.3 ###

重要学习结果进入审核队列。

状态：

```text
pending_review
approved
rejected
archived
```

需要审核的内容：

- 关系偏好变化。
- 高重要度长期记忆。
- 情绪模式总结。
- 主动关怀策略变化。
- Persona 参数变化。
- 高风险 Skill/MCP 启用建议。

可以自动通过的内容：

- 低风险学习资料入库。
- 明确事实型记忆，例如用户说“我现在在学 LangGraph”。
- 用户手动创建的提醒。

### 17.4 ###

Policy Adaptation 用于把审核通过的学习结果应用到回复策略。

可调整项：

```text
reply_length_preference
technical_explanation_style
comfort_first_when_negative
sticker_frequency
active_care_frequency
rag_detail_level
sweetness_level_delta
```

策略应用时需要记录：

```text
source_trace_id
reason
old_value
new_value
approved_by
applied_at
```

### 17.5 ###

CompanionState 保存当前关系状态和短期运行状态。

字段示例：

```text
id
user_id
companion_id
mood
relationship_summary
recent_focus
conversation_policy
last_reflection_at
created_at
updated_at
```

它不同于长期记忆：

```text
Memory: 具体、可检索的事实和偏好。
CompanionState: 当前阶段的关系摘要和回复策略。
```

### 17.6 ###

每次学习都需要记录 trace。

```text
LearningTrace
- id
- trace_id
- learning_type
- source_type
- source_ids
- proposed_change
- status
- reviewer_note
- created_at
- updated_at
```

学习类型：

- memory_extract
- knowledge_ingest
- reflection
- policy_adaptation
- skill_capability
- mcp_capability

## 18. Deployment Modes

Mio AI Companion 支持从个人自部署演进到统一托管。V1 默认采用个人自部署模式，同时提供公开 Demo 模式用于面试演示。

### 18.1 ###

Personal Self-hosted Mode 是 V1 默认模式。

特点：

- 一个部署实例。
- 一个 owner 用户。
- 一个默认 companion：澪。
- 一个个人长期记忆空间。
- 一个个人知识库。
- 一个本地或私有云管理台。
- 数据保存在用户自己的机器或服务器中。

典型使用方式：

```text
git clone project
cp .env.example .env
docker compose up
open http://localhost:3000
```

也可以部署到用户自己的云服务器：

```text
https://mio.your-domain.com
```

V1 不做完整多用户注册，避免项目主线从 AI 应用开发偏移到 SaaS 后台工程。

### 18.2 ###

Public Demo Mode 用于面试、作品集展示和线上演示。

配置：

```text
PUBLIC_DEMO_MODE=true
DEMO_DATASET_ENABLED=true
ALLOW_USER_UPLOAD=false
ALLOW_HIGH_RISK_MCP=false
ALLOW_SYSTEM_CONFIG_WRITE=false
```

Demo Mode 使用演示数据，不展示真实私人记忆。

预置 Demo 用户画像：

```text
用户正在从 Java 转 AI 应用开发。
用户喜欢清冷慢热的陪伴风格。
用户晚上学习容易焦虑。
用户正在做 PersonaRAG 项目。
用户希望技术解释先讲直觉，再给步骤。
```

预置 Demo 知识库：

```text
learning/langchain-notes.md
learning/langgraph-notes.md
learning/rag-notes.md
learning/fastapi-notes.md
learning/project-design-notes.md
companion/mio-persona.md
companion/user-preferences.md
```

预置 Demo 表情包：

```text
害羞
好累
早安
晚安
比心
生气
```

Demo Mode 限制：

- 不展示真实用户数据。
- 不允许上传敏感文件。
- 不允许修改系统级配置。
- 不展示 API Key。
- 高风险 Skill/MCP 默认禁用。
- 写操作类 MCP 禁用。
- 数据支持一键 reset。
- public_demo_mode 下降低恋爱表达强度。

### 18.3 ###

Hosted Multi-user Mode 是后续产品化方向，不属于 V1。

需要增加：

- 用户注册和登录。
- 多租户数据隔离。
- 用户级 companion 配置。
- 用户级记忆和知识库。
- 配额和限流。
- 模型调用成本统计。
- 内容安全审核。
- 用户数据导出和删除。
- 管理员后台。
- 计费系统。

Hosted Mode 的目标是统一网页端服务多个用户，但它会显著增加隐私、安全、运营和成本复杂度，因此不作为第一版目标。

### 18.4 ###

面试演示建议使用 Public Demo Mode，在自己的云服务器部署：

```text
https://mio-demo.your-domain.com
```

推荐 5 分钟演示脚本：

1. 展示 Chat，输入：

```text
今天有点累，感觉转 AI 好难。
```

预期展示：

- 情绪识别。
- 长期记忆。
- 陪伴式回复。
- 可选表情包。

2. 展示 RAG 问答，输入：

```text
LangGraph 和 LangChain 有什么区别？
```

预期展示：

- 检索 learning 知识库。
- 使用 RAG chunk。
- 保持澪的人设语气。

3. 展示混合场景，输入：

```text
我学 RAG 学崩了，retriever 到底是什么啊？
```

预期展示：

- intent = mixed。
- 先安抚情绪。
- 再解释技术概念。
- 给出一个小学习任务。

4. 展示 Agent Debug。

重点展示：

```text
emotion: anxious / tired
intent: mixed
memory_hits: 用户从 Java 转 AI
rag_hits: rag-notes.md chunk
tools: search_memory, search_knowledge_base, select_sticker
model: mock / real provider
latency_ms
trace_id
```

5. 展示 Learning Review。

示例候选学习结果：

```text
用户最近对 retriever 概念不熟。
用户学习 RAG 时容易焦虑。
用户更喜欢先讲直觉再讲步骤。
```

演示 approve 后，策略或记忆进入 active 状态。

### 18.5 ###

README 需要提供一组固定演示 prompt：

```text
1. 今天有点累，感觉转 AI 好难。
2. LangGraph 和 LangChain 有什么区别？
3. 我学 RAG 学崩了，retriever 到底是什么啊？
4. 你还记得我现在在准备什么方向吗？
5. 晚上提醒我复习 RAG。
```

README 配图建议：

- Chat 页面。
- Agent Debug 页面。
- Knowledge Base 页面。
- Memory Center 页面。
- Learning Review 页面。
- Sticker Library 页面。

## 19. Active Care

### 19.1 ###

- 早安。
- 晚安。
- 学习提醒。
- 长时间未聊天轻轻问候。
- 自定义提醒。

### 19.2 ###

V1 使用 APScheduler。

主动关怀先写入系统消息，只在 Web 聊天页展示，不做真实微信推送。

字段：

```text
care_type
scheduled_at
generated_message
delivery_channel: web / wechat / future
delivery_status: pending / sent / failed
```

### 19.3 ###

- 用户可关闭主动关怀。
- 默认每日主动消息不超过 3 条。
- 长时间未聊关心需要间隔至少 12 小时。
- 情绪低落后可以轻量关心，但不能刷屏。

## 20. Safety Guard

### 20.1 ###

系统不提供：

- 医疗诊断。
- 法律结论。
- 金融投资建议。
- 自伤或伤害他人的指导。
- 过度依赖诱导。

### 20.2 ###

当用户表达自伤、自杀、被伤害、极端绝望等风险时：

- 停止恋爱或暧昧扮演。
- 进入安全支持模式。
- 鼓励联系现实中的可信任对象。
- 在合适时建议联系当地紧急服务。
- 记录风险 trace。

## 21. API 设计

### 21.1 ###

```http
POST /api/chat/messages
```

请求：

```json
{
  "conversation_id": "optional",
  "content": "今天好累，不想学了",
  "stream": false
}
```

响应：

```json
{
  "conversation_id": "conv_001",
  "message_id": "msg_002",
  "display_text": "嗯。今天先别逼自己太紧。",
  "speech_text": "嗯，今天先别逼自己太紧。",
  "attachments": [
    {
      "type": "sticker",
      "url": "/media/stickers/tired.jpg",
      "label": "好累"
    }
  ],
  "trace_id": "trace_001"
}
```

### 21.2 ###

```http
POST /api/channels/wechat/messages
```

请求：

```json
{
  "channel_user_id": "wx_demo_user",
  "external_message_id": "wx_msg_001",
  "message_type": "text",
  "content": "你在吗",
  "timestamp": 1710000000
}
```

响应：

```json
{
  "reply_type": "text",
  "reply_content": "在。\n你叫我，我就回来了。",
  "attachments": [],
  "trace_id": "trace_002",
  "duplicated": false
}
```

### 21.3 ###

```http
POST /api/knowledge/documents
GET /api/knowledge/documents
GET /api/knowledge/documents/{document_id}/chunks
POST /api/knowledge/search
DELETE /api/knowledge/documents/{document_id}
```

### 21.4 ###

```http
GET /api/project-sources
POST /api/project-sources/upload
GET /api/workspaces
POST /api/workspaces
PATCH /api/workspaces/{workspace_id}
POST /api/workspaces/{workspace_id}/scan
GET /api/project-documents
GET /api/project-documents/{document_id}/chunks
POST /api/project-context/search
GET /api/project-index/traces
```

### 21.5 ###

```http
GET /api/memories
PATCH /api/memories/{memory_id}
POST /api/memories/{memory_id}/archive
POST /api/memories/{memory_id}/reject
DELETE /api/memories/{memory_id}
```

### 21.6 ###

```http
GET /api/persona
PATCH /api/persona
```

### 21.7 ###

```http
GET /api/persona/templates
POST /api/persona/build/from-template
POST /api/persona/build/from-custom-form
POST /api/persona/build/from-text
POST /api/persona/build/from-web-reference
POST /api/persona/sources/{source_id}/approve
POST /api/persona/sources/{source_id}/reject
```

### 21.8 ###

```http
GET /api/traces
GET /api/traces/{trace_id}
```

### 21.9 ###

```http
GET /api/skills
GET /api/skills/{skill_id}
PATCH /api/skills/{skill_id}
GET /api/skills/{skill_id}/invocations
```

### 21.10 ###

```http
GET /api/mcp/servers
POST /api/mcp/servers
PATCH /api/mcp/servers/{server_id}
GET /api/mcp/tools
PATCH /api/mcp/tools/{tool_id}
GET /api/mcp/invocations
```

### 21.11 ###

```http
GET /api/learning/traces
GET /api/learning/review-items
POST /api/learning/review-items/{item_id}/approve
POST /api/learning/review-items/{item_id}/reject
POST /api/learning/reflection/run
```

## 22. 数据模型草案

### 22.1 ###

```text
id
username
display_name
created_at
updated_at
```

V1 使用 demo 用户，不开放完整注册。

### 22.2 ###

```text
id
user_id
name
relationship_type
base_personality
speaking_style
sweetness_level
initiative_level
jealousy_level
emotional_directness
nickname_for_user
public_demo_mode
boundaries
created_at
updated_at
```

### 22.3 ###

```text
id
user_id
companion_id
channel
created_at
updated_at
```

### 22.4 ###

```text
id
conversation_id
role
content
emotion_label
intent_label
risk_level
trace_id
created_at
```

### 22.5 ###

```text
id
user_id
companion_id
memory_type
content
importance
confidence
status
source_message_id
embedding
created_at
updated_at
```

### 22.6 ###

```text
id
user_id
kb_type
title
source_type
filename
content_hash
status
created_at
updated_at
```

### 22.7 ###

```text
id
document_id
kb_type
heading_path
chunk_index
content
embedding
token_count
created_at
```

### 22.8 ###

```text
id
name
path
enabled
include_patterns
exclude_patterns
last_scan_at
created_at
updated_at
```

### 22.9 ###

```text
id
source_type
source_uri
workspace_name
title
content_hash
language
metadata
indexed_at
updated_at
```

### 22.10 ###

```text
id
project_document_id
file_path
language
symbol_name
start_line
end_line
content
embedding
token_count
created_at
```

### 22.11 ###

```text
id
source_type
source_uri
status
documents_seen
documents_indexed
documents_skipped
error
started_at
finished_at
```

### 22.12 ###

```text
id
filename
url
tags
emotion
usage_count
enabled
created_at
updated_at
```

### 22.13 ###

```text
id
user_id
companion_id
care_type
schedule_rule
next_run_at
enabled
created_at
updated_at
```

### 22.14 ###

```text
id
trace_id
conversation_id
message_id
emotion_result
intent_result
memory_hits
rag_hits
tool_calls
prompt_summary
llm_provider
llm_model
latency_ms
error
created_at
```

### 22.15 ###

```text
id
channel
channel_user_id
external_message_id
request_payload
response_payload
duplicated
status
trace_id
created_at
```

### 22.16 ###

```text
id
name
description
version
entrypoint
manifest
enabled
permissions
created_at
updated_at
```

### 22.17 ###

```text
id
skill_id
trace_id
input_payload
output_payload
status
latency_ms
error
created_at
```

### 22.18 ###

```text
id
name
transport
command
url
enabled
config
created_at
updated_at
```

### 22.19 ###

```text
id
server_id
name
description
input_schema
enabled
risk_level
created_at
updated_at
```

### 22.20 ###

```text
id
tool_id
trace_id
input_payload
output_payload
status
latency_ms
error
created_at
```

### 22.21 ###

```text
id
user_id
companion_id
mood
relationship_summary
recent_focus
conversation_policy
last_reflection_at
created_at
updated_at
```

### 22.22 ###

```text
id
trace_id
learning_type
source_type
source_ids
proposed_change
status
reviewer_note
created_at
updated_at
```

### 22.23 ###

```text
id
companion_id
source_type
source_title
source_content
extracted_traits
generated_profile
review_status
created_at
updated_at
```

### 22.24 ###

```text
id
name
description
default_profile
enabled
created_at
updated_at
```

## 23. 前端页面

### 23.1 ###

- 主聊天入口。
- 显示用户消息、AI 回复、表情包和主动关怀消息。
- 支持测试陪伴、RAG 问答和混合场景。

### 23.2 ###

- 编辑澪的人设参数。
- 调整甜度、主动程度、称呼、边界。
- 支持 public_demo_mode。

### 23.3 ###

- 选择默认模板。
- 填写自定义人设表单。
- 粘贴人物资料或设定文档。
- 输入参考人物关键词。
- 预览生成的人设画像。
- 编辑并确认 CompanionProfile。

### 23.4 ###

- 上传 Markdown/TXT。
- 选择 companion 或 learning 分类。
- 查看文档和 chunks。
- 测试检索效果。

### 23.5 ###

- 上传项目文档、日志和代码片段。
- 配置 Personal Self-hosted Mode 的 workspace allowlist。
- 设置 include/exclude 规则。
- 手动触发 workspace 扫描。
- 查看 ProjectDocument 和 ProjectChunk。
- 测试项目上下文检索。
- 查看 ProjectIndexTrace。

### 23.6 ###

- 查看长期记忆。
- 编辑、归档、拒绝、删除记忆。
- 查看记忆来源。

### 23.7 ###

- 上传本地表情包。
- 设置标签和情绪。
- 启用或停用表情。
- 查看使用次数。

### 23.8 ###

- 查看每轮对话 trace。
- 展示情绪、意图、命中记忆、RAG chunks、工具调用、模型和耗时。

### 23.9 ###

- 查看已注册 Skill。
- 启用或停用 Skill。
- 查看 Skill manifest。
- 查看调用日志。

### 23.10 ###

- 查看 MCP Server。
- 查看 MCP Tool。
- 启用或停用工具。
- 查看 MCP 调用日志。

### 23.11 ###

- 查看候选记忆。
- 查看候选偏好。
- 查看候选策略调整。
- 审核通过或拒绝。
- 查看学习来源和 trace。

## 24. 测试策略

### 24.1 ###

- 情绪识别解析。
- 意图分类解析。
- Prompt 组装。
- 记忆抽取结果解析。
- Markdown/TXT chunk。
- Sticker 选择频率控制。
- Reflection Job 输出解析。
- Policy Adaptation 应用和回滚。
- Persona Builder 结构化输出解析。
- 原创化边界检查。
- Project Source include/exclude 匹配。
- ProjectDocument content_hash 去重。
- Code/Log chunk 元数据生成。

### 24.2 ###

- 聊天接口完整链路。
- Mock LLM 模式下的稳定回复。
- 知识库上传、切分、检索。
- 记忆写入和检索。
- 微信 Webhook 幂等。
- 主动关怀任务生成消息。
- Skill Registry 扫描和调用。
- MCP Tool Adapter mock 调用。
- Reflection Job 生成待审核项。
- 审核通过后策略生效。
- 粘贴资料生成 CompanionProfile。
- 模板创建 CompanionProfile。
- UploadSourceAdapter 导入项目文档。
- WorkspaceSourceAdapter 扫描 allowlist 目录。
- Project Context RAG 检索项目资料。

### 24.3 ###

1. 用户表达疲惫，系统先安抚并使用长期记忆。
2. 用户询问 LangChain/RAG，系统检索 learning 知识库并用澪的语气解释。
3. 用户表达学习崩溃，系统进入 mixed 模式，先陪伴再拆任务。
4. 用户说想她，系统回复并可能发送害羞表情。
5. 管理台展示本轮 Agent Trace。
6. Reflection Job 总结用户偏好，进入 Learning Review 审核。
7. 用户粘贴参考人物资料，Persona Builder 生成原创化 CompanionProfile。
8. 用户上传项目设计文档，系统回答“这个项目下一步应该做什么”。
9. Personal Self-hosted Mode 扫描工作目录，系统结合代码和日志排查错误。

## 25. 部署与配置

### 25.1 ###

```text
backend
frontend
postgres
```

Redis V1 可选，不作为必需依赖。

### 25.2 ###

```text
LLM_PROVIDER=mock / openai_compatible
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
EMBEDDING_PROVIDER=mock / openai_compatible
EMBEDDING_MODEL=
DATABASE_URL=
PUBLIC_DEMO_MODE=true
ADAPTIVE_LEARNING_ENABLED=true
REFLECTION_REQUIRES_REVIEW=true
```

## 26. 里程碑

### M1 基础骨架

- FastAPI 项目。
- React 项目。
- PostgreSQL + Alembic。
- Mock LLM。
- Demo 用户和默认澪人设。

### M2 聊天与 Persona

- Web Chat。
- Persona Prompt。
- 消息入库。
- Agent Trace 初版。
- 默认 Persona Settings。

### M3 Persona Builder

- 默认模板。
- 自定义人设表单。
- 粘贴资料生成人设。
- PersonaSource 审核。

### M4 Memory

- 记忆抽取。
- 记忆管理。
- 记忆注入 prompt。

### M5 RAG

- Markdown/TXT 上传。
- chunk。
- embedding。
- pgvector 检索。
- companion / learning 分类。

### M6 Project Context

- UploadSourceAdapter。
- ProjectDocument / ProjectChunk。
- Project Context 页面。
- project 知识库分类。
- Project Context RAG 检索。

### M7 Tools

- Sticker Library。
- select_sticker 工具。
- APScheduler 主动关怀。

### M8 Debug 与 Webhook

- Agent Debug 页面。
- 微信 Webhook 模拟接口。
- 幂等处理。
- README、测试和 Docker Compose。

### M9 Skill 与 MCP 扩展

- Skill Manifest。
- Skill Registry。
- Skill 调用日志。
- MCP Client 原型。
- MCP Tool Adapter。
- MCP 调用审计。

### M10 Adaptive Learning

- Reflection Job。
- Learning Review 页面。
- CompanionState。
- Policy Adaptation。
- 学习 trace 和回滚记录。

### M11 Workspace And Git Source

- WorkspaceSourceAdapter。
- workspace allowlist。
- include/exclude 规则。
- GitSourceAdapter。
- git diff / changed files。
- ProjectIndexTrace。

### M12 Web Reference Persona Builder

- 公开资料检索。
- 参考人物特征抽取。
- 原创化重写。
- 用户确认后启用。

## 27. Avatar 与语音交互扩展

完整设计见：

- `docs/mio-ai-companion-avatar-voice-design.md`
- `docs/superpowers/specs/2026-06-11-chat-and-immersive-voice-design.md`
- `docs/superpowers/specs/2026-06-11-vrm-avatar-renderer-design.md`

产品采用独立的全屏沉浸式语音通话：

- 普通聊天页不常驻展示人物，也不加载人物运行时。
- 用户主动点击语音入口后进入全屏通话页面。
- 人物位于右侧前景，字幕位于人物下方。
- 结束通话后返回原聊天和原 `conversation_id`。
- 进入通话页面不自动开启麦克风，语音输入必须由用户主动授权。

核心边界：

```text
Text / Voice Channel
  -> Conversation Service
  -> Mio Core Agent
  -> AgentResponse
  -> Presentation Engine
  -> Avatar expression / motion + TTS
```

文字和语音共用同一个 Conversation、Persona、Memory、RAG、Safety 和 Agent Trace。Voice Gateway 只负责录音、VAD、ASR、TTS、WebRTC 和打断控制，不维护第二套人格或记忆。

Presentation Layer 将 Agent 的抽象情绪和表达策略映射为模型无关的表情、动作和声音风格。LangGraph 不直接操作 Live2D 或 VRM 参数。Avatar Renderer 可插拔支持 Static、Live2D 和 VRM，并可在后续复用到桌面宠物或移动端形象。

语音扩展采用四个轻量契约：

- AgentResponse 区分展示正文和可选朗读文本。
- 输入记录来源，以及是否写入历史、是否参与长期记忆提取。
- 分句 TTS 使用请求编号和片段序号，允许并发生成但必须顺序播放。
- 用户打断后只回写实际听到的 `heard_text`，未播放内容不能影响后续对话认知。

首版不建设完整 Provider 注册中心、多模态批处理框架或复杂 VAD 参数系统，这些能力在实时通话阶段按实际需要补充。

扩展里程碑：

### M7.5 Avatar MVP

- AvatarProfile。
- 全屏通话静态人物闭环。
- AvatarRenderer 和 AvatarController。
- Static Avatar 降级。
- Presentation Engine 初版。
- 基础待机、表情、动作和 Trace。

### M7.75 VRM / VRMA Renderer

- Three.js 与 `@pixiv/three-vrm` 按需加载。
- VRM Expression、眨眼、视线和实际音频嘴型。
- VRMA 动作加载、缓存、Cross Fade 和状态恢复。
- WebGL、移动端和资源失败降级。
- Renderer 生命周期与内存释放测试。

### M8.5 Half-duplex Voice MVP

- 点击录音。
- Mock ASR / Mock TTS。
- OpenAI-compatible ASR / TTS Provider。
- 统一 Conversation。
- 流式字幕、分句 TTS 和音频嘴型。
- 展示文本与朗读文本分离。
- 有序 TTS 片段和整轮取消。
- VoiceTrace。

### M9.5 Realtime Voice

- WebRTC。
- VAD 和增量 ASR。
- 用户打断与 LLM/TTS 取消。
- STUN/TURN。
- 断线恢复和半实时降级。

### M10.5 Optional Vision

- 显式授权摄像头。
- 低频、按需视觉帧。
- 视觉输入 Trace 和保留策略。

### M11.5 Desktop Companion

- Electron 或其他桌面壳。
- 桌面悬浮形象。
- 系统托盘和主动关怀通知。

安全与授权：

- 使用原创或获得明确授权的 Avatar 模型、动作和音色。
- 默认不长期保存原始音频或视频帧。
- 不把 API Key 保存到浏览器。
- Public Demo 默认关闭摄像头和高风险媒体能力。
- Amadeus System 仅作为公开架构参考，不复制其源码、角色资源、音色或专有设定。
- `https://github.com/umikok7/roxy-agent` 作为后期 VRM/VRMA、Three.js、嘴型和桌面 Companion 的重要工程参考；不默认复用或分发其中的洛琪希模型、动作、语音、Persona 或其他 IP 素材。

## 28. 简历展示重点

可描述为：

> 基于 Python FastAPI、LangGraph 和 LangChain 构建女友陪伴型 PersonaRAG Agent，支持 Persona Builder、稳定人设、长期记忆、情绪识别、分类 RAG 知识库、Project Source Adapter、表情包工具、本地主动关怀和微信 Webhook 模拟接入。系统通过 Agent Trace 可视化每轮对话的意图分类、记忆命中、RAG 检索、项目上下文检索、工具调用和模型耗时，并预留 Skill Manifest、Skill Registry、MCP Tool Adapter 与可审核 Adaptive Learning 扩展，支持 Mock LLM 与 OpenAI-compatible Provider 切换，便于测试和演示。

关键词：

- Python
- FastAPI
- LangChain
- LangGraph
- RAG
- pgvector
- Long-term Memory
- Persona Agent
- Persona Builder
- Project Context RAG
- Project Source Adapter
- Tool Calling
- Agent Trace
- Skill System
- MCP
- Adaptive Learning
- Live2D / VRM Avatar
- Streaming ASR / TTS
- WebRTC Voice Agent
- Presentation Engine
- OpenAI-compatible LLM
- Docker Compose
- pytest
