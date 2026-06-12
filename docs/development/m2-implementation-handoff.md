# M2 分类与安全路由——实施交接文档

## 1. M2 总目标

为 Mio 后端添加结构化消息分类（emotion/intent/risk）、条件 LangGraph 安全路由、增强 AgentTrace 分类字段、Trace 查询 API 和 Alembic 迁移。

### 四阶段拆分

| 阶段 | 内容 | 状态 |
|------|------|------|
| 1 | 分类 Pydantic Schema + Mock 分类器 | ✅ 已完成 |
| 2 | OpenAI-compatible 分类器 + 工厂 + LangGraph 路由 + Safety + Persona Prompt | ✅ 已完成 |
| 3 | AgentTrace 分类字段增强 + Alembic 迁移 | 待实现 |
| 4 | Trace 查询 API + 文档终稿 | 待实现 |

---

## 2. 第一阶段完成范围

### 2.1 新增文件及职责

| 文件 | 职责 |
|------|------|
| `backend/src/mio/classification/__init__.py` | 包入口，re-export 所有公开类型和 `classification_fallback` |
| `backend/src/mio/classification/models.py` | 枚举 + Pydantic Schema + 交叉约束 + fallback 工厂 |
| `backend/src/mio/classification/base.py` | `MessageClassifier` ABC（async 接口 + cancel + aclose） |
| `backend/src/mio/classification/mock.py` | `MockMessageClassifier`（确定性关键词分类器） |
| `backend/src/mio/classification/exceptions.py` | 分类异常层次 |
| `backend/src/mio/py.typed` | PEP 561 标记 |
| `backend/tests/test_classification.py` | 55 条测试 |

---

## 3. 分类枚举与 Schema 契约

### 3.1 EmotionLabel（9 值）

```
crisis, angry, anxious, sad, lonely, tired, happy, embarrassed, calm
```

检测优先级：crisis > angry > anxious > sad/lonely > tired > happy > embarrassed > calm

### 3.2 IntentLabel（5 值）

```
unsafe, reminder, mixed, knowledge_qa, companion
```

检测优先级：unsafe > reminder > mixed > knowledge_qa > companion

### 3.3 RiskLevel（4 值）

```
none, low, medium, high
```

支持 `<`/`<=`/`>`/`>=` 语义排序。

### 3.4 ClassificationResult

```python
ClassificationResult(
    emotion=EmotionResult(label=EmotionLabel, confidence=0.0~1.0),
    intent=IntentResult(label=IntentLabel, confidence=0.0~1.0),
    risk=RiskResult(level=RiskLevel, confidence=0.0~1.0),
)
```

**验证规则：**

- 所有 Schema 使用 `strict=True`：拒绝字符串隐式转枚举、字符串隐式转浮点数。
- 所有 Schema 使用 `extra="forbid"`：拒绝未知字段。
- `confidence` 范围：`0.0 <= x <= 1.0`。

**交叉约束（model_validator）：**

- `emotion=crisis` → `risk.level` 必须为 `high`
- `intent=unsafe` → `risk.level` 必须为 `high`

违反约束时抛出 `ValidationError`，错误信息包含触发条件和实际值。

---

## 4. MessageClassifier 接口

```python
class MessageClassifier(ABC):
    name: str

    @abstractmethod
    async def classify(self, text: str, *, request_id: UUID) -> ClassificationResult:
        raise NotImplementedError

    @abstractmethod
    async def cancel(self, request_id: UUID) -> None:
        raise NotImplementedError

    async def aclose(self) -> None:
        return None
```

调用方在分类失败时应使用 `classification_fallback()` 降级。

---

## 5. Mock 分类器

### 5.1 关键词表

**Emotion（按优先级）：**

