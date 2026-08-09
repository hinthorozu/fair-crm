export interface QuoteSelectedItem { content_id: string; value: string }
export interface Quote {
  id: string; organization_id: string; todo_id: string; customer_id: string; fair_id: string;
  template_id: string; quote_date: string; status: "draft" | "given"; price: string;
  selected_items: QuoteSelectedItem[]; created_at: string; updated_at: string;
}
export interface QuotePayload { template_id: string; quote_date: string; status: "draft" | "given"; price: string; selected_items: QuoteSelectedItem[] }
