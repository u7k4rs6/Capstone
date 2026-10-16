async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (res.status === 204) return null;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join(', ') : body.detail;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return body;
}

export const api = {
  list: (params) => request(`/items?${new URLSearchParams(params)}`),
  stats: () => request('/stats'),
  create: (item) => request('/items', { method: 'POST', body: JSON.stringify(item) }),
  update: (id, item) => request(`/items/${id}`, { method: 'PUT', body: JSON.stringify(item) }),
  adjust: (id, delta) => request(`/items/${id}/adjust`, { method: 'POST', body: JSON.stringify({ delta }) }),
  remove: (id) => request(`/items/${id}`, { method: 'DELETE' }),
};
