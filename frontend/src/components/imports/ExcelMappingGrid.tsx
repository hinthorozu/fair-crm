import React from "react";
import { GRID_MAPPING_FIELD_OPTIONS } from "../../utils/outputFieldDefinitions";

export interface ExcelGridColumn {
  index: number;
  letter: string;
  header: string | null;
}

export interface ExcelMappingGridProps {
  columns: ExcelGridColumn[];
  rows: unknown[][];
  columnFieldMap: Record<number, string>;
  onColumnFieldChange: (columnIndex: number, field: string) => void;
  totalDataRows?: number;
  previewRowCount?: number;
}

export function ExcelMappingGrid({
  columns,
  rows,
  columnFieldMap,
  onColumnFieldChange,
  totalDataRows,
  previewRowCount,
}: ExcelMappingGridProps) {
  const usedFields = new Set(
    Object.entries(columnFieldMap)
      .filter(([, field]) => field && field !== "")
      .map(([, field]) => field),
  );

  return (
    <div className="excel-mapping-grid-wrap">
      {(totalDataRows != null || previewRowCount != null) && (
        <p className="text-muted excel-mapping-grid-meta">
          {previewRowCount != null && `${previewRowCount} satır önizleniyor`}
          {totalDataRows != null && previewRowCount != null && " · "}
          {totalDataRows != null && `Toplam ${totalDataRows} veri satırı`}
        </p>
      )}
      <div className="table-wrap table-wrap--scroll-only excel-mapping-grid-scroll">
        <table className="data-table excel-mapping-grid">
          <thead>
            <tr>
              <th className="excel-mapping-row-num">#</th>
              {columns.map((col) => {
                const selected = columnFieldMap[col.index] ?? "";
                return (
                  <th key={col.index} className="excel-mapping-col-header">
                    <div className="excel-mapping-col-label">
                      <span className="excel-mapping-col-letter">{col.letter}</span>
                      {col.header ? <span className="excel-mapping-col-title">{col.header}</span> : null}
                    </div>
                    <select
                      className="form-select excel-mapping-col-select"
                      value={selected}
                      onChange={(e) => onColumnFieldChange(col.index, e.target.value)}
                      aria-label={`Kolon ${col.letter} eşleştirme`}
                    >
                      {GRID_MAPPING_FIELD_OPTIONS.map((opt) => {
                        const disabled =
                          opt.value !== "" &&
                          opt.value !== selected &&
                          usedFields.has(opt.value);
                        return (
                          <option key={opt.value || "ignore"} value={opt.value} disabled={disabled}>
                            {opt.label}
                          </option>
                        );
                      })}
                    </select>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIdx) => (
              <tr key={rowIdx}>
                <td className="excel-mapping-row-num">{rowIdx + 1}</td>
                {columns.map((col) => (
                  <td key={col.index} className="excel-mapping-cell">
                    {row[col.index] == null || row[col.index] === "" ? "—" : String(row[col.index])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function extractFieldMappingsFromColumnConfig(
  columnMappingJson: unknown,
): Record<string, { type: string; value: number }> {
  if (!columnMappingJson || typeof columnMappingJson !== "object") return {};
  const obj = columnMappingJson as Record<string, unknown>;
  if (obj.mappings && typeof obj.mappings === "object" && !Array.isArray(obj.mappings)) {
    return obj.mappings as Record<string, { type: string; value: number }>;
  }
  const mappings: Record<string, { type: string; value: number }> = {};
  for (const [key, value] of Object.entries(obj)) {
    if (
      value &&
      typeof value === "object" &&
      "value" in value &&
      typeof (value as { value: unknown }).value === "number"
    ) {
      mappings[key] = value as { type: string; value: number };
    }
  }
  return mappings;
}

export function columnFieldMapToMappings(
  columnFieldMap: Record<number, string>,
): Record<string, { type: "column_index"; value: number }> {
  const mappings: Record<string, { type: "column_index"; value: number }> = {};
  for (const [colIndex, field] of Object.entries(columnFieldMap)) {
    if (!field) continue;
    mappings[field] = { type: "column_index", value: Number(colIndex) };
  }
  return mappings;
}

export function mappingsToColumnFieldMap(
  mappings: Record<string, { value: number }>,
): Record<number, string> {
  const result: Record<number, string> = {};
  for (const [field, spec] of Object.entries(mappings)) {
    result[spec.value] = field;
  }
  return result;
}

export function isMappingGridValid(columnFieldMap: Record<number, string>): boolean {
  const fields = Object.values(columnFieldMap).filter(Boolean);
  if (!fields.includes("company_name")) return false;
  return new Set(fields).size === fields.length;
}
