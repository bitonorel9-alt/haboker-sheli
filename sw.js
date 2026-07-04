// הבוקר שלי — service worker: מאפשר התקנה כאפליקציה + עבודה גם בלי אינטרנט
const CACHE = 'haboker-sheli-v1';
const SHELL = ['./', './index.html', './manifest.json',
  './icons/icon-192.png', './icons/icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // נתוני החדשות: תמיד לנסות רשת קודם כדי לקבל את העדכון היומי, ליפול לקאש רק אם אין רשת
  if (url.pathname.endsWith('/data/news_data.js')) {
    e.respondWith(
      fetch(e.request).then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return res;
      }).catch(() => caches.match(e.request))
    );
    return;
  }
  // שאר הקבצים: קאש קודם, רשת כגיבוי
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
