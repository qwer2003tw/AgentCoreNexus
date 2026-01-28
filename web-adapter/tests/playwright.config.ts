import { defineConfig, devices } from '@playwright/test'
import dotenv from 'dotenv'

// Load environment-specific config
const envFile = process.env.E2E_ENV === 'aws' ? '.env.aws' : '.env.local'
dotenv.config({ path: envFile })

export default defineConfig({
  testDir: './tests',
  
  // Maximum time one test can run (based on p95: 25.7s, allowing for retries)
  timeout: 120 * 1000,  // 45s AI processing + margin + retries
  
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
    // Use real AWS URL if E2E_ENV=aws, otherwise local dev server
    baseURL: process.env.E2E_ENV === 'aws' 
      ? (process.env.FRONTEND_URL || 'https://d3hplgekizttn1.cloudfront.net')
      : 'http://localhost:5173',
    
    // Increase timeout for real AWS based on actual performance (p95: 25.7s)
    actionTimeout: process.env.E2E_ENV === 'aws' ? 35000 : 15000,
    trace: 'retain-on-failure',  //  Optimized: only keep trace on failure
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
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
  
  // Dev server configuration (only for local testing)
  ...(process.env.E2E_ENV !== 'aws' && {
    webServer: {
      command: 'cd ../frontend && npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
  }),
})