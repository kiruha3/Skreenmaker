import { defineConfig } from 'vite'

export default defineConfig({
  define: {
    'process.env.NODE_ENV': '"production"'
  },
  build: {
    lib: {
      entry: 'main.js',
      name: 'SkreenMakerApp',
      fileName: 'app',
      formats: ['es']
    },
    outDir: '../static/dist',
    emptyOutDir: true,
    rollupOptions: {
      external: []
    }
  },
  resolve: {
    alias: {
      'vue': 'vue/dist/vue.esm-bundler.js'
    }
  }
})
