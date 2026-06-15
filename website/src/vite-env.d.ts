/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** URL of the SNAPPY billing app users get sent to from marketing CTAs. */
  readonly VITE_APP_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
