import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  use: { baseURL: process.env.BROWSER_BASE_URL || 'http://127.0.0.1:8000', browserName: 'chromium' },
  reporter: 'list',
});
