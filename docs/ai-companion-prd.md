# AI Companion Agent 情感陪伴系统需求文档

## 1. 项目背景

AI 应用开发岗位越来越关注大模型在真实业务场景中的落地能力，包括多轮对话、长期记忆、工具调用、多渠道接入、用户画像、安全控制和工程化部署。本项目面向个人情感陪伴场景，构建一个可通过 Web 和微信渠道使用的 AI Companion Agent。

项目不直接依赖某一个微信机器人方案。微信、ClawBot 或其他消息入口只作为渠道适配层，核心能力沉淀在独立的 Python 后端服务中，便于后续扩展到小程序、飞书、Telegram、Discord 或移动 App。

## 2. 项目目标

### 2.1 产品目标

- 为用户提供一个稳定、温和、有记忆能力的 AI 陪伴对象。
- 支持日常聊天、情绪安抚、主动关怀、纪念日提醒和生活陪伴。
- 允许用户自定义陪伴角色的人设、称呼、说话风格和边界。
- 在用户出现明显风险表达时，系统从角色扮演模式切换到安全支持模式。

### 2.2 技术目标

- 使用 Python 构建生产级 AI 应用后端。
- 展示 RAG、长期记忆、Agent 工作流、多渠道消息适配、异步任务和安全策略能力。
- 支持 Web 端和微信/ClawBot 通道接入。
- 通过 Docker 实现本地一键启动，便于演示和部署。

## 3. 目标用户

### 3.1 普通用户

希望获得日常陪伴、情绪倾听、生活提醒和轻量关系感的用户。

### 3.2 作品集/面试受众

AI 应用开发、AI 后端开发、Python 后端、LLM Agent 开发岗位的面试官或技术评审者。

## 4. 产品定位

本项目定位为“AI 情感陪伴 Agent”，而不是单纯的聊天机器人。系统需要具备以下特点：

- 有连续关系感：能记住用户长期信息。
- 有情绪理解能力：能识别用户当前情绪，并调整回复策略。
- 有主动性：可根据时间、事件和用户状态主动发送关怀。
- 有边界：不提供医疗、法律、金融等高风险建议；遇到危机表达时触发安全回应。
- 可多渠道使用：核心服务独立于 Web、微信或其他客户端。

## 5. 核心场景

### 5.1 日常聊天

用户可以通过 Web 或微信发送文本消息。AI 根据用户画像、角色设定、历史上下文和当前情绪生成回复。

### 5.2 长期记忆

系统从对话中提取稳定信息，例如昵称、生日、作息、偏好、重要关系、近期压力源和重要事件。记忆需要可查看、可编辑、可删除。

### 5.3 主动关怀

系统可以在用户设定的时间发送早安、晚安、喝水、休息、纪念日、考试/面试/工作节点提醒。

### 5.4 情绪陪伴

当用户表达低落、焦虑、生气、孤独等情绪时，系统应优先倾听、共情、澄清需求，再给出温和建议。

### 5.5 微信接入

系统提供统一的消息回调接口，ClawBot 或其他微信通道负责把微信消息转发给后端。后端完成 AI 回复后，再通过适配层返回微信。

### 5.6 安全支持

当用户出现自伤、自杀、极端危险、被伤害等高风险表达时，系统不继续恋爱或暧昧扮演，而是切换为安全支持话术，鼓励联系可信任的人或当地紧急支持渠道。

## 6. 功能需求

### 6.1 用户系统

- 支持用户注册、登录和退出。
- 支持用户基础资料维护。
- 支持多渠道账号绑定，例如 Web 用户与微信用户绑定。
- 支持用户数据删除。

### 6.2 角色设定

- 用户可以创建一个或多个陪伴角色。
- 角色字段包括名称、关系定位、说话风格、称呼方式、禁忌话题和回复长度偏好。
- 系统提供默认角色模板。
- MVP 阶段至少支持一个默认角色和一个自定义角色。

### 6.3 对话系统

- 支持多轮文本对话。
- 支持流式回复，Web 端优先实现。
- 支持对话历史保存。
- 支持按会话查看历史记录。
- 支持上下文压缩，避免长对话超过模型上下文限制。
- 支持失败重试和错误提示。

### 6.4 记忆系统

- 自动从对话中提取候选记忆。
- 记忆分为事实记忆、偏好记忆、事件记忆和情绪记忆。
- 重要记忆写入数据库。
- 对话时检索相关记忆并注入提示词。
- 用户可以查看、修改、删除记忆。
- 系统需要避免把临时情绪误写成长期事实。

### 6.5 情绪识别

- 对每条用户消息进行情绪分类。
- MVP 情绪类别包括平静、开心、低落、焦虑、生气、孤独、危机风险。
- 情绪识别结果影响回复策略。
- 情绪识别结果写入会话元数据，用于后续统计。

### 6.6 主动关怀

- 支持用户设置提醒时间。
- 支持早安、晚安、纪念日和自定义提醒。
- 支持基于最近状态的轻量主动关怀，例如用户连续多天表达压力时发送关心。
- 支持关闭主动消息。
- 主动消息必须控制频率，避免打扰。

