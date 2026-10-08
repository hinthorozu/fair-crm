import JSZip from "jszip";
import { standProjectCostLabels } from "../labels/standProjectsLabels";
import type { CostSheetRow, CostTotals } from "./standProjectCost";

export type CostWorkbookCell = string | number;

const HEADERS: string[] = [
  standProjectCostLabels.colSource,
  standProjectCostLabels.colName,
  standProjectCostLabels.colQuantity,
  standProjectCostLabels.colUnit,
  standProjectCostLabels.colPurchaseUnit,
  standProjectCostLabels.colPurchaseTotal,
  standProjectCostLabels.colSaleUnit,
  standProjectCostLabels.colSaleTotal,
];

function sourceLabel(source: CostSheetRow["source"]): string {
  return source === "BOM" ? standProjectCostLabels.sourceBom : standProjectCostLabels.sourceManual;
}

function priceCell(value: number | null): CostWorkbookCell {
  return value == null ? standProjectCostLabels.missingPrice : value;
}

function totalCell(value: number | null): CostWorkbookCell {
  return value == null ? standProjectCostLabels.noTotal : value;
}

function quantityCell(value: number | null): CostWorkbookCell {
  return value == null ? standProjectCostLabels.noTotal : value;
}

export function costSheetExportRows(rows: CostSheetRow[], totals: CostTotals): CostWorkbookCell[][] {
  const body = rows.map((row) => [
    sourceLabel(row.source),
    row.name,
    quantityCell(row.quantity),
    row.unitLabel,
    priceCell(row.purchaseUnit),
    totalCell(row.purchaseTotal),
    priceCell(row.saleUnit),
    totalCell(row.saleTotal),
  ]);
  const band: Array<[string, number]> = [
    [standProjectCostLabels.bandBomPurchase, totals.bomPurchase],
    [standProjectCostLabels.bandBomSale, totals.bomSale],
    [standProjectCostLabels.bandManualPurchase, totals.manualPurchase],
    [standProjectCostLabels.bandManualSale, totals.manualSale],
    [standProjectCostLabels.bandGrandPurchase, totals.grandPurchase],
    [standProjectCostLabels.bandGrandSale, totals.grandSale],
  ];
  return [
    HEADERS,
    ...body,
    [],
    ...band.map(([label, amount]) => [label, amount]),
  ];
}

export function costWorkbookFileName(projectName: string): string {
  const cleaned = projectName.replace(/[<>:"/\\|?*\u0000-\u001f]/g, " ").replace(/\s+/g, " ").trim();
  return `${cleaned || "maliyet"} - maliyet.xlsx`;
}

function columnName(index: number): string {
  let name = "";
  let current = index + 1;
  while (current > 0) {
    const remainder = (current - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    current = Math.floor((current - 1) / 26);
  }
  return name;
}

function xmlEscape(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function cellXml(value: CostWorkbookCell, ref: string): string {
  if (typeof value === "number" && Number.isFinite(value)) {
    return `<c r="${ref}"><v>${value}</v></c>`;
  }
  return `<c r="${ref}" t="inlineStr"><is><t xml:space="preserve">${xmlEscape(String(value))}</t></is></c>`;
}

function sheetXml(rows: CostWorkbookCell[][]): string {
  const xmlRows = rows.map((row, rowIndex) => {
    const cells = row.map((value, columnIndex) => cellXml(value, `${columnName(columnIndex)}${rowIndex + 1}`)).join("");
    return `<row r="${rowIndex + 1}">${cells}</row>`;
  }).join("");
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>${xmlRows}</sheetData></worksheet>`;
}

export async function buildStandProjectCostWorkbook(rows: CostSheetRow[], totals: CostTotals): Promise<Blob> {
  const zip = new JSZip();
  zip.file("[Content_Types].xml", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>`);
  zip.file("_rels/.rels", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>`);
  zip.file("xl/workbook.xml", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Maliyet" sheetId="1" r:id="rId1"/></sheets>
</workbook>`);
  zip.file("xl/_rels/workbook.xml.rels", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>`);
  zip.file("xl/worksheets/sheet1.xml", sheetXml(costSheetExportRows(rows, totals)));
  return zip.generateAsync({
    type: "blob",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}