| 标签 | 关键词 |
|------|--------|
| crisis | 不想活、自杀、想死、活不下去、结束生命、轻生 |
| angry | 气死、愤怒、烦死、生气、可恶、恼火 |
| anxious | 焦虑、紧张、害怕、恐惧、不安、慌 |
| sad | 难过、伤心、想哭、悲伤、心碎、痛苦 |
| lonely | 孤独、寂寞、没人陪、一个人、被抛弃 |
| tired | 累、疲惫、不想动、好困、筋疲力尽 |
| happy | 开心、高兴、太好了、快乐、幸福、棒 |
| embarrassed | 尴尬、害羞、不好意思、丢脸 |
| calm | 兜底 |

**Intent（按优先级）：**

| 标签 | 关键词 |
|------|--------|
| unsafe | 自残、自杀、不想活、结束生命、轻生、想死 |
| reminder | 提醒、记得、别忘了、定时、闹钟 |
| mixed | 情绪信号 + 知识信号同时出现 |
| knowledge_qa | 什么是、为什么、怎么、如何、解释、原理、GIL |
| companion | 兜底 |

**注意：** `unsafe` 关键词故意排除了单独的「伤害」——因为「他伤害了我」「我不想伤害别人」「不小心伤害了朋友」均不是自残意图。

### 5.2 Risk 映射

| 条件 | Risk |
|------|------|
| emotion=crisis 或 intent=unsafe | high |
| emotion=angry 或 emotion=anxious | medium |
| 其他 | none |

### 5.3 已知局限

- 关键词匹配，非语义理解。
- `knowledge_qa` 中的「怎么」可能误触发，但优先级低于 `unsafe`。
- 置信度固定为 0.9，不反映实际匹配强度。

---

## 6. Fallback 结果

```python
classification_fallback() → ClassificationResult(
    emotion=EmotionResult(label=calm, confidence=0.0),
    intent=IntentResult(label=companion, confidence=0.0),
    risk=RiskResult(level=medium, confidence=0.0),
)
```

---

## 7. 第二阶段完成范围

### 7.1 新增文件及职责

| 文件 | 职责 |
|------|------|
| `backend/src/mio/classification/openai_compatible.py` | OpenAI-compatible 分类器（asyncio task 取消） |
| `backend/src/mio/classification/factory.py` | 分类器工厂 |
| `backend/src/mio/classification/exceptions.py` | 分类异常层次 |
| `backend/src/mio/agent/safety.py` | 确定性 Safety 回复模板 |
| `backend/tests/test_openai_compatible_classifier.py` | OpenAI-compatible 分类器测试 |
| `backend/tests/test_classifier_factory.py` | 工厂和配置测试 |
| `backend/tests/test_graph_routing.py` | LangGraph 路由测试 |
| `backend/tests/test_cancel_and_isolation.py` | 取消和轮次隔离回归测试 |

### 7.2 修改文件

| 文件 | 变更 |
|------|------|
| `backend/src/mio/classification/base.py` | 新增 `request_id` 参数、`cancel()`、`aclose()` |
| `backend/src/mio/classification/mock.py` | 实现 asyncio task 取消，活动任务映射 |
| `backend/src/mio/classification/__init__.py` | 新增异常 re-export |
| `backend/src/mio/config.py` | 新增 4 个分类器配置字段 |
| `backend/src/mio/agent/graph.py` | 完整重写：分类节点、条件路由、Safety 路径 |
| `backend/src/mio/agent/prompt.py` | 新增分类上下文感知的回复策略 |
| `backend/src/mio/services/conversations.py` | 接受 classifier 参数、支持分类阶段取消、精确查询用户消息 |
| `backend/src/mio/main.py` | 工厂创建 classifier、传递给 graph 和 service |
| `backend/.env.example` | 新增分类器配置项 |
| `backend/tests/conftest.py` | Settings fixture 新增 classifier 配置 |
| `backend/tests/test_provider_failure.py` | 构造 ConversationService 时传入 classifier |
| `backend/tests/test_classification.py` | Mock 分类器测试适配 request_id 参数 |

---

## 8. OpenAI-compatible 分类器协议

### 8.1 请求

- 端点：`{base_url}/chat/completions`
- `stream=false`、`temperature=0`
- `response_format.type=json_schema`，使用 `ClassificationResult.model_json_schema()` 生成
- Authorization header 仅在 api_key 非空时发送
- System prompt 要求模型按 schema 返回 JSON

### 8.2 响应校验

- 直接使用 `ClassificationResult.model_validate_json(content)` 校验
- 禁止删除 Markdown fence、正则提取 JSON、修补枚举或模糊解析
- 空 choices → `ClassificationProviderError`
- 空 content → `ClassificationSchemaInvalidError`
- 非法 JSON → `ClassificationSchemaInvalidError`
- 非法枚举 → `ClassificationSchemaInvalidError`
- 额外字段 → `ClassificationSchemaInvalidError`
- confidence 越界 → `ClassificationSchemaInvalidError`
- 交叉约束失败 → `ClassificationSchemaInvalidError`
- HTTP 4xx/5xx → `ClassificationProviderError`

### 8.3 异常层次

```
ClassificationError (base)
├── ClassificationProviderError      — HTTP/连接错误
├── ClassificationSchemaInvalidError — 响应校验失败
└── ClassificationCancelledError     — 分类请求被取消（业务级取消，非 asyncio.CancelledError）
```

---

## 9. 工厂与配置

### 9.1 新增 Settings 字段

```python
classifier_provider: Literal["mock", "openai_compatible"] = "mock"
classifier_model: str = "mock-classifier"
classifier_base_url: str = ""
classifier_api_key: str = ""
```

### 9.2 工厂函数

```python
create_message_classifier(settings) → MessageClassifier
```

- `mock` → `MockMessageClassifier()`
- `openai_compatible` → `OpenAICompatibleMessageClassifier(...)`
- 缺少 `classifier_base_url` 时抛出 `ValueError`

### 9.3 .env.example

```
MIO_CLASSIFIER_PROVIDER=mock
MIO_CLASSIFIER_MODEL=mock-classifier
MIO_CLASSIFIER_BASE_URL=
MIO_CLASSIFIER_API_KEY=
```

---

## 10. MessageClassifier 生命周期与取消契约

### 10.1 接口

```python
class MessageClassifier(ABC):
    async def prepare(self, request_id: UUID) -> None: ...
    async def classify(self, text: str, *, request_id: UUID) -> ClassificationResult: ...
    async def cancel(self, request_id: UUID) -> None: ...
    async def release(self, request_id: UUID) -> None: ...
    async def aclose(self) -> None: ...
```

### 10.2 生命周期（由 ConversationService.stream_turn 驱动）

```
stream_turn 开始
  → classifier.prepare(request_id)     # 在 message.started 之前
  → yield message.started
  → 用户可能 cancel
  → Graph 运行 → classify(text, request_id)
  → terminal event (completed/cancelled/failed)
  → finally:
      classifier.release(request_id)   # 在 registry.release 之前
      registry.release(conversation_id, request_id)
```

### 10.3 竞态根因与解决方案

**问题**：如果 `cancel_event` 在 `classify()` 内部注册，存在以下窗口：
1. `stream_turn` yield `message.started`
2. 用户调用 `cancel()` → `classifier.cancel()` 是 no-op（event 尚未注册）
3. `classify()` 创建全新的、未取消的 Event
4. HTTP 请求正常发出

**解决方案**：`prepare()` 在 `message.started` 之前注册 Event。`cancel()` 只 `set()` 已存在的 Event。`classify()` 复用 `prepare()` 创建的 Event。

### 10.4 各方法职责

- **`prepare(request_id)`**：在 `_cancel_events` 中注册 `asyncio.Event`。幂等，不覆盖已 set 的 Event。
- **`classify(text, request_id)`**：复用 `prepare()` 的 Event。如果已 set，立即抛出 `ClassificationCancelledError`，不执行 I/O。
- **`cancel(request_id)`**：只对 `_cancel_events` 中已存在的 Event 调用 `set()`。非活跃 request_id 为 no-op。
- **`release(request_id)`**：删除 `_cancel_events` 和 `_active_tasks` 中的状态。多次调用安全。
- **`aclose()`**：set 所有 active cancel events → 等待所有 active classify tasks 退出 → 清理 → 关闭 HTTP client。

