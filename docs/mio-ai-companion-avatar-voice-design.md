# Mio AI Companion Avatar 与语音交互扩展设计

## 1. 文档目标

本文定义 Mio AI Companion 的可插拔 Avatar 与语音交互扩展。Avatar 支持静态立绘、Live2D 和 VRM/VRMA，用于指导后续产品设计、接口设计、数据建模、分阶段开发和验收。

扩展目标不是复制一个“会说话的二次元页面”，而是让澪已有的 Persona、情绪理解、长期记忆、RAG、工具、安全策略和 Agent Trace 通过声音、表情和动作自然地表达出来。

已确认的产品方向：

- 保留现有文字 Web Chat。
- 普通聊天页不常驻展示人物，也不加载 Avatar 运行时。
- 用户主动点击语音入口后进入全屏沉浸式语音通话。
- 通话页人物位于右侧，字幕位于人物下方。
- 语音输入必须由用户主动授权。
- 第一阶段实现半实时语音闭环。
- 后续升级为基于 WebRTC 的可打断实时通话。
- 文字和语音始终共用同一个 Mio Core Agent、Conversation、Memory 和 Trace。

## 2. 参考项目结论

本设计参考了 Amadeus System 的公开文档与源码结构。

调研时间：2026-06-06。

参考来源：

- `https://docs.amadeus-web.top/tutorial_overview.html`
- `https://github.com/ai-poet/amadeus-system-new`

Amadeus 的主要实现包括：

- React、PixiJS 和 `pixi-live2d-display` 渲染 Live2D。
- WebRTC 与 FastRTC 传输实时音频。
- Whisper-compatible ASR 将用户语音转成文本。
- OpenAI-compatible LLM 生成流式回复。
- CosyVoice2 等 TTS 服务生成流式音频。
- 根据返回音频频谱驱动 Live2D 嘴型。
- 根据回复情绪产生表情和动作事件。
- 使用 Mem0 保存长期记忆。
- 可选摄像头帧输入与 Electron 桌面客户端。

值得采纳的是交互链路与模块思想：

```text
语音输入
  -> VAD / 录音结束
  -> ASR
  -> Agent
  -> 流式文本
  -> 分句 TTS
  -> 音频播放
  -> 嘴型、表情和动作
```

不直接复用其整体实现，原因包括：

- 仓库已声明停止维护。
- GitHub 仓库未声明明确的软件许可证。
- 示例角色、Live2D 模型和音色存在独立版权与授权要求。
- 会话、记忆、语音和表现逻辑耦合较重，不符合 Mio 的核心边界。
- Mio 已设计可审核、可回滚的 Memory Layer，不应被 Mem0 直接替换。

因此，本项目只吸收公开的技术思想与交互经验，不复制其源码、角色模型、音色或专有角色设定。

本设计涉及的第三方技术在真正引入依赖时仍需重新核对最新版本、维护状态和许可证，不能把本次调研结论视为永久许可证明。

### 2.1 VRM / VRMA 重要参考

后期 VRM Renderer、VRMA 动作和桌面 Companion 的重要工程参考：

- `https://github.com/umikok7/roxy-agent`

调研时间：2026-06-11。

重点参考其 React、Three.js、`@pixiv/three-vrm`、`@pixiv/three-vrm-animation`、VRMA 状态动作、TTS 嘴型和 Electron 桌面角色实现。

截至调研日，GitHub API 未识别该仓库许可证，仓库根目录也没有可读取的 `LICENSE` 文件。README 中的 MIT 声明不能自动证明其中 VRM、VRMA、语音、Persona 和动漫 IP 素材可再分发。因此 Mio 只参考公开工程思路，不默认复制或分发洛琪希模型、动作、语音、Persona 或其他角色素材。完整方案见 `docs/superpowers/specs/2026-06-11-vrm-avatar-renderer-design.md`。

## 3. 产品形态

### 3.1 普通聊天模式

普通聊天模式仍是默认入口：

- 保留文字输入和消息历史。
- 不加载人物，不压缩消息和输入区域。
- 用户主动点击语音入口后进入全屏通话。
- Avatar Renderer、ASR 或 TTS 加载失败不得影响普通文字聊天。

### 3.2 全屏语音交互

全屏语音通话包含：

- 当前通话状态。
- 用户语音转录字幕。
- 澪的流式回复字幕。
- 右侧人物和底部字幕。
- 静音、结束和字幕按钮。
- ASR、TTS 或网络失败时的明确降级提示。
- 后续支持用户说话打断澪。

