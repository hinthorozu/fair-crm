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

function DetailPrimaryBadge() {
  return <span className="detail-primary-badge">Primary</span>;
}

export function DetailPhoneList({ items }: { items: { id: string; phone: string; is_primary: boolean }[] }) {
  if (!items.length) return <>—</>;
  return (
    <ul className="detail-collection-list">
      {items.map((item) => (
        <li key={item.id} className="detail-collection-item">
          <DetailPhone value={item.phone} />
          {item.is_primary ? <DetailPrimaryBadge /> : null}
        </li>
      ))}
    </ul>
  );
}

export function DetailEmailList({ items }: { items: { id: string; email: string; is_primary: boolean }[] }) {
  if (!items.length) return <>—</>;
  return (
    <ul className="detail-collection-list">
      {items.map((item) => (
        <li key={item.id} className="detail-collection-item">
          <DetailEmail value={item.email} />
          {item.is_primary ? <DetailPrimaryBadge /> : null}
        </li>
      ))}
    </ul>
  );
}

export function DetailWebsiteList({
  items,
}: {
  items: { id: string; website: string; is_primary: boolean }[];
}) {
  if (!items.length) return <>—</>;
  return (
    <ul className="detail-collection-list">
      {items.map((item) => (
        <li key={item.id} className="detail-collection-item">
          <DetailWebsite value={item.website} />
          {item.is_primary ? <DetailPrimaryBadge /> : null}
        </li>
      ))}
    </ul>
  );
}
