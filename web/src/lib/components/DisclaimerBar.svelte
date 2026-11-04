<!-- specs/v8 §8.5 — a persistent, unobtrusive clinical disclaimer. Placed
     at the layout level so it's always present on Consult (the page a
     practitioner forms a clinical judgment from) and every client-facing
     record page, without depending on where in a large page's own markup
     a one-off insertion would need to land. -->
<p class="disclaimer">
	Decision-support, not medical advice — every answer is grounded and
	checked, but a practitioner's own clinical judgment always governs care.
</p>

<style>
	.disclaimer {
		margin: var(--space-4) 0 0; padding-top: var(--space-3); border-top: 1px solid var(--line);
		font-size: var(--text-xs); color: var(--muted); text-align: center;
	}
</style>