### 6.7 微信/ClawBot 适配

- 后端提供 `POST /api/channels/wechat/messages` 回调接口。
- 接口接收渠道用户 ID、消息 ID、消息类型、文本内容和时间戳。
- 后端返回回复文本和可选元数据。
- 适配层负责对接 ClawBot、微信机器人、公众号或其他微信入口。
- 后端不直接保存微信登录凭证。
- MVP 阶段只要求支持文本消息。

### 6.8 管理后台

MVP 阶段提供简化后台或接口文档即可。后续版本支持：

- 用户列表。
- 消息量统计。
- 情绪趋势统计。
- 模型调用成本统计。
- 风险消息审计。

## 7. 非功能需求

### 7.1 性能

- 普通文本回复首字响应时间应小于 3 秒。
- 非流式完整回复应尽量控制在 15 秒内。
- 文档和记忆检索延迟应控制在 1 秒内。

### 7.2 稳定性

- 模型接口失败时需要返回可理解的降级提示。
- 异步任务失败需要记录日志并支持重试。
- 微信渠道重复推送消息时需要通过消息 ID 去重。

### 7.3 安全与隐私

- 用户敏感信息加密或最小化存储。
- 用户可以删除对话和记忆。
- 日志中避免记录完整隐私内容。
- 不使用非必要的个人身份信息。
- 高风险内容触发安全策略。

### 7.4 可维护性

- 核心对话逻辑、记忆逻辑、情绪识别、渠道适配需要模块化。
- 微信接入不可与核心 Agent 强耦合。
- 提供 OpenAPI 文档。
- 使用 Docker Compose 管理本地依赖。

## 8. 技术方案

### 8.1 推荐技术栈

- 后端：Python、FastAPI
- 数据库：PostgreSQL
- 向量检索：pgvector 或 Qdrant
- 缓存：Redis
- 异步任务：Celery、RQ 或 APScheduler
- Agent 编排：LangGraph 或轻量自研工作流
- 模型接入：OpenAI API 或其他兼容 OpenAI 协议的大模型服务
- 前端：React 或 Vue
- 部署：Docker Compose

### 8.2 系统架构

```text
Web / 微信 / ClawBot
        |
Channel Adapter
        |
FastAPI API Gateway
        |
Conversation Service
        |
+----------------------+---------------------+
|                      |                     |
Memory Service   Emotion Service      Safety Guard
|                      |                     |
PostgreSQL + Vector DB |              Policy Rules
        |
LLM Provider
```

### 8.3 核心模块

- API Gateway：统一接收 Web 和渠道消息。
- Channel Adapter：处理不同渠道的消息格式转换。
- Conversation Service：负责上下文组装、模型调用和回复生成。
- Memory Service：负责记忆提取、存储、检索和管理。
- Emotion Service：负责情绪识别和风险分类。
- Safety Guard：负责风险检测、回复约束和安全降级。
- Scheduler：负责主动关怀和定时提醒。

## 9. MVP 范围

MVP 版本只做最小可演示闭环：

- Web 聊天页面。
- 用户登录。
- 单个默认陪伴角色。
- 多轮文本对话。
- 长期记忆提取和检索。
- 基础情绪识别。
- 早安/晚安定时关怀。
- 微信/ClawBot 文本消息回调接口。
- Docker Compose 本地启动。

暂不实现：

- V1 基线不实现实时 WebRTC 语音通话；基础闭环完成后按独立扩展里程碑实现 Live2D、半实时语音和实时通话。
- 图片生成。
- 多角色复杂关系。
- 付费系统。
- 移动 App。
- 医疗级心理咨询能力。

## 10. 版本规划

### V0.1 原型版

- 完成 Web 聊天。
- 完成基础角色提示词。
- 完成模型调用。
- 完成对话历史保存。

### V0.2 记忆版

- 完成记忆抽取。
- 完成记忆检索。
- 完成记忆管理页面。

### V0.3 陪伴版

- 完成情绪识别。
- 完成主动关怀。
- 完成安全策略。

### V0.4 渠道版

- 完成微信/ClawBot 回调接口。
- 完成消息去重。
- 完成渠道用户绑定。

### V1.0 展示版

- 完成 Docker Compose。
- 完成 README、架构图、接口文档和演示视频。
- 完成测试用例和基础监控。

## 11. 数据模型草案

### 11.1 User

- id
- username
- password_hash
- display_name
- created_at
- updated_at

### 11.2 CompanionProfile

- id
- user_id
- name
- relationship_type
- speaking_style
- boundaries
- created_at
- updated_at

### 11.3 Conversation

- id
- user_id
- companion_id
- channel
- created_at
- updated_at

### 11.4 Message

- id
- conversation_id
- role
- content
- emotion_label
- risk_level
- external_message_id
- created_at

### 11.5 Memory

- id
- user_id
- companion_id
- memory_type
- content
- importance
- source_message_id
- embedding
- created_at
- updated_at

### 11.6 Reminder

