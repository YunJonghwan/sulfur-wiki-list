import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base is set for GitHub Pages project site (https://<user>.github.io/sulfur-wiki-list/).
// Use '/' locally via `npm run dev`; the build uses the repo path.
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'build' ? '/sulfur-wiki-list/' : '/',
}))
