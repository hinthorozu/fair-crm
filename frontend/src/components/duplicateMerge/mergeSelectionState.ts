import type { DuplicateGroupCustomerDetail } from "../../types/dataOperations";

export type ScalarFieldKey = "company_name" | "legal_name" | "trade_name" | "city" | "country";
export type CommChannel = "email" | "phone" | "website";

export const SCALAR_FIELDS: { key: ScalarFieldKey; labelKey: string }[] = [
  { key: "company_name", labelKey: "company_name" },
  { key: "legal_name", labelKey: "legal_name" },
  { key: "trade_name", labelKey: "trade_name" },
  { key: "city", labelKey: "city" },
  { key: "country", labelKey: "country" },
];

export const COMM_CHANNELS: CommChannel[] = ["email", "phone", "website"];

export type CommSelectionKey = string;

export function commSelectionKey(customerId: string, rowId: string): CommSelectionKey {
  return `${customerId}:${rowId}`;
}

export function parseCommSelectionKey(key: CommSelectionKey): { customerId: string; rowId: string } {
  const separatorIndex = key.indexOf(":");
  return {
    customerId: key.slice(0, separatorIndex),
    rowId: key.slice(separatorIndex + 1),
  };
}

export type ScalarSelections = Record<ScalarFieldKey, string>;

export interface MergeSelectionState {
  survivingCustomerId: string;
  scalarSelections: ScalarSelections;
  communicationSelections: Set<CommSelectionKey>;
}

export function getScalarFieldValue(
  customer: DuplicateGroupCustomerDetail,
  field: ScalarFieldKey,
): string | null {
  switch (field) {
    case "company_name":
      return customer.company_name?.trim() || null;
    case "legal_name":
      return customer.legal_name?.trim() || null;
    case "trade_name":
      return customer.trade_name?.trim() || null;
    case "city":
      return customer.city?.trim() || null;
    case "country":
      return customer.country?.trim() || null;
    default:
      return null;
  }
}

export function allCommunicationKeys(
  customers: DuplicateGroupCustomerDetail[],
  channel: CommChannel,
): CommSelectionKey[] {
  const keys: CommSelectionKey[] = [];
  for (const customer of customers) {
    const items =
      channel === "email"
        ? customer.emails
        : channel === "phone"
          ? customer.phones
          : customer.websites;
    for (const item of items) {
      keys.push(commSelectionKey(customer.id, item.id));
    }
  }
  return keys;
}

export function winnerCommunicationKeys(
  customers: DuplicateGroupCustomerDetail[],
  channel: CommChannel,
  survivingCustomerId: string,
): CommSelectionKey[] {
  const customer = customers.find((item) => item.id === survivingCustomerId);
  if (!customer) return [];
  const items =
    channel === "email"
      ? customer.emails
      : channel === "phone"
        ? customer.phones
        : customer.websites;
  return items.map((item) => commSelectionKey(customer.id, item.id));
}

export function createDefaultMergeSelectionState(
  customers: DuplicateGroupCustomerDetail[],
  survivingCustomerId: string,
): MergeSelectionState {
  const scalarSelections = SCALAR_FIELDS.reduce((acc, field) => {
    acc[field.key] = survivingCustomerId;
    return acc;
  }, {} as ScalarSelections);

  const communicationSelections = new Set<CommSelectionKey>();
  for (const channel of COMM_CHANNELS) {
    for (const key of winnerCommunicationKeys(customers, channel, survivingCustomerId)) {
      communicationSelections.add(key);
    }
  }

  return {
    survivingCustomerId,
    scalarSelections,
    communicationSelections,
  };
}

export function sanitizeCommunicationSelections(
  customers: DuplicateGroupCustomerDetail[],
  selections: Set<CommSelectionKey>,
): Set<CommSelectionKey> {
  const validKeys = new Set<CommSelectionKey>();
  for (const channel of COMM_CHANNELS) {
    for (const key of allCommunicationKeys(customers, channel)) {
      if (selections.has(key)) {
        validKeys.add(key);
      }
    }
  }
  return validKeys;
}

export function sanitizeMergeSelectionState(
  customers: DuplicateGroupCustomerDetail[],
  state: MergeSelectionState,
): MergeSelectionState {
  if (customers.length === 0) {
    return createDefaultMergeSelectionState([], "");
  }

  const customerIds = new Set(customers.map((customer) => customer.id));
  let survivingCustomerId = state.survivingCustomerId;
  if (!customerIds.has(survivingCustomerId)) {
    survivingCustomerId = customers[0]?.id ?? "";
  }

  const scalarSelections = { ...state.scalarSelections };
  for (const field of SCALAR_FIELDS) {
    if (!customerIds.has(scalarSelections[field.key])) {
      scalarSelections[field.key] = survivingCustomerId;
    }
  }

  return {
    survivingCustomerId,
    scalarSelections,
    communicationSelections: sanitizeCommunicationSelections(
      customers,
      state.communicationSelections,
    ),
  };
}

export function countTotalParticipations(customers: DuplicateGroupCustomerDetail[]): number {
  return customers.reduce((total, customer) => total + customer.participations.length, 0);
}

export function countUniqueFairs(customers: DuplicateGroupCustomerDetail[]): number {
  const fairNames = new Set<string>();
  for (const customer of customers) {
    for (const participation of customer.participations) {
      fairNames.add(participation.fair_name);
    }
  }
  return fairNames.size;
}

export function countCustomerCommunicationSelections(
  customer: DuplicateGroupCustomerDetail,
  selections: Set<CommSelectionKey>,
): number {
  let count = 0;
  for (const email of customer.emails) {
    if (selections.has(commSelectionKey(customer.id, email.id))) count += 1;
  }
  for (const phone of customer.phones) {
    if (selections.has(commSelectionKey(customer.id, phone.id))) count += 1;
  }
  for (const website of customer.websites) {
    if (selections.has(commSelectionKey(customer.id, website.id))) count += 1;
  }
  return count;
}

export function shortenCustomerId(value: string): string {
  if (value.length <= 13) return value;
  return `${value.slice(0, 4)}…${value.slice(-4)}`;
}
