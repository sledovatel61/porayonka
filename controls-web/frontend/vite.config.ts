import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Явный минимум браузеров стенда W01. Основание: на Win7 установлен
// «Яндекс Браузер 24.10.3.843 corp» — последняя линейка с поддержкой Windows 7
// (поддержка Win7 у Яндекса прекращена в декабре 2024). Точная версия движка
// Chromium в этой сборке публично не раскрыта и на реальной машине пока не
// считана, поэтому target взят консервативный: вывод для chrome109 работает на
// любом Chromium >= 109, включая Яндекс Браузер 24.10.
// После фиксации browser://version с реальной машины target может быть поднят (W02).
const TARGET = ['chrome109', 'edge109', 'firefox115'];

export default defineConfig({
  plugins: [react()],
  build: {
    target: TARGET,
    cssTarget: TARGET,
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    minify: 'esbuild',
    reportCompressedSize: true,
    chunkSizeWarningLimit: 600,
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8080', changeOrigin: true },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
    allowedHosts: true,
  },
});
