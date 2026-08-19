/* Piarte Web Push service worker — admin nakit tahsilat bildirimleri */
self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: "Piarte", body: event.data ? event.data.text() : "" };
  }
  const title = data.title || "Piarte";
  const options = {
    body: data.body || "",
    icon: "/icons/piarte-icon-192.png",
    badge: "/icons/piarte-icon-192.png",
    tag: data.tag || "piarte-push",
    renotify: true,
    data: { url: data.url || "/ui/finance/income" },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || "/dashboard";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url && client.url.startsWith(self.location.origin) && "focus" in client) {
          return client.focus().then(() => {
            if ("navigate" in client) {
              return client.navigate(target);
            }
          });
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(target);
      }
    })
  );
});
