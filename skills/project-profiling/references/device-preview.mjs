#!/usr/bin/env node
// Opens the app on the user's own phone over the local network: prints a QR code the phone scans.
// No companion app: the phone uses its browser, Android's built-in Wireless debugging, or installs the APK.
//
// Usage: node $TEAM_BIN/device-preview.mjs <mode> [options]
//   web <dir>          serve a built web app (SPA fallback to index.html) on this machine's LAN address
//   url <url>          QR for a dev server that already listens on all interfaces (localhost is replaced
//                      by the LAN address; the server must be started with --host 0.0.0.0 or similar)
//   apk <file.apk>     serve one APK for download; the phone installs it (allow "install unknown apps")
//   android-pair       pair the phone with adb through Android's "Pair device with QR code" (Android 11+,
//                      Developer options → Wireless debugging), then connect; prints the device serial for
//                      `flutter run -d <serial>` or `npx cap run android --target <serial>`
// Options: --host <ip>      LAN address to use (default: the first private IPv4 address that is not a container bridge)
//          --port <n>       port for web/apk (default: a free random port)
//          --minutes <n>    web/apk server stops by itself after n minutes (default 30)
//          --svg <file>     also write the QR code as SVG (open it when the terminal cannot show the code)
// Exit: 0 done (server stopped, or device connected), 1 failure, 64 usage error.
// Only the local network is used. Exposing the app to the internet (a tunnel) is never done by this script.

import { createServer } from 'node:http';
import { createReadStream, existsSync, statSync, writeFileSync } from 'node:fs';
import { networkInterfaces } from 'node:os';
import { extname, join, normalize, resolve, sep, basename } from 'node:path';
import { execFileSync } from 'node:child_process';
import { randomBytes, randomInt } from 'node:crypto';
import { encodeQr, toTerminal, toSvg } from './qr.mjs';

const args = process.argv.slice(2);
const mode = args.shift();
const opt = (name, fallback) => {
  const i = args.indexOf(`--${name}`);
  if (i < 0) return fallback;
  const v = args[i + 1];
  args.splice(i, 2);
  return v;
};
const host = opt('host', '') || lanAddress();
const port = Number(opt('port', '0'));
const minutes = Number(opt('minutes', '30'));
const svgFile = opt('svg', '');
const target = args[0];

function usage(msg) {
  if (msg) console.error(msg);
  console.error('usage: node device-preview.mjs web <dir> | url <url> | apk <file.apk> | android-pair [--host ip] [--port n] [--minutes n] [--svg file]');
  process.exit(64);
}

function lanAddress() {
  const skip = /^(docker|br-|veth|virbr|lo|cni|flannel|tun|tap|wg)/;
  const found = [];
  for (const [name, list] of Object.entries(networkInterfaces())) {
    if (skip.test(name)) continue;
    for (const a of list || []) if (a.family === 'IPv4' && !a.internal) found.push(a.address);
  }
  const priv = found.find((a) => /^(192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.)/.test(a));
  return priv || found[0] || '';
}

function showQr(text, caption) {
  console.log(`\n${caption}\n${text}\n`);
  const modules = encodeQr(text);
  console.log(toTerminal(modules));
  if (svgFile) { writeFileSync(svgFile, toSvg(modules)); console.log(`\nQR also written to ${svgFile}`); }
  console.log('');
}

const TYPES = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.webmanifest': 'application/manifest+json', '.svg': 'image/svg+xml',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.gif': 'image/gif',
  '.ico': 'image/x-icon', '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.wasm': 'application/wasm',
  '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.mp4': 'video/mp4', '.apk': 'application/vnd.android.package-archive',
};

function serve(handler, label) {
  if (!host) { console.error('device-preview: no LAN address found; pass --host <ip>'); process.exit(1); }
  const server = createServer(handler);
  server.listen(port, host, () => {
    const url = `http://${host}:${server.address().port}/`;
    showQr(url, `${label} — scan with the phone's camera (same Wi-Fi as this machine):`);
    console.log(`Serving on the local network only. Stops by itself in ${minutes} min; Ctrl-C stops it now.`);
  });
  const stop = () => { server.close(); process.exit(0); };
  setTimeout(stop, minutes * 60 * 1000).unref();
  process.on('SIGINT', stop);
  process.on('SIGTERM', stop);
}

