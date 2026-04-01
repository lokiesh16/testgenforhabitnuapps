// popup.js
const TESTGEN_URL = 'http://localhost:5001';

async function checkConnection() {
  try {
    const r = await fetch(`${TESTGEN_URL}/api/status`);
    const d = await r.json();
    document.getElementById('dot').classList.add('on');
    document.getElementById('status').textContent =
      `Connected · ${d.captures} capture(s) so far`;
    document.getElementById('btn-capture').disabled = false;
    loadRecent();
  } catch {
    document.getElementById('status').textContent = 'TestGen not running — start server.py first';
    document.getElementById('btn-capture').disabled = true;
  }
}

async function captureScreen() {
  const name = document.getElementById('screen-name').value.trim() || 'screen';
  const fb   = document.getElementById('feedback');

  // Ask content script to extract DOM
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  let snapshot;
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractDOM,
    });
    snapshot = results[0].result;
  } catch (e) {
    showFeedback(`Content script error: ${e.message}`, 'err'); return;
  }

  // Send to TestGen backend
  try {
    const r = await fetch(`${TESTGEN_URL}/api/extension-capture`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ name, snapshot }),
    });
    const d = await r.json();
    if (d.success) {
      showFeedback(`✅ Captured screen #${d.index}: ${name}`, 'ok');
      document.getElementById('screen-name').value = '';
      checkConnection();
    } else {
      showFeedback(`Error: ${d.error}`, 'err');
    }
  } catch (e) {
    showFeedback(`Failed to send: ${e.message}`, 'err');
  }
}

function extractDOM() {
  // This runs IN the target page context
  const results = [];
  const selectors = [
    'button','a','input','select','textarea',
    '[role="button"]','[role="link"]','[role="tab"]',
    '[role="checkbox"]','[role="radio"]','[role="menuitem"]',
    '[data-testid]','[aria-label]','[placeholder]',
    'h1','h2','h3','label',
  ];
  const seen = new Set();
  selectors.forEach(sel => {
    document.querySelectorAll(sel).forEach(el => {
      if (seen.has(el)) return;
      seen.add(el);
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return;
      const info = {
        tag:         el.tagName.toLowerCase(),
        type:        el.type || null,
        text:        (el.textContent || '').trim().slice(0, 80),
        ariaLabel:   el.getAttribute('aria-label') || null,
        testId:      el.getAttribute('data-testid') || null,
        placeholder: el.getAttribute('placeholder') || null,
        id:          el.id || null,
        name:        el.getAttribute('name') || null,
        role:        el.getAttribute('role') || null,
        href:        el.tagName === 'A' ? el.href : null,
        x: Math.round(rect.x),
        y: Math.round(rect.y),
      };
      if (info.testId)          info.locator = `[data-testid="${info.testId}"]`;
      else if (info.ariaLabel)  info.locator = `[aria-label="${info.ariaLabel}"]`;
      else if (info.id)         info.locator = `#${info.id}`;
      else if (info.placeholder)info.locator = `[placeholder="${info.placeholder}"]`;
      else if (info.name)       info.locator = `[name="${info.name}"]`;
      else if (info.text && info.text.length < 40)
        info.locator = `${info.tag}:has-text("${info.text}")`;
      else info.locator = info.tag;
      results.push(info);
    });
  });
  return {
    url:      window.location.href,
    title:    document.title,
    elements: results,
  };
}

async function loadRecent() {
  try {
    const r = await fetch(`${TESTGEN_URL}/api/status`);
    const d = await r.json();
    if (d.captures > 0) {
      document.getElementById('recent-wrap').style.display = 'block';
    }
  } catch {}
}

function showFeedback(msg, type) {
  const fb = document.getElementById('feedback');
  fb.textContent  = msg;
  fb.className    = `feedback ${type}`;
}

function openTestGen() {
  chrome.tabs.create({ url: TESTGEN_URL });
}

checkConnection();
