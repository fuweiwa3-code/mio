import type { Conversation, UUID } from "../../api/types";

interface TraceFiltersProps {
  conversations: Conversation[];
  conversationId?: UUID;
  status?: string;
  disabled?: boolean;
  onConversationChange: (conversationId?: UUID) => void;
  onStatusChange: (status?: string) => void;
}

const STATUS_OPTIONS = [
  { value: "", label: "全部状态" },
  { value: "completed", label: "已完成" },
  { value: "cancelled", label: "已取消" },
  { value: "failed", label: "失败" },
  { value: "pending", label: "等待中" },
  { value: "streaming", label: "生成中" },
];

export function TraceFilters({
  conversations,
  conversationId,
  status,
  disabled = false,
  onConversationChange,
  onStatusChange,
}: TraceFiltersProps): React.JSX.Element {
  return (
    <div className="trace-filters">
      <label className="trace-filter-label" htmlFor="trace-conversation-filter">
        <span>对话</span>
        <select
          id="trace-conversation-filter"
          value={conversationId ?? ""}
          disabled={disabled}
          onChange={(e) => {
            const val = e.target.value;
            onConversationChange(val === "" ? undefined : val);
          }}
        >
          <option value="">全部对话</option>
          {conversations.map((c) => (
            <option key={c.id} value={c.id}>
              {c.title || "未命名对话"}
            </option>
          ))}
        </select>
      </label>

      <label className="trace-filter-label" htmlFor="trace-status-filter">
        <span>状态</span>
        <select
          id="trace-status-filter"
          value={status ?? ""}
          disabled={disabled}
          onChange={(e) => {
            const val = e.target.value;
            onStatusChange(val === "" ? undefined : val);
          }}
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