Voice Session 是媒体生命周期。全屏页面是独立 Experience Layer，不是另一套 Agent。

### 3.3 输入方式连续性

文字和语音输入必须满足：

- 使用同一个 `conversation_id`。
- 共享最近对话上下文。
- 共享长期记忆和候选记忆。
- 共享 CompanionProfile 和 CompanionState。
- 共享安全策略。
- 共享 Agent Trace。
- 可以在文字和语音之间无缝切换。

## 4. 核心设计原则

### 4.1 Mio Core 是唯一大脑

语音网关不得维护独立人格、独立记忆或第二套 LLM 对话历史。

```text
Text Channel ----\
                  -> Conversation Service -> LangGraph Agent
Voice Channel ---/
```

ASR 输出只是用户消息的另一种来源，TTS 只是回复的另一种呈现方式。

### 4.2 Presentation Layer 独立

LangGraph 不直接调用 Live2D 模型参数，也不依赖具体动作名。

核心 Agent 输出抽象表现语义，Presentation Engine 再映射为具体资源：

```text
Agent semantic state
  -> Presentation Engine
  -> Avatar expression / motion
  -> Voice style
  -> Client events
```

这样未来可以替换为：

- 不同 Live2D 模型。
- 静态立绘。
- VRM 或其他 3D 模型。
- 桌面宠物。
- 移动端原生形象。

### 4.3 陪伴表达服从 Persona

情绪分类不等于直接播放夸张动作。

例如 `sad` 对于默认澪应映射为克制的担心表情、较慢语速和轻微点头，而不是强烈哭泣动作。

### 4.4 实时能力渐进实现

开发顺序：

```text
模拟表现事件
  -> 半实时语音
  -> 流式 TTS
  -> VAD
  -> WebRTC
  -> Barge-in
  -> 可选视觉输入
```

不得在基础聊天闭环完成前引入 TURN、复杂实时媒体服务或自动视觉输入。

### 4.5 默认隐私最小化

- 默认保存语音转录文本，不长期保存原始音频。
- 摄像头必须由用户显式开启。
- 原始音频或图像若需保存，必须单独授权并配置保留期。
- Trace 记录阶段耗时和状态，不记录完整敏感音频。
- API Key 只保存在服务端，不写入浏览器 Local Storage。

## 5. 总体架构

```text
+----------------------------------------------------------------+
| Experience Layer                                               |
| Web Chat + Lightweight Avatar | Immersive Voice Call | Future  |
+-------------------------------+------------------------+--------+
                                |
                      Channel Adapters
                text / voice / wechat / future IDE
                                |
+-------------------------------v--------------------------------+
| Voice Gateway                                                   |
| Voice Session | Audio Upload/WebRTC | VAD | ASR | TTS | Cancel |
+-------------------------------+--------------------------------+
                                |
+-------------------------------v--------------------------------+
| Mio Core Agent                                                  |
| Conversation | LangGraph | Persona | Emotion | Memory | RAG    |
| Tools | Safety | Trace                                           |
+-------------------------------+--------------------------------+
                                |
+-------------------------------v--------------------------------+
| Presentation Layer                                              |
| Semantic State | Expression Mapper | Motion Mapper | Voice Style|
+----------------------+--------------------------+---------------+
                       |                          |
             Avatar Event Stream           TTS Parameters
                       |                          |
+----------------------v--------------------------v---------------+
| Client Runtime                                                  |
| Static / Live2D / VRM Renderer | Audio Player | Lip Sync | Subtitle |
+----------------------------------------------------------------+
```

### 5.1 Experience Layer

负责页面布局、用户授权、字幕、控制按钮和模式切换，不处理 Persona 或长期记忆。

### 5.2 Voice Gateway

负责实时或半实时媒体生命周期：

- 创建和关闭 Voice Session。
- 接收录音或 WebRTC 音轨。
- VAD 和端点检测。
- 调用 ASR Provider。
- 将转录文本提交给 Conversation Service。
- 调用 TTS Provider。
- 管理音频播放顺序和取消信号。
- 产生语音阶段 Trace。

### 5.3 Mio Core Agent

沿用已有主流程，不因语音而复制逻辑：

```text
转录文本
  -> 保存用户消息
  -> 情绪和意图识别
  -> Memory / RAG / Tool
  -> Persona Prompt
  -> LLM
  -> Safety
  -> Candidate Memory
  -> 保存回复和 Trace
```

### 5.4 Presentation Layer

将 Agent 输出转换为渠道无关的表现计划：

- 表情。
- 动作。
- 注视方向。
- 能量与节奏。
- 语速、音量和声音风格。
- 是否允许播放表情包或其他附件。

