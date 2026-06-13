# Mio 前端开发与联调须知

> 面向后续负责 Web 前端实现和前后端联调的开发者。完整接口字段和示例请以
> `docs/development/frontend-backend-integration.md` 为准；本文侧重开发范围、现有基线、实施顺序和验收。

## 1. 开始前必读

1. `AGENTS.md`
2. `docs/development/frontend-backend-integration.md`
3. `docs/development/chat-backend.md`
4. `docs/development/m2-implementation-handoff.md`
5. `frontend/src/api/types.ts`
6. `frontend/src/api/chat-api.ts`
7. `frontend/src/features/chat/useChatStream.ts`

后端代码和测试是最终事实来源。文档与代码冲突时，以当前代码和较新的开发文档为准。

## 2. 当前基线

前端已经具备：

- React 19、Vite、TypeScript 和 Vitest 工程。
- Conversation 初始化、创建、选择和历史消息加载。
- `fetch` 读取 SSE 流。
- 五类聊天事件处理：`started`、`delta`、`completed`、`cancelled`、`failed`。
- 服务端取消请求。
- 基础聊天页面和 Mock 语音页面。

M2 后端已经具备：

- 情绪、意图、风险分类。
- Persona/Safety 条件路由。
- AgentTrace 分类数据持久化。
- 安全的 Trace 列表和详情 API。

当前前端尚未接入：

- Trace API 请求方法与类型。
- Trace 查看或调试界面。
- Trace 列表分页和筛选交互。

## 3. 本轮前端范围

建议按以下优先级开发：

1. 保持现有聊天闭环可用。
2. 补齐 Trace TypeScript 类型。
3. 增加 Trace API client。
4. 增加只读 Trace 查看入口或调试面板。
5. 完成取消、失败、分页和安全脱敏联调。

本轮不要实现：

- Memory、RAG、知识库和项目检索。
- Reminder 创建能力。
- Tool Calling、Skill 或 MCP。
- Persona Builder。
- 真实语音、Live2D 或 VRM 集成。
- 登录注册和完整多用户系统。

未实现入口可以显示“开发中”，但不得请求不存在的 API。

## 4. 环境与启动

前端本地环境：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

启动：

```powershell
cd frontend
npm install
npm run dev
```

检查：

```powershell
npm run test
npm run lint
npm run build
```

浏览器中不得保存模型 API Key、数据库 URL 或数据库密码。所有 `VITE_*` 变量都会进入前端构建产物。

## 5. API 接入约束

Base URL 从 `VITE_API_BASE_URL` 读取。JSON 字段保持后端的 `snake_case`，不要在同一网络层混用 camelCase。

M2 主要接口：

```text
GET  /api/health/ready
GET  /api/v1/companion/profile
POST /api/v1/conversations
GET  /api/v1/conversations
GET  /api/v1/conversations/{conversation_id}/messages
POST /api/v1/conversations/{conversation_id}/messages
POST /api/v1/chat/requests/{request_id}/cancel
GET  /api/v1/traces
GET  /api/v1/traces/{trace_id}
```

完整字段以 `frontend-backend-integration.md` 为准。

## 6. SSE 状态机

公开事件只有：

```text
message.started
message.delta
message.completed
message.cancelled
message.failed
```

推荐状态变化：

```text
sending
  -> thinking
  -> streaming
  -> completed | cancelled | failed
```

约束：

- `agent.completed` 是后端内部事件，前端不会收到。
- 分类结果不随 SSE 返回，应通过 `trace_id` 查询 Trace。
- 一个网络 chunk 不等于一个 SSE event，必须继续使用缓冲解析器。
- 收到 terminal event 后清理当前 `request_id`。
- 流结束后重新加载消息历史，以服务端持久化结果为准。

## 7. 取消与断连

`AbortController.abort()` 和服务端取消不是同一件事：

- `AbortController`：停止浏览器继续读取当前响应。
- Cancel API：通知后端停止分类或生成，并把消息保存为 `cancelled`。

用户点击“停止生成”时调用 Cancel API。切换页面或组件卸载时可以 abort 本地读取。取消后应重新加载历史，避免本地状态与数据库不一致。

常见结果：

- `404 request_not_active`：请求已经结束，清理本地 request ID 并刷新历史。
- `409 conversation_busy`：当前 Conversation 已有生成，不要重复提交。

## 8. Trace 前端契约

需要在 `frontend/src/api/types.ts` 增加：

