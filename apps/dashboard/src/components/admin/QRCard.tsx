"use client";

import { useState } from "react";
import { Check, Copy, QrCode } from "lucide-react";
import dynamic from "next/dynamic";

const QRCodeSVG = dynamic(
  () => import("qrcode.react").then((m) => m.QRCodeSVG),
  { ssr: false, loading: () => <div className="w-[160px] h-[160px] bg-gray-100 rounded animate-pulse" /> },
);

interface QRCardProps {
  areaId: string;
  areaName: string;
  clinicId: string;
}

export function QRCard({ areaId, areaName, clinicId }: QRCardProps) {
  const [copied, setCopied] = useState(false);

  const waPhoneNumber = process.env.NEXT_PUBLIC_WA_PHONE_NUMBER ?? "";
  const checkinUrl = `https://wa.me/${waPhoneNumber}?text=CHECKIN_${clinicId}_${areaId}`;

  function handleCopy() {
    navigator.clipboard.writeText(checkinUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="bg-[var(--color-surface-card)] border border-[var(--color-surface-border)] rounded-lg p-5 flex flex-col items-center gap-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-content-primary)]">
        <QrCode className="w-4 h-4 text-[var(--color-brand-green)]" />
        {areaName}
      </div>

      <div className="p-3 bg-white border border-[var(--color-surface-border)] rounded-lg">
        <QRCodeSVG value={checkinUrl} size={160} level="M" />
      </div>

      <div className="w-full">
        <p className="text-xs text-[var(--color-content-secondary)] mb-1.5 text-center">
          URL de check-in
        </p>
        <div className="flex items-center gap-2 bg-[var(--color-surface-base)] border border-[var(--color-surface-border)] rounded-lg px-3 py-2">
          <span className="text-xs text-[var(--color-content-secondary)] truncate flex-1 font-mono">
            {checkinUrl}
          </span>
          <button
            onClick={handleCopy}
            className="shrink-0 text-[var(--color-content-secondary)] hover:text-[var(--color-content-primary)] transition-colors"
            title="Copiar URL"
          >
            {copied ? (
              <Check className="w-4 h-4 text-[var(--color-brand-green)]" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      <p className="text-xs text-[var(--color-content-secondary)] text-center">
        ID:{" "}
        <span className="font-mono text-[var(--color-content-primary)]">{areaId}</span>
      </p>
    </div>
  );
}
