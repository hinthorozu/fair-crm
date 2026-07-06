import React from "react";
import { DetailValue, formatDetailDate } from "../ui/DetailFields";
import { scraperLabels } from "../../labels/scraperLabels";
import type { AdapterEngine, RequestedOutputField } from "../../types/scraper";
import {
  DYNAMIC_ENGINE_VALUE,
  type AdapterFormMetadata,
  type AdapterFormState,
} from "../../utils/adapterManifestForm";
import { OutputFieldsSection, toggleRequestedFieldSelection } from "./OutputFieldsSection";

export type AdapterFormMode = "create" | "edit" | "readOnly";

export interface AdapterFormProps {
  mode: AdapterFormMode;
  values: AdapterFormState;
  onChange: (updater: (current: AdapterFormState) => AdapterFormState) => void;
  capabilities: Record<RequestedOutputField, boolean> | null;
  metadata?: AdapterFormMetadata;
  engines?: AdapterEngine[];
  enginesLoading?: boolean;
  enginesError?: string | null;
  className?: string;
}

function ManifestField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </>
  );
}

function readOnlyBoolean(value: boolean): string {
  return value ? "Evet" : "Hayır";
}

export function AdapterForm({
  mode,
  values,
  onChange,
  capabilities,
  metadata,
  engines = [],
  enginesLoading = false,
  enginesError = null,
  className = "detail-grid adapter-manifest-fields",
}: AdapterFormProps) {
  const readOnly = mode === "readOnly";
  const showEngineSelect = mode === "create";

  const setField = <K extends keyof AdapterFormState>(key: K, value: AdapterFormState[K]) => {
    if (readOnly) return;
    onChange((current) => ({ ...current, [key]: value }));
  };

  const toggleRequestedField = (field: RequestedOutputField, enabled: boolean) => {
    if (readOnly) return;
    onChange((current) => ({
      ...current,
      requested_fields: toggleRequestedFieldSelection(current.requested_fields, field, enabled),
    }));
  };

  const engineReadOnlyValue =
    mode === "create"
      ? values.engine_selection === DYNAMIC_ENGINE_VALUE
        ? scraperLabels.formEngineDynamic
        : values.engine_selection
      : metadata?.adapter_key ?? values.engine_selection;

  return (
    <dl className={className}>
      <ManifestField
        label={scraperLabels.formEngine}
        value={
          showEngineSelect ? (
            <>
              <select
                className="input"
                value={values.engine_selection}
                onChange={(event) => setField("engine_selection", event.target.value)}
                disabled={enginesLoading || readOnly}
              >
                <option value={DYNAMIC_ENGINE_VALUE}>{scraperLabels.formEngineDynamic}</option>
                {engines.map((engine) => (
                  <option key={engine.engine_key} value={engine.engine_key}>
                    {engine.display_name} - {engine.engine_key}
                  </option>
                ))}
              </select>
              {enginesLoading ? (
                <p className="form-hint text-muted">{scraperLabels.formEngineLoading}</p>
              ) : null}
              {enginesError ? <p className="form-error">{enginesError}</p> : null}
              {values.engine_selection === DYNAMIC_ENGINE_VALUE ? (
                <p className="form-hint">{scraperLabels.formEngineDynamicHint}</p>
              ) : null}
            </>
          ) : (
            <DetailValue value={engineReadOnlyValue} />
          )
        }
      />

      <ManifestField
        label={scraperLabels.formAdapterName}
        value={
          readOnly ? (
            <DetailValue value={values.display_name} />
          ) : (
            <input
              className="input"
              type="text"
              value={values.display_name}
              onChange={(event) => setField("display_name", event.target.value)}
              required
              maxLength={255}
            />
          )
        }
      />

      <ManifestField
        label={scraperLabels.colVersion}
        value={
          readOnly ? (
            <DetailValue value={values.version} />
          ) : (
            <input
              className="input"
              value={values.version}
              onChange={(event) => setField("version", event.target.value)}
              maxLength={50}
            />
          )
        }
      />

      <ManifestField
        label={scraperLabels.colLastVerified}
        value={
          readOnly ? (
            formatDetailDate(values.last_verified || null)
          ) : (
            <input
              className="input"
              type="date"
              value={values.last_verified}
              onChange={(event) => setField("last_verified", event.target.value)}
            />
          )
        }
      />

      {metadata?.author ? (
        <ManifestField label="Author" value={<DetailValue value={metadata.author} />} />
      ) : null}

      {metadata?.scraper_version ? (
        <ManifestField label="Scraper Version" value={<DetailValue value={metadata.scraper_version} />} />
      ) : null}

      <ManifestField
        label={scraperLabels.manifestSites}
        value={
          readOnly ? (
            values.supported_sites.trim() ? (
              <ul className="detail-collection-list">
                {values.supported_sites
                  .split(/\n+/)
                  .map((site) => site.trim())
                  .filter(Boolean)
                  .map((site) => (
                    <li key={site}>{site}</li>
                  ))}
              </ul>
            ) : (
              "—"
            )
          ) : (
            <textarea
              className="input"
              rows={3}
              value={values.supported_sites}
              onChange={(event) => setField("supported_sites", event.target.value)}
            />
          )
        }
      />

      <ManifestField
        label={scraperLabels.manifestNotes}
        value={
          readOnly ? (
            <DetailValue value={values.notes} />
          ) : (
            <textarea
              className="input"
              rows={3}
              value={values.notes}
              onChange={(event) => setField("notes", event.target.value)}
              maxLength={5000}
            />
          )
        }
      />

      <ManifestField
        label={scraperLabels.manifestOutput}
        value={
          readOnly ? (
            `JSON: ${readOnlyBoolean(values.output_json_handoff)}, Excel: ${readOnlyBoolean(values.output_excel)}`
          ) : (
            <div className="adapter-manifest-checkboxes">
              <label>
                <input
                  type="checkbox"
                  checked={values.output_json_handoff}
                  onChange={(event) => setField("output_json_handoff", event.target.checked)}
                />{" "}
                JSON Handoff
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={values.output_excel}
                  onChange={(event) => setField("output_excel", event.target.checked)}
                />{" "}
                Excel
              </label>
            </div>
          )
        }
      />

      <ManifestField
        label={scraperLabels.manifestBrowser}
        value={
          readOnly ? (
            `JS: ${readOnlyBoolean(values.browser_requires_js)}, Playwright: ${readOnlyBoolean(values.browser_requires_playwright)}`
          ) : (
            <div className="adapter-manifest-checkboxes">
              <label>
                <input
                  type="checkbox"
                  checked={values.browser_requires_js}
                  onChange={(event) => setField("browser_requires_js", event.target.checked)}
                />{" "}
                JS
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={values.browser_requires_playwright}
                  onChange={(event) => setField("browser_requires_playwright", event.target.checked)}
                />{" "}
                Playwright
              </label>
            </div>
          )
        }
      />

      <ManifestField
        label={scraperLabels.manifestOutputFields}
        value={
          <OutputFieldsSection
            requestedFields={values.requested_fields}
            capabilities={capabilities}
            readOnly={readOnly}
            onChange={readOnly ? undefined : toggleRequestedField}
          />
        }
      />
    </dl>
  );
}
