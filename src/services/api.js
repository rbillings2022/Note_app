/* ============================================
   Notebook — shared API helpers
   Assumes the backend uses a session cookie for
   auth (credentials: 'include' on every call).
   Adjust here if the backend uses a token instead.
   ============================================ */

const Api = (() => {
  async function request(path, options = {}) {
    let response;
    try {
      response = await fetch(path, {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        ...options,
      });
    } catch (networkErr) {
      throw new Error('Could not reach the server. Check your connection and try again.');
    }

    let data = null;
    const text = await response.text();
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (parseErr) {
        // Non-JSON response body; leave data as null.
      }
    }

    if (!response.ok) {
      const message = (data && (data.error || data.message)) || `Request failed (${response.status}).`;
      throw new Error(message);
    }

    return data;
  }

  return {
    register(username, password) {
      return request('/api/register', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
    },

    login(username, password) {
      return request('/api/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
    },

    logout() {
      return request('/api/logout', { method: 'POST' });
    },

    saveNote(content) {
      return request('/api/notes-save', {
        method: 'POST',
        body: JSON.stringify({ content }),
      });
    },

    loadNote() {
      return request('/api/notes-load', { method: 'GET' });
    },
  };
})();
