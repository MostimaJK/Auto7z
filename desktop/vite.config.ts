import { defineConfig } from 'vite';
export default defineConfig({
  clearScreen: false,
  build: {
    rolldownOptions: {
      onwarn(warning, defaultHandler) {
        // Fluent's client-only markers are redundant in this entirely client-rendered app.
        if (warning.code === 'MODULE_LEVEL_DIRECTIVE') return;
        defaultHandler(warning);
      },
      output: { codeSplitting: { groups: [{ name: 'fluent', test: /@fluentui|@griffel|@floating-ui/ }] } },
    },
  },
});
