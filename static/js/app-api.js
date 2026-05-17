(function () {
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop().split(";").shift();
    }
    return "";
  }

  function normalizeError(payload) {
    if (!payload) {
      return "Не удалось выполнить запрос.";
    }
    if (typeof payload === "string") {
      return payload;
    }
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    const entries = Object.entries(payload);
    if (!entries.length) {
      return "Не удалось выполнить запрос.";
    }
    return entries
      .map(([field, messages]) => {
        const text = Array.isArray(messages) ? messages.join(", ") : String(messages);
        return field === "__all__" ? text : `${field}: ${text}`;
      })
      .join("; ");
  }

  async function request(url, options = {}) {
    const headers = new Headers(options.headers || {});
    const method = (options.method || "GET").toUpperCase();

    if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    headers.set("X-Requested-With", "fetch");

    if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
      const csrfToken = getCookie("csrftoken");
      if (csrfToken) {
        headers.set("X-CSRFToken", csrfToken);
      }
    }

    const response = await fetch(url, {
      credentials: "same-origin",
      ...options,
      method,
      headers,
    });

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json") ? await response.json() : await response.text();

    if (!response.ok) {
      throw new Error(normalizeError(payload));
    }
    return payload;
  }

  function formatDateTime(value) {
    if (!value) {
      return "—";
    }
    return new Intl.DateTimeFormat("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function showAlert(container, type, message) {
    if (container) {
      container.innerHTML = `<div class="alert alert-${escapeHtml(type)}">${escapeHtml(message)}</div>`;
    }
  }

  function clearAlert(container) {
    if (container) {
      container.innerHTML = "";
    }
  }

  function toApiDateTime(value) {
    return value ? new Date(value).toISOString() : "";
  }

  window.RoomFlowApi = {
    request,
    formatDateTime,
    escapeHtml,
    showAlert,
    clearAlert,
    toApiDateTime,
  };
})();
