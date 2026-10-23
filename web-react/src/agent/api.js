// Cliente de la API Python del agente (src/insight_trader/agent/server.py).
// En desarrollo Vite redirige /api a http://127.0.0.1:8000 (vite.config.js).
// Si la API no responde (ej. despliegue estatico en Vercel) la vista usa
// el modo grabado con data/agent_demo.json.

export async function detectLiveApi() {
  try {
    const res = await fetch("/api/health", {
      signal: AbortSignal.timeout(1500),
    });
    if (!res.ok) return false;
    const data = await res.json();
    return data.ok === true;
  } catch {
    return false;
  }
}

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error ?? `Error ${res.status}`);
  return data;
}

export const fetchClients = () => request("/api/clients");

export const askAgent = (body) =>
  request("/api/ask", { method: "POST", body: JSON.stringify(body) });

export const resetMemory = (clientId) =>
  request("/api/reset", {
    method: "POST",
    body: JSON.stringify({ client_id: clientId }),
  });

export const fetchCatalog = () => request("/api/catalog");

export const createClient = (data) =>
  request("/api/clients", { method: "POST", body: JSON.stringify(data) });

export const deleteClient = (clientId) =>
  request("/api/clients/delete", {
    method: "POST",
    body: JSON.stringify({ client_id: clientId }),
  });

export const fetchMarket = (scenario) =>
  request(`/api/market?scenario=${encodeURIComponent(scenario)}`);

export const fetchRealMarket = () => request("/api/market/real");

export const fetchRecommendations = (scenario) =>
  request(`/api/recommendations?scenario=${encodeURIComponent(scenario)}`);
