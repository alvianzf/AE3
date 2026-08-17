import { defineConfig } from "vite";

// Bundles only the component/JS entry points for pages that have been
// migrated to Material Web (specs/v3/15-design-system.md) — not the HTML
// pages themselves, which stay served exactly as before by FastAPI's
// existing /static mount. Add one line here per page as it migrates.
export default defineConfig({
  build: {
    outDir: "static/dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        theme: "src/theme.css",
        login: "src/pages/login.js",
        "practitioner-signup": "src/pages/practitioner-signup.js",
        "client-signup": "src/pages/client-signup.js",
        account: "src/pages/account.js",
        clients: "src/pages/clients.js",
        consult: "src/pages/consult.js",
        profile: "src/pages/profile.js",
        upgrade: "src/pages/upgrade.js",
        contacts: "src/pages/contacts.js",
      },
      output: {
        // No hashing: this project has no CDN cache-busting infra (pages
        // already use manual ?v=N query strings, e.g. style.css?v=11),
        // and predictable filenames keep the <script src> in each HTML
        // page a plain, stable path.
        entryFileNames: "[name].js",
        assetFileNames: "[name][extname]",
      },
    },
  },
});