function sendFile(res, file) {
  res.writeHead(200, {
    'Content-Type': TYPES[extname(file).toLowerCase()] || 'application/octet-stream',
    'Content-Length': statSync(file).size,
    'Cache-Control': 'no-store',
  });
  createReadStream(file).pipe(res);
}

function webMode(dir) {
  const root = resolve(dir || '');
  if (!dir || !existsSync(join(root, 'index.html'))) usage(`device-preview web: ${root} has no index.html (build the web app first)`);
  serve((req, res) => {
    const path = decodeURIComponent((req.url || '/').split('?')[0]);
    const file = normalize(join(root, path));
    if (!file.startsWith(root + sep) && file !== root) { res.writeHead(403); res.end(); return; }
    if (existsSync(file) && statSync(file).isFile()) sendFile(res, file);
    else sendFile(res, join(root, 'index.html'));
  }, 'Web app');
}

function apkMode(file) {
  if (!file || !existsSync(file) || extname(file) !== '.apk') usage('device-preview apk: give the path of a built .apk');
  const name = basename(file);
  serve((req, res) => {
    if ((req.url || '/') === '/') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(`<!doctype html><meta name="viewport" content="width=device-width"><p style="font:18px sans-serif;padding:24px"><a href="/${encodeURIComponent(name)}">Download ${name}</a></p>`);
    } else if (decodeURIComponent(req.url.slice(1)) === name) {
      res.setHeader('Content-Disposition', `attachment; filename="${name}"`);
      sendFile(res, file);
    } else { res.writeHead(404); res.end(); }
  }, `APK ${name}`);
}

function urlMode(url) {
  if (!url) usage('device-preview url: give the dev server URL, e.g. http://localhost:5173/');
  const u = new URL(url);
  if (['localhost', '127.0.0.1', '0.0.0.0', '::1', '[::1]'].includes(u.hostname)) u.hostname = host;
  showQr(u.toString(), 'Dev server — scan with the phone (the server must listen on all interfaces, e.g. --host 0.0.0.0):');
}

function adb(...a) { return execFileSync('adb', a, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }); }

async function androidPair() {
  try { adb('version'); } catch { console.error('device-preview android-pair: adb not found (Android platform-tools)'); process.exit(1); }
  const name = `studio-${randomBytes(4).toString('hex')}`;
  const password = String(randomInt(100000, 999999));
  showQr(`WIFI:T:ADB;S:${name};P:${password};;`,
    'On the phone: Settings → Developer options → Wireless debugging → Pair device with QR code, then scan:');
  const deadline = Date.now() + 3 * 60 * 1000;
  const find = (type, pick) => {
    const out = adb('mdns', 'services');
    const line = out.split('\n').find((l) => l.includes(type) && pick(l));
    const m = line && line.match(/(\d+\.\d+\.\d+\.\d+:\d+)/);
    return m ? m[1] : '';
  };
  let pairAddr = '';
  while (!pairAddr && Date.now() < deadline) {
    pairAddr = find('_adb-tls-pairing._tcp', (l) => l.includes(name));
    if (!pairAddr) await new Promise((r) => setTimeout(r, 1500));
  }
  if (!pairAddr) { console.error('device-preview: the phone did not show up for pairing within 3 min (same Wi-Fi? QR scanned?)'); process.exit(1); }
  console.log(adb('pair', pairAddr, password).trim());
  const ip = pairAddr.split(':')[0];
  let connectAddr = '';
  while (!connectAddr && Date.now() < deadline + 60 * 1000) {
    connectAddr = find('_adb-tls-connect._tcp', (l) => l.includes(ip));
    if (!connectAddr) await new Promise((r) => setTimeout(r, 1500));
  }
  if (connectAddr) console.log(adb('connect', connectAddr).trim());
  const serial = connectAddr || ip;
  console.log(`\nDevice serial: ${serial}\nRun the app on it: flutter run -d ${serial}   |   npx cap run android --target ${serial}`);
  console.log(`Disconnect when done: adb disconnect ${serial}`);
}

if (mode === 'web') webMode(target);
else if (mode === 'apk') apkMode(target);
else if (mode === 'url') urlMode(target);
else if (mode === 'android-pair') await androidPair();
else usage();
