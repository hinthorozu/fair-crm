import React from "react";
import { ColorInput, TextInput } from "../ui/form";

function colorIntToHex(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const n = Number(trimmed);
  if (!Number.isInteger(n) || n < 0 || n > 0xffffff) return null;
  return `#${n.toString(16).padStart(6, "0").toUpperCase()}`;
}

function hexToColorIntString(raw: string): string | null {
  const cleaned = raw.trim().replace(/^#/, "");
  if (!cleaned) return "";
  if (!/^[0-9a-fA-F]{6}$/.test(cleaned)) return null;
  return String(parseInt(cleaned, 16));
}

export type FairStandDefaultColorFieldProps = {
  id: string;
  value: string;
  disabled?: boolean;
  onChange: (nextIntString: string) => void;
};

/** Admin Item varsayılan renk: swatch (native picker + damlalık) + HEX; form değeri hex-int string. */
export function FairStandDefaultColorField({
  id,
  value,
  disabled = false,
  onChange,
}: FairStandDefaultColorFieldProps) {
  const hexFromInt = colorIntToHex(value);
  const [hexDraft, setHexDraft] = React.useState(hexFromInt ?? "");
  const pickerValue = hexFromInt ?? "#FFFFFF";

  React.useEffect(() => {
    setHexDraft(hexFromInt ?? "");
  }, [hexFromInt]);

  const commitHex = (raw: string) => {
    const next = hexToColorIntString(raw);
    if (next === null) {
      setHexDraft(hexFromInt ?? "");
      return;
    }
    onChange(next);
    setHexDraft(next === "" ? "" : colorIntToHex(next) ?? "");
  };

  return (
    <div className="fair-stand-default-color-field">
      <ColorInput
        id={id}
        className="fair-stand-default-color-field__swatch"
        value={pickerValue}
        disabled={disabled}
        title="Renk seç / damlalık"
        aria-label="Renk seçici"
        onChange={(event) => {
          const next = hexToColorIntString(event.target.value);
          if (next === null || next === "") return;
          onChange(next);
          setHexDraft(colorIntToHex(next) ?? event.target.value.toUpperCase());
        }}
      />
      <TextInput
        id={`${id}-hex`}
        className="fair-stand-default-color-field__hex"
        value={hexDraft}
        disabled={disabled}
        placeholder="#FFFFFF"
        maxLength={7}
        spellCheck={false}
        autoComplete="off"
        aria-label="HEX"
        onChange={(event) => {
          const raw = event.target.value;
          setHexDraft(raw);
          if (/^#?[0-9a-fA-F]{6}$/.test(raw.trim())) {
            const next = hexToColorIntString(raw);
            if (next !== null) onChange(next);
          }
        }}
        onBlur={() => commitHex(hexDraft)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            commitHex(hexDraft);
            (event.target as HTMLInputElement).blur();
          }
        }}
      />
    </div>
  );
}