### 10.5 OpenAI-compatible Task 管理

`_do_classify()` 创建两个子 task：
- `http_task`：HTTP POST 请求
- `cancel_task`：`cancel_event.wait()`

`asyncio.wait()` 竞争两者。`finally` 中对未完成的 task 执行 `cancel()` + `await asyncio.gather(return_exceptions=True)`。

`_active_tasks: dict[UUID, asyncio.Task]` 跟踪外层 classify task，使 `aclose()` 能真正停止活动分类。

### 10.6 ConversationService 集成

- `stream_turn` 在 `message.started` 前调用 `classifier.prepare()`
- `stream_turn.finally` 中调用 `classifier.release()`（在 `registry.release()` 之前）
- `cancel()` 只对活跃请求的 Event 调用 `set()`
- 分类取消后 graph 产生 fallback → `stream_turn` 检查 `registry.is_cancelled()` → `message.cancelled`
- 不会为已结束的请求重新创建 Event

---

## 11. LangGraph 新拓扑

### 11.1 图结构

```text
START
→ load_context
→ classify_message
   → [safety] → build_safety_response → stream_safety_response → finalize_response → END
   → [persona] → build_persona_prompt → stream_llm → finalize_response → END
```

### 11.2 AgentState 新增字段

```python
current_user_text: str          # 当前用户消息文本
classification: ClassificationResult  # 分类结果
classification_status: str      # "success" | "fallback"
classification_error_code: str  # "classification_provider_error" | "classification_schema_invalid"
route: str                      # "safety" | "persona"
safety_response: str            # Safety 回复文本
node_summary: dict[str, Any]    # 节点执行追踪
```

### 11.3 条件路由规则

| 条件 | 路由 |
|------|------|
| `risk=high` 或 `emotion=crisis` 或 `intent=unsafe` | safety |
| 其他 | persona |

### 11.4 节点执行追踪

```json
{
  "load_context": {"status": "completed", "error_code": null},
  "classify_message": {"status": "completed", "duration_ms": 18, "error_code": null},
  "build_persona_prompt": {"status": "completed", "error_code": null},
  "stream_llm": {"status": "completed", "error_code": null},
  "finalize_response": {"status": "completed", "error_code": null}
}
```

---

## 12. Safety 路由规则

### 12.1 Safety 回复模板

- **crisis/unsafe**: 确认安全、建议联系紧急服务、鼓励联系信任的人
- **其他 high risk**: 确认安全、建议联系信任的人、建议紧急服务

### 12.2 Safety 路径约束

- 不调用 ChatModelProvider
- 停止恋爱、暧昧和角色扮演表达
- 不做医疗诊断
- 不假设用户所在国家
- 不硬编码某个国家的电话号码
- 通过 `message.delta` + `message.completed` 流式输出
- 按 20 字符固定切片，行为确定且可测试

---

## 13. Persona Prompt 分类策略

分类结果转换为简短回复策略文本，不将完整 JSON 塞入 Prompt。

| 分类 | 策略 |
|------|------|
| sad/lonely | 先温柔回应感受，再询问是否想聊或需要建议 |
| anxious | 先帮助稳定情绪，再温和拆分问题 |
| tired | 避免立刻施压，优先承认疲惫 |
| angry | 先承认感受，避免激化 |
| mixed | 先简短回应情绪，再回答问题 |
| knowledge_qa | 保持人设，清晰回答 |
| reminder | 说明理解意图，不假装已创建提醒 |
| risk=medium | 加入谨慎、安全约束 |
| fallback | 加格外谨慎约束 |

---

## 14. SSE 兼容情况

公开事件名不变：
```
message.started
message.delta
message.completed
message.cancelled
message.failed
```

