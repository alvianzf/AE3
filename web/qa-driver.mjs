// Minimal Playwright REPL driver for live QA of the graphRAG web app.
// Run under node with web/node_modules on NODE_PATH (see launch command).
import { chromium } from 'playwright';
import * as readline from 'node:readline';
import * as fs from 'node:fs';

const SHOT_DIR = process.env.SCREENSHOT_DIR || '/tmp/shots';
fs.mkdirSync(SHOT_DIR, { recursive: true });

let browser = null;
let context = null;
let page = null;
const consoleErrors = [];

const COMMANDS = {
	async launch() {
		if (browser) return console.log('already launched');
		browser = await chromium.launch({ headless: true });
		context = await browser.newContext();
		page = await context.newPage();
		page.on('console', (msg) => {
			if (msg.type() === 'error') consoleErrors.push(msg.text());
		});
		page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err.message));
		console.log('launched');
	},
	async newctx() {
		// A fresh, unauthenticated context — for the no-login intake link.
		context = await browser.newContext();
		page = await context.newPage();
		page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
		console.log('new context (no cookies)');
	},
	async nav(url) {
		await page.goto(url, { waitUntil: 'domcontentloaded' });
		console.log('nav ->', page.url());
	},
	async reload() {
		await page.reload({ waitUntil: 'domcontentloaded' });
		console.log('reloaded ->', page.url());
	},
	async ss(name) {
		const f = `${SHOT_DIR}/${name || 'ss-' + Date.now()}.png`;
		await page.screenshot({ path: f, fullPage: true });
		console.log('screenshot:', f);
	},
	async click(sel) {
		try { await page.click(sel, { timeout: 8000 }); console.log('clicked', sel); }
		catch (e) { console.log('CLICK_FAIL', sel, e.message.split('\n')[0]); }
	},
	async clicktext(...words) {
		const text = words.join(' ');
		try {
			await page.getByText(text, { exact: false }).first().click({ timeout: 8000 });
			console.log('clicked text', text);
		} catch (e) { console.log('CLICK_TEXT_FAIL', text, e.message.split('\n')[0]); }
	},
	async fill(sel, ...words) {
		const text = words.join(' ');
		try { await page.fill(sel, text, { timeout: 8000 }); console.log('filled', sel); }
		catch (e) { console.log('FILL_FAIL', sel, e.message.split('\n')[0]); }
	},
	// contentEditable (TipTap) isn't a <textarea> — focus then type.
	async typein(sel, ...words) {
		const text = words.join(' ');
		try {
			await page.click(sel, { timeout: 8000 });
			await page.keyboard.type(text, { delay: 10 });
			console.log('typed into', sel);
		} catch (e) { console.log('TYPE_FAIL', sel, e.message.split('\n')[0]); }
	},
	async press(key) { await page.keyboard.press(key); console.log('pressed', key); },
	async wait(sel) {
		try { await page.waitForSelector(sel, { timeout: 15000 }); console.log('found:', sel); }
		catch { console.log('TIMEOUT:', sel); }
	},
	async waittext(...words) {
		const text = words.join(' ');
		try { await page.getByText(text, { exact: false }).first().waitFor({ timeout: 15000 }); console.log('found text:', text); }
		catch { console.log('TIMEOUT text:', text); }
	},
	async text(sel) {
		try { console.log(await page.locator(sel).first().innerText()); }
		catch (e) { console.log('TEXT_FAIL', e.message.split('\n')[0]); }
	},
	async html(sel) {
		try { console.log((await page.locator(sel).first().innerHTML()).slice(0, 2000)); }
		catch (e) { console.log('HTML_FAIL', e.message.split('\n')[0]); }
	},
	async url() { console.log(page.url()); },
	async errors() {
		console.log('console errors so far:', consoleErrors.length);
		for (const e of consoleErrors) console.log(' -', e);
	},
	async clearerrors() { consoleErrors.length = 0; console.log('cleared'); },
	async eval(expr) {
		try { console.log(JSON.stringify(await page.evaluate(expr))); }
		catch (e) { console.log('EVAL_FAIL', e.message); }
	},
	async sleep(ms) { await new Promise((r) => setTimeout(r, Number(ms) || 1000)); console.log('slept', ms); },
	async quit() { if (browser) await browser.close().catch(() => {}); browser = null; process.exit(0); },
	help() { console.log('commands:', Object.keys(COMMANDS).join(', ')); },
};

const stdin = fs.createReadStream(null, { fd: fs.openSync('/dev/stdin', 'r') });
const rl = readline.createInterface({ input: stdin, output: process.stdout, prompt: 'driver> ' });
// readline keeps emitting 'line' events while a previous async handler is
// still pending (EventEmitter doesn't wait) — without this chain, lines
// piped in via a heredoc all fire nearly at once instead of in order.
let chain = Promise.resolve();
rl.on('line', (line) => {
	chain = chain.then(async () => {
		const parts = line.trim().match(/(?:[^\s"]+|"[^"]*")+/g) || [];
		const [cmd, ...rest] = parts.map((p) => p.replace(/^"|"$/g, ''));
		if (!cmd) return;
		const fn = COMMANDS[cmd];
		if (!fn) { console.log('unknown:', cmd); return; }
		try { await fn(...rest); } catch (e) { console.log('ERROR:', e.message); }
		rl.prompt();
	});
});
rl.on('close', async () => { await chain; await COMMANDS.quit(); });
console.log('driver ready - "help" for commands, "launch" to start');
rl.prompt();
