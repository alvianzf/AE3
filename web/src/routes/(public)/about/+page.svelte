<!-- specs/v4.1/01 — this route only exists so +page.ts's redirect to "/"
     fires; +page.svelte is never actually rendered (the load() throws
     first), but SvelteKit requires one for the route to exist at all. -->
