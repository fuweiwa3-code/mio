import type { ChatApi } from "../../api/chat-api";
import type {
  CompanionProfile,
  Conversation,
  Message,
} from "../../api/types";

export interface ChatBootstrapResult {
  profile: CompanionProfile;
  conversations: Conversation[];
  currentConversation: Conversation;
  messages: Message[];
}

let pendingBootstrap: Promise<ChatBootstrapResult> | null = null;

export function bootstrapChatOnce(
  api: ChatApi,
  savedConversationId: string | null,
): Promise<ChatBootstrapResult> {
  if (!pendingBootstrap) {
    pendingBootstrap = bootstrapChat(api, savedConversationId).finally(() => {
      pendingBootstrap = null;
    });
  }
  return pendingBootstrap;
}

export async function bootstrapChat(
  api: ChatApi,
  savedConversationId: string | null,
): Promise<ChatBootstrapResult> {
  const [, profile, listing] = await Promise.all([
    api.checkReady(),
    api.getProfile(),
    api.listConversations(),
  ]);

  let conversations = listing.items;
  let currentConversation =
    conversations.find(({ id }) => id === savedConversationId) ??
    conversations[0];

  if (!currentConversation) {
    currentConversation = await api.createConversation({
      title: "新对话",
      channel: "web",
    });
    conversations = [currentConversation];
  }

  const history = await api.listMessages(currentConversation.id, 100);

  return {
    profile,
    conversations,
    currentConversation,
    messages: history.items,
  };
}
