// Shared by the live intake page (web/src/routes/intake/[token]/+page.svelte)
// and the builder's preview modal (QuestionnairePreview.svelte) so the two
// group questions into themed sections identically — two copies of this
// logic could silently drift apart (ux-implementation-spec.md#7).
export function groupIntoSections(questions: { theme?: string }[]) {
	const order: string[] = [];
	const byTheme = new Map<string, any[]>();
	for (const question of questions) {
		const theme = question.theme || 'General';
		if (!byTheme.has(theme)) { byTheme.set(theme, []); order.push(theme); }
		byTheme.get(theme)!.push(question);
	}
	return order.map((theme) => ({ theme, questions: byTheme.get(theme)! }));
}
