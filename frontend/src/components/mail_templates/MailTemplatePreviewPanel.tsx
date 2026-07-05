import React from "react";
import { adminLabels } from "../../labels/adminLabels";
import { FormField, FormSection, TextareaInput } from "../ui/form";
import type { RenderMailTemplateResponse } from "../../types/mailTemplates";
import {
  DEFAULT_RENDER_VARIABLES_JSON,
  parseRenderVariablesJson,
} from "../../utils/mailTemplateForm";

interface MailTemplatePreviewPanelProps {
  variablesJson: string;
  onVariablesJsonChange: (value: string) => void;
  rendering: boolean;
  error: string | null;
  result: RenderMailTemplateResponse | null;
  onRender: (variables: Record<string, unknown>) => Promise<void>;
  canRender: boolean;
}

export function MailTemplatePreviewPanel({
  variablesJson,
  onVariablesJsonChange,
  rendering,
  error,
  result,
  onRender,
  canRender,
}: MailTemplatePreviewPanelProps) {
  const [localError, setLocalError] = React.useState<string | null>(null);

  const handleRender = async () => {
    setLocalError(null);
    try {
      const variables = parseRenderVariablesJson(variablesJson);
      await onRender(variables ?? {});
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : adminLabels.mailTemplatesRenderError);
    }
  };

  return (
    <div className="mail-template-preview-panel">
      <FormSection title={adminLabels.mailTemplatesSectionPreview}>
        <FormField label={adminLabels.mailTemplatesFieldSampleVariables} htmlFor="mail-template-sample-vars" fullWidth>
          <TextareaInput
            id="mail-template-sample-vars"
            value={variablesJson}
            onChange={(event) => onVariablesJsonChange(event.target.value)}
            rows={8}
            placeholder={DEFAULT_RENDER_VARIABLES_JSON}
          />
        </FormField>

        {localError || error ? (
          <div className="banner error">{localError ?? error}</div>
        ) : null}

        {canRender ? (
          <div className="mail-template-preview-actions">
            <button
              type="button"
              className="btn secondary"
              disabled={rendering}
              onClick={() => void handleRender()}
            >
              {rendering ? adminLabels.mailTemplatesRenderRunning : adminLabels.mailTemplatesRenderAction}
            </button>
          </div>
        ) : null}

        {result ? (
          <div className="mail-template-preview-output">
            <div className="mail-template-preview-block">
              <h4>{adminLabels.mailTemplatesRenderedSubject}</h4>
              <pre className="mail-template-preview-text">{result.subject}</pre>
            </div>

            {result.body_text ? (
              <div className="mail-template-preview-block">
                <h4>{adminLabels.mailTemplatesRenderedBodyText}</h4>
                <pre className="mail-template-preview-text">{result.body_text}</pre>
              </div>
            ) : null}

            {result.body_html ? (
              <div className="mail-template-preview-block">
                <h4>{adminLabels.mailTemplatesRenderedBodyHtml}</h4>
                <iframe
                  className="mail-template-html-preview"
                  title={adminLabels.mailTemplatesRenderedBodyHtml}
                  sandbox=""
                  srcDoc={result.body_html}
                />
              </div>
            ) : null}
          </div>
        ) : null}
      </FormSection>
    </div>
  );
}
