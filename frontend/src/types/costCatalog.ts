export type CostUnit = "Adet" | "Kg" | "m²" | "Metre" | "Gün" | "Saat";
export type CostCurrency = "TL" | "USD";

export interface CostCategory {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface CostCategoryPayload { name: string; slug: string; description: string | null; }
export interface CostCategoryOption { id: string; name: string; }

export interface CostProduct {
  id: string;
  organization_id: string;
  category_id: string;
  category_name: string;
  name: string;
  slug: string;
  unit: CostUnit;
  unit_price: string;
  currency: CostCurrency;
  created_at: string;
  updated_at: string;
}

export interface CostProductPayload {
  category_id: string;
  name: string;
  slug: string;
  unit: CostUnit;
  unit_price: string;
  currency: CostCurrency;
}