### 5.5 Client Runtime

浏览器负责：

- 加载和释放当前 Avatar Renderer 资源。
- 执行表情与动作。
- 播放音频。
- 根据实际播放音频驱动嘴型。
- 展示字幕。
- 在资源失败时降级。

## 6. 统一响应契约

### 6.1 AgentResponse

Agent 的业务响应保持渠道无关：

```json
{
  "message_id": "msg_002",
  "conversation_id": "conv_001",
  "display_text": "嗯。先休息一会儿，我陪着你。",
  "speech_text": "嗯，先休息一会儿。我陪着你。",
  "emotion": "tired",
  "intent": "mixed",
  "risk_level": "none",
  "response_strategy": "comfort_first",
  "presentation": {
    "affect": "gentle_concern",
    "energy": 0.25,
    "warmth": 0.75,
    "pace": "slow",
    "gesture_hint": "small_nod"
  },
  "attachments": [],
  "trace_id": "trace_001"
}
```

`display_text` 是消息正文和字幕的权威文本。`speech_text` 是可选的朗读版本，用于去除 Markdown、代码、URL 或不适合直接朗读的内容；缺省时使用 `display_text`。二者必须表达相同事实，不允许为了语音效果改变结论。

### 6.2 InteractionInput

文字、语音和后续视觉输入统一为轻量输入信封：

```json
{
  "conversation_id": "conv_001",
  "source": "voice",
  "text": "这个错误又卡住了，我有点烦。",
  "persist_history": true,
  "allow_memory_extraction": true,
  "consent_context": "microphone_session"
}
```

首版只要求：

- `source`：`text`、`voice`、`active_care` 或 `system`。
- `persist_history`：是否写入正常对话历史。
- `allow_memory_extraction`：是否允许生成长期记忆候选。
- `consent_context`：语音或视觉输入使用的授权上下文，可为空。

主动关怀和内部系统事件默认不参与长期记忆提取。首版不实现复杂的多模态批处理或通用文件信封。

### 6.3 PresentationPlan

Presentation Engine 输出具体但仍与渲染 SDK 解耦的计划：

```json
{
  "expression_key": "soft_concern",
  "motion_key": "nod_small",
  "gaze": "user",
  "voice_style": "quiet_warm",
  "speech_rate": 0.9,
  "volume": 0.85,
  "allow_idle_motion": true
}
```

`expression_key` 和 `motion_key` 不能直接等于某个模型文件中的动作组名称。客户端通过 AvatarProfile 的资源映射获得实际名称。

### 6.4 AvatarEvent

表现事件采用版本化事件协议：

```json
{
  "schema_version": "1",
  "event_id": "evt_001",
  "voice_session_id": "voice_001",
  "sequence": 12,
  "type": "avatar.state.changed",
  "timestamp": "2026-06-06T12:00:00Z",
  "payload": {
    "state": "speaking",
    "expression_key": "soft_concern",
    "motion_key": "nod_small"
  }
}
```

首版事件类型：

- `voice.session.started`
- `voice.session.ended`
- `voice.state.changed`
- `asr.partial`
- `asr.final`
- `agent.text.delta`
- `agent.response.completed`
- `presentation.plan.ready`
- `tts.audio.started`
- `tts.audio.completed`
- `avatar.state.changed`
- `voice.error`

同一会话内使用递增 `sequence`，客户端忽略重复或过期事件。

## 7. Voice Session 状态机

统一状态：

```text
idle
  -> listening
  -> transcribing
  -> thinking
  -> speaking
  -> idle
```

附加状态：

- `interrupted`
- `reconnecting`
- `failed`
- `ended`

状态规则：

1. 一个 Voice Session 同一时刻只有一个主状态。
2. 用户开始新一轮说话时，旧的 TTS 和未完成回复必须可取消。
3. `failed` 不自动删除 Conversation。
4. WebRTC 断开后可以在短时间窗口内恢复同一个 Voice Session。
5. 结束通话只关闭媒体会话，不关闭文字 Conversation。

状态与默认表现：

| Voice State | Avatar State | 说明 |
|---|---|---|
| `idle` | `idle` | 低频眨眼和呼吸 |
| `listening` | `listening` | 注视用户，减少随机动作 |
| `transcribing` | `thinking` | 轻微思考状态 |
| `thinking` | `thinking` | 禁止嘴型，允许低频动作 |
| `speaking` | `speaking` | 使用 PresentationPlan 并启用嘴型 |
| `interrupted` | `listening` | 立即停音频并回到倾听 |
| `failed` | `neutral` | 中性表情，避免错误状态持续 |

