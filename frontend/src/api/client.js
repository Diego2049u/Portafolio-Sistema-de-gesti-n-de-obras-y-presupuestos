const API_BASE_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/+$/, '');

let csrfToken = null;
let refreshInFlight = null;

export class ApiError extends Error {
  constructor(message, { status: statusCode, data } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = statusCode;
    this.data = data;
  }
}

function endpoint(path) {
  return `${API_BASE_URL}/${String(path).replace(/^\/+/, '')}`;
}

export function withQuery(path, params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value));
  });
  const suffix = query.toString();
  return suffix ? `${path}${path.includes('?') ? '&' : '?'}${suffix}` : path;
}

function getErrorMessage(data, fallback) {
  if (typeof data === 'string' && data.trim()) return data;
  if (data?.detalle) return String(data.detalle);
  if (data?.detail) return String(data.detail);
  if (data?.error && typeof data.error === 'string') return data.error;
  if (Array.isArray(data)) return data.map(String).join(' ');
  if (data && typeof data === 'object') {
    const fieldMessages = Object.entries(data)
      .filter(([key]) => !['error', 'detail', 'detalle'].includes(key))
      .flatMap(([field, value]) => {
        const messages = Array.isArray(value) ? value : [value];
        return messages.map((message) => `${field}: ${String(message)}`);
      });
    if (fieldMessages.length) return fieldMessages.join(' ');
  }
  return fallback;
}

async function readResponse(response) {
  if (response.status === 204) return null;
  if (response.status >= 500) return null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }
  return response.text();
}

async function fetchCsrfToken() {
  const response = await fetch(endpoint('/auth/csrf/'), {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  const data = await readResponse(response);
  if (!response.ok || !data?.csrfToken) {
    throw new ApiError(getErrorMessage(data, 'No se pudo iniciar la protección CSRF.'), {
      status: response.status,
      data,
    });
  }
  csrfToken = data.csrfToken;
  return csrfToken;
}

async function ensureCsrfToken() {
  return csrfToken || fetchCsrfToken();
}

async function refreshSession() {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const token = await ensureCsrfToken();
        const response = await fetch(endpoint('/auth/refresh/'), {
          method: 'POST',
          credentials: 'include',
          headers: { Accept: 'application/json', 'X-CSRFToken': token },
        });
        return response.ok;
      } catch {
        return false;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

async function sendRequest(path, options = {}, { mayRefresh = true, csrfRetry = true } = {}) {
  const { responseType, ...fetchOptions } = options;
  const method = (options.method || 'GET').toUpperCase();
  const headers = new Headers(options.headers || {});
  headers.set('Accept', 'application/json');

  let body = options.body;
  if (body !== undefined && body !== null && !(body instanceof FormData) && typeof body !== 'string') {
    headers.set('Content-Type', 'application/json');
    body = JSON.stringify(body);
  }

  if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
    headers.set('X-CSRFToken', await ensureCsrfToken());
  }

  const response = await fetch(endpoint(path), {
    ...fetchOptions,
    method,
    body,
    headers,
    credentials: 'include',
  });

  if (response.status === 401 && mayRefresh && await refreshSession()) {
    return sendRequest(path, options, { mayRefresh: false, csrfRetry });
  }

  if (response.ok && responseType === 'blob') return response.blob();

  const data = await readResponse(response);
  if (!response.ok) {
    const message = response.status >= 500
      ? 'El servidor no pudo completar la solicitud. Intenta nuevamente.'
      : getErrorMessage(data, `La solicitud falló (${response.status}).`);
    if (response.status === 403 && csrfRetry && /csrf/i.test(message)) {
      csrfToken = null;
      await fetchCsrfToken();
      return sendRequest(path, options, { mayRefresh, csrfRetry: false });
    }
    throw new ApiError(message, { status: response.status, data });
  }

  return data;
}

export const api = {
  request: sendRequest,
  async listAll(path) {
    const rows = [];
    let nextPath = path;
    while (nextPath) {
      const page = await sendRequest(nextPath);
      if (Array.isArray(page)) return rows.concat(page);
      rows.push(...(page?.results || []));
      if (!page?.next) break;
      const nextUrl = new URL(page.next, window.location.origin);
      const firstUrl = new URL(path, window.location.origin);
      nextPath = `${firstUrl.pathname.replace(/^\/api\//, '')}${nextUrl.search}`;
    }
    return rows;
  },
  download: (path) => sendRequest(path, { responseType: 'blob' }),
  auth: {
    me: () => sendRequest('/auth/me/'),
    login: (credentials) => sendRequest('/auth/login/', { method: 'POST', body: credentials }, { mayRefresh: false }),
    logout: async () => {
      try {
        return await sendRequest('/auth/logout/', { method: 'POST' }, { mayRefresh: false });
      } finally {
        csrfToken = null;
      }
    },
  },
};
