"use client";

import { useCallback, useRef } from "react";
import { QRCodeSVG } from "qrcode.react";

import { Button } from "@/components/ui/button";

interface InviteQRCodeProps {
  code: string;
  familyName: string;
}

export function InviteQRCode({ code, familyName }: InviteQRCodeProps) {
  const qrRef = useRef<HTMLDivElement>(null);
  const joinUrl = `https://familykeeper.app/families/join?code=${code}`;

  const handleDownload = useCallback(() => {
    const svg = qrRef.current?.querySelector("svg");
    if (!svg) return;

    const svgData = new XMLSerializer().serializeToString(svg);
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);
      canvas.toBlob((blob) => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `invite-${familyName.toLowerCase().replace(/\s+/g, "-")}.png`;
        a.click();
        URL.revokeObjectURL(url);
      }, "image/png");
    };
    img.src = `data:image/svg+xml;base64,${btoa(svgData)}`;
  }, [familyName]);

  return (
    <div className="flex flex-col items-center gap-3">
      <div ref={qrRef} className="rounded-lg bg-white p-3">
        <QRCodeSVG
          value={joinUrl}
          size={200}
          level="M"
          fgColor="#4F46E5"
        />
      </div>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={handleDownload}
      >
        <svg className="mr-1.5 h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
        </svg>
        Download QR
      </Button>
    </div>
  );
}