## 8. 半实时语音设计

### 8.1 交互方式

首版支持以下任一录音方式：

- 点击开始、点击结束。
- 按住说话、松开提交。
- 浏览器端简单静音检测后自动结束。

推荐先实现点击开始和结束，避免 VAD 环境差异影响主闭环。

### 8.2 数据流

```text
Browser records audio
  -> POST audio blob
  -> ASR Provider
  -> final transcript
  -> existing Conversation Service
  -> AgentResponse
  -> PresentationPlan
  -> segmented streaming TTS
  -> audio chunks + subtitle events
  -> browser playback and lip sync
```

### 8.3 流式 TTS

LLM 回复按自然语义边界切分：

- 句号、问号、感叹号优先。
- 逗号只在片段达到最小长度时使用。
- 不对 Markdown 代码块逐句朗读。
- 技术回答中的 URL、代码和表格可跳过语音或转换为口语摘要。

音频片段必须保持文本顺序。后生成的片段不得抢先播放。

每轮合成使用一个 `request_id`，每个片段使用递增 `sequence_id`。TTS 可以并发生成片段，但客户端只按 `sequence_id` 播放；中断或新一轮输入到达时，使用同一个取消信号停止该 `request_id` 下尚未播放的片段。首版不建设通用任务调度框架。

### 8.4 延迟目标

个人自部署和公网模型情况下，MVP 目标：

- ASR 完成：通常小于 1.5 秒。
- Agent 首段文本：通常小于 2 秒。
- TTS 首音频：通常小于 1 秒。
- 用户停止说话到首音频：目标 1.5 到 4 秒。

这些是体验目标，不作为所有 Provider 的硬 SLA。Trace 必须能拆分各阶段耗时。

## 9. WebRTC 实时通话设计

### 9.1 升级范围

实时阶段增加：

- WebRTC 音轨。
- 服务端 VAD 和端点检测。
- 流式或增量 ASR。
- Barge-in 用户打断。
- 取消 LLM 和 TTS。
- ICE、STUN 和 TURN。
- 断线重连与会话恢复。

### 9.2 信令与业务分离

WebRTC 只负责媒体连接和实时事件。Conversation Service 仍通过稳定的内部接口处理业务消息。

```text
WebRTC Media Session
  -> ASR final turn
  -> submit_message(conversation_id, content, channel="voice")
  -> AgentResponse stream
  -> TTS stream
  -> WebRTC outbound audio
```

### 9.3 Barge-in

用户说话打断澪时：

1. VAD 检测到用户语音。
2. 服务端发送取消信号。
3. 停止当前音频播放。
4. 取消尚未开始的 TTS 片段。
5. 尽力取消 LLM 流。
6. 将本轮助手消息标记为 `interrupted`。
7. 已播放的文本范围写入元数据。
8. 根据播放进度生成 `heard_text`，作为后续 Agent 可见的已听回复。
9. 状态切回 `listening`。

不得把未播放的完整回复当作用户已经听到的内容。

### 9.4 TURN

- 本地开发可先使用 host candidate 或公共测试 STUN。
- 公网演示必须使用受控 TURN 服务。
- TURN 凭证不得写入前端仓库。
- 使用短期凭证或服务端下发的临时配置。
- Public Demo 限制单次通话时长和并发数。

## 10. Avatar 表现系统

### 10.1 AvatarProfile

AvatarProfile 描述渲染资源和语义映射：

```text
id
companion_id
renderer_type: static / live2d / vrm
model_uri
model_version
license_metadata
default_scale
default_position
expression_map
motion_map
parameter_map
fallback_image_uri
enabled
created_at
updated_at
```

示例映射：

```json
{
  "expression_map": {
    "neutral": "exp_neutral",
    "soft_concern": "exp_concern_01",
    "quiet_happy": "exp_smile_01",
    "shy": "exp_shy_01"
  },
  "motion_map": {
    "nod_small": {"group": "Nod", "index": 0},
    "thinking": {"group": "Think", "index": 0}
  }
}
```

### 10.2 最小动作集合

Avatar MVP 只要求：

- `idle`
- `listening`
- `thinking`
- `speaking`
- `nod_small`
- `greeting`

最小表情集合：

- `neutral`
- `soft_concern`
- `quiet_happy`
- `shy`
- `slightly_unhappy`
- `safety_neutral`

不追求大量动作。默认澪的表现应低频、克制、自然。

### 10.3 嘴型

