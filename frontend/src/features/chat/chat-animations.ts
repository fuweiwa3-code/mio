import { animate, createScope, stagger } from "animejs";
import { useEffect, useRef, type RefObject } from "react";

export function useChatEntranceAnimation(
  rootRef: RefObject<HTMLElement | null>,
  ready: boolean,
) {
  useEffect(() => {
    if (!rootRef.current || !ready) return;

    const scope = createScope({ root: rootRef }).add(() => {
      if (window.matchMedia("(min-width: 721px)").matches) {
        animate(".sidebar", {
          opacity: [0, 1],
          translateX: [-24, 0],
          duration: 720,
          ease: "outExpo",
        });
      }
      animate(".topbar", {
        opacity: [0, 1],
        translateY: [-18, 0],
        duration: 680,
        ease: "outExpo",
      });
      animate(".composer-shell", {
        opacity: [0, 1],
        translateY: [34, 0],
        duration: 820,
        delay: 120,
        ease: "outExpo",
      });
    });

    return () => scope.revert();
  }, [ready, rootRef]);
}

export function useMessageListAnimation(
  rootRef: RefObject<HTMLElement | null>,
  latestKey: string | undefined,
  messageCount: number,
) {
  const initialAnimationPlayed = useRef(false);

  useEffect(() => {
    if (!rootRef.current || !latestKey) return;
    const node = rootRef.current.querySelector(
      `[data-message-key="${CSS.escape(latestKey)}"]`,
    );
    if (!node) return;

    animate(node, {
      opacity: [0, 1],
      translateY: [18, 0],
      scale: [0.985, 1],
      duration: 520,
      ease: "outCubic",
    });
  }, [latestKey, rootRef]);

  useEffect(() => {
    if (
      !rootRef.current ||
      messageCount === 0 ||
      initialAnimationPlayed.current
    ) {
      return;
    }
    initialAnimationPlayed.current = true;

    animate(rootRef.current.querySelectorAll(".message-row"), {
      opacity: [0, 1],
      translateY: [10, 0],
      delay: stagger(45),
      duration: 420,
      ease: "outQuad",
    });
  }, [messageCount, rootRef]);
}

export function useAvatarEntranceAnimation(
  rootRef: RefObject<HTMLElement | null>,
  visible: boolean,
) {
  useEffect(() => {
    if (!rootRef.current || !visible) return;

    const scope = createScope({ root: rootRef }).add(() => {
      animate(".avatar-figure", {
        opacity: [0, 1],
        translateX: [72, 0],
        translateY: [20, 0],
        scale: [0.94, 1],
        duration: 900,
        ease: "outExpo",
      });
      animate(".avatar-glow", {
        opacity: [0, 0.72],
        scale: [0.72, 1],
        duration: 1100,
        ease: "outQuad",
      });
    });

    return () => scope.revert();
  }, [rootRef, visible]);
}