```ts
export type TraceNodeStatus =
  | "pending"
  | "streaming"
  | "completed"
  | "failed"
  | "cancelled"
  | "fallback"
  | "skipped";

export interface TraceNodeSummary {
  status?: TraceNodeStatus;
  duration_ms?: number;
  error_code?: string | null;
}

export interface TraceResponse {
  id: UUID;
  conversation_id: UUID;
  request_id: UUID;
  status: string;
  provider: string;
  model: string;
  duration_ms: number | null;
  error_stage: string | null;
  error_code: string | null;
  emotion_label: string | null;
  emotion_confidence: number | null;
  intent_label: string | null;
  intent_confidence: number | null;
  risk_level: string | null;
  risk_confidence: number | null;
  classification_status: string | null;
  classification_error_code: string | null;
  route: string | null;
  trace_schema_version: number;
  node_summary: Record<string, TraceNodeSummary>;
  created_at: string;
  updated_at: string;
}
```

注意：

- `trace_schema_version` 永远是非空整数；历史记录返回 `1`。
- Cursor 是不透明字符串，只能原样传回后端。
- Trace 不包含聊天正文和完整 Prompt，不要尝试从 Trace 还原对话。
- 其他 owner 的 Trace 与不存在的 Trace 都返回 `404 trace_not_found`。

## 9. Trace UI 建议

Trace 界面应保持只读，最小展示：

- 状态、模型、耗时和时间。
- emotion、intent、risk、confidence。
- Persona/Safety route。
- classification status/error code。
- 节点时间线：节点名、状态、耗时和错误码。

不要展示或要求后端提供：

- API Key 或 Authorization。
- 完整系统 Prompt。
- 完整用户/助手消息。
- Provider 原始响应。
- Python 堆栈或数据库连接信息。

列表默认按后端顺序展示，不在前端重新排序。分页使用 `next_cursor`。

## 10. 错误处理

统一错误结构：

```ts
interface ApiError {
  code: string;
  message: string;
  trace_id: string;
  details: Record<string, unknown>;
}
```

重点错误码：

| code | 前端行为 |
|---|---|
| `conversation_not_found` | 刷新 Conversation 列表或创建新对话 |
| `conversation_busy` | 禁止重复发送，保留当前生成状态 |
| `request_not_active` | 清理本地 request ID，刷新历史 |
| `invalid_cursor` | 丢弃 cursor，从第一页重新加载 |
| `trace_not_found` | 关闭 Trace 详情并刷新列表 |
| `validation_error` | 检查请求参数并显示可理解提示 |
| `internal_error` | 显示通用错误和 `trace_id` |

不要向用户直接展示 `details` 中的未知内部值。

## 11. 推荐开发顺序

1. 确认现有聊天测试、构建和页面正常。
2. 为 Trace 类型和 API client 先写测试。
3. 实现 `listTraces()` 和 `getTrace()`。
4. 实现 Trace 列表、分页、筛选和详情。
5. 用 Mock 后端完成前端状态测试。
6. 启动真实 FastAPI，执行前后端联调。
7. 验证取消、失败、Safety、历史 Trace 和越权场景。
8. 完成构建、测试和联调记录。

## 12. 联调测试清单

### 聊天

- 正常消息收到 `started -> delta -> completed`。
- crisis/unsafe 输入走 Safety 回复，仍以标准 SSE 事件返回。
- 连续两轮不会复用上一轮分类。
- 同一 Conversation 重复发送得到 `conversation_busy`。
- 点击停止得到 `message.cancelled`，刷新历史后状态一致。
- 网络断开后重新加载历史，不重复插入消息。
- Provider 失败得到 `message.failed`。

### Trace

- completed、cancelled、failed Trace 均可查询。
- emotion、intent、risk、route 与测试输入相符。
- 历史 Trace 的 `trace_schema_version` 为 `1`。
- 新 Trace 的版本为 `2`。
- Cursor 分页无重复、无遗漏。
- conversation/status 过滤生效。
- 非法 cursor 后可以从第一页恢复。
- 不存在或越权 Trace 返回统一 404。
- 页面中不存在 Prompt、聊天正文、API Key 或堆栈。

### 兼容性

- Chrome/Edge 最新稳定版。
- 页面刷新后恢复最后选择的 Conversation。
- 切换 Conversation 时旧流不会污染新页面。
- 窄屏下聊天和 Trace 面板仍可操作。

## 13. 联调前置条件

在连接云端 PostgreSQL 的环境联调前，后端负责人需要：

1. 备份数据库。
2. 确认 `alembic current`。
3. 执行并确认迁移至 `20260613_0002`。
4. 使用 Mock Provider 完成一次后端健康检查和聊天回归。
5. 确认 CORS 包含实际前端 Origin。

前端开发者不要自行修改数据库或执行生产迁移。

## 14. 提交要求

前端提交至少附带：

- 修改范围和页面截图。
- 新增或修改的测试。
- `npm run test`、`npm run lint`、`npm run build` 结果。
- 已联调接口和未联调接口。
- 已知限制。

涉及 API 契约变化时，必须同步更新
`docs/development/frontend-backend-integration.md`，不能只修改前端类型。
