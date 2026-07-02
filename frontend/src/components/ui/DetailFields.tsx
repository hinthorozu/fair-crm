import React from "react";

export function detailText(value: string | null | undefined): string {
  return value?.trim() ? value.trim() : "—";
}

export function websiteHref(url: string): string {
  const trimmed = url.trim();
  return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

export function formatDetailDate(value: string | null | undefined): string {
  if (!value?.trim()) return "—";
  const dateOnly = value.trim().slice(0, 10);
  const parsed = new Date(`${dateOnly}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString("tr-TR");
}

export function DetailValue({ value }: { value: string | null | undefined }) {
  return <>{detailText(value)}</>;
}

export function DetailDate({ value }: { value: string | null | undefined }) {
  return <>{formatDetailDate(value)}</>;
}

export function DetailPhone({ value }: { value: string | null | undefined }) {
  const text = value?.trim();
  if (!text) return <>—</>;
  return (
    <a className="detail-link" href={`tel:${text}`}>
      {text}
    </a>
  );
}

export function DetailEmail({ value }: { value: string | null | undefined }) {
  const text = value?.trim();
  if (!text) return <>—</>;
  return (
    <a className="detail-link" href={`mailto:${text}`}>
      {text}
    </a>
  );
}

export function DetailWebsite({ value }: { value: string | null | undefined }) {
  const text = value?.trim();
  if (!text) return <>—</>;
  return (
    <a className="detail-link" href={websiteHref(text)} target="_blank" rel="noopener noreferrer">
      {text}
    </a>
  );
}
