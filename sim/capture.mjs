// Usage:
//   node capture.mjs stills <page> <outPrefix> t1,t2,...           -> JPEG stills
//   node capture.mjs video  <page> <out.mp4> <duration> [query]    -> encoded scene file
//   node capture.mjs png    <page> <out.png> [query]               -> transparent PNG
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import puppeteer from 'puppeteer-core';

const ROOT = process.cwd();  // run from sim/ after `npm i three puppeteer-core`; the page loads three from the CDN
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.png': 'image/png', '.css': 'text/css' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const port = server.address().port;

const browser = await puppeteer.launch({
  executablePath: '/usr/bin/google-chrome', headless: true,
  args: ['--no-sandbox', '--no-proxy-server', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist',
         '--enable-webgl', '--hide-scrollbars', '--force-color-profile=srgb', '--font-render-hinting=none'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
page.on('pageerror', e => console.error('PAGE ERROR:', e.message));
page.on('console', m => { if (m.type() === 'error') console.error('CONSOLE:', m.text()); });

const [mode, pg, out, a4, a5] = process.argv.slice(2);
const open = async (query = '') => {
  await page.goto(`http://127.0.0.1:${port}/${pg}${query ? '?' + query : ''}`, { waitUntil: 'load' });
  await page.waitForFunction('window.ready === true', { timeout: 60000 });
};

if (mode === 'stills') {
  await open(a5 || '');
  for (const t of a4.split(',').map(Number)) {
    await page.evaluate(t => window.setTime(t), t);
    await page.screenshot({ path: `${out}_${t.toFixed(2)}.jpg`, type: 'jpeg', quality: 90 });
    console.log('still', t);
  }
} else if (mode === 'png') {
  await open(a4 || '');
  await page.screenshot({ path: out, type: 'png', omitBackground: true });
} else if (mode === 'video') {
  const dur = parseFloat(a4), fps = 30, n = Math.round(dur * fps);
  await open(a5 || '');
  const tmp = out.replace(/\.mp4$/, '.part.mp4');
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-vf', process.env.VF || 'format=yuv420p', '-c:v', 'libx264', '-crf', '17', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-r', String(fps), tmp],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => window.setTime(t), i / fps);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 30 === 0) console.log(`frame ${i}/${n}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  const code = await new Promise(r => ff.on('close', r));
  if (code === 0) fs.renameSync(tmp, out); else { console.error('ffmpeg failed', code); process.exitCode = 1; }
}
await browser.close();
server.close();