- id
- user_id
- companion_id
- reminder_type
- schedule_time
- content
- enabled
- created_at
- updated_at

## 12. API 草案

### 12.1 Web 对话

```http
POST /api/conversations/{conversation_id}/messages
```

请求字段：

- content
- stream

响应字段：

- message_id
- display_text
- speech_text（可选，缺省时朗读 display_text）
- emotion_label
- memory_used

### 12.2 微信渠道回调

```http
POST /api/channels/wechat/messages
```

请求字段：

- channel_user_id
- external_message_id
- message_type
- content
- timestamp

响应字段：

- reply_type
- reply_content
- trace_id

### 12.3 记忆管理

```http
GET /api/memories
POST /api/memories
PATCH /api/memories/{memory_id}
DELETE /api/memories/{memory_id}
```

## 13. 提示词与策略要求

系统提示词需要包含：

- 当前角色设定。
- 用户长期记忆摘要。
- 最近对话上下文。
- 当前情绪识别结果。
- 安全边界。
- 回复风格约束。

回复策略：

- 普通聊天：自然、轻松、短句优先。
- 低落情绪：先共情，再询问是否需要建议。
- 焦虑情绪：先稳定情绪，再帮助拆分问题。
- 生气情绪：先承认感受，避免激化。
- 危机风险：停止暧昧或恋爱扮演，提供安全支持。

## 14. 验收标准

- 用户可以通过 Web 完成连续 10 轮聊天。
- 系统能记住至少 3 条用户长期信息，并在后续对话中自然使用。
- 用户可以查看和删除记忆。
- 系统能识别低落、焦虑和危机风险消息。
- 定时关怀任务可以按设定时间发送消息。
- 微信/ClawBot 回调接口可以接收文本消息并返回 AI 回复。
- 本地环境可以通过 Docker Compose 启动。
- README 包含架构说明、启动方式、接口说明和演示截图。

## 15. 简历展示重点

该项目可以在简历中描述为：

> 基于 Python FastAPI 构建 AI 情感陪伴 Agent，支持多轮对话、长期记忆、情绪识别、主动关怀和微信渠道适配。系统采用模块化 Channel Adapter 设计，核心 Agent 服务与微信/ClawBot 接入解耦，并通过 PostgreSQL、pgvector、Redis 和异步任务实现可演示的生产级 AI 应用闭环。

可突出技术关键词：

- Python
- FastAPI
- LLM Agent
- LangGraph
- RAG
- Long-term Memory
- Prompt Engineering
- PostgreSQL
- pgvector
- Redis
- Docker
- WeChat Adapter
- Async Task
- Safety Guard

## 16. 风险与边界

- 微信个人号机器人存在账号风控和稳定性风险，正式演示应强调系统支持可替换渠道适配。
- 项目不宣称提供心理治疗或医疗建议。
- 主动消息需要用户授权并可关闭。
- 陪伴角色不能诱导用户产生现实依赖或进行高风险行为。
- 用户隐私数据需要可删除、可导出，并尽量减少日志暴露。

## 17. Avatar 与语音扩展需求

完整技术设计见：

- `docs/mio-ai-companion-avatar-voice-design.md`
- `docs/superpowers/specs/2026-06-11-chat-and-immersive-voice-design.md`
- `docs/superpowers/specs/2026-06-11-vrm-avatar-renderer-design.md`

产品采用独立的全屏沉浸式语音通话：

- 普通聊天页不常驻人物，不加载 Live2D 或 VRM 运行时。
- 用户主动点击语音入口后进入全屏通话页。
- 人物位于右侧，字幕位于人物下方。
- 结束后返回原聊天和原 `conversation_id`。
- 进入通话页面不自动开启麦克风。

功能演进：

1. Avatar MVP：静态人物、AvatarRenderer、Presentation Engine 和降级链。
2. VRM/VRMA：3D 模型、动作、表情、眨眼、视线和音频嘴型。
3. 半实时语音：点击录音、ASR、统一 Agent、流式 TTS、字幕和嘴型。
4. 实时语音：WebRTC、VAD、用户打断、TURN 和断线恢复。
5. 可选视觉输入和桌面端形态。

验收原则：

- 文字和语音共享 Conversation、长期记忆和 Agent Trace。
- Avatar Renderer、ASR 或 TTS 失败时，文字聊天仍可使用。
- Mock ASR 和 Mock TTS 支持无 API Key 自动化测试。
- 表情和动作通过结构化 PresentationPlan 驱动。
- 展示文本与语音朗读文本分离，代码、URL 等内容不要求直接朗读。
- TTS 片段可以并发生成，但必须编号并按原文顺序播放。
- 用户打断后只把实际听到的回复作为已听内容，不写入未播放语义。
- 主动关怀和系统事件可显式禁止进入历史或长期记忆提取。
- 默认不长期保存原始音频和视频帧。
- 仅使用原创或已明确授权的模型、动作与音色。
- `https://github.com/umikok7/roxy-agent` 只作为后期 VRM/VRMA 工程参考，不默认复用或分发其中的洛琪希角色素材。