已验证：
- 正常 Persona 回复事件顺序不变
- Safety 回复产生 delta + completed
- 分类 fallback 不产生 message.failed
- Provider 失败仍产生 message.failed code=provider_error
- 显式取消保留已生成文本
- 分类阶段取消允许空的部分文本
- SSE 断连收敛为 cancelled
- 同一 Conversation 并发返回 409 conversation_busy
- 取消后下一轮可发送
- 内部节点事件不暴露给前端

---

## 15. 测试与静态检查结果

```bash
# 完整测试套件
cd backend
.venv\Scripts\python.exe -m pytest -q --durations=10
# 149 passed, 414 warnings in 6.50s

# test_cancel_and_isolation.py 单独
.venv\Scripts\python.exe -m pytest tests/test_cancel_and_isolation.py -q --durations=10
# 11 passed in 0.99s

# Ruff
.venv\Scripts\python.exe -m ruff check .
# All checks passed

# Mypy
.venv\Scripts\python.exe -m mypy src
# Success: no issues found in 34 source files
```

### 测试分类覆盖

| 测试文件 | 条数 | 覆盖范围 |
|----------|------|----------|
| test_classification.py | 57 | 枚举、Schema、交叉约束、Mock 分类器、prepare/cancel/release 生命周期 |
| test_openai_compatible_classifier.py | 27 | 请求构造、合法响应、错误路径、prepare-cancel-classify、HTTP 中断、aclose、release 清理 |
| test_classifier_factory.py | 10 | 配置默认值、工厂类型、缺少 URL 错误、.env.example |
| test_graph_routing.py | 22 | Persona/Safety 路由、fallback、Prompt 策略、状态追踪 |
| test_cancel_and_isolation.py | 11 | 分类前取消（无 HTTP）、分类中取消（2s）、20 次正常清理、HTTP 错误清理、aclose 中断、轮次隔离、Graph CancelledError |
| test_conversations_api.py | 12 | API 回归：事件顺序、取消、断连、并发、分页 |
| test_provider_failure.py | 1 | Provider 失败事件和用户消息保留 |
| test_agent_and_providers.py | 3 | Provider 和 Prompt 基础 |
| test_runtime_behaviors.py | 2 | Registry 和 Recovery |
| test_health_and_profile.py | 2 | 健康检查和 Profile |
| test_config.py | 1 | 配置路径 |

### 第二阶段修复记录（验收后）

**P1-P3：取消生命周期竞态**
- 根因：`classify()` 内部注册 `cancel_event`，`cancel()` 在注册前到达是 no-op，导致 HTTP 请求正常发出
- 修复：引入 `prepare()` / `release()` 生命周期方法。`prepare()` 在 `message.started` 之前注册 Event，消除注册窗口
- `cancel()` 只 `set()` 已存在的 Event，不创建新 Event
- `release()` 在 `stream_turn.finally` 中清理状态，在 `registry.release()` 之前执行

**P4：异步任务泄漏**
- 根因：`asyncio.ensure_future(cancel_event.wait())` 在 HTTP 正常完成时未被取消和 await
- 修复：`_do_classify` 显式保存 `http_task` + `cancel_task`，`finally` 中 `cancel()` + `await asyncio.gather(return_exceptions=True)`

**P5：_cancel_events 残留**
- 根因：`stream_turn` post-graph 取消检查再次调用 `classifier.cancel()`，为已结束请求重新创建 Event
- 修复：`cancel()` 只对已存在的 Event 生效；`stream_turn` post-graph 不再调用 `classifier.cancel()`

**P6：aclose 不能中断活动分类**
- 修复：`_active_tasks: dict[UUID, asyncio.Task]` 跟踪外层 classify task。`aclose()` 先 set 所有 cancel events，再 `await asyncio.gather()` 等待所有 active tasks 退出

**P7：无效测试断言**
- 删除 `assert "安全" not in text2 or "安全" in text2`（永真式）
- 替换为 `assert "紧急" not in text2`

**P8：测试耗时 60 秒**
- 根因：取消测试的"下一轮"仍使用阻塞 60s 的 handler
- 修复：MockTransport `call_count` 计数，第一次请求阻塞，后续请求立即返回
- `test_cancel_and_isolation.py` 从 60s+ 降至 0.99s

