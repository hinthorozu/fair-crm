import type {
  CreateCustomerPayload,
  Customer,
  CustomerEmail,
  CustomerPhone,
  CustomerWebsite,
} from "../types/customer";
import { isValidSingleEmail } from "./email";

export interface CommunicationFormItem {
  id: string;
  value: string;
  is_primary: boolean;
}

function createItemId(): string {
  return `comm-${Math.random().toString(36).slice(2, 10)}`;
}

export function createCommunicationItem(
  value = "",
  isPrimary = false,
): CommunicationFormItem {
  return { id: createItemId(), value, is_primary: isPrimary };
}

/** Keep all rows (including empty) while enforcing exactly one primary. */
export function ensureSinglePrimary(items: CommunicationFormItem[]): CommunicationFormItem[] {
  if (items.length === 0) {
    return [];
  }

  const primaryCount = items.filter((item) => item.is_primary).length;
  if (primaryCount === 1) {
    return items;
  }

  if (primaryCount === 0) {
    return items.map((item, index) => ({
      ...item,
      is_primary: index === 0,
    }));
  }

  let keptPrimary = false;
  return items.map((item) => {
    if (!item.is_primary) {
      return item;
    }
    if (!keptPrimary) {
      keptPrimary = true;
      return item;
    }
    return { ...item, is_primary: false };
  });
}

/** Drop blank rows and normalize primary before API submission. */
export function nonEmptyCommunicationItems(
  items: CommunicationFormItem[],
): CommunicationFormItem[] {
  return ensureSinglePrimary(items.filter((item) => item.value.trim()));
}

export function collectionToFormItems(
  collection: CustomerPhone[] | CustomerEmail[] | CustomerWebsite[] | undefined,
  valueKey: "phone" | "email" | "website",
): CommunicationFormItem[] {
  if (!collection?.length) {
    return [];
  }

  return collection.map((item) =>
    createCommunicationItem(String(item[valueKey]), item.is_primary),
  );
}

export function validateCommunicationEmails(items: CommunicationFormItem[]): string | null {
  for (const item of items) {
    const value = item.value.trim();
    if (!value) continue;
    if (!isValidSingleEmail(value.toLowerCase())) {
      return `Geçersiz e-posta adresi: ${value}`;
    }
  }
  return null;
}

export function formValuesToCustomerPayload(
  values: Omit<CreateCustomerPayload, "phone" | "email" | "website"> & {
    phones: CommunicationFormItem[];
    emails: CommunicationFormItem[];
    websites: CommunicationFormItem[];
  },
): CreateCustomerPayload {
  const phones = nonEmptyCommunicationItems(values.phones).map((item) => ({
    phone: item.value.trim(),
    is_primary: item.is_primary,
  }));
  const emails = nonEmptyCommunicationItems(values.emails).map((item) => ({
    email: item.value.trim().toLowerCase(),
    is_primary: item.is_primary,
  }));
  const websites = nonEmptyCommunicationItems(values.websites).map((item) => ({
    website: item.value.trim(),
    is_primary: item.is_primary,
  }));

  return {
    display_name: values.display_name,
    legal_name: values.legal_name,
    trade_name: values.trade_name,
    customer_type: values.customer_type,
    status: values.status,
    country: values.country,
    city: values.city,
    district: values.district,
    address: values.address,
    description: values.description,
    instagram_url: values.instagram_url,
    facebook_url: values.facebook_url,
    linkedin_url: values.linkedin_url,
    youtube_url: values.youtube_url,
    source: values.source,
    phones,
    emails,
    websites,
  };
}

export function customerToCommunicationForm(customer: Customer) {
  return {
    phones: collectionToFormItems(customer.phones, "phone"),
    emails: collectionToFormItems(customer.emails, "email"),
    websites: collectionToFormItems(customer.websites, "website"),
  };
}
