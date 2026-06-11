// @vitest-environment node

import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const sourceRoot = fileURLToPath(new URL(".", import.meta.url));

async function readSource(path: string) {
  return readFile(new URL(path, import.meta.url), "utf8");
}

function countSelector(css: string, selector: string) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return css.match(new RegExp(`(^|\\n)${escaped}\\s*\\{`, "g"))?.length ?? 0;
}

describe("frontend architecture", () => {
  it("keeps styles.css free of retired and duplicate top-level selectors", async () => {
    const css = await readSource("./styles.css");
    const retiredSelectors = [
      ".brand",
      ".brand-copy",
      ".section-label",
      ".new-conversation",
      ".sidebar-spacer",
      ".sidebar-action",
      ".connection-state",
      ".connection-dot",
      ".profile-orb",
      ".switch-track",
      ".empty-state",
      ".empty-aura",
      ".suggestions",
      ".composer",
      ".composer-icon",
      ".composer-hint",
      ".thinking",
      ".retry-button",
      ".date-pill",
      ".avatar-controls",
      ".avatar-orbit.one",
      ".avatar-orbit.two",
      ".avatar-toggle",
      ".message-list.has-avatar",
      ".avatar-stage + .composer-shell",
    ];

    for (const selector of retiredSelectors) {
      expect(countSelector(css, selector), `${selector} should be removed`).toBe(
        0,
      );
    }

    for (const selector of [".message-row", ".composer-shell"]) {
      expect(countSelector(css, selector), `${selector} should be defined once`).toBe(
        1,
      );
    }

    // Check for retired CSS patterns
    expect(css).not.toMatch(/\.avatar-toggle\b/);
    expect(css).not.toMatch(/\.message-list\.has-avatar\b/);
    expect(css).not.toMatch(/\.avatar-stage\s*\+\s*\.composer-shell\b/);
  });

  it("keeps ChatPage focused on composition instead of animation and orchestration", async () => {
    const source = await readSource("./features/chat/ChatPage.tsx");
    const lines = source.trim().split("\n");

    expect(source).not.toContain('from "animejs"');
    expect(source).not.toContain("handleStreamEvent");
    expect(source).not.toContain("streamMessage(");
    expect(lines.length).toBeLessThanOrEqual(200);
  });

  it("stores shared animation implementation outside visual components", async () => {
    const componentPaths = [
      "./features/chat/ChatPage.tsx",
      "./features/chat/MessageList.tsx",
      "./components/avatar/AvatarStage.tsx",
    ];

    for (const path of componentPaths) {
      const source = await readSource(path);
      expect(source, `${path} should use animation helpers`).not.toContain(
        'from "animejs"',
      );
    }

    expect(sourceRoot).toContain("/src/");
  });

  it("composes chat responsibilities from focused hooks", async () => {
    const source = await readSource("./features/chat/useChatSession.ts");

    expect(source).toContain('from "./useChatBoot"');
    expect(source).toContain('from "./useChatStream"');
    expect(source).toContain('from "./useConversationManager"');
    expect(source.trim().split("\n").length).toBeLessThanOrEqual(100);
  });

  it("keeps the normal chat experience free of avatar rendering", async () => {
    const chatPage = await readSource("./features/chat/ChatPage.tsx");
    const messageList = await readSource("./features/chat/MessageList.tsx");
    const preferences = await readSource("./features/chat/useChatPreferences.ts");

    expect(chatPage).not.toContain("AvatarStage");
    expect(chatPage).not.toContain("avatarVisible");
    expect(chatPage).not.toContain("显示澪");
    expect(messageList).not.toContain("has-avatar");
    expect(messageList).not.toContain("avatarVisible");
    expect(preferences).not.toContain("mio:avatar-visible");
  });
});

  it("renders AvatarStage only from the voice-call feature", async () => {
    const chatPage = await readSource("./features/chat/ChatPage.tsx");
    const voicePage = await readSource(
      "./features/voice-call/VoiceCallPage.tsx",
    );

    expect(chatPage).not.toContain("AvatarStage");
    expect(voicePage).toContain("AvatarStage");
  });

  it("removes decorative shimmer and hover translations from chat", async () => {
    const css = await readSource("./styles.css");
    expect(css).not.toContain("@keyframes shimmer-sweep");
    expect(css).not.toMatch(/\.message-row\.user \.message-bubble::after\b/);
    expect(css).toMatch(/--plum:\s*#5b4652/);
    expect(css).toMatch(/--canvas:\s*#f3efed/);
  });