---

## 16. 已知限制

1. 分类使用 LLM（或 mock）——不是专用小模型。生产环境可能需要更快/更便宜的分类器。
2. Mock 分类器基于关键词，非语义理解。
3. 单进程 ActiveRequestRegistry——多实例需要 Redis/DB 锁。
4. Safety 模板是确定性的——M2 不使用 LLM 生成安全回复。
5. `knowledge_qa`、`mixed`、`reminder` 意图只影响 Prompt/Trace 状态，不接入 RAG 或 Tool。

---

## 17. 尚未实现

| 内容 | 阶段 |
|------|------|
| AgentTrace 分类字段（数据库列） | 3 |
| Alembic 迁移文件 | 3 |
| Trace 查询 API（单条 + 列表游标分页） | 4 |
| 开发文档和学习文档终稿更新 | 4 |

---

## 18. 环境说明

- **云端 PostgreSQL**：未连接、未迁移。
- **backend/.env**：未修改。
- **Git 交付**：Phase 1/2 代码、测试、设计说明和本交接文档随同一次提交推送。
- **Python 版本**：3.14（项目声明 3.12，使用 `--ignore-requires-python` 安装依赖，运行正常）。
- **venv 路径**：`backend/.venv/`。

---

## 19. 第三阶段开始前应阅读

1. `docs/superpowers/specs/2026-06-12-m2-classification-safety-trace-design.md`——第 3.3 节 AgentTrace 增强和第 3.5 节 Alembic 迁移。
2. `backend/src/mio/db/models.py`——AgentTrace 模型，第三阶段需要新增分类字段。
3. `backend/src/mio/agent/graph.py`——当前图的 node_summary 结构，第三阶段写入 Trace。
4. `backend/src/mio/services/conversations.py`——`_finish()` 方法，第三阶段需要写入分类字段。
5. `backend/tests/test_graph_routing.py`——当前路由测试，第三阶段需要扩展 Trace 相关断言。

### 第三阶段注意事项

- AgentTrace 新字段全部 nullable，保持向后兼容。
- `trace_schema_version` 默认 2，历史记录视为 v1。
- Alembic 迁移文件不得在本机执行 `upgrade head`。
- Trace 查询 API 只返回脱敏数据，不暴露 message content 或 prompt。
- Cursor 分页使用与 messages 相同的 `(created_at, id)` 模式。

---

## 20. 换机继续开发清单

在能够访问云端 PostgreSQL 的电脑上继续开发时：

```powershell
git clone git@github.com:fuweiwa3-code/mio.git
cd mio
git pull origin main
cd backend

# 优先使用项目声明的 Python 3.12，并按 uv.lock 恢复依赖。
uv sync

uv run pytest -q
uv run ruff check .
uv run mypy src
```

开始 Phase 3 前必须确认：

1. 工作区基线测试为 `149 passed`，Ruff 和 Mypy 通过。
2. `backend/.env` 只在本机创建，不提交 API Key 或数据库凭据。
3. 先生成并审查 AgentTrace Alembic 迁移，再连接云端 PostgreSQL。
4. 执行迁移前备份数据库，并记录当前 `alembic current`。
5. 先测试新增 nullable 字段和历史 Trace 兼容，再执行 `alembic upgrade head`。
6. Phase 3 只实现 AgentTrace 字段、迁移和写入，不提前实现 Trace 查询 API。
7. Phase 4 完成后再同步更新 `docs/development/chat-backend.md` 和 `docs/learning/01-python-fastapi-chat-backend.md` 的最终实现说明。

本阶段验收基线：

- M2 Phase 1：结构化分类 Schema 和确定性 Mock 分类器已完成。
- M2 Phase 2：OpenAI-compatible 分类、LangGraph 条件路由、Safety、Persona 策略和完整取消生命周期已完成。
- M2 Phase 3：未开始，云端数据库未修改。
- M2 Phase 4：未开始。
