"use client";

import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [isIOS, setIsIOS] = useState(false);
  const [showIOSModal, setShowIOSModal] = useState(false);
  const [dismissed, setDismissed] = useState(true); // default hidden until checked

  useEffect(() => {
    if (localStorage.getItem("install-prompt-dismissed")) return;
    if (window.matchMedia("(display-mode: standalone)").matches) return;

    setDismissed(false);

    const ua = navigator.userAgent;
    const isIOSDevice =
      /iPad|iPhone|iPod/.test(ua) && !("MSStream" in window);
    setIsIOS(isIOSDevice);

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const result = await deferredPrompt.userChoice;
    if (result.outcome === "accepted") {
      setDismissed(true);
    }
    setDeferredPrompt(null);
  };

  const handleDismiss = () => {
    setDismissed(true);
    localStorage.setItem("install-prompt-dismissed", "true");
  };

  if (dismissed || (!deferredPrompt && !isIOS)) return null;

  return (
    <>
      <div className="fixed bottom-16 left-0 right-0 z-40 border-t border-indigo-100 bg-indigo-50 px-4 py-3">
        <div className="mx-auto flex max-w-lg items-center justify-between">
          <p className="text-sm font-medium text-indigo-900">
            Install Family Keeper for quick access
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleDismiss}
              className="text-sm text-indigo-600 hover:text-indigo-800"
            >
              Later
            </button>
            <button
              onClick={isIOS ? () => setShowIOSModal(true) : handleInstall}
              className="rounded-lg bg-indigo-600 px-3 py-1 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Install
            </button>
          </div>
        </div>
      </div>

      {showIOSModal && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-t-2xl bg-white p-6">
            <h3 className="text-lg font-semibold text-gray-900">
              Install on iOS
            </h3>
            <ol className="mt-4 list-inside list-decimal space-y-2 text-sm text-gray-700">
              <li>
                Tap the <strong>Share</strong> button (square with arrow)
              </li>
              <li>
                Scroll down and tap <strong>Add to Home Screen</strong>
              </li>
              <li>
                Tap <strong>Add</strong>
              </li>
            </ol>
            <button
              onClick={() => {
                setShowIOSModal(false);
                handleDismiss();
              }}
              className="mt-6 w-full rounded-lg bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Got it
            </button>
          </div>
        </div>
      )}
    </>
  );
}
