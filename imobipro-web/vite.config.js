import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  build: {
    // es2022 libera top-level await (usado para restaurar a sessão antes de
    // montar o app). Cobre Chrome 89+, Safari 15+, Firefox 89+ o parque de
    // navegadores que a SPA suporta.
    target: 'es2022',
  },
  server: {
    port: 5173,
    // O Nginx de desenvolvimento chega como host "web" (nome do serviço no
    // Compose); sem isso o Vite recusa a requisição vinda do proxy.
    allowedHosts: ['web', 'localhost'],
    // O front fala com a API pelo mesmo host em desenvolvimento: o cookie
    // HttpOnly de refresh precisa de origem consistente.
    proxy: {
      '/api': { target: 'http://api:8000', changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['tests/unit/**/*.spec.js'],
    setupFiles: ['tests/setup.js'],
    // Os testes conferem horários de Brasília; sem fixar o fuso, a máquina do
    // CI (UTC) mostraria 17:30 onde a imobiliária vê 14:30.
    env: { TZ: 'America/Sao_Paulo' },
    coverage: {
      provider: 'v8',
      // lcov alimenta o SonarQube; text mantém o resumo no terminal.
      reporter: ['text-summary', 'lcov'],
      include: ['src/**/*.{js,vue}'],
      exclude: ['src/main.js', 'src/router/**'],
    },
  },
})
