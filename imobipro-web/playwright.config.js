import { defineConfig, devices } from '@playwright/test'

// Os testes rodam contra a stack completa servida pelo proxy (front + API na
// mesma origem), que é exatamente como o usuário navega.
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:8080'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  // Um worker só: as suítes compartilham o mesmo servidor e banco. Em paralelo,
  // a limpeza de dados de uma apagaria o cenário da outra.
  workers: 1,
  retries: 1,
  reporter: [['list'], ['html', { outputFolder: 'tests/e2e/relatorio', open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    locale: 'pt-BR',
    timezoneId: 'America/Sao_Paulo',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    video: 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
