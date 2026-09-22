import React from "react";
import {
  getFairStandAdminSettings,
  updateFairStandAdminRuntimeSettings,
  updateFairStandAdminStandDimensions,
  type FairStandAdminRuntimeSettings,
  type FairStandAdminStandDimensions,
} from "../api/fairStandAdmin";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { LoadingState } from "../components/ui/LoadingState";
import {
  CheckboxField,
  FormDirtyHost,
  FormField,
  TextInput,
  useReportFormDirty,
} from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import {
  FAIR_STAND_SETTINGS_READ,
  FAIR_STAND_SETTINGS_UPDATE,
  getGrantedFairStandAdminPermissions,
} from "../permissions/fairStandAdminPermissions";

type DimensionsForm = {
  depth_m: string;
  strip_count: string;
  strip_height_m: string;
  frame_width_m: string;
  frame_depth_m: string;
};

type SettingsForm = {
  max_image_upload_mb: string;
  export_button_visible: boolean;
  import_button_visible: boolean;
};

const emptyDimensions: DimensionsForm = {
  depth_m: "",
  strip_count: "",
  strip_height_m: "",
  frame_width_m: "",
  frame_depth_m: "",
};

const emptySettings: SettingsForm = {
  max_image_upload_mb: "",
  export_button_visible: true,
  import_button_visible: true,
};

function FormDirtyReporter<T>({ values, baseline }: { values: T; baseline: T }) {
  useReportFormDirty(values, baseline);
  return null;
}

function round3(value: number): number {
  return Math.round(value * 1000) / 1000;
}

function dimensionsToForm(row: FairStandAdminStandDimensions): DimensionsForm {
  return {
    depth_m: String(row.depth),
    strip_count: String(row.stripCount),
    strip_height_m: String(row.stripHeight),
    frame_width_m: String(row.frameWidth),
    frame_depth_m: String(row.frameDepth),
  };
}

function settingsToForm(row: FairStandAdminRuntimeSettings): SettingsForm {
  return {
    max_image_upload_mb: String(row.maxImageUploadMb),
    export_button_visible: row.exportButtonVisible,
    import_button_visible: row.importButtonVisible,
  };
}

function computedHeight(form: DimensionsForm): number | null {
  const strips = Number(form.strip_count);
  const stripHeight = Number(form.strip_height_m);
  if (!Number.isFinite(strips) || !Number.isFinite(stripHeight) || strips <= 0 || stripHeight <= 0) {
    return null;
  }
  return round3(strips * stripHeight);
}

function parsePositiveNumber(raw: string, label: string): number {
  const value = Number(raw);
  if (!Number.isFinite(value) || value <= 0) {
    throw new Error(`${label} 0'dan büyük bir sayı olmalıdır.`);
  }
  return value;
}

function parsePositiveInt(raw: string, label: string): number {
  const value = Number(raw);
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`${label} 0'dan büyük bir tam sayı olmalıdır.`);
  }
  return value;
}

