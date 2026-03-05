import { defaultCache } from "@serwist/next/worker";
import type { PrecacheEntry, SerwistGlobalConfig } from "serwist";
import {
  CacheFirst,
  ExpirationPlugin,
  NetworkFirst,
  NetworkOnly,
  Serwist,
  StaleWhileRevalidate,
} from "serwist";

declare global {
  interface WorkerGlobalScope extends SerwistGlobalConfig {
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}

declare const self: ServiceWorkerGlobalScope;

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: [
    // Auth endpoints: never cache tokens
    {
      matcher: /\/v1\/auth\/.*/,
      handler: new NetworkOnly(),
    },
    // API responses: network first, fall back to cache
    {
      matcher: /\/v1\/.*/,
      handler: new NetworkFirst({
        cacheName: "api-cache",
        plugins: [
          new ExpirationPlugin({
            maxEntries: 64,
            maxAgeSeconds: 5 * 60,
          }),
        ],
        networkTimeoutSeconds: 5,
      }),
    },
    // Next.js static assets
    {
      matcher: /\/_next\/static\/.*/,
      handler: new StaleWhileRevalidate({
        cacheName: "static-assets",
        plugins: [
          new ExpirationPlugin({
            maxEntries: 128,
            maxAgeSeconds: 30 * 24 * 60 * 60,
          }),
        ],
      }),
    },
    // Images
    {
      matcher: /\.(?:png|jpg|jpeg|svg|gif|webp|ico)$/,
      handler: new CacheFirst({
        cacheName: "image-cache",
        plugins: [
          new ExpirationPlugin({
            maxEntries: 64,
            maxAgeSeconds: 7 * 24 * 60 * 60,
          }),
        ],
      }),
    },
    ...defaultCache,
  ],
});

serwist.addEventListeners();
