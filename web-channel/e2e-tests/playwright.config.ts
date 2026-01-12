import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  
  // Maximum time one test can run (increased for Lambda cold start)
  timeout: 120 * 1000,  // Increased from 60s to 120s
  
  // Test execution settings
  fullyParallel: true,  //  Enable parallel execution
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 4,  //  Use 4 workers for faster execution (local and CI)
  
  // Reporter
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }]
  ],
  
  // Shared settings
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',  //  Optimized: only keep trace on failure
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000,  // Increased from 10s to 15s for slow APIs
  },
  
  // Configure projects for different browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Can add more browsers later
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
  ],
  
  // Dev server configuration
  webServer: {
    command: 'cd ../frontend && npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
})