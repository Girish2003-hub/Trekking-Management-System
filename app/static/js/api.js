// One place for every call to Flask. Pages call api("/treks") instead of fetch().
const TOKEN_KEY = "tma_token";

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch { /* storage blocked: cookie session still works */ }
}

export async function api(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authentication-Token"] = token; // only used if your auth is token based

  const res = await fetch("/api" + path, {
    method,
    headers,
    credentials: "same-origin", // sends the session cookie
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  let data = {};
  try { data = await res.json(); } catch { /* empty body */ }

  if (!res.ok) {
    const err = new Error(data.message || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}
