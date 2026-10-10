import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

const target = process.env.VITE_ENGINE_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/snapshot': target, '/history': target, '/days': target, '/day': target, '/control': target, '/ws': { target, ws: true } } },
  test: { environment: 'node', include: ['tests/**/*.test.ts'] },
})
