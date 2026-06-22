// Service worker mínimo: solo necesario para que los navegadores (sobre todo Android/Chrome)
// consideren la página "instalable". No cachea nada — la app real vive en Streamlit.
self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  // Pass-through: no se intercepta ni cachea nada, solo se registra el SW.
});
