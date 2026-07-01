/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_APP_ENV: string;
  readonly VITE_DEV_BYPASS_ENABLED: string;
  readonly VITE_DEV_BYPASS_TOKEN: string;
  readonly VITE_ORGANIZATION_ID: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
