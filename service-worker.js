// service-worker.js

const CACHE_NAME = 'photo-eval-cache-v1';
const urlsToCache = [
    '/',
    '/styles.css',
    '/scripts.js',
    '/index.html',
    '/favicon.ico',
    // 必要に応じて他のリソースを追加
];

// インストールイベント - リソースをキャッシュに保存
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                return cache.addAll(urlsToCache);
            })
    );
});

// リクエストのインターセプトとキャッシュからのリソース提供
self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // キャッシュがヒットした場合
                if (response) {
                    return response;
                }
                return fetch(event.request);
            })
    );
});

// アクティベーションイベント - 古いキャッシュの削除
self.addEventListener('activate', (event) => {
    const cacheWhitelist = [CACHE_NAME];
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheWhitelist.indexOf(cacheName) === -1) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});