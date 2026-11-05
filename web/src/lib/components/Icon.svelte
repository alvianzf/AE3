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
		watch: 'M8 6h8l-.8 4.5a3 3 0 0 1 0 3L16 18H8l.8-4.5a3 3 0 0 1 0-3zM12 10.5v2l1.2.8',
		history: 'M12 2A10 10 0 1 0 12 22A10 10 0 1 0 12 2ZM12 7v5l3.5 2',
		eye: 'M1 12S4 5 12 5s11 7 11 7-4 7-11 7-11-7-11-7ZM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z',
		trash: 'M3 6h18M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M10 11v6M14 11v6',
		chevron: 'M6 9l6 6 6-6',
		search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3',
		'new-chat': 'M12 5v14M5 12h14',
		calendar: 'M4 5.5A1.5 1.5 0 0 1 5.5 4h13A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18.5zM4 9h16M8 3v3M16 3v3',
		globe: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3 12h18M12 3a13 13 0 0 1 0 18M12 3a13 13 0 0 0 0 18',
		send: 'M4 11l16-7-6 16-3-6-7-3z',
		check: 'M4 12.5l5 5L20 6.5',
		x: 'M6 6l12 12M18 6L6 18',
		plus: 'M12 5v14M5 12h14',
		pause: 'M8 5v14M16 5v14',
		play: 'M7 4l13 8-13 8z',
		refresh: 'M20 11A8 8 0 1 0 18.5 15.5M20 5v6h-6',
		edit: 'M15 5l4 4M4 20l.9-4L16 4.9a2 2 0 0 1 2.8 0l.3.3a2 2 0 0 1 0 2.8L8 19l-4 1z',
		bolt: 'M13 3 5 13h6l-1 8 8-11h-6z',
		'user-card': 'M4 5.5A1.5 1.5 0 0 1 5.5 4h13A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18.5zM8 15c0-1.7 1.3-3 3-3s3 1.3 3 3M11 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM15 8h2M15 12h2',
		'external-link': 'M14 4h6v6M20 4L10 14M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6',
		lock: 'M6 11V8a6 6 0 1 1 12 0v3M5 11h14v9H5zM12 15v2',
		unlock: 'M6 11V8a6 6 0 0 1 11-3.6M5 11h14v9H5zM12 15v2',
		file: 'M6 3.5h8l4 4v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1zM14 3.5V8h4.5',
		grid: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
		list: 'M4 6h16M4 12h16M4 18h16',
		table: 'M4 4h16v16H4zM4 10h16M10 4v16',
		bell: 'M6 10a6 6 0 1 1 12 0v5l2 3H4l2-3zM9.5 20a2.5 2.5 0 0 0 5 0',
		// Three zero-length round-capped segments, not circles — this is a
		// stroke-only icon set (the <svg> wrapper below has fill="none"),
		// and a thin stroked ring reads as a tiny "o", not a filled dot;
		// a fat round line-cap at a point does read as one.
		'more-vertical': 'M12 5.5h.01M12 12h.01M12 18.5h.01',
		switch: 'M7 4l-4 4 4 4M3 8h13M17 20l4-4-4-4M21 16H8',
		menu: 'M4 6h16M4 12h16M4 18h16',
		// A branching outline — root node, two indented children off one
		// vertical spine — standing in for a folder tree / hierarchy view.
		tree: 'M4 5h4M4 5v12M4 12h4M4 17h4M8 4h3v3H8zM8 10h3v3H8zM8 15h3v3H8z',
		power: 'M12 3v8M6.3 6.3a8 8 0 1 0 11.4 0',
		// Up/down arrow pair — a dedicated glyph for "Sort" triggers, so
		// they read differently from the generic "⋮" more-actions menu
		// trigger (found confusing live: two "⋮" buttons side by side in
		// the Library toolbar, Sort and More, were indistinguishable).
		sort: 'M7 20V4M7 20l-4-4M7 20l4-4M17 4v16M17 4l-4 4M17 4l4 4',
		// File-type glyphs for the Library's tiles/rows — a distinct shape
		// per common file kind instead of every file sharing the same
		// plain document icon.
		image: 'M4 5.5A1.5 1.5 0 0 1 5.5 4h13A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18.5zM8.5 11a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zM4 16l5-5 3 3 4-5 4 5',
		slide: 'M3 5.5A1.5 1.5 0 0 1 4.5 4h15A1.5 1.5 0 0 1 21 5.5v11A1.5 1.5 0 0 1 19.5 18h-15A1.5 1.5 0 0 1 3 16.5zM10 8.5l6 3-6 3zM8 21h8',
		audio: 'M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM21 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
		video: 'M3 6.5A1.5 1.5 0 0 1 4.5 5h11A1.5 1.5 0 0 1 17 6.5v11a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 3 17.5zM17 10l4-2.5v9L17 14',
		archive: 'M4 4h16v16H4zM4 9h16M10 4v2M10 9v2M10 13v2M10 17v2'
	};

	let { name, size = 17 }: { name: string; size?: number } = $props();
</script>

<svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
     stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
	<path d={PATHS[name] ?? PATHS.home} stroke-width={name === 'more-vertical' ? 3.5 : undefined} />
</svg>
