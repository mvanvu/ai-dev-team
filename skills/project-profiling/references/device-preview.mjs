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
//                      `flutter run -d <serial>` or `npx cap run android --target <serial>`. QR pairing needs
//                      mDNS between phone and machine, which some networks block: after 90 s it stops and
//                      prints the pairing-code fallback below.
//   android-code <pair ip:port> <6-digit code> [<connect ip:port>]
//                      fallback: the user taps "Pair device with pairing code" and reads out the IP:port and
//                      code of that dialog, and the IP:port on the Wireless debugging screen itself (connect)
// Options: --host <ip>      LAN address to use (default: a Wi-Fi interface first, since phones join over Wi-Fi;
//                           every other LAN address is listed so the user can say which network the phone is on)
//          --port <n>       port for web/apk (default: a free random port)
//          --minutes <n>    web/apk server stops by itself after n minutes (default 30)
//          --svg <file>     also write the QR code as SVG (open it when the terminal cannot show the code)
//          --light-bg       plain-text QR for a light background (default: dark background)
// When stdout is not a terminal (a tool call, a log) the QR is printed as plain block characters between
// `QR-BEGIN` and `QR-END` lines: paste that block, in a code block, into the reply to the user.
// Exit: 0 done (server stopped, or device connected), 1 failure, 64 usage error.
// Only the local network is used. Exposing the app to the internet (a tunnel) is never done by this script.

import { createServer } from 'node:http';
import { createReadStream, existsSync, statSync, writeFileSync } from 'node:fs';
import { homedir, networkInterfaces } from 'node:os';
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
const lightBg = args.includes('--light-bg') ? (args.splice(args.indexOf('--light-bg'), 1), true) : false;
const tty = Boolean(process.stdout.isTTY);
const target = args[0];

function usage(msg) {
  if (msg) console.error(msg);
  console.error('usage: node device-preview.mjs web <dir> | url <url> | apk <file.apk> | android-pair | android-code <pair ip:port> <code> [<connect ip:port>] [--host ip] [--port n] [--minutes n] [--svg file] [--light-bg]');
  process.exit(64);
}

function lanAddresses() {
  const skip = /^(docker|br-|veth|virbr|lo|cni|flannel|tun|tap|wg|tailscale|zt)/;
  const priv = /^(192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.)/;
  const found = [];
  for (const [name, list] of Object.entries(networkInterfaces())) {
    if (skip.test(name)) continue;
    for (const a of list || []) {
      if (a.family !== 'IPv4' || a.internal) continue;
      // Phones join over Wi-Fi, so wireless interfaces (wl*, wlan*, en0 on macOS laptops) come first.
      const rank = (/^(wl|wlan|wifi)/.test(name) ? 0 : 1) + (priv.test(a.address) ? 0 : 2);
      found.push({ name, address: a.address, rank });
    }
  }
  return found.sort((a, b) => a.rank - b.rank);
}

function lanAddress() {
  const all = lanAddresses();
  if (all.length > 1) {
    console.log(`LAN addresses: ${all.map((a) => `${a.address} (${a.name})`).join(', ')} — using ${all[0].address}.`);
    console.log('If the phone is on another of these networks, run again with --host <that address>.');
  }
  return all[0] ? all[0].address : '';
}

function showQr(text, caption) {
  console.log(`\n${caption}\n${text}\n`);
  const modules = encodeQr(text);
  if (tty) console.log(toTerminal(modules));
  else console.log(`QR-BEGIN\n${toTerminal(modules, { ansi: false, lightBg })}\nQR-END`);
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

// adb from PATH, else from the usual Android SDK locations (Android Studio does not put it on PATH).
const ADB = (() => {
  const sdks = [process.env.ANDROID_HOME, process.env.ANDROID_SDK_ROOT, join(homedir(), 'Android', 'Sdk'), join(homedir(), 'Library', 'Android', 'sdk')];
  for (const sdk of sdks) {
    const bin = sdk && join(sdk, 'platform-tools', process.platform === 'win32' ? 'adb.exe' : 'adb');
    if (bin && existsSync(bin)) return bin;
  }
  return 'adb';
})();

function adb(...a) { return execFileSync(ADB, a, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }); }

function needAdb() {
  try { adb('version'); } catch { console.error('device-preview: adb not found on PATH, $ANDROID_HOME, $ANDROID_SDK_ROOT or ~/Android/Sdk (install Android platform-tools)'); process.exit(1); }
}

function printRun(serial) {
  console.log(`\nadb: ${ADB}`);
  console.log(`Device serial: ${serial}\nRun the app on it: flutter run -d ${serial}   |   npx cap run android --target ${serial}`);
  console.log('A dev server or demo the app calls must be reachable at this machine\'s address on the phone\'s network.');
  console.log('Some brands (vivo, Xiaomi, OPPO, realme) need "Install via USB" in Developer options, and the phone asks to allow each install.');
  console.log('Keep the phone unlocked while it is connected (auto-lock off): a locked screen drops the connection.');
  console.log('Debug builds are slow; judge smoothness with: flutter run --profile -d ' + serial);
  console.log(`Disconnect when done: adb disconnect ${serial}`);
}

const PAIR_CODE_HELP = `Pairing by QR did not complete (mDNS between phone and machine may be blocked on this network).
Fallback: on the phone, Wireless debugging → "Pair device with pairing code". Ask the user for the IP:port and the
6-digit code in that dialog, and the IP:port shown on the Wireless debugging screen itself, then run:
  node device-preview.mjs android-code <pair ip:port> <code> <connect ip:port>
The pairing port is open only while that dialog is showing.`;

function androidCode(pairAddr, code, connectAddr) {
  if (!pairAddr || !code) usage('device-preview android-code: give <pair ip:port> <6-digit code> [<connect ip:port>]');
  needAdb();
  console.log(adb('pair', pairAddr, code).trim());
  if (connectAddr) console.log(adb('connect', connectAddr).trim());
  printRun(connectAddr || pairAddr.split(':')[0]);
}

async function androidPair() {
  needAdb();
  const name = `studio-${randomBytes(4).toString('hex')}`;
  const password = String(randomInt(100000, 999999));
  showQr(`WIFI:T:ADB;S:${name};P:${password};;`,
    'On the phone: Settings → Developer options → Wireless debugging → Pair device with QR code, then scan:');
  const deadline = Date.now() + 90 * 1000;
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
  if (!pairAddr) { console.error(PAIR_CODE_HELP); process.exit(1); }
  console.log(adb('pair', pairAddr, password).trim());
  const ip = pairAddr.split(':')[0];
  let connectAddr = '';
  while (!connectAddr && Date.now() < deadline + 60 * 1000) {
    connectAddr = find('_adb-tls-connect._tcp', (l) => l.includes(ip));
    if (!connectAddr) await new Promise((r) => setTimeout(r, 1500));
  }
  if (connectAddr) console.log(adb('connect', connectAddr).trim());
  printRun(connectAddr || ip);
}

if (mode === 'web') webMode(target);
else if (mode === 'apk') apkMode(target);
else if (mode === 'url') urlMode(target);
else if (mode === 'android-pair') await androidPair();
else if (mode === 'android-code') androidCode(args[0], args[1], args[2]);
else usage();
