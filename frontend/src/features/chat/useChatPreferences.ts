import { useState } from "react";

export function useChatPreferences() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return {
    closeSidebar: () => setSidebarOpen(false),
    openSidebar: () => setSidebarOpen(true),
    sidebarOpen,
  };
}
