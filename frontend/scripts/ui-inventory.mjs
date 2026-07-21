import fs from "fs";
import path from "path";

const root = "src";
const exts = new Set([".tsx", ".ts", ".css"]);
const files = [];

function walk(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) {
      if (e.name === "node_modules" || e.name === "dist") continue;
      walk(p);
    } else if (exts.has(path.extname(e.name))) {
      files.push(p);
    }
  }
}
walk(root);

const counts = {
  button: 0,
  iconButton: 0,
  input: 0,
  textarea: 0,
  select: 0,
  checkbox: 0,
  radio: 0,
  form: 0,
  table: 0,
  Card: 0,
  Modal: 0,
  Drawer: 0,
  EmptyState: 0,
  LoadingState: 0,
  Banner: 0,
  FormModal: 0,
  CheckboxField: 0,
  RadioField: 0,
  SelectInput: 0,
  TextInput: 0,
  TextareaInput: 0,
  PasswordInput: 0,
  UniversalDataTable: 0,
  WidthResponsiveDataTable: 0,
  FilterPanel: 0,
  PageShell: 0,
  PageHeader: 0,
  Pagination: 0,
  PaginationBar: 0,
  ConfirmDialog: 0,
  Tabs: 0,
  Badge: 0,
  classBtn: 0,
};

const re = {
  button: /<button\b/g,
  iconButton: /<IconButton\b/g,
  input: /<input\b/g,
  textarea: /<textarea\b/g,
  select: /<select\b/g,
  checkbox: /type=["']checkbox["']/g,
  radio: /type=["']radio["']/g,
  form: /<form\b/g,
  table: /<table\b/g,
  Card: /<Card\b/g,
  Modal: /<(?:Modal|FormModal)\b/g,
  Drawer: /<Drawer\b/g,
  EmptyState: /<EmptyState\b/g,
  LoadingState: /<LoadingState\b/g,
  Banner: /<Banner\b/g,
  FormModal: /<FormModal\b/g,
  CheckboxField: /<CheckboxField\b/g,
  RadioField: /<RadioField\b/g,
  SelectInput: /<SelectInput\b/g,
  TextInput: /<TextInput\b/g,
  TextareaInput: /<TextareaInput\b/g,
  PasswordInput: /<PasswordInput\b/g,
  UniversalDataTable: /<UniversalDataTable\b/g,
  WidthResponsiveDataTable: /<WidthResponsiveDataTable\b/g,
  FilterPanel: /<FilterPanel\b/g,
  PageShell: /<PageShell\b/g,
  PageHeader: /<PageHeader\b/g,
  Pagination: /<Pagination\b/g,
  PaginationBar: /<PaginationBar\b/g,
  ConfirmDialog: /<ConfirmDialog\b/g,
  Tabs: /<Tabs\b/g,
  Badge: /<Badge\b/g,
  classBtn: /className=["'][^"']*\bbtn\b/g,
};

for (const f of files) {
  const t = fs.readFileSync(f, "utf8");
  for (const [k, r] of Object.entries(re)) {
    const m = t.match(r);
    if (m) counts[k] += m.length;
  }
}

const pages = fs.readdirSync("src/pages").filter((f) => f.endsWith(".tsx"));
console.log(JSON.stringify({ files: files.length, pages: pages.length, counts }, null, 2));