export function FairStandSettingsAdminPage() {
  const granted = React.useMemo(() => getGrantedFairStandAdminPermissions(), []);
  const canRead = granted.has(FAIR_STAND_SETTINGS_READ);
  const canUpdate = granted.has(FAIR_STAND_SETTINGS_UPDATE);

  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [dimensionsForm, setDimensionsForm] = React.useState<DimensionsForm>(emptyDimensions);
  const [dimensionsBaseline, setDimensionsBaseline] = React.useState<DimensionsForm>(emptyDimensions);
  const [settingsForm, setSettingsForm] = React.useState<SettingsForm>(emptySettings);
  const [settingsBaseline, setSettingsBaseline] = React.useState<SettingsForm>(emptySettings);
  const [savingDimensions, setSavingDimensions] = React.useState(false);
  const [savingSettings, setSavingSettings] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const bundle = await getFairStandAdminSettings();
      const nextDimensions = dimensionsToForm(bundle.standDimensions);
      const nextSettings = settingsToForm(bundle.settings);
      setDimensionsForm(nextDimensions);
      setDimensionsBaseline(nextDimensions);
      setSettingsForm(nextSettings);
      setSettingsBaseline(nextSettings);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Temel ayarlar yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (canRead) void load();
    else setLoading(false);
  }, [canRead, load]);

  const heightM = computedHeight(dimensionsForm);

  const saveDimensions = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canUpdate) return;
    setSavingDimensions(true);
    setError(null);
    setSuccess(null);
    try {
      const stripCount = parsePositiveInt(dimensionsForm.strip_count, "Şerit sayısı");
      const stripHeight = round3(parsePositiveNumber(dimensionsForm.strip_height_m, "Şerit yüksekliği"));
      const height = round3(stripCount * stripHeight);
      const updated = await updateFairStandAdminStandDimensions({
        height_m: height,
        depth_m: round3(parsePositiveNumber(dimensionsForm.depth_m, "Derinlik")),
        strip_count: stripCount,
        strip_height_m: stripHeight,
        frame_width_m: round3(parsePositiveNumber(dimensionsForm.frame_width_m, "Çerçeve genişliği")),
        frame_depth_m: round3(parsePositiveNumber(dimensionsForm.frame_depth_m, "Çerçeve derinliği")),
      });
      const next = dimensionsToForm(updated);
      setDimensionsForm(next);
      setDimensionsBaseline(next);
      setSuccess("Stand zarfı kaydedildi.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Stand zarfı kaydedilemedi.");
    } finally {
      setSavingDimensions(false);
    }
  };

  const saveSettings = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canUpdate) return;
    setSavingSettings(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateFairStandAdminRuntimeSettings({
        max_image_upload_mb: parsePositiveInt(settingsForm.max_image_upload_mb, "Görsel yükleme tavanı"),
        export_button_visible: settingsForm.export_button_visible,
        import_button_visible: settingsForm.import_button_visible,
      });
      const next = settingsToForm(updated);
      setSettingsForm(next);
      setSettingsBaseline(next);
      setSuccess("Runtime ayarları kaydedildi.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Runtime ayarları kaydedilemedi.");
    } finally {
      setSavingSettings(false);
    }
  };

  if (!canRead) {
    return (
      <PageShell>
        <PageHeader title="Temel Ayarlar" subtitle="Fair Stand zarfı ve runtime ayarları." />
        <EmptyState
          title="Yetki yok"
          description="Bu ekranı görüntülemek için Fair Stand temel ayar okuma yetkisi gerekir."
        />
      </PageShell>
    );
  }

  return (
    <PageShell className="fair-stand-settings-admin-page">
      <PageHeader
        title="Temel Ayarlar"
        subtitle="Stand zarfı ve runtime ayarları. Yalnız güncelleme; oluşturma/silme yok."
      />
      {error ? <Banner variant="error">{error}</Banner> : null}
      {success ? <Banner variant="success">{success}</Banner> : null}
      {loading ? <LoadingState /> : null}

      {!loading ? (
        <>
          <section aria-labelledby="fair-stand-dimensions-heading">
            <PageHeader title="Stand zarfı" subtitle="Tavan yüksekliği = şerit sayısı × şerit yüksekliği." />
            <h2 id="fair-stand-dimensions-heading" className="sr-only">
              Stand zarfı
            </h2>
            <FormDirtyHost
              onClose={() => {
                setDimensionsForm(dimensionsBaseline);
              }}
            >
              <FormDirtyReporter values={dimensionsForm} baseline={dimensionsBaseline} />
              <form className="crm-form" onSubmit={(event) => void saveDimensions(event)}>
                <FormField label="Şerit sayısı" htmlFor="fs-strip-count" required>
                  <TextInput
                    id="fs-strip-count"
                    type="number"
                    min={1}
                    step={1}
                    value={dimensionsForm.strip_count}
                    disabled={!canUpdate || savingDimensions}
                    onChange={(event) =>
                      setDimensionsForm((current) => ({ ...current, strip_count: event.target.value }))
                    }
                    required
                  />
                </FormField>
                <FormField label="Şerit yüksekliği (m)" htmlFor="fs-strip-height" required>
                  <TextInput
                    id="fs-strip-height"
                    type="number"
                    min={0.001}
                    step={0.001}
                    value={dimensionsForm.strip_height_m}
                    disabled={!canUpdate || savingDimensions}
                    onChange={(event) =>
                      setDimensionsForm((current) => ({
                        ...current,
                        strip_height_m: event.target.value,
                      }))
                    }
                    required
                  />
                </FormField>
                <FormField
                  label="Tavan yüksekliği (m)"
                  htmlFor="fs-height"
                  hint="Şerit sayısı × şerit yüksekliği"
                >
                  <TextInput
                    id="fs-height"
                    type="number"
                    value={heightM == null ? "" : String(heightM)}
                    disabled
                    readOnly
                  />
                </FormField>
                <FormField label="Duvar kalınlığı / derinlik (m)" htmlFor="fs-depth" required>
                  <TextInput
                    id="fs-depth"
                    type="number"
                    min={0.001}
                    step={0.001}
                    value={dimensionsForm.depth_m}
                    disabled={!canUpdate || savingDimensions}
                    onChange={(event) =>
                      setDimensionsForm((current) => ({ ...current, depth_m: event.target.value }))
                    }
                    required
                  />
                </FormField>
                <FormField label="Çerçeve genişliği (m)" htmlFor="fs-frame-width" required>
                  <TextInput
                    id="fs-frame-width"
                    type="number"
                    min={0.001}
                    step={0.001}
                    value={dimensionsForm.frame_width_m}
                    disabled={!canUpdate || savingDimensions}
                    onChange={(event) =>
                      setDimensionsForm((current) => ({
                        ...current,
                        frame_width_m: event.target.value,
                      }))
                    }
                    required
                  />
                </FormField>
                <FormField label="Çerçeve derinliği (m)" htmlFor="fs-frame-depth" required>
                  <TextInput
                    id="fs-frame-depth"
                    type="number"
                    min={0.001}
                    step={0.001}
                    value={dimensionsForm.frame_depth_m}
                    disabled={!canUpdate || savingDimensions}
                    onChange={(event) =>
                      setDimensionsForm((current) => ({
                        ...current,
                        frame_depth_m: event.target.value,
                      }))
                    }
                    required
                  />
                </FormField>
                {canUpdate ? (
                  <div className="form-actions">
                    <Button type="submit" loading={savingDimensions}>
                      Zarfı kaydet
                    </Button>
                  </div>
                ) : null}
              </form>
            </FormDirtyHost>
          </section>

          <section aria-labelledby="fair-stand-runtime-heading">
            <PageHeader
              title="Runtime"
              subtitle="Görsel yükleme tavanı ve arşiv buton görünürlüğü."
            />
            <h2 id="fair-stand-runtime-heading" className="sr-only">
              Runtime
            </h2>
            <FormDirtyHost
              onClose={() => {
                setSettingsForm(settingsBaseline);
              }}
            >
              <FormDirtyReporter values={settingsForm} baseline={settingsBaseline} />
              <form className="crm-form" onSubmit={(event) => void saveSettings(event)}>
                <FormField label="Görsel yükleme tavanı (MB)" htmlFor="fs-max-upload" required>
                  <TextInput
                    id="fs-max-upload"
                    type="number"
                    min={1}
                    step={1}
                    value={settingsForm.max_image_upload_mb}
                    disabled={!canUpdate || savingSettings}
                    onChange={(event) =>
                      setSettingsForm((current) => ({
                        ...current,
                        max_image_upload_mb: event.target.value,
                      }))
                    }
                    required
                  />
                </FormField>
                <CheckboxField
                  id="fs-export-visible"
                  label="Dışarı Aktar butonu görünür"
                  checked={settingsForm.export_button_visible}
                  disabled={!canUpdate || savingSettings}
                  onChange={(checked) =>
                    setSettingsForm((current) => ({
                      ...current,
                      export_button_visible: checked,
                    }))
                  }
                />
                <CheckboxField
                  id="fs-import-visible"
                  label="İçe Aktar butonu görünür"
                  checked={settingsForm.import_button_visible}
                  disabled={!canUpdate || savingSettings}
                  onChange={(checked) =>
                    setSettingsForm((current) => ({
                      ...current,
                      import_button_visible: checked,
                    }))
                  }
                />
                {canUpdate ? (
                  <div className="form-actions">
                    <Button type="submit" loading={savingSettings}>
                      Runtime kaydet
                    </Button>
                  </div>
                ) : null}
              </form>
            </FormDirtyHost>
          </section>
        </>
      ) : null}
    </PageShell>
  );
}
