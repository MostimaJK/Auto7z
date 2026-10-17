import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
export default defineConfig({ plugins: [vue()], clearScreen: false,
  build: { rolldownOptions: { output: { codeSplitting: { groups: [{ name: 'element', test: /element-plus|@element-plus/ }] } } } }
});
