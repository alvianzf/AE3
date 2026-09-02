<script lang="ts">
	// Single-color stroke icons, replacing the rail's mixed emoji/unicode
	// glyphs (👥💬📚⌂ etc. rendered as multi-color platform emoji, not
	// "professional") — same line-icon style already used elsewhere in this
	// app (the account-menu icons: stroke="currentColor", 24x24, round caps).
	const PATHS: Record<string, string> = {
		home: 'M4 11l8-7 8 7M6 10v9a1 1 0 0 0 1 1h4v-6h2v6h4a1 1 0 0 0 1-1v-9',
		users: 'M8 12a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2 20c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5M16.5 12a3 3 0 1 0 0-6M22 20c0-2.6-1.9-4.5-4.3-5.2',
		message: 'M21 12a8 8 0 1 1-3.4-6.5L21 4l-1 4.5A8 8 0 0 1 21 12z',
		mail: 'M4 6h16v12H4zM4 6l8 7 8-7',
		book: 'M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5zM4 5.5v15',
		settings: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19 12a7 7 0 0 0-.1-1.2l2-1.6-2-3.4-2.3.9a7 7 0 0 0-2.1-1.2L14 3h-4l-.5 2.5a7 7 0 0 0-2.1 1.2l-2.3-.9-2 3.4 2 1.6a7 7 0 0 0 0 2.4l-2 1.6 2 3.4 2.3-.9a7 7 0 0 0 2.1 1.2L10 21h4l.5-2.5a7 7 0 0 0 2.1-1.2l2.3.9 2-3.4-2-1.6c.07-.4.1-.8.1-1.2z',
		star: 'M12 2.5l2.9 6 6.6.9-4.8 4.6 1.1 6.5L12 17.4l-5.8 3.1 1.1-6.5-4.8-4.6 6.6-.9z',
		clipboard: 'M9 4h6v3H9zM6 6h2M16 6h2a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h2M8 12h8M8 16h5',
		folder: 'M3 6.5A1.5 1.5 0 0 1 4.5 5h5l2 2h8A1.5 1.5 0 0 1 21 8.5v9A1.5 1.5 0 0 1 19.5 19h-15A1.5 1.5 0 0 1 3 17.5z',
		watch: 'M8 6h8l-.8 4.5a3 3 0 0 1 0 3L16 18H8l.8-4.5a3 3 0 0 1 0-3zM12 10.5v2l1.2.8'
	};

	let { name, size = 17 }: { name: string; size?: number } = $props();
</script>

<svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
     stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
	<path d={PATHS[name] ?? PATHS.home} />
</svg>
