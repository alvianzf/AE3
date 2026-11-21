<script lang="ts">
	import { put, post } from '$lib/api';
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { toast } from '$lib/stores/toast';
	import { chunkedUpload } from '$lib/chunkedUpload';

	// Mirrors app/main.py's _MAX_CLIENT_FILE_BYTES — anything over this used
	// to just fail with an error telling the client to "use the chunked
	// upload", a path this page never actually offered (journey-audit
	// finding #3). Above the line, route through chunkedUpload instead.
	const DIRECT_UPLOAD_LIMIT = 20 * 1024 * 1024;

	let { data } = $props();
	const q = $derived(data.questionnaire);

	// text/number/date/choice/multi_choice round-trip exactly the same way
	// (vault.py stores answers_json as opaque JSON either way). A repeater
	// answer is an array of row-objects keyed by column name; an "Other"
	// text value for a choice/multi_choice question lives in `others`,
	// separate from `answers`, and is folded in only at save/submit time.
	let answers = $state<Record<string, any>>({});
	let others = $state<Record<string, string>>({});
	let submitting = $state(false);
	let submitted = $state(data.state === 'submitted');
	let uploadedFiles = $state<string[]>([]);
	let uploading = $state(false);

	let isHydrating = true;
	// Hydrates once per token rather than reactively on every change to
	// `answers` — the old version read AND wrote `answers` inside the same
	// $effect (reassigning the whole object, then also setting a repeater
	// default on it), which made the effect depend on its own write and
	// re-run forever (Svelte's effect_update_depth_exceeded) the moment any
	// questionnaire had a repeater question. Building the initial value in
	// a plain local object and assigning `answers` exactly once breaks that
	// cycle structurally instead of just guarding it.
	let hydratedToken: string | null = null;
	$effect(() => {
		if (data.state !== 'active' || hydratedToken === data.token) return;
		hydratedToken = data.token;
		const initial: Record<string, any> = { ...(data.draft_answers ?? {}) };
		if (q) {
			for (const question of q.questions) {
				if (question.input_type === 'repeater' && !initial[question.id]) {
					initial[question.id] = question.fixed_rows?.length
						? question.fixed_rows.map(() => ({}))
						: [];
				}
			}
		}
		answers = initial;
		isHydrating = true;
		// Next tick: the assignment above must not itself trigger an
		// autosave — only a real edit after hydration should.
		queueMicrotask(() => (isHydrating = false));
	});

	const sections = $derived.by(() => {
		if (!q) return [];
		const order: string[] = [];
		const byTheme = new Map<string, any[]>();
		for (const question of q.questions) {
			const theme = question.theme || 'General';
			if (!byTheme.has(theme)) { byTheme.set(theme, []); order.push(theme); }
			byTheme.get(theme)!.push(question);
		}
		return order.map((theme) => ({ theme, questions: byTheme.get(theme)! }));
	});
	const showThemeHeadings = $derived(sections.length > 1);

	function toggleMulti(id: string, option: string) {
		const current = Array.isArray(answers[id]) ? [...answers[id]] : [];
		const at = current.indexOf(option);
		if (at === -1) current.push(option); else current.splice(at, 1);
		answers = { ...answers, [id]: current };
	}

	function addRow(id: string, columns: string[]) {
		const current = Array.isArray(answers[id]) ? [...answers[id]] : [];
		answers = { ...answers, [id]: [...current, Object.fromEntries(columns.map((c) => [c, '']))] };
	}
	function removeRow(id: string, index: number) {
		const current = Array.isArray(answers[id]) ? [...answers[id]] : [];
		current.splice(index, 1);
		answers = { ...answers, [id]: current };
	}

	// Folds a choice/multi_choice question's typed "Other" text into the
	// payload sent to the server — the UI's `others` state never leaves
	// the browser as its own field.
	function answersForSave() {
		const out = { ...answers };
		if (q) {
			for (const question of q.questions) {
				if (!question.allow_other) continue;
				const other = (others[question.id] ?? '').trim();
				if (!other) continue;
				if (question.input_type === 'multi_choice') {
					const current = Array.isArray(out[question.id]) ? [...out[question.id]] : [];
					out[question.id] = [...current.filter((v: string) => v !== other), other];
				} else if (question.input_type === 'choice' && others[`${question.id}:on`]) {
					out[question.id] = other;
				}
			}
		}
		return out;
	}

	let saveTimer: ReturnType<typeof setTimeout> | undefined;
	let saveState = $state<'idle' | 'saving' | 'saved'>('idle');
	$effect(() => {
		// Bare `answers;`/`others;` only subscribes to those two variables'
		// own identity (i.e. a full reassignment like `answers = {...}`) —
		// not to in-place property writes, which is exactly what every
		// text/number/date field's `bind:value={answers[question.id]}`
		// does. JSON.stringify actually dereferences every nested property,
		// which is what establishes a dependency on each of them, so an
		// edit in any field actually reruns this effect.
		JSON.stringify(answers);
		JSON.stringify(others);
		if (isHydrating || data.state !== 'active' || q === undefined) return;
		clearTimeout(saveTimer);
		saveState = 'saving';
		saveTimer = setTimeout(async () => {
			try {
				await put(fetch, `/intake/${data.token}`, { answers: answersForSave() });
				saveState = 'saved';
			} catch {
				/* a failed autosave just retries on the next edit — nothing
				   the client is filling in is lost from their own screen. */
			}
		}, 1200);
	});

	async function submitQuestionnaire(e: Event) {
		e.preventDefault();
		submitting = true;
		try {
			await post(fetch, `/intake/${data.token}/submit`, { answers: answersForSave() });
			submitted = true;
		} catch (err: any) {
			toast(err.message || 'Could not submit this form.', 'alert');
		} finally {
			submitting = false;
		}
	}

	async function onFilesPicked(e: Event) {
		const files = (e.target as HTMLInputElement).files;
		if (!files?.length) return;
		uploading = true;
		try {
			for (const file of Array.from(files)) {
				if (file.size > DIRECT_UPLOAD_LIMIT) {
					await chunkedUpload(`/intake/${data.token}`, file);
				} else {
					const form = new FormData();
					form.set('file', file);
					const res = await fetch(`${PUBLIC_API_BASE}/api/intake/${data.token}/upload`, {
						method: 'POST',
						credentials: 'include',
						body: form
					});
					if (!res.ok) throw new Error('Could not upload ' + file.name + '.');
				}
				uploadedFiles = [...uploadedFiles, file.name];
			}
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			uploading = false;
		}
	}

	async function finishUpload() {
		submitting = true;
		try {
			await post(fetch, `/intake/${data.token}/submit`, {});
			submitted = true;
		} catch (err: any) {
			toast(err.message || 'Could not close this link.', 'alert');
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head><title>{data.state === 'active' && q ? q.title : 'Intake'}</title></svelte:head>

<svelte:window
	onbeforeunload={(e) => {
		// The autosave debounce (1.2s) means a close right after the last
		// keystroke can beat it — warn rather than silently lose that
		// answer (journey-audit finding #6).
		if (saveState !== 'saving') return;
		e.preventDefault();
	}}
/>

<div class="shell">
	{#if data.state === 'invalid'}
		<div class="card">
			<h1>This link isn't valid</h1>
			<p class="hint">Check that you copied the whole link, or ask your practitioner for a new one.</p>
		</div>
	{:else if submitted}
		<div class="card">
			<h1>All set</h1>
			<p class="hint">This has been submitted. You can close this page now.</p>
		</div>
	{:else if data.state === 'active'}
		<div class="card">
			{#if data.practitioner_name}
				<div class="letterhead">
					{#if data.practitioner_logo_path}<img src={data.practitioner_logo_path} alt="" />{/if}
					<span>{data.practitioner_name}</span>
				</div>
			{/if}

			{#if data.kind === 'upload'}
				<h1>Upload your results</h1>
				<p class="hint">Add one or more files. You can come back to this link any time before you're done.</p>
				<label class="upload-btn">
					{uploading ? 'Uploading…' : 'Choose files'}
					<input type="file" multiple onchange={onFilesPicked} disabled={uploading} hidden />
				</label>
				{#if uploadedFiles.length}
					<ul class="file-list">
						{#each uploadedFiles as name}<li>{name}</li>{/each}
					</ul>
				{/if}
				<button class="submit-btn" onclick={finishUpload} disabled={submitting || !uploadedFiles.length}>
					{submitting ? 'Finishing…' : 'Done'}
				</button>
			{:else if q}
				<h1>{q.title}</h1>
				<p class="save-hint">{saveState === 'saving' ? 'Saving…' : saveState === 'saved' ? 'Saved — come back any time before you submit.' : ''}</p>
				<form onsubmit={submitQuestionnaire}>
					{#each sections as section (section.theme)}
						<div class="section">
							{#if showThemeHeadings}<h3 class="theme">{section.theme}</h3>{/if}
							{#each section.questions as question (question.id)}
								{#if question.input_type === 'info'}
									<p class="info-text">{question.prompt}</p>
								{:else}
									<div class="question">
										<label class="prompt" for="q-{question.id}">{question.prompt}</label>

										{#if question.input_type === 'choice'}
											<div class="pills" role="radiogroup">
												{#each question.options as opt (opt)}
													<button type="button" class="pill" class:selected={answers[question.id] === opt}
														onclick={() => { answers = { ...answers, [question.id]: opt }; others[`${question.id}:on`] = ''; }}>
														{opt}
													</button>
												{/each}
												{#if question.allow_other}
													<button type="button" class="pill" class:selected={!!others[`${question.id}:on`]}
														onclick={() => (others = { ...others, [`${question.id}:on`]: others[`${question.id}:on`] ? '' : '1' })}>
														Other
													</button>
												{/if}
											</div>
											{#if question.allow_other && others[`${question.id}:on`]}
												<input type="text" placeholder="Please specify" bind:value={others[question.id]} />
											{/if}
										{:else if question.input_type === 'multi_choice'}
											<div class="pills">
												{#each question.options as opt (opt)}
													<button type="button" class="pill" class:selected={Array.isArray(answers[question.id]) && answers[question.id].includes(opt)}
														onclick={() => toggleMulti(question.id, opt)}>
														{opt}
													</button>
												{/each}
											</div>
											{#if question.allow_other}
												<input type="text" placeholder="Other — please specify" bind:value={others[question.id]} />
											{/if}
										{:else if question.input_type === 'repeater'}
											<div class="repeater">
												<table>
													<thead>
														<tr>
															{#if question.fixed_rows}<th></th>{/if}
															{#each question.columns as col}<th>{col}</th>{/each}
															{#if !question.fixed_rows}<th></th>{/if}
														</tr>
													</thead>
													<tbody>
														{#each (answers[question.id] ?? []) as row, ri}
															<tr>
																{#if question.fixed_rows}<td class="row-label">{question.fixed_rows[ri]}</td>{/if}
																{#each question.columns as col}
																	<td><input type="text" bind:value={row[col]} /></td>
																{/each}
																{#if !question.fixed_rows}
																	<td><button type="button" class="row-remove" onclick={() => removeRow(question.id, ri)}>&times;</button></td>
																{/if}
															</tr>
														{/each}
													</tbody>
												</table>
												{#if !question.fixed_rows}
													<button type="button" class="add-row" onclick={() => addRow(question.id, question.columns)}>+ Add row</button>
												{/if}
											</div>
										{:else if question.input_type === 'number'}
											<input id="q-{question.id}" type="number" bind:value={answers[question.id]} />
										{:else if question.input_type === 'date'}
											<input id="q-{question.id}" type="date" bind:value={answers[question.id]} />
										{:else if question.maps_to === 'client_name' || question.maps_to === 'client_email'}
											<!-- A name or an email is always single-line — the generic
											     "text" question type otherwise means free-form prose
											     (matches the client questionnaire page's own convention),
											     but these two are a structured field underneath. -->
											<input id="q-{question.id}" type={question.maps_to === 'client_email' ? 'email' : 'text'} bind:value={answers[question.id]} />
										{:else}
											<textarea id="q-{question.id}" bind:value={answers[question.id]} rows="3"></textarea>
										{/if}
									</div>
								{/if}
							{/each}
						</div>
					{/each}
					<button class="submit-btn" type="submit" disabled={submitting}>{submitting ? 'Submitting…' : 'Submit'}</button>
				</form>
			{/if}
		</div>
	{/if}
</div>

<style>
	.shell { min-height: 100dvh; display: flex; justify-content: center; padding: var(--space-6) var(--space-4); background: var(--panel-2); }
	.card { width: 100%; max-width: 38rem; background: var(--panel); border: 1px solid var(--line); border-radius: var(--r-lg); padding: var(--space-6); }
	h1 { margin: 0 0 var(--space-3); font-size: var(--text-lg, 1.3rem); }
	.hint { color: var(--muted); font-size: var(--text-sm); }

	.letterhead { display: flex; align-items: center; gap: .6rem; margin-bottom: var(--space-4); padding-bottom: var(--space-3); border-bottom: 1px solid var(--line); font-weight: 650; font-size: var(--text-sm); }
	.letterhead img { width: 2rem; height: 2rem; object-fit: contain; border-radius: 6px; }

	.save-hint { min-height: 1.2em; color: var(--muted); font-size: var(--text-xs); margin: 0 0 var(--space-3); }
	form { display: grid; gap: var(--space-6); }
	.section { display: grid; gap: var(--space-4); }
	.theme { font-size: var(--text-sm); font-weight: 700; letter-spacing: .04em; color: var(--muted); border-bottom: 1px solid var(--line); padding-bottom: .4rem; }
	.question { display: grid; gap: .5rem; }
	.prompt { font-weight: 650; }
	.info-text { margin: 0; padding: var(--space-3); background: var(--panel-2); border-radius: var(--r); font-size: var(--text-sm); color: var(--ink-2); }

	textarea, input[type='number'], input[type='date'], input[type='text'], input[type='email'] {
		border: none; border-bottom: 1px solid var(--line-2); border-radius: 0; background: none;
		padding: var(--space-2) .1rem; font: inherit; color: var(--ink); width: 100%; box-sizing: border-box;
	}
	textarea:focus, input:focus { outline: none; border-bottom-color: var(--accent); box-shadow: 0 1px 0 0 var(--accent); }

	.pills { display: flex; flex-wrap: wrap; gap: .5rem; }
	.pill {
		font: inherit; font-size: var(--text-sm); font-weight: 600; cursor: pointer;
		border: 1px solid var(--line-2); background: var(--panel); color: var(--ink);
		border-radius: 99px; padding: .5rem 1.1rem;
	}
	.pill.selected { border-color: var(--accent); background: var(--accent); color: #fff; }

	.repeater table { width: 100%; border-collapse: collapse; }
	.repeater th { text-align: left; font-size: var(--text-xs); color: var(--muted); padding: .3rem .4rem; }
	.repeater td { padding: .2rem .4rem; }
	.row-label { font-size: var(--text-sm); font-weight: 600; white-space: nowrap; }
	.row-remove { border: none; background: none; color: var(--muted); cursor: pointer; font-size: 1.1rem; }
	.add-row { margin-top: .4rem; border: 1px dashed var(--line-2); background: none; border-radius: var(--r); padding: .3rem .7rem; font-size: var(--text-sm); cursor: pointer; }

	.upload-btn { display: inline-flex; border: 1px solid var(--line-2); border-radius: var(--r); padding: .6rem 1.2rem; font-weight: 650; cursor: pointer; background: var(--panel-2); margin-bottom: var(--space-4); }
	.file-list { margin: 0 0 var(--space-4); padding-left: 1.2rem; font-size: var(--text-sm); }

	.submit-btn {
		justify-self: start; border: none; background: var(--accent); color: #fff; font-weight: 650;
		border-radius: var(--r); padding: .7rem 1.6rem; cursor: pointer; font-size: var(--text-base);
	}
	.submit-btn:disabled { opacity: .5; cursor: not-allowed; }
</style>
