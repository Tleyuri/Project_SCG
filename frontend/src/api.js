// dev: ใช้ /api ผ่าน vite proxy ไปที่ backend local
// production: ตั้ง VITE_API_BASE_URL เป็น URL ของ backend ที่ deploy แล้ว เช่น https://xxx.onrender.com/api
const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

async function handle(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return res;
}

export async function uploadDxf(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: form });
  await handle(res);
  return res.json();
}

export async function getConfig() {
  const res = await fetch(`${BASE}/config`);
  await handle(res);
  return res.json();
}

export async function getLayers(sessionId) {
  const res = await fetch(`${BASE}/sessions/${sessionId}/layers`);
  await handle(res);
  return res.json();
}

export async function extractBoq(sessionId, body) {
  const res = await fetch(`${BASE}/sessions/${sessionId}/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  await handle(res);
  return res.json();
}

export async function exportBoq(sessionId, body) {
  const res = await fetch(`${BASE}/sessions/${sessionId}/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  await handle(res);
  return res.blob();
}

export async function updateLayerMapping(mapping) {
  const res = await fetch(`${BASE}/config/layer-mapping`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mapping }),
  });
  await handle(res);
  return res.json();
}

export async function updatePriceTable(priceTable) {
  const res = await fetch(`${BASE}/config/price-table`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ price_table: priceTable }),
  });
  await handle(res);
  return res.json();
}

export async function updatePipeSizes(pipeSizes) {
  const res = await fetch(`${BASE}/config/pipe-sizes`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pipe_sizes: pipeSizes }),
  });
  await handle(res);
  return res.json();
}

export async function updateSettings(settings) {
  const res = await fetch(`${BASE}/config/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ settings }),
  });
  await handle(res);
  return res.json();
}