MVP 使用客户端 Web Audio API 分析实际播放的 TTS 音频：

```text
Audio stream
  -> AnalyserNode
  -> normalized amplitude
  -> smoothing
  -> ParamMouthOpenY
```

要求：

- 以实际播放音频为准，不以文本长度模拟。
- 使用平滑系数，避免嘴型抖动。
- 静音时恢复闭嘴。
- 模型参数名通过 `parameter_map` 配置。
- 不支持嘴型参数时仍可正常播放音频。

后续可升级为音素或 viseme 驱动，但不属于首版。

### 10.4 待机行为

- 随机眨眼和轻微呼吸。
- 头部和眼睛移动频率受 Persona 与状态控制。
- `listening` 时减少随机视线漂移。
- `speaking` 时动作不能连续覆盖表情。
- 同一个高辨识动作设置冷却时间。
- Public Demo 可关闭容易引发误解的亲密动作。

## 11. Presentation Engine

### 11.1 输入

- CompanionProfile。
- CompanionState。
- 当前用户情绪。
- 回复情绪。
- 意图和 response strategy。
- risk level。
- 当前 Voice Session 状态。
- 最近表现事件和冷却时间。

### 11.2 输出

- `PresentationPlan`。
- 选择原因摘要。
- 使用的规则版本。
- 是否发生安全覆盖。

### 11.3 规则优先级

```text
Safety override
  > Voice session state
  > Persona boundaries
  > Response strategy
  > Reply affect
  > Idle variation
```

安全模式下：

- 强制 `safety_neutral`。
- 停止暧昧或亲密动作。
- 使用清晰、稳定、不过度角色化的语音风格。

### 11.4 决策方式

首版使用确定性规则映射，不额外调用 LLM：

- 延迟更低。
- 可测试。
- 可解释。
- 避免动作随机失控。

未来可以让模型生成抽象的 `affect` 和 `gesture_hint`，但最终资源映射仍由规则完成。

## 12. Provider 接口

### 12.1 ASRProvider

```text
transcribe(audio, language, context_hint) -> TranscriptResult
```

`TranscriptResult`：

```text
text
language
confidence
duration_ms
provider
model
```

实现：

- `MockASRProvider`
- `OpenAICompatibleASRProvider`
- 后续本地 Whisper Provider

### 12.2 TTSProvider

```text
synthesize(request_id, text_segments, VoiceSynthesisOptions) -> AudioChunk stream
cancel(request_id)
```

`AudioChunk` 至少包含：

```text
request_id
sequence_id
text
audio
is_final
```

`VoiceSynthesisOptions`：

```text
voice_id
language
style
speech_rate
volume
sample_rate
```

实现：

- `MockTTSProvider`
- OpenAI-compatible TTS Provider
- 后续 CosyVoice / Fish Audio Adapter

### 12.3 RealtimeTransport

```text
create_session()
accept_offer()
send_event()
send_audio()
close_session()
```

半实时阶段不需要实现该接口的完整 WebRTC 版本。

### 12.4 AvatarRenderer

前端接口：

```text
load(profile)
set_state(state)
set_expression(key)
play_motion(key)
set_lip_sync(value)
dispose()
```

实现：

- `Live2DAvatarRenderer`
- `VrmAvatarRenderer`
- `StaticAvatarRenderer`

VRM/VRMA 的具体契约、资源映射、性能预算和生命周期见 `docs/superpowers/specs/2026-06-11-vrm-avatar-renderer-design.md`。

## 13. API 草案

### 13.1 半实时语音

```http
POST /api/voice/transcriptions
```

使用 multipart/form-data：

```text
audio
conversation_id
language
```

响应：

```json
{
  "transcript": "这个错误又卡住了，我有点烦。",
  "message_id": "msg_user_001",
  "trace_id": "trace_001"
}
```

提交转录文本后仍调用统一聊天接口，或者由服务端组合为一个事务性 Voice Turn：

```http
POST /api/voice/turns
```

响应可使用 SSE：

```text
asr.final
agent.text.delta
presentation.plan.ready
tts.audio.chunk
agent.response.completed
```

### 13.2 Voice Session

```http
POST /api/voice/sessions
GET /api/voice/sessions/{session_id}
POST /api/voice/sessions/{session_id}/end
POST /api/voice/sessions/{session_id}/interrupt
```

### 13.3 WebRTC

```http
GET /api/voice/rtc/ice-config
POST /api/voice/rtc/offer
GET /api/voice/sessions/{session_id}/events
```

具体传输协议在实时阶段实施前再次评审。

### 13.4 Avatar

