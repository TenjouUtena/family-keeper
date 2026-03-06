"use client";

import { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";

import { Button } from "@/components/ui/button";

interface QRScannerProps {
  onScan: (decodedText: string) => void;
  onClose: () => void;
}

const SCANNER_ID = "qr-scanner-region";

export function QRScanner({ onScan, onClose }: QRScannerProps) {
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const scanner = new Html5Qrcode(SCANNER_ID);
    scannerRef.current = scanner;

    scanner
      .start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        (decodedText) => {
          scanner.stop().then(() => {
            onScan(decodedText);
          });
        },
        () => {
          // ignore scan failures (no QR in frame)
        },
      )
      .catch((err: Error) => {
        setError(
          err.message?.includes("Permission")
            ? "Camera access is required to scan QR codes. Please allow camera permission."
            : "Unable to start camera. Try entering the code manually.",
        );
      });

    return () => {
      scanner
        .stop()
        .catch(() => {})
        .then(() => scanner.clear())
        .catch(() => {});
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/80">
      <div className="w-full max-w-sm px-4">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Scan QR Code</h2>
          <Button variant="ghost" size="sm" onClick={onClose} className="text-white hover:text-gray-300">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </Button>
        </div>

        {error ? (
          <div className="rounded-lg bg-white p-6 text-center">
            <p className="text-sm text-red-600">{error}</p>
            <Button variant="secondary" onClick={onClose} className="mt-4">
              Close
            </Button>
          </div>
        ) : (
          <div
            id={SCANNER_ID}
            className="overflow-hidden rounded-lg"
          />
        )}
      </div>
    </div>
  );
}
