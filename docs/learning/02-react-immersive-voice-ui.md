# 02 React 沉浸式语音通话 UI

## 学习目标

完成本章后，你应该能够独立解释并复现：

1. React 组件组合与 props 回调反转。
2. `useState`、`useReducer`、`useEffect` 与清理。
3. TypeScript 判别联合类型建模状态机。
4. 无障碍状态控件（`aria-pressed`、`aria-label`、`role`）。
5. Mock Provider 在 AI 应用工程中的作用。
6. 全屏覆盖页面的布局与动画。

## 前置概念

- 已完成第 01 章的 FastAPI 聊天后端。
- 了解 React 基本 JSX 和函数组件。
- 了解 TypeScript 基本类型标注。

## 1. 组件组合与 Props 回调

### 1.1 React props 不是 Spring 依赖注入

在 Spring Boot 中，Bean 由 IoC 容器自动注入：

```java
@Service
public class ChatService {
    @Autowired
    private MessageRepository repository;
}
```

在 React 中，父组件通过 props 手动传递数据和回调：

```tsx
// App.tsx
<ChatPage onStartVoiceCall={() => setVoiceCallOpen(true)} />
```

关键差异：
- Spring 注入是全局单例，React props 是每层显式传递。
- Spring 在启动时注入一次，React 在每次渲染时传递最新值。
- React 的回调函数让子组件通知父组件，而不是通过事件总线。

### 1.2 体验模式切换

本项目的 App 组件管理两种体验模式：

```tsx
// App.tsx
export default function App() {
  const [voiceCallOpen, setVoiceCallOpen] = useState(false);

  return (
    <>
      <ChatPage onStartVoiceCall={() => setVoiceCallOpen(true)} />
      {voiceCallOpen && (
        <VoiceCallPage onEnd={() => setVoiceCallOpen(false)} />
      )}
    </>
  );
}
```

`ChatPage` 始终挂载，`VoiceCallPage` 作为全屏覆盖层叠加。这样聊天页的滚动位置、输入草稿和 hook 状态都不会丢失。

## 2. useReducer 建模状态机

### 2.1 判别联合类型

TypeScript 的联合类型可以在编译时确保状态转换安全：

```ts
// voice-call-types.ts
export type VoiceCallPhase =
  | "requesting_permission"
  | "listening"
  | "transcribing"
  | "thinking"
  | "speaking"
  | "failed";

export type VoiceCallAction =
  | { type: "permission.granted" }
  | { type: "permission.denied" }
  | { type: "phase.changed"; phase: VoiceCallPhase; subtitle: string; speaker: VoiceSpeaker }
  | { type: "mute.toggled" }
  | { type: "failed"; message: string }
  | { type: "retry" };
```

这类似于 Java 的 sealed interface，但 TypeScript 在运行时不会验证类型，需要靠测试保证。

### 2.2 Reducer 模式

`useReducer` 是 React 内置的状态管理 hook，类似于一个小型显式状态机：

```ts
// voice-call-reducer.ts
export function voiceCallReducer(
  state: VoiceCallState,
  action: VoiceCallAction,
): VoiceCallState {
  switch (action.type) {
    case "permission.granted":
      return { ...state, phase: "listening", subtitle: "我在听。" };
    case "mute.toggled":
      return { ...state, muted: !state.muted };
    case "retry":
      return { ...initialVoiceCallState, muted: state.muted };
  }
}
```

与 Spring 的可变单例不同，Reducer 每次返回新状态对象，React 通过引用比较判断是否需要重新渲染。

### 2.3 useEffect 清理

```ts
// useMockVoiceSession.ts
useEffect(() => {
  return () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
  };
}, []);
```

`useEffect` 的清理函数在组件卸载或依赖变化时执行。这比 `@PreDestroy` 更细粒度——每个 effect 实例都有自己的清理逻辑。

## 3. 无障碍状态控件

### 3.1 aria-pressed

toggle 按钮使用 `aria-pressed` 告知屏幕阅读器当前状态：

```tsx
<button
  aria-label={muted ? "取消静音" : "静音麦克风"}
  aria-pressed={muted}
  onClick={onToggleMute}
>
```

### 3.2 role="status" 与 aria-live

字幕使用 `role="status"` 让屏幕阅读器自动朗读更新：

```tsx
<div className="voice-subtitle" role="status" aria-live="polite">
```

## 4. Mock Provider 的意义

在 AI 应用中，Mock Provider 让前端可以在没有真实 ASR/TTS/LLM 的情况下完成 UI 开发和测试：

- 降低开发环境依赖。
- 使测试确定性可重复。
- 让 UI 状态可手动检查。

本项目的 Mock Voice Session 使用 `simulateNextPhase` 手动切换状态，而不是自动循环，这样每个状态都可以仔细检查。

## 5. 全屏覆盖布局

### 5.1 position: fixed 覆盖

```css
.voice-call-page {
  position: fixed;
  z-index: 100;
  inset: 0;
}
```

`inset: 0` 等价于 `top: 0; right: 0; bottom: 0; left: 0`，让元素铺满视口。

### 5.2 安全区域

移动端底部控制栏需要避开系统手势区域：

```css
.voice-call-controls {
  bottom: max(24px, env(safe-area-inset-bottom));
}
```

## 常见错误

1. **Fake timers 未恢复**：测试中使用 `vi.useFakeTimers()` 后必须在 `afterEach` 中调用 `vi.useRealTimers()`。
2. **Interval 未清理**：组件卸载后 interval 仍在运行，导致内存泄漏和状态更新错误。
3. **aria-pressed 与视觉状态不一致**：按钮看起来是"按下"但 `aria-pressed="false"`。

## 自测题

1. React 的 props 和 Spring 的 `@Autowired` 有什么本质区别？
2. 为什么 Reducer 每次返回新对象而不是修改原对象？
3. `useEffect` 的清理函数什么时候执行？
4. 为什么 Mock Provider 对 AI 应用前端开发很重要？
5. `aria-pressed` 和 `aria-label` 分别解决什么问题？

## 参考答案

1. Spring 注入是全局单例、启动时确定；React props 是每层显式传递、每次渲染更新。
2. React 通过引用比较判断状态是否变化，修改原对象不会触发重新渲染。
3. 组件卸载或依赖变化时执行。
4. 让前端在没有真实 AI 服务的情况下完成 UI 开发和测试，保证确定性和可重复性。
5. `aria-pressed` 告知 toggle 状态，`aria-label` 提供按钮用途描述。

## 下一章

第 03 章将介绍真实的 ASR/TTS Provider 接入，以及如何用 LangGraph 替换 Mock Voice Session 的状态生产者。