```http
GET /api/avatar/profile
PATCH /api/avatar/profile
GET /api/avatar/assets
POST /api/avatar/preview
```

## 14. 数据模型

### 14.1 VoiceProfile

```text
id
companion_id
provider
voice_id
language
default_style
default_speech_rate
license_metadata
enabled
created_at
updated_at
```

### 14.2 VoiceSession

```text
id
conversation_id
user_id
companion_id
mode: half_duplex / realtime
transport: http / webrtc
state
started_at
ended_at
last_active_at
disconnect_reason
created_at
updated_at
```

### 14.3 VoiceTurn

```text
id
voice_session_id
user_message_id
assistant_message_id
asr_provider
asr_model
tts_provider
tts_model
transcript_confidence
was_interrupted
played_text_end_offset
heard_text
audio_retention_policy
created_at
updated_at
```

### 14.4 VoiceTrace

```text
id
trace_id
voice_session_id
voice_turn_id
recording_duration_ms
upload_latency_ms
asr_latency_ms
agent_first_token_ms
agent_total_latency_ms
tts_first_audio_ms
tts_total_latency_ms
playback_duration_ms
interruption_count
error_stage
error_code
created_at
```

### 14.5 PresentationTrace

```text
id
trace_id
presentation_plan
rule_version
decision_reason
safety_overridden
avatar_events
created_at
```

原始音频不作为上述表的默认字段。若未来允许保存，使用独立 MediaAsset 和明确的 retention policy。

## 15. Trace 与可观测性

Agent Debug 增加 Voice 标签页：

- Voice Session 和 Voice Turn。
- ASR Provider、模型和置信度。
- 转录文本摘要。
- Agent 首 token 和总耗时。
- TTS 首包和总耗时。
- PresentationPlan。
- Avatar Event 时间线。
- 打断与取消。
- 降级和失败阶段。

关键指标：

- `voice_turn_success_rate`
- `asr_empty_result_rate`
- `voice_first_audio_latency_ms`
- `voice_interruption_rate`
- `tts_failure_rate`
- `avatar_load_failure_rate`
- `webrtc_reconnect_rate`

日志不得打印 API Key、完整音频或未经脱敏的敏感转录。

## 16. 错误处理与降级

| 失败点 | 用户体验 | 系统行为 |
|---|---|---|
| 麦克风拒绝 | 提示授权，可继续打字 | 不创建录音 |
| ASR 失败 | 请用户重试或编辑转录 | 不提交空消息 |
| Agent 失败 | 显示现有降级回复 | 记录统一 Trace |
| TTS 失败 | 保留完整文字回复 | Avatar 回到 idle |
| Avatar 主渲染器加载失败 | 显示静态头像 | 聊天和语音继续 |
| 表情动作不存在 | 使用 neutral | 记录资源映射错误 |
| WebRTC 断开 | 显示重连或切换半实时 | 保留 Conversation |
| TURN 不可用 | 尝试直连，失败则降级 | 不暴露长期凭证 |
| 用户打断 | 立即停止播放 | 标记 interrupted |

任何表现层错误都不能导致核心消息丢失。

## 17. 安全、隐私与授权

### 17.1 模型和素材

- 默认澪必须使用原创或已明确获得授权的 Avatar 模型。
- 模型文件保存来源、作者、授权范围和署名要求。
- 不使用 Amadeus 的牧濑红莉栖模型或其他受保护角色素材。
- 不默认分发 `umikok7/roxy-agent` 中的洛琪希模型、VRMA、语音、Persona 或其他角色素材。
- Public Demo 发布前执行素材授权检查。

### 17.2 音色

- 默认使用授权明确的预置音色或原创委托音色。
- 声音克隆必须获得声音主体授权。
- 不克隆公众人物、主播、演员或用户未获授权的真人声音。
- VoiceProfile 保存授权元数据。

### 17.3 用户媒体

- 麦克风和摄像头分别授权。
- 默认不长期保存原始音频和视频帧。
- 明确显示录音和摄像头状态。
- 结束通话时立即停止媒体轨道。
- Public Demo 默认关闭摄像头。

### 17.4 项目依赖

- 引入 Live2D SDK、Three.js、VRM/VRMA 渲染库和模型素材前分别核对许可证。
- 第三方渲染库的开源许可证不等于 Live2D SDK Core、VRM 模型、动作或角色素材的授权。
- 在 `THIRD_PARTY_NOTICES` 或 README 中记录依赖和素材许可。

## 18. 配置

