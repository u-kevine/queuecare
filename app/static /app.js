async function api(method, path, body) {
  const headers = { 'Content-Type': 'application/json' };
  const token = sessionStorage.getItem('token');

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(readError(data));
  }
  return data;
}

function readError(data) {
  const detail = data.detail;

  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length) return detail[0].msg;
  return 'Something went wrong. Please try again.';
}

function value(id) {
  return document.getElementById(id).value.trim();
}

function clear(ids) {
  ids.forEach(id => (document.getElementById(id).value = ''));
}

function showMessage(text) {
  document.querySelector('[data-testid="message"]').textContent = text;
}

function logout() {
  sessionStorage.clear();
  window.location.href = '/';
}
