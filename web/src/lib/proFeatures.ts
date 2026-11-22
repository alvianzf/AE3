// Single source of truth for which practitioner features are Pro-only —
// used both to gate the Rail nav ((practitioner)/practitioner/+layout.svelte)
// and to generate the Upgrade page's feature comparison table, so the two
// can't silently drift apart (ux-implementation-spec.md#9).
export const PRO_FEATURES: { label: string; href: string }[] = [
	{ label: 'Consult (AI-assisted)', href: '/practitioner/consult' },
	{ label: 'Client vault', href: '/practitioner/clients' },
	{ label: 'Knowledge library weighting', href: '/practitioner/knowledge' },
	{ label: 'Questionnaires', href: '/practitioner/questionnaires' }
];
