export interface BackendConfig {
  port: number;
  token: string;
}

declare global {
  interface Window {
    __REETA_CONFIG__?: BackendConfig;
    __TAURI_INTERNALS__?: unknown;
  }
}

let cachedConfig: BackendConfig = {
  port: 8765,
  token: '',
};

export async function initBackendConfig(): Promise<BackendConfig> {
  if (window.__REETA_CONFIG__ && window.__REETA_CONFIG__.port) {
    cachedConfig = window.__REETA_CONFIG__;
    return cachedConfig;
  }

  try {
    const { invoke } = await import('@tauri-apps/api/core');
    const conf = await invoke<BackendConfig>('get_backend_config');
    if (conf && conf.port) {
      cachedConfig = conf;
      window.__REETA_CONFIG__ = conf;
      return cachedConfig;
    }
  } catch {
    // Outside Tauri (dev browser mode), fall back to defaults
  }

  return cachedConfig;
}

export function getBackendConfig(): BackendConfig {
  return window.__REETA_CONFIG__ || cachedConfig;
}

export function getApiBase(): string {
  const cfg = getBackendConfig();
  return `http://127.0.0.1:${cfg.port}/api/v1`;
}

export function getWsUrl(): string {
  const cfg = getBackendConfig();
  const tokenParam = cfg.token ? `?token=${encodeURIComponent(cfg.token)}` : '';
  return `ws://127.0.0.1:${cfg.port}/ws/v1/stream${tokenParam}`;
}

export function getAuthHeaders(): HeadersInit {
  const cfg = getBackendConfig();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (cfg.token) {
    headers['Authorization'] = `Bearer ${cfg.token}`;
  }
  return headers;
}