```text
AVATAR_ENABLED=true
AVATAR_RENDERER=static / live2d / vrm
AVATAR_PROFILE_ID=
AVATAR_AUTOPLAY_VOICE=false

ASR_PROVIDER=mock / openai_compatible
ASR_BASE_URL=
ASR_API_KEY=
ASR_MODEL=

TTS_PROVIDER=mock / openai_compatible
TTS_BASE_URL=
TTS_API_KEY=
TTS_MODEL=
TTS_VOICE_ID=

VOICE_REALTIME_ENABLED=false
VOICE_MAX_SESSION_SECONDS=600
VOICE_AUDIO_RETENTION=none
VOICE_CAMERA_ENABLED=false

TURN_URL=
TURN_USERNAME=
TURN_CREDENTIAL=
```

敏感配置只存在于服务端环境变量或 Secret 管理系统。

## 19. 测试策略

### 19.1 单元测试

- AgentResponse 到 PresentationPlan 的映射。
- Safety override 优先级。
- AvatarProfile expression/motion 映射。
- Voice Session 状态转换。
- 非法状态转换拒绝。
- TTS 文本分段和顺序。
- display_text 与 speech_text 的回退和语义一致性。
- InteractionInput 的历史与记忆策略。
- Barge-in 取消逻辑。
- Barge-in 只回写 heard_text，不把未播放内容标记为已听。
- 音频保留策略。
- Mock ASR 和 Mock TTS。

### 19.2 集成测试

- 音频上传到转录。
- 转录进入统一 Conversation。
- Voice Turn 使用 Memory 和 RAG。
- AgentResponse 生成 PresentationPlan。
- TTS 失败时返回文字。
- Avatar 资源映射缺失时回退 neutral。
- 结束通话后 Conversation 仍可继续文字聊天。
- WebRTC 断线后恢复或降级。

### 19.3 前端测试

- 麦克风授权拒绝。
- 录音状态和按钮状态。
- 字幕事件顺序。
- 重复事件忽略。
- 音频队列顺序。
- request_id 取消后不再播放剩余 sequence_id。
- 中断后停止播放。
- Avatar 主渲染器加载失败时显示静态头像。
- 组件卸载时释放 AudioContext、MediaStream 和模型资源。

### 19.4 演示验收

固定场景：

```text
用户语音：这个错误又卡住了，我有点烦。
```

预期：

1. ASR 生成正确转录。
2. intent 为 `mixed` 或等价分类。
3. Emotion Layer 识别挫败或疲惫。
4. 检索当前项目上下文和相关记忆。
5. 回复先回应情绪，再提供排查建议。
6. 澪使用克制的担心表情、轻微点头和较慢语速。
7. 字幕、音频和嘴型同步。
8. Debug Console 展示完整 Voice Trace 和 Agent Trace。

## 20. 分阶段里程碑

### M7.5 Avatar MVP

范围：

- 全屏沉浸式通话静态人物闭环。
- AvatarProfile。
- AvatarRenderer 和 AvatarController。
- StaticAvatarRenderer 降级。
- Presentation Engine 初版。
- Mock Presentation Event。

完成标准：

- 不调用真实 LLM 也能预览全部基础表现。
- 模型加载失败不影响聊天。
- 表现决策有 Trace。

### M7.75 VRM / VRMA Renderer

范围：

- Three.js、`@pixiv/three-vrm` 和 `@pixiv/three-vrm-animation` 按需加载。
- VRM Expression、眨眼、视线和实际音频嘴型。
- VRMA 动作加载、Cross Fade、缓存和状态恢复。
- WebGL、移动端和资源失败降级。
- Renderer 生命周期和资源释放测试。

完成标准：

- 普通聊天页构建不静态加载 VRM 运行时和模型。
- VRM 失败后语音、字幕和 Conversation 继续工作。
- 多次进入和退出通话后无残留 Canvas、AudioNode 或动画循环。
- Public Demo 不包含授权不明的第三方角色素材。

### M8.5 Half-duplex Voice MVP

范围：

- 点击录音。
- Mock ASR、Mock TTS。
- OpenAI-compatible ASR/TTS Adapter。
- 统一 Conversation。
- 流式字幕和分句 TTS。
- 显示文本与朗读文本分离。
- request_id 和 sequence_id 顺序播放。
- 实际音频驱动嘴型。
- VoiceTrace。

完成标准：

- 无 API Key 环境可跑自动化测试。
- 文字和语音共享上下文、记忆和 Trace。
- TTS 失败仍显示文字。
- 首音频延迟可观测。

### M9.5 Realtime Voice

范围：

