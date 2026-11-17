/*
 * token-tuner.js — live token panel for HTML mockups (ai-dev-team design gate, DESIGN-20).
 *
 * Include it in a mockup page whose design tokens are CSS custom properties on :root:
 *   <script src="token-tuner.js" defer></script>
 * Optional: name the tokens and their kinds instead of auto-detection:
 *   <script src="token-tuner.js" defer
 *     data-tokens="--accent:color,--bg:color,--surface:color,--ink:color,--radius:length,--space:scale,--font-size:length,--font:font"
 *     data-fonts="Inter, system-ui|Be Vietnam Pro, sans-serif|Plus Jakarta Sans, sans-serif"></script>
 * The panel changes the tokens live and exports the chosen values as JSON (download and copy).
 * No dependencies; nothing is sent anywhere.
 */
(function () {
  'use strict';
  var script = document.currentScript;
  var STORE = 'token-tuner:' + location.pathname;
  var root = document.documentElement;

  function readTokens() {
    var spec = script && script.getAttribute('data-tokens');
    if (spec) {
      return spec.split(',').map(function (pair) {
        var p = pair.trim().split(':');
        return { name: p[0].trim(), kind: (p[1] || 'text').trim() };
      });
    }
    var names = {};
    Array.prototype.forEach.call(document.styleSheets, function (sheet) {
      var rules;
      try { rules = sheet.cssRules; } catch (e) { return; }
      Array.prototype.forEach.call(rules || [], function (rule) {
        if (!rule.style || !/(^|,)\s*(:root|html)\s*(,|$)/.test(rule.selectorText || '')) return;
        for (var i = 0; i < rule.style.length; i++) {
          if (rule.style[i].indexOf('--') === 0) names[rule.style[i]] = true;
        }
      });
    });
    return Object.keys(names).map(function (name) { return { name: name, kind: guessKind(name, current(name)) }; });
  }

  function current(name) { return getComputedStyle(root).getPropertyValue(name).trim(); }

  function guessKind(name, value) {
    if (/font-family|^--font$|-font$/.test(name)) return 'font';
    if (/^#|^rgb|^hsl|^oklch|^color\(/i.test(value)) return 'color';
    if (/^-?[\d.]+(px|rem|em)$/.test(value)) return 'length';
    if (/^-?[\d.]+$/.test(value)) return 'scale';
    return 'text';
  }

  function toHex(value) {
    var probe = document.createElement('span');
    probe.style.color = value;
    document.body.appendChild(probe);
    var rgb = getComputedStyle(probe).color.match(/\d+(\.\d+)?/g) || [0, 0, 0];
    probe.remove();
    return '#' + rgb.slice(0, 3).map(function (n) { return ('0' + Math.round(+n).toString(16)).slice(-2); }).join('');
  }

  function load() { try { return JSON.parse(localStorage.getItem(STORE) || '{}'); } catch (e) { return {}; } }
  function save(values) { try { localStorage.setItem(STORE, JSON.stringify(values)); } catch (e) { /* storage blocked */ } }

  function build() {
    var tokens = readTokens();
    var saved = load();
    var initial = {};
    tokens.forEach(function (t) { initial[t.name] = current(t.name); });
    Object.keys(saved).forEach(function (k) { root.style.setProperty(k, saved[k]); });

    var fonts = ((script && script.getAttribute('data-fonts')) || 'system-ui, sans-serif|Inter, sans-serif|Georgia, serif')
      .split('|').map(function (f) { return f.trim(); });

    var host = document.createElement('div');
    host.setAttribute('data-token-tuner', '');
    var shadow = host.attachShadow({ mode: 'open' });
    shadow.innerHTML =
      '<style>' +
      ':host{all:initial}' +
      '.btn{position:fixed;right:16px;bottom:16px;z-index:2147483647;font:600 13px system-ui;padding:10px 14px;border-radius:999px;border:0;background:#111;color:#fff;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.25)}' +
      '.panel{position:fixed;right:16px;bottom:64px;z-index:2147483647;width:300px;max-height:70vh;overflow:auto;background:#fff;color:#111;border-radius:14px;box-shadow:0 8px 32px rgba(0,0,0,.25);font:13px system-ui;padding:12px}' +
      '.panel[hidden]{display:none}.row{display:grid;grid-template-columns:1fr 120px;gap:8px;align-items:center;margin:6px 0}' +
      'label{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}input,select{width:100%;box-sizing:border-box;font:inherit}' +
      '.bar{display:flex;gap:6px;margin-top:10px}.bar button{flex:1;padding:8px;border-radius:8px;border:1px solid #ccc;background:#f6f6f6;cursor:pointer;font:inherit}' +
      '</style>' +
      '<button class="btn" type="button" aria-expanded="false">Tokens</button>' +
      '<div class="panel" role="dialog" aria-label="Design tokens" hidden><div class="rows"></div>' +
      '<div class="bar"><button type="button" data-a="copy">Copy JSON</button><button type="button" data-a="save">Download</button><button type="button" data-a="reset">Reset</button></div></div>';

    var rows = shadow.querySelector('.rows');
    var values = {};
    tokens.forEach(function (t, i) {
      var id = 'tt' + i;
      var row = document.createElement('div');
      row.className = 'row';
      var label = document.createElement('label');
      label.htmlFor = id;
      label.textContent = t.name;
      label.title = t.name;
      var input;
      var value = current(t.name);
      if (t.kind === 'color') {
        input = document.createElement('input');
        input.type = 'color';
        input.value = toHex(value);
      } else if (t.kind === 'font') {
        input = document.createElement('select');
        (fonts.indexOf(value) < 0 ? [value].concat(fonts) : fonts).forEach(function (f) {
          var o = document.createElement('option');
          o.value = f; o.textContent = f.split(',')[0]; o.selected = f === value;
          input.appendChild(o);
        });
      } else if (t.kind === 'length' || t.kind === 'scale') {
        var m = value.match(/^(-?[\d.]+)(\D*)$/) || [0, '1', ''];
        var unit = m[2];
        var num = parseFloat(m[1]);
        input = document.createElement('input');
        input.type = 'range';
        input.min = 0;
        input.max = unit === 'px' ? Math.max(48, num * 3) : Math.max(4, num * 3);
        input.step = unit === 'px' ? 1 : 0.05;
        input.value = num;
        input.dataset.unit = unit;
      } else {
        input = document.createElement('input');
        input.type = 'text';
        input.value = value;
      }
      input.id = id;
      input.addEventListener('input', function () {
        var v = input.type === 'range' ? input.value + (input.dataset.unit || '') : input.value;
        root.style.setProperty(t.name, v);
        values[t.name] = v;
        save(values);
      });
      row.appendChild(label);
      row.appendChild(input);
      rows.appendChild(row);
    });
    Object.keys(saved).forEach(function (k) { values[k] = saved[k]; });

    var toggle = shadow.querySelector('.btn');
    var panel = shadow.querySelector('.panel');
    toggle.addEventListener('click', function () {
      panel.hidden = !panel.hidden;
      toggle.setAttribute('aria-expanded', String(!panel.hidden));
    });

    function exportJson() {
      var all = {};
      tokens.forEach(function (t) { all[t.name] = current(t.name); });
      return JSON.stringify({ page: location.pathname, changed: values, tokens: all }, null, 2);
    }

    shadow.querySelector('.bar').addEventListener('click', function (e) {
      var action = e.target && e.target.getAttribute('data-a');
      if (action === 'copy' && navigator.clipboard) {
        navigator.clipboard.writeText(exportJson()).catch(function () { window.prompt('Copy the tokens JSON', exportJson()); });
      } else if (action === 'copy') {
        window.prompt('Copy the tokens JSON', exportJson());
      } else if (action === 'save') {
        var a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([exportJson()], { type: 'application/json' }));
        a.download = 'tokens.json';
        a.click();
        setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
      } else if (action === 'reset') {
        Object.keys(values).forEach(function (k) { root.style.removeProperty(k); delete values[k]; });
        save(values);
        Object.keys(initial).forEach(function (k) { root.style.setProperty(k, initial[k]); });
      }
    });

    document.body.appendChild(host);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build);
  else build();
})();
