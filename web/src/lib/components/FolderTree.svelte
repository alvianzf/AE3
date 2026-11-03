<script lang="ts">
	// Self-importing for recursion (Svelte 5's recommended pattern — see
	// https://svelte.dev/docs/svelte/legacy-svelte-self — rather than
	// <svelte:self>, which still works but is deprecated).
	import FolderTree from './FolderTree.svelte';
	import Icon from './Icon.svelte';

	export interface TreeNode {
		name: string;
		path: string;
		count: number;
		children: TreeNode[];
		docs: any[];
	}

	let {
		nodes,
		activePath,
		onSelect,
		onDrop,
		onRename,
		onPrivatize,
		onDelete,
		docs = [],
		showDocs = false,
		depth = 0
	}: {
		nodes: TreeNode[];
		activePath: string | null;
		onSelect: (path: string) => void;
		onDrop: (path: string) => void;
		onRename: (path: string) => void;
		onPrivatize: (path: string, isPrivate: boolean) => void;
		onDelete: (path: string, count: number) => void;
		// Documents to show as leaf rows at this exact level (not
		// subfolder contents — those come from each node's own `.docs`)
		// — opt-in via showDocs, so the admin-page sidebar's existing
		// folder-only FolderTree (quick navigation, not a full browser)
		// doesn't suddenly grow a leaf row per document just because
		// TreeNode now always carries `.docs`.
		docs?: any[];
		showDocs?: boolean;
		depth?: number;
	} = $props();

	// Tree shows 3 levels deep by default (root + 2 more), with a chevron
	// to go further — each recursive instance only knows its own depth, so
	// "auto-expand" is just "this instance's nodes land at depth < 2".
	let expanded = $state<Set<string>>(depth < 2 ? new Set(nodes.map((n) => n.path)) : new Set());
	let dragOverPath = $state<string | null>(null);

	function toggle(path: string, e: MouseEvent) {
		e.stopPropagation();
		const next = new Set(expanded);
		if (next.has(path)) next.delete(path);
		else next.add(path);
		expanded = next;
	}
</script>

<ul class="tree" style="--depth: {depth}">
	{#each nodes as node (node.path)}
		<li>
			<div
				class="node"
				class:active={activePath === node.path}
				class:dragover={dragOverPath === node.path}
				ondragover={(e) => { e.preventDefault(); dragOverPath = node.path; }}
				ondragleave={() => (dragOverPath = null)}
				ondrop={(e) => { e.preventDefault(); dragOverPath = null; onDrop(node.path); }}
			>
				{#if node.children.length || (showDocs && node.docs.length)}
					<button class="chevron" onclick={(e) => toggle(node.path, e)} aria-label="Toggle {node.name}">
						<span class:open={expanded.has(node.path)}><Icon name="chevron" size={11} /></span>
					</button>
				{:else}
					<span class="chevron-spacer"></span>
				{/if}
				<button class="name" onclick={() => onSelect(node.path)}>
					<Icon name="folder" size={13} />
					<span class="label">{node.name}</span>
					<span class="count">{node.count}</span>
				</button>
				<span class="node-actions">
					<button onclick={() => onRename(node.path)} title="Rename folder" aria-label="Rename {node.name}"><Icon name="edit" size={11} /></button>
					<button onclick={() => onPrivatize(node.path, true)} title="Privatize folder" aria-label="Privatize {node.name}"><Icon name="lock" size={11} /></button>
					<button onclick={() => onPrivatize(node.path, false)} title="Make folder public" aria-label="Make {node.name} public"><Icon name="unlock" size={11} /></button>
					<button onclick={() => onDelete(node.path, node.count)} title="Delete folder" aria-label="Delete {node.name}"><Icon name="trash" size={11} /></button>
				</span>
			</div>
			{#if expanded.has(node.path)}
				{#if showDocs && node.docs.length}
					<ul class="docs" style="--depth: {depth + 1}">
						{#each node.docs as doc (doc.id)}
							<li>
								<a class="doc-leaf" href="/admin/{doc.id}">
									<Icon name="file" size={13} />
									<span class="label">{doc.title}</span>
								</a>
							</li>
						{/each}
					</ul>
				{/if}
				{#if node.children.length}
					<FolderTree nodes={node.children} {activePath} {onSelect} {onDrop} {onRename} {onPrivatize} {onDelete} {showDocs} depth={depth + 1} />
				{/if}
			{/if}
		</li>
	{/each}
</ul>
{#if showDocs && docs.length}
	<ul class="docs" style="--depth: {depth + 1}">
		{#each docs as doc (doc.id)}
			<li>
				<a class="doc-leaf" href="/admin/{doc.id}">
					<Icon name="file" size={13} />
					<span class="label">{doc.title}</span>
				</a>
			</li>
		{/each}
	</ul>
{/if}

<style>
	/* padding-left via --depth, not a ".tree .tree" descendant selector —
	   each recursive <FolderTree> invocation is its own component
	   instance, so Svelte's per-component scoped CSS doesn't cascade a
	   parent's nested selector onto the child's root element. */
	.tree { list-style: none; margin: 0; padding: 0; padding-left: calc(var(--depth) * 1rem); }
	.node {
		display: flex; align-items: center; gap: .15rem; border-radius: var(--r);
		transition: background-color .12s var(--ease);
	}
	.node:hover { background: var(--panel-2); }
	.node.active { background: var(--accent-soft); }
	.node.dragover { outline: 2px dashed var(--accent); outline-offset: -2px; }
	.chevron, .chevron-spacer { width: 1.1rem; height: 1.1rem; flex: 0 0 auto; }
	.chevron {
		border: none; background: none; cursor: pointer; display: inline-flex; align-items: center; justify-content: center;
		color: var(--muted); padding: 0;
	}
	.chevron span { display: inline-flex; transition: transform .12s var(--ease); }
	.chevron span.open { transform: rotate(90deg); }
	.name {
		flex: 1 1 auto; min-width: 0; display: flex; align-items: center; gap: .35rem;
		border: none; background: none; cursor: pointer; font: inherit; font-size: var(--text-sm);
		color: var(--ink); padding: .3rem 0; text-align: left;
	}
	.label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.count { color: var(--muted); font-size: var(--text-xs); flex: 0 0 auto; }
	/* Always visible, not hover-revealed — matches the admin Library
	   page's doc-card-actions, and hover-reveal on a flex row would grow
	   the row's content width on hover (shifting the name/count next to
	   it) and is unreachable on touch devices anyway. */
	.node-actions { display: flex; gap: .15rem; flex: 0 0 auto; padding-right: .2rem; }
	.node-actions button {
		border: none; background: none; cursor: pointer; color: var(--muted); padding: .2rem;
		border-radius: var(--r); display: inline-flex;
	}
	.node-actions button:hover { color: var(--accent); background: var(--panel); }
	.docs { list-style: none; margin: 0; padding: 0; padding-left: calc(var(--depth) * 1rem + 1.1rem); }
	.doc-leaf {
		display: flex; align-items: center; gap: .35rem; padding: .3rem 0; text-decoration: none;
		color: var(--muted); font-size: var(--text-sm); border-radius: var(--r);
	}
	.doc-leaf:hover { color: var(--ink); }
	.doc-leaf .label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