- WebRTC 音轨。
- VAD。
- 增量 ASR。
- Barge-in。
- LLM/TTS 取消。
- STUN/TURN。
- 断线恢复。

完成标准：

- 用户可以在澪说话时打断。
- 中断后只保存 heard_text，未播放内容不会被标记为已听取。
- 公网演示环境可建立稳定连接。
- 实时失败可以降级为半实时模式。

### M10.5 Optional Vision

范围：

- 用户显式启用摄像头。
- 低频、按需视觉帧。
- 视觉输入 Trace。
- 隐私提示和保留策略。

不做持续录制，不默认开启。

### M11.5 Desktop Companion

范围：

- Electron 或其他桌面壳。
- 桌面悬浮形象。
- 系统托盘。
- 主动关怀通知。

桌面端继续调用相同的 Mio Core API。

## 21. 推荐文件边界

代码工程初始化后，建议采用以下职责划分。最终路径可根据实际项目骨架调整，但边界必须保留。

```text
backend/app/voice/
  models.py
  session_service.py
  turn_service.py
  state_machine.py
  providers/
    base.py
    mock_asr.py
    mock_tts.py
    openai_compatible_asr.py
    openai_compatible_tts.py
  realtime/
    transport.py
    interruption.py

backend/app/presentation/
  models.py
  service.py
  rules.py
  avatar_profile_service.py

frontend/src/features/avatar/
  AvatarRenderer.ts
  Live2DAvatarRenderer.ts
  VrmAvatarRenderer.ts
  StaticAvatarRenderer.ts
  AvatarController.ts
  AudioLipSync.ts

frontend/src/features/voice/
  VoiceSession.ts
  AudioCapture.ts
  AudioPlaybackQueue.ts
  VoiceCallPage.tsx
  SubtitleStream.tsx
```

边界规则：

- `voice` 不实现 Persona 和 RAG。
- `presentation` 不调用 LLM Provider。
- `avatar` 不读取 Memory。
- `Conversation Service` 不依赖 WebRTC SDK。
- Channel Adapter 只转换输入输出格式。

## 22. 明确不做

近期不做：

- 自动生成完整 Live2D 或 VRM 模型。
- 未授权真人声音克隆。
- 默认持续摄像头监控。
- 语音情绪识别替代文本与上下文情绪判断。
- 为语音模式建立独立 Memory。
- 在 V1 主线完成前部署复杂实时媒体集群。
- 复制 Amadeus 源码、角色资源或专有提示词。
- 复制或公开分发 `umikok7/roxy-agent` 中授权不明的角色模型、动作、语音或 Persona。

## 23. 开发启动门槛

进入 M7.5 前必须确认：

- 已完成基础 Web Chat 和结构化 AgentResponse。
- 已确认普通聊天页移除常驻人物，并完成全屏通话页面边界。
- 已定义 AvatarProfile 和 PresentationPlan schema。
- 已具备静态头像降级资源。

进入 M7.75 前必须确认：

- 已完成 StaticAvatarRenderer 和 Renderer 降级链。
- 已确定 Three.js、VRM/VRMA 渲染依赖及许可证。
- 已准备原创、明确授权或仅用于 Personal Self-hosted 的测试模型和动作。
- 已定义模型大小、移动端和 WebGL 降级策略。

进入 M8.5 前必须确认：

- Conversation Service 可接受 `channel=voice` 的普通文本消息。
- Mock ASR 和 Mock TTS 的确定性测试数据已准备。
- 已选择首个 OpenAI-compatible ASR/TTS Provider。
- 已确定浏览器支持的录音格式和服务端转换策略。
- 已定义原始音频默认不保留的清理流程。

进入 M9.5 前必须确认：

- 半实时链路稳定且 Trace 可拆分各阶段耗时。
- Provider 支持取消或已有可接受的取消补偿方案。
- 已选定 WebRTC/FastRTC 或其他实时媒体实现。
- 已准备受控的 STUN/TURN 环境和临时凭证下发方式。
- 已完成 Barge-in、断线恢复和半实时降级的测试设计。

## 24. 最终决策

Mio 采用“文字聊天与沉浸通话分离 + 统一核心 + 可插拔表现层”的方案：

```text
普通聊天页不常驻人物
        +
全屏沉浸式语音通话
        +
Static / Live2D / VRM Avatar Renderer
        +
同一个 PersonaRAG Agent
        +
先半实时、后 WebRTC 实时
```

该方案保留现有全部扩展方向，同时为未来的桌面端、3D 形象、移动端、视觉输入和硬件终端提供稳定边界。
