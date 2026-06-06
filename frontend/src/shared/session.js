const DEMO_SESSION_STORAGE_KEY = "finlab_demo_session_id";

export function getDemoSessionId() {
  const existingSessionId = window.localStorage.getItem(DEMO_SESSION_STORAGE_KEY);

  if (existingSessionId) {
    return existingSessionId;
  }

  const sessionId = createSessionId();
  window.localStorage.setItem(DEMO_SESSION_STORAGE_KEY, sessionId);

  return sessionId;
}

function createSessionId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }

  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (character) => {
    const random = Math.floor(Math.random() * 16);
    const value = character === "x" ? random : (random & 0x3) | 0x8;

    return value.toString(16);
  });
}
