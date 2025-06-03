import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,  // Changed from 3002 to 3000
    host: true,  // Add this to allow external connections
  },
});