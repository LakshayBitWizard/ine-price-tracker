const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

export async function api(path, options = {}) {
  const response = await request(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const text = response.text;
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (response.status < 200 || response.status >= 300) {
    const message = data?.detail || `Request failed with ${response.status}`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return data;
}

function request(url, options) {
  if (typeof window !== "undefined" && typeof window.fetch === "function") {
    return window.fetch(url, options).then(async (response) => ({
      status: response.status,
      text: await response.text(),
    }));
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(options.method || "GET", url);
    Object.entries(options.headers || {}).forEach(([key, value]) => {
      xhr.setRequestHeader(key, value);
    });
    xhr.onload = () => resolve({ status: xhr.status, text: xhr.responseText });
    xhr.onerror = () => reject(new Error("Network request failed"));
    xhr.send(options.body || null);
  });
}

export function money(value, currency = "INR") {
  if (value === null || value === undefined || value === "") {
    return "Awaiting scrape";
  }
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

export function compactDate(value) {
  if (!value) {
    return "Never";
  }
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function relativeTime(value) {
  if (!value) {
    return "Not yet";
  }
  const delta = Date.now() - new Date(value).getTime();
  const minutes = Math.round(delta / 60000);
  if (Math.abs(minutes) < 1) {
    return "Just now";
  }
  if (Math.abs(minutes) < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 48) {
    return `${hours}h ago`;
  }
  return compactDate(value);
}
