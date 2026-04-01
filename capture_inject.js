(function() {
  if (window.__testgenInjected) return;
  if (!document.body) return;
  window.__testgenInjected = true;
  window.__testgenCaptures = [];
  window.__testgenMode     = false;

  var banner = document.createElement('div');
  banner.id = '__testgen_banner';
  banner.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:999999;background:#7c6aff;color:#fff;padding:8px 16px;font-family:monospace;font-size:13px;font-weight:600;display:flex;align-items:center;gap:12px;box-shadow:0 2px 12px rgba(0,0,0,0.3);transition:background .2s;';
  banner.innerHTML = '<span>o</span><span id="__tg_status">TestGen - Click any element to capture it</span><span style="margin-left:auto;opacity:.7;font-weight:400">ESC to stop</span>';
  document.body.appendChild(banner);

  var highlight = document.createElement('div');
  highlight.style.cssText = 'position:fixed;pointer-events:none;z-index:999998;border:2px solid #7c6aff;background:rgba(124,106,255,0.08);border-radius:4px;transition:all .1s;display:none;';
  document.body.appendChild(highlight);

  function getBestLocator(el) {
    var testId = el.getAttribute('data-testid');
    if (testId) return { strategy: 'get_by_test_id', value: 'page.get_by_test_id("' + testId + '")', confidence: 'high' };
    var aria = el.getAttribute('aria-label');
    var tag = el.tagName.toLowerCase();
    var roleMap = { button: 'button', a: 'link', input: 'textbox', select: 'combobox', textarea: 'textbox', h1: 'heading', h2: 'heading', h3: 'heading' };
    var role = el.getAttribute('role') || roleMap[tag] || null;
    if (role && aria) return { strategy: 'get_by_role', value: 'page.get_by_role("' + role + '", name="' + aria + '")', confidence: 'high' };
    var ph = el.getAttribute('placeholder');
    if (ph) return { strategy: 'get_by_placeholder', value: 'page.get_by_placeholder("' + ph + '")', confidence: 'high' };
    var labelFor = el.id ? document.querySelector('label[for="' + el.id + '"]') : null;
    if (labelFor) return { strategy: 'get_by_label', value: 'page.get_by_label("' + labelFor.textContent.trim() + '")', confidence: 'high' };
    var text = (el.textContent || '').trim().slice(0, 50);
    if (role && text) return { strategy: 'get_by_role', value: 'page.get_by_role("' + role + '", name="' + text + '", exact=True)', confidence: 'medium' };
    if (text && text.length < 40) return { strategy: 'get_by_text', value: 'page.get_by_text("' + text + '", exact=True)', confidence: 'medium' };
    return { strategy: 'locator', value: 'page.locator("' + tag + '")', confidence: 'low' };
  }

  function getParentContext(el) {
    var parents = [];
    var p = el.parentElement;
    var depth = 0;
    while (p && depth < 4) {
      var t = p.tagName.toLowerCase();
      if (['form','section','nav','header','main','aside','footer','dialog'].indexOf(t) > -1 || p.getAttribute('role') || p.getAttribute('aria-label')) {
        parents.push({ tag: t, role: p.getAttribute('role'), label: p.getAttribute('aria-label') });
      }
      p = p.parentElement; depth++;
    }
    return parents;
  }

  function captureElement(el, x, y) {
    var rect = el.getBoundingClientRect();
    var locator = getBestLocator(el);
    var tag = el.tagName.toLowerCase();
    var roleMap = { button: 'button', a: 'link', input: 'textbox', select: 'combobox', textarea: 'textbox' };
    var isInteractive = ['a','button','input','select','textarea'].indexOf(tag) > -1 || el.getAttribute('role');
    var captured = {
      timestamp: new Date().toISOString(),
      url:       window.location.href,
      title:     document.title,
      locator:   locator,
      element: {
        tag:         tag,
        type:        el.type || null,
        text:        (el.textContent || '').trim().slice(0, 100),
        ariaLabel:   el.getAttribute('aria-label'),
        testId:      el.getAttribute('data-testid'),
        placeholder: el.getAttribute('placeholder'),
        id:          el.id || null,
        name:        el.getAttribute('name'),
        role:        el.getAttribute('role'),
        href:        el.href || null,
        isInteractive: !!isInteractive,
        state: {
          disabled: !!el.disabled,
          checked:  !!el.checked,
          visible:  rect.width > 0 && rect.height > 0
        },
        position: { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) }
      },
      parentContext: getParentContext(el)
    };
    window.__testgenCaptures.push(captured);
    return captured;
  }

  document.addEventListener('mousemove', function(e) {
    if (!window.__testgenMode) return;
    var el = document.elementFromPoint(e.clientX, e.clientY);
    if (!el || el === banner || banner.contains(el)) return;
    var rect = el.getBoundingClientRect();
    highlight.style.display = 'block';
    highlight.style.left   = (rect.left - 2) + 'px';
    highlight.style.top    = (rect.top  - 2) + 'px';
    highlight.style.width  = (rect.width + 4) + 'px';
    highlight.style.height = (rect.height + 4) + 'px';
  }, true);

  document.addEventListener('click', function(e) {
    if (!window.__testgenMode) return;
    if (e.target === banner || banner.contains(e.target)) return;
    e.preventDefault();
    e.stopPropagation();
    var el = document.elementFromPoint(e.clientX, e.clientY);
    if (!el) return;
    captureElement(el, e.clientX, e.clientY);
    highlight.style.background = 'rgba(45,212,160,0.2)';
    highlight.style.border = '2px solid #2dd4a0';
    document.getElementById('__tg_status').textContent = 'OK Captured ' + window.__testgenCaptures.length + ' element(s) - keep clicking or save';
    setTimeout(function() {
      highlight.style.background = 'rgba(124,106,255,0.08)';
      highlight.style.border = '2px solid #7c6aff';
    }, 400);
  }, true);

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && window.__testgenMode) {
      window.__testgenMode = false;
      highlight.style.display = 'none';
      banner.style.background = '#444';
      document.getElementById('__tg_status').textContent = 'Capture paused - press Space to resume';
    } else if (e.key === ' ' && !window.__testgenMode) {
      window.__testgenMode = true;
      banner.style.background = '#7c6aff';
      document.getElementById('__tg_status').textContent = 'TestGen - Click any element to capture it';
    }
  }, true);

  window.__testgenMode = true;
  console.log('[TestGen] Click-to-capture active');
})();