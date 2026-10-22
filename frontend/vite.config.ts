import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'

export default defineConfig({
  plugins: [
    frappeui({
      frontendRoute: '/tos',
      frappeProxy: {
        port: 8082,   // <-- this is what actually sets the Vite port
      },
    }),
    vue(),
  ],
  server: {
    host: true,       // listen on 0.0.0.0 so Windows can reach it
    port: 8082,
    strictPort: true, // fail loudly if 8082 is taken
  },
})