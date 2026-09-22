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
import { SectionHeader } from "../components/ui/SectionHeader";
import { TableRowActions } from "../components/ui/TableRowActions";
import {
  CheckboxField,
  FormDirtyHost,
  FormField,
  FormGrid,
  FormModal,
  FormSection,
  TextInput,
  useReportFormDirty,
} from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { adminLabels } from "../labels/adminLabels";
import {
  FAIR_STAND_SETTINGS_READ,
  FAIR_STAND_SETTINGS_UPDATE,
  getGrantedFairStandAdminPermissions,
} from "../permissions/fairStandAdminPermissions";

type DimensionsForm = {
  height_cm: string;
  depth_cm: string;
  frame_width_cm: string;
  frame_depth_cm: string;
};

type SettingsForm = {
  max_image_upload_mb: string;
  export_button_visible: boolean;
  import_button_visible: boolean;
};

type DimensionsRow = FairStandAdminStandDimensions & { id: 1 };
type SettingsRow = FairStandAdminRuntimeSettings & { id: 1 };

function FormDirtyReporter<T>({ values, baseline }: { values: T; baseline: T }) {
  useReportFormDirty(values, baseline);
  return null;
}

function formatCm(cm: number): string {
  return Number.isInteger(cm) ? String(cm) : String(Number(cm.toFixed(3)));
}

function dimensionsToForm(row: FairStandAdminStandDimensions): DimensionsForm {
  return {
    height_cm: formatCm(row.heightCm),
    depth_cm: formatCm(row.depthCm),
    frame_width_cm: formatCm(row.frameWidthCm),
    frame_depth_cm: formatCm(row.frameDepthCm),
  };
}

function settingsToForm(row: FairStandAdminRuntimeSettings): SettingsForm {
  return {
    max_image_upload_mb: String(row.maxImageUploadMb),
    export_button_visible: row.exportButtonVisible,
    import_button_visible: row.importButtonVisible,
  };
}

function parsePositiveNumber(raw: string, label: string): number {
  const value = Number(raw);
  if (!Number.isFinite(value) || value <= 0) {
    throw new Error(adminLabels.fairStandSettingsValidationPositiveNumber.replace("{label}", label));
  }
  return value;
}

function parsePositiveInt(raw: string, label: string): number {
  const value = Number(raw);
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(adminLabels.fairStandSettingsValidationPositiveInt.replace("{label}", label));
  }
  return value;
}

function visibleLabel(value: boolean): string {
  return value ? adminLabels.fairStandSettingsVisibleYes : adminLabels.fairStandSettingsVisibleNo;
}

export function FairStandSettingsAdminPage() {
  const granted = React.useMemo(() => getGrantedFairStandAdminPermissions(), []);
  const canRead = granted.has(FAIR_STAND_SETTINGS_READ);
  const canUpdate = granted.has(FAIR_STAND_SETTINGS_UPDATE);

  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [dimensions, setDimensions] = React.useState<DimensionsRow | null>(null);
  const [settings, setSettings] = React.useState<SettingsRow | null>(null);
  const [dimensionsForm, setDimensionsForm] = React.useState<DimensionsForm | null>(null);
  const [settingsForm, setSettingsForm] = React.useState<SettingsForm | null>(null);
  const [savingDimensions, setSavingDimensions] = React.useState(false);
  const [savingSettings, setSavingSettings] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const bundle = await getFairStandAdminSettings();
      setDimensions({ id: 1, ...bundle.standDimensions });
      setSettings({ id: 1, ...bundle.settings });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : adminLabels.fairStandSettingsLoadError);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (canRead) void load();
    else setLoading(false);
  }, [canRead, load]);

  const openDimensionsEdit = () => {
    if (!dimensions) return;
    setSuccess(null);
    setError(null);
    setDimensionsForm(dimensionsToForm(dimensions));
  };

  const openSettingsEdit = () => {
    if (!settings) return;
    setSuccess(null);
    setError(null);
    setSettingsForm(settingsToForm(settings));
  };

  const closeDimensionsModal = () => setDimensionsForm(null);
  const closeSettingsModal = () => setSettingsForm(null);

  const saveDimensions = async () => {
    if (!canUpdate || !dimensionsForm) return;
    setSavingDimensions(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateFairStandAdminStandDimensions({
        height_cm: parsePositiveNumber(
          dimensionsForm.height_cm,
          adminLabels.fairStandSettingsFieldHeight,
        ),
        depth_cm: parsePositiveNumber(
          dimensionsForm.depth_cm,
          adminLabels.fairStandSettingsFieldDepth,
        ),
        frame_width_cm: parsePositiveNumber(
          dimensionsForm.frame_width_cm,
          adminLabels.fairStandSettingsFieldFrameWidth,
        ),
        frame_depth_cm: parsePositiveNumber(
          dimensionsForm.frame_depth_cm,
          adminLabels.fairStandSettingsFieldFrameDepth,
        ),
      });
      setDimensions({ id: 1, ...updated });
      setDimensionsForm(null);
      setSuccess(adminLabels.fairStandSettingsDimensionsSaveSuccess);
    } catch (saveError) {
      setError(
        saveError instanceof Error ? saveError.message : adminLabels.fairStandSettingsDimensionsSaveError,
      );
    } finally {
      setSavingDimensions(false);
    }
  };

  const saveSettings = async () => {
    if (!canUpdate || !settingsForm) return;
    setSavingSettings(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateFairStandAdminRuntimeSettings({
        max_image_upload_mb: parsePositiveInt(
          settingsForm.max_image_upload_mb,
          adminLabels.fairStandSettingsFieldMaxUpload,
        ),
        export_button_visible: settingsForm.export_button_visible,
        import_button_visible: settingsForm.import_button_visible,
      });
      setSettings({ id: 1, ...updated });
      setSettingsForm(null);
      setSuccess(adminLabels.fairStandSettingsRuntimeSaveSuccess);
    } catch (saveError) {
      setError(
        saveError instanceof Error ? saveError.message : adminLabels.fairStandSettingsRuntimeSaveError,
      );
    } finally {
      setSavingSettings(false);
    }
  };

  const dimensionsColumns: UniversalDataTableColumn<DimensionsRow>[] = [
    { key: "id", title: adminLabels.fairStandSettingsColId, sortable: false, render: (row) => String(row.id) },
    {
      key: "height",
      title: adminLabels.fairStandSettingsColHeight,
      sortable: false,
      render: (row) => formatCm(row.heightCm),
    },
    {
      key: "depth",
      title: adminLabels.fairStandSettingsColDepth,
      sortable: false,
      render: (row) => formatCm(row.depthCm),
    },
    {
      key: "frameWidth",
      title: adminLabels.fairStandSettingsColFrameWidth,
      sortable: false,
      render: (row) => formatCm(row.frameWidthCm),
    },
    {
      key: "frameDepth",
      title: adminLabels.fairStandSettingsColFrameDepth,
      sortable: false,
      render: (row) => formatCm(row.frameDepthCm),
    },
    {
      key: "actions",
      title: adminLabels.fairStandSettingsColActions,
      sortable: false,
      render: () =>
        canUpdate ? (
          <TableRowActions>
            <Button size="sm" variant="secondary" onClick={openDimensionsEdit}>
              {adminLabels.fairStandSettingsActionEdit}
            </Button>
          </TableRowActions>
        ) : null,
    },
  ];

  const settingsColumns: UniversalDataTableColumn<SettingsRow>[] = [
    { key: "id", title: adminLabels.fairStandSettingsColId, sortable: false, render: (row) => String(row.id) },
    {
      key: "maxUpload",
      title: adminLabels.fairStandSettingsColMaxUpload,
      sortable: false,
      render: (row) => String(row.maxImageUploadMb),
    },
    {
      key: "exportVisible",
      title: adminLabels.fairStandSettingsColExportVisible,
      sortable: false,
      render: (row) => visibleLabel(row.exportButtonVisible),
    },
    {
      key: "importVisible",
      title: adminLabels.fairStandSettingsColImportVisible,
      sortable: false,
      render: (row) => visibleLabel(row.importButtonVisible),
    },
    {
      key: "actions",
      title: adminLabels.fairStandSettingsColActions,
      sortable: false,
      render: () =>
        canUpdate ? (
          <TableRowActions>
            <Button size="sm" variant="secondary" onClick={openSettingsEdit}>
              {adminLabels.fairStandSettingsActionEdit}
            </Button>
          </TableRowActions>
        ) : null,
    },
  ];

  const dimensionsBaseline = dimensions ? dimensionsToForm(dimensions) : null;
  const settingsBaseline = settings ? settingsToForm(settings) : null;

  return (
    <PageShell>
      <PageHeader
        title={adminLabels.fairStandSettingsTitle}
        subtitle={adminLabels.fairStandSettingsSubtitle}
      />
      {error ? <Banner variant="error">{error}</Banner> : null}
      {success ? <Banner variant="success">{success}</Banner> : null}
      {!canRead ? <Banner variant="info">{adminLabels.fairStandSettingsPermissionDenied}</Banner> : null}
      {loading ? <LoadingState /> : null}

      {canRead && !loading ? (
        <>
          <section>
            <SectionHeader
              title={adminLabels.fairStandSettingsDimensionsSection}
              description={adminLabels.fairStandSettingsDimensionsDescription}
            />
            <UniversalDataTable
              items={dimensions ? [dimensions] : []}
              columns={dimensionsColumns}
              rowKey={(row) => String(row.id)}
              emptyState={
                <EmptyState
                  title={adminLabels.fairStandSettingsEmptyTitle}
                  description={adminLabels.fairStandSettingsEmptyDescription}
                />
              }
            />
          </section>

          <section>
            <SectionHeader
              title={adminLabels.fairStandSettingsRuntimeSection}
              description={adminLabels.fairStandSettingsRuntimeDescription}
            />
            <UniversalDataTable
              items={settings ? [settings] : []}
              columns={settingsColumns}
              rowKey={(row) => String(row.id)}
              emptyState={
                <EmptyState
                  title={adminLabels.fairStandSettingsEmptyTitle}
                  description={adminLabels.fairStandSettingsEmptyDescription}
                />
              }
            />
          </section>
        </>
      ) : null}

      {dimensionsForm && dimensionsBaseline ? (
        <FormDirtyHost onClose={closeDimensionsModal}>
          <FormDirtyReporter values={dimensionsForm} baseline={dimensionsBaseline} />
          <FormModal
            title={adminLabels.fairStandSettingsDimensionsEditTitle}
            onClose={closeDimensionsModal}
            formWidth="standard"
            footer={
              <>
                <Button variant="secondary" onClick={closeDimensionsModal} disabled={savingDimensions}>
                  {adminLabels.fairStandSettingsCancel}
                </Button>
                <Button
                  variant="primary"
                  loading={savingDimensions}
                  onClick={() => {
                    void saveDimensions();
                  }}
                >
                  {adminLabels.fairStandSettingsSave}
                </Button>
              </>
            }
          >
            <FormSection title={adminLabels.fairStandSettingsDimensionsSection}>
              <FormGrid columns={2}>
                <FormField
                  label={adminLabels.fairStandSettingsFieldHeight}
                  htmlFor="fs-height"
                  hint={adminLabels.fairStandSettingsFieldHeightHint}
                  required
                >
                  <TextInput
                    id="fs-height"
                    type="number"
                    min={1}
                    step={1}
                    value={dimensionsForm.height_cm}
                    disabled={savingDimensions}
                    onChange={(event) =>
                      setDimensionsForm({ ...dimensionsForm, height_cm: event.target.value })
                    }
                    required
                  />
                </FormField>
                <FormField
                  label={adminLabels.fairStandSettingsFieldDepth}
                  htmlFor="fs-depth"
                  hint={adminLabels.fairStandSettingsFieldDepthHint}
                  required
                >
                  <TextInput
                    id="fs-depth"
                    type="number"
                    min={1}
                    step={1}
                    value={dimensionsForm.depth_cm}
                    disabled={savingDimensions}
                    onChange={(event) =>
                      setDimensionsForm({ ...dimensionsForm, depth_cm: event.target.value })
                    }
                    required
                  />
                </FormField>
                <FormField
                  label={adminLabels.fairStandSettingsFieldFrameWidth}
                  htmlFor="fs-frame-width"
                  hint={adminLabels.fairStandSettingsFieldFrameWidthHint}
                  required
                >
                  <TextInput
                    id="fs-frame-width"
                    type="number"
                    min={0.1}
                    step={0.1}
                    value={dimensionsForm.frame_width_cm}
                    disabled={savingDimensions}
                    onChange={(event) =>
                      setDimensionsForm({ ...dimensionsForm, frame_width_cm: event.target.value })
                    }
                    required
                  />
                </FormField>
                <FormField
                  label={adminLabels.fairStandSettingsFieldFrameDepth}
                  htmlFor="fs-frame-depth"
                  hint={adminLabels.fairStandSettingsFieldFrameDepthHint}
                  required
                >
                  <TextInput
                    id="fs-frame-depth"
                    type="number"
                    min={1}
                    step={1}
                    value={dimensionsForm.frame_depth_cm}
                    disabled={savingDimensions}
                    onChange={(event) =>
                      setDimensionsForm({ ...dimensionsForm, frame_depth_cm: event.target.value })
                    }
                    required
                  />
                </FormField>
              </FormGrid>
            </FormSection>
          </FormModal>
        </FormDirtyHost>
      ) : null}

      {settingsForm && settingsBaseline ? (
        <FormDirtyHost onClose={closeSettingsModal}>
          <FormDirtyReporter values={settingsForm} baseline={settingsBaseline} />
          <FormModal
            title={adminLabels.fairStandSettingsRuntimeEditTitle}
            onClose={closeSettingsModal}
            formWidth="narrow"
            footer={
              <>
                <Button variant="secondary" onClick={closeSettingsModal} disabled={savingSettings}>
                  {adminLabels.fairStandSettingsCancel}
                </Button>
                <Button
                  variant="primary"
                  loading={savingSettings}
                  onClick={() => {
                    void saveSettings();
                  }}
                >
                  {adminLabels.fairStandSettingsSave}
                </Button>
              </>
            }
          >
            <FormSection title={adminLabels.fairStandSettingsRuntimeSection}>
              <FormGrid columns={2}>
                <FormField
                  label={adminLabels.fairStandSettingsFieldMaxUpload}
                  htmlFor="fs-max-upload"
                  hint={adminLabels.fairStandSettingsFieldMaxUploadHint}
                  required
                >
                  <TextInput
                    id="fs-max-upload"
                    type="number"
                    min={1}
                    step={1}
                    value={settingsForm.max_image_upload_mb}
                    disabled={savingSettings}
                    onChange={(event) =>
                      setSettingsForm({ ...settingsForm, max_image_upload_mb: event.target.value })
                    }
                    required
                  />
                </FormField>
              </FormGrid>
              <CheckboxField
                id="fs-export-visible"
                label={adminLabels.fairStandSettingsFieldExportVisible}
                hint={adminLabels.fairStandSettingsFieldExportVisibleHint}
                checked={settingsForm.export_button_visible}
                disabled={savingSettings}
                onChange={(checked) =>
                  setSettingsForm({ ...settingsForm, export_button_visible: checked })
                }
              />
              <CheckboxField
                id="fs-import-visible"
                label={adminLabels.fairStandSettingsFieldImportVisible}
                hint={adminLabels.fairStandSettingsFieldImportVisibleHint}
                checked={settingsForm.import_button_visible}
                disabled={savingSettings}
                onChange={(checked) =>
                  setSettingsForm({ ...settingsForm, import_button_visible: checked })
                }
              />
            </FormSection>
          </FormModal>
        </FormDirtyHost>
      ) : null}
    </PageShell>
  );
}
