import type {
  DuplicateGroupCustomerDetail,
  DuplicateGroupMergePreviewRequest,
} from "../../types/dataOperations";
import { commSelectionKey, parseCommSelectionKey, type MergeSelectionState } from "./mergeSelectionState";

interface ValidCommunicationRowIds {
  emailIds: Set<string>;
  phoneIds: Set<string>;
  websiteIds: Set<string>;
}

function collectValidCommunicationRowIds(
  customers: DuplicateGroupCustomerDetail[],
): ValidCommunicationRowIds {
  const emailIds = new Set<string>();
  const phoneIds = new Set<string>();
  const websiteIds = new Set<string>();

  for (const customer of customers) {
    for (const email of customer.emails) {
      emailIds.add(email.id);
    }
    for (const phone of customer.phones) {
      phoneIds.add(phone.id);
    }
    for (const website of customer.websites) {
      websiteIds.add(website.id);
    }
  }

  return { emailIds, phoneIds, websiteIds };
}

function selectedCommunicationIdsByChannel(
  customers: DuplicateGroupCustomerDetail[],
  selections: Set<string>,
): {
  emailIds: string[];
  phoneIds: string[];
  websiteIds: string[];
} {
  const channelByKey = new Map<string, "email" | "phone" | "website">();
  for (const customer of customers) {
    for (const email of customer.emails) {
      channelByKey.set(commSelectionKey(customer.id, email.id), "email");
    }
    for (const phone of customer.phones) {
      channelByKey.set(commSelectionKey(customer.id, phone.id), "phone");
    }
    for (const website of customer.websites) {
      channelByKey.set(commSelectionKey(customer.id, website.id), "website");
    }
  }

  const validRowIds = collectValidCommunicationRowIds(customers);
  const emailIds: string[] = [];
  const phoneIds: string[] = [];
  const websiteIds: string[] = [];
  const seenEmailIds = new Set<string>();
  const seenPhoneIds = new Set<string>();
  const seenWebsiteIds = new Set<string>();

  for (const key of selections) {
    const channel = channelByKey.get(key);
    if (!channel) continue;
    const { rowId } = parseCommSelectionKey(key);
    if (channel === "email") {
      if (!validRowIds.emailIds.has(rowId) || seenEmailIds.has(rowId)) continue;
      seenEmailIds.add(rowId);
      emailIds.push(rowId);
    }
    if (channel === "phone") {
      if (!validRowIds.phoneIds.has(rowId) || seenPhoneIds.has(rowId)) continue;
      seenPhoneIds.add(rowId);
      phoneIds.push(rowId);
    }
    if (channel === "website") {
      if (!validRowIds.websiteIds.has(rowId) || seenWebsiteIds.has(rowId)) continue;
      seenWebsiteIds.add(rowId);
      websiteIds.push(rowId);
    }
  }

  return { emailIds, phoneIds, websiteIds };
}

export function buildMergePreviewRequest(
  runId: string,
  state: MergeSelectionState,
  customers: DuplicateGroupCustomerDetail[],
): DuplicateGroupMergePreviewRequest {
  const { emailIds, phoneIds, websiteIds } = selectedCommunicationIdsByChannel(
    customers,
    state.communicationSelections,
  );

  return {
    run_id: runId,
    surviving_customer_id: state.survivingCustomerId,
    scalar_selections: {
      company_name: state.scalarSelections.company_name,
      legal_name: state.scalarSelections.legal_name,
      trade_name: state.scalarSelections.trade_name,
      city: state.scalarSelections.city,
      country: state.scalarSelections.country,
    },
    selected_email_ids: emailIds,
    selected_phone_ids: phoneIds,
    selected_website_ids: websiteIds,
  };
}
