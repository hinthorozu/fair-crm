/**
 * Exhaustive UI consumer inventory with file:line evidence.
 */
import fs from "fs";
import path from "path";

const ROOT = "src";
const OUT = "reports/full-ui-evidence";
fs.mkdirSync(OUT, { recursive: true });

const files = [];
function walk(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) {
      if (e.name === "node_modules" || e.name === "dist") continue;
      walk(p);
    } else if (/\.(tsx|ts)$/.test(e.name) && !e.name.endsWith(".d.ts")) files.push(p);
  }
}
walk(ROOT);

const patterns = [
  { kind: "form", re: /<form\b/g, ds: "crm-form / FormModal" },
  { kind: "FormModal", re: /<FormModal\b/g, ds: "FormModal" },
  { kind: "button", re: /<button\b/g, ds: ".btn / Button / IconButton / specialty chrome" },
  { kind: "Button", re: /<Button\b/g, ds: "Button" },
  { kind: "IconButton", re: /<IconButton\b/g, ds: "IconButton" },
  { kind: "TextInput", re: /<TextInput\b/g, ds: "TextInput" },
  { kind: "PasswordInput", re: /<PasswordInput\b/g, ds: "PasswordInput" },
  { kind: "TextareaInput", re: /<TextareaInput\b/g, ds: "TextareaInput" },
  { kind: "SelectInput", re: /<SelectInput\b/g, ds: "SelectInput" },
  { kind: "CheckboxField", re: /<CheckboxField\b/g, ds: "CheckboxField" },
  { kind: "RadioField", re: /<RadioField\b/g, ds: "RadioField" },
  { kind: "raw_input", re: /<input\b/g, ds: "raw <input> (inspect)" },
  { kind: "raw_textarea", re: /<textarea\b/g, ds: "raw <textarea>" },
  { kind: "raw_select", re: /<select\b/g, ds: "raw <select>" },
  { kind: "UniversalDataTable", re: /<UniversalDataTable\b/g, ds: "UniversalDataTable" },
  { kind: "WidthResponsiveDataTable", re: /<WidthResponsiveDataTable\b/g, ds: "WidthResponsiveDataTable" },
  { kind: "raw_table", re: /<table\b/g, ds: "raw <table>" },
  { kind: "Card", re: /<Card\b/g, ds: "Card" },
  { kind: "Modal", re: /<(?:Modal|FormModal|ConfirmDialog)\b/g, ds: "Modal family" },
  { kind: "Drawer", re: /<Drawer\b/g, ds: "Drawer" },
  { kind: "FilterPanel", re: /<FilterPanel\b/g, ds: "FilterPanel" },
  { kind: "PaginationBar", re: /<PaginationBar\b/g, ds: "PaginationBar" },
  { kind: "Banner", re: /<Banner\b/g, ds: "Banner" },
  { kind: "LoadingState", re: /<LoadingState\b/g, ds: "LoadingState" },
  { kind: "EmptyState", re: /<EmptyState\b/g, ds: "EmptyState" },
  { kind: "AdapterSelect", re: /<AdapterSelect\b/g, ds: "specialty combobox" },
  { kind: "FairEntitySelect", re: /<FairEntitySelect\b/g, ds: "specialty combobox" },
];

const rows = [];
const summary = {};

for (const file of files) {
  const text = fs.readFileSync(file, "utf8");
  const lines = text.split(/\r?\n/);
  for (const { kind, re, ds } of patterns) {
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      re.lastIndex = 0;
      if (!re.test(line)) continue;
      // Skip definition sites for primitives when counting consumers roughly
      const isDef =
        (kind === "CheckboxField" || kind === "RadioField" || kind === "TextInput") &&
        file.includes(`${path.sep}form${path.sep}FormInputs.tsx`);
      const specialty =
        kind.startsWith("raw_") ||
        kind === "AdapterSelect" ||
        kind === "FairEntitySelect" ||
        (kind === "button" && !/\bbtn\b/.test(line) && !line.includes("IconButton"));
      rows.push({
        kind,
        file: file.replace(/\\/g, "/"),
        line: i + 1,
        ds,
        specialty: Boolean(specialty && !isDef),
        snippet: line.trim().slice(0, 140),
        defSite: isDef,
      });
      summary[kind] = (summary[kind] || 0) + 1;
    }
  }
}

fs.writeFileSync(path.join(OUT, "consumer-raw.json"), JSON.stringify({ summary, rows }, null, 2));

// Aggregate summary table
const groups = {
  forms: ["form", "FormModal"],
  buttons: ["button", "Button"],
  iconButtons: ["IconButton"],
  inputs: ["TextInput", "PasswordInput", "raw_input"],
  textareas: ["TextareaInput", "raw_textarea"],
  selects: ["SelectInput", "raw_select"],
  comboboxes: ["AdapterSelect", "FairEntitySelect"],
  checkbox: ["CheckboxField"],
  radio: ["RadioField"],
  switch: [],
  tables: ["UniversalDataTable", "WidthResponsiveDataTable", "raw_table"],
  cards: ["Card"],
  modals: ["Modal"],
  drawers: ["Drawer"],
  toolbars: ["FilterPanel"],
  pagination: ["PaginationBar"],
  banners: ["Banner"],
  loadingStates: ["LoadingState"],
  emptyStates: ["EmptyState"],
};

const specialtyAllow = new Set([
  "src/components/ui/form/FormInputs.tsx", // implements checkbox/radio
  "src/components/AdapterSelect.tsx",
  "src/components/FairEntitySelect.tsx",
  "src/pages/ImportWizardPage.tsx",
  "src/components/imports/ExcelMappingGrid.tsx",
]);

let md = [
  "# UI_CONSUMER_INVENTORY",
  "",
  "Source scan of `src/**/*.{ts,tsx}`. Counts are JSX/tag occurrences.",
  "",
  "| Tür | Toplam consumer | Design system altında | Specialty | NOT VERIFIED |",
  "|---|---:|---:|---:|---:|",
];

const detail = ["", "## Consumer detail", ""];

for (const [label, kinds] of Object.entries(groups)) {
  const subset = rows.filter((r) => kinds.includes(r.kind) && !r.defSite);
  const specialty = subset.filter((r) => r.specialty);
  const ds = subset.length - specialty.length;
  // Verification status filled later by visual QA script; mark specialty as pending until QA
  md.push(`| ${label} | ${subset.length} | ${ds} | ${specialty.length} | PENDING |`);
  detail.push(`### ${label} (${subset.length})`, "");
  for (const r of subset) {
    detail.push(
      `- \`${r.file}:${r.line}\` — **${r.kind}** — ds=\`${r.ds}\`${r.specialty ? " — SPECIALTY" : ""} — \`${r.snippet.replace(/`/g, "'")}\``,
    );
  }
  detail.push("");
}

fs.writeFileSync(path.join(OUT, "UI_CONSUMER_INVENTORY.md"), md.join("\n") + "\n" + detail.join("\n"));
console.log(JSON.stringify(summary, null, 2));
console.log(`Wrote ${path.join(OUT, "UI_CONSUMER_INVENTORY.md")} rows=${rows.length}`);
