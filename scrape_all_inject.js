(function() {
  // Scrape all interactive/testable elements from the page without clicking
  
  function getBestLocator(el) {
    var testId = el.getAttribute('data-testid');
    if (testId) return { strategy: 'get_by_test_id', value: 'page.get_by_test_id("' + testId + '")', confidence: 'high' };
    
    var aria = el.getAttribute('aria-label');
    var tag = el.tagName.toLowerCase();
    var roleMap = { 
      button: 'button', a: 'link', input: 'textbox', select: 'combobox', 
      textarea: 'textbox', h1: 'heading', h2: 'heading', h3: 'heading',
      img: 'img', nav: 'navigation', form: 'form', table: 'table',
      checkbox: 'checkbox', radio: 'radio'
    };
    var role = el.getAttribute('role') || roleMap[tag] || null;
    
    // Handle input types
    if (tag === 'input') {
      var inputType = (el.type || 'text').toLowerCase();
      if (inputType === 'checkbox') role = 'checkbox';
      else if (inputType === 'radio') role = 'radio';
      else if (inputType === 'submit' || inputType === 'button') role = 'button';
    }
    
    if (role && aria) return { strategy: 'get_by_role', value: 'page.get_by_role("' + role + '", name="' + escapeStr(aria) + '")', confidence: 'high' };
    
    var ph = el.getAttribute('placeholder');
    if (ph) return { strategy: 'get_by_placeholder', value: 'page.get_by_placeholder("' + escapeStr(ph) + '")', confidence: 'high' };
    
    var labelFor = el.id ? document.querySelector('label[for="' + el.id + '"]') : null;
    if (labelFor) return { strategy: 'get_by_label', value: 'page.get_by_label("' + escapeStr(labelFor.textContent.trim()) + '")', confidence: 'high' };
    
    // Check for parent label
    var parentLabel = el.closest('label');
    if (parentLabel) {
      var labelText = parentLabel.textContent.trim().replace(el.textContent || '', '').trim();
      if (labelText) return { strategy: 'get_by_label', value: 'page.get_by_label("' + escapeStr(labelText) + '")', confidence: 'medium' };
    }
    
    var text = (el.textContent || '').trim().slice(0, 50);
    if (role && text && text.length < 40) return { strategy: 'get_by_role', value: 'page.get_by_role("' + role + '", name="' + escapeStr(text) + '")', confidence: 'medium' };
    if (text && text.length > 0 && text.length < 40) return { strategy: 'get_by_text', value: 'page.get_by_text("' + escapeStr(text) + '")', confidence: 'medium' };
    
    // Alt text for images
    var alt = el.getAttribute('alt');
    if (alt) return { strategy: 'get_by_alt_text', value: 'page.get_by_alt_text("' + escapeStr(alt) + '")', confidence: 'medium' };
    
    // Title attribute
    var title = el.getAttribute('title');
    if (title) return { strategy: 'get_by_title', value: 'page.get_by_title("' + escapeStr(title) + '")', confidence: 'medium' };
    
    // Fall back to CSS selector
    var selector = buildCssSelector(el);
    return { strategy: 'locator', value: 'page.locator("' + selector + '")', confidence: 'low' };
  }
  
  function escapeStr(str) {
    return (str || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, ' ').trim();
  }
  
  function buildCssSelector(el) {
    var tag = el.tagName.toLowerCase();
    if (el.id) return tag + '#' + el.id;
    if (el.className && typeof el.className === 'string') {
      var classes = el.className.trim().split(/\s+/).filter(function(c) { return c && !c.includes(':'); }).slice(0, 2);
      if (classes.length) return tag + '.' + classes.join('.');
    }
    var name = el.getAttribute('name');
    if (name) return tag + '[name="' + name + '"]';
    return tag;
  }
  
  function getParentContext(el) {
    var parents = [];
    var p = el.parentElement;
    var depth = 0;
    while (p && depth < 4) {
      var t = p.tagName.toLowerCase();
      if (['form','section','nav','header','main','aside','footer','dialog','article','fieldset'].indexOf(t) > -1 
          || p.getAttribute('role') || p.getAttribute('aria-label')) {
        parents.push({ 
          tag: t, 
          role: p.getAttribute('role'), 
          label: p.getAttribute('aria-label'),
          id: p.id || null
        });
      }
      p = p.parentElement; 
      depth++;
    }
    return parents;
  }
  
  function isVisible(el) {
    var rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return false;
    var style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
    return true;
  }
  
  function isInteractive(el) {
    var tag = el.tagName.toLowerCase();
    var interactiveTags = ['a', 'button', 'input', 'select', 'textarea', 'details', 'summary'];
    if (interactiveTags.indexOf(tag) > -1) return true;
    if (el.getAttribute('role')) return true;
    if (el.hasAttribute('onclick') || el.hasAttribute('tabindex')) return true;
    if (el.getAttribute('contenteditable') === 'true') return true;
    var style = window.getComputedStyle(el);
    if (style.cursor === 'pointer') return true;
    return false;
  }
  
  function scrapeElement(el) {
    var rect = el.getBoundingClientRect();
    var locator = getBestLocator(el);
    var tag = el.tagName.toLowerCase();
    
    return {
      timestamp: new Date().toISOString(),
      url: window.location.href,
      title: document.title,
      locator: locator,
      element: {
        tag: tag,
        type: el.type || null,
        text: (el.textContent || '').trim().slice(0, 100),
        ariaLabel: el.getAttribute('aria-label'),
        testId: el.getAttribute('data-testid'),
        placeholder: el.getAttribute('placeholder'),
        id: el.id || null,
        name: el.getAttribute('name'),
        role: el.getAttribute('role'),
        href: el.href || null,
        value: (tag === 'input' || tag === 'textarea' || tag === 'select') ? (el.value || '').slice(0, 50) : null,
        isInteractive: true,
        state: {
          disabled: !!el.disabled,
          checked: !!el.checked,
          required: !!el.required,
          readonly: !!el.readOnly,
          visible: true
        },
        position: { 
          x: Math.round(rect.x), 
          y: Math.round(rect.y), 
          width: Math.round(rect.width), 
          height: Math.round(rect.height) 
        }
      },
      parentContext: getParentContext(el),
      autoScraped: true
    };
  }
  
  // Main scraping function
  function scrapeAllElements() {
    var elements = [];
    var seen = new Set();
    
    // Selectors for interactive/testable elements
    var selectors = [
      'a[href]',
      'button',
      'input',
      'select',
      'textarea',
      '[role="button"]',
      '[role="link"]',
      '[role="checkbox"]',
      '[role="radio"]',
      '[role="tab"]',
      '[role="menuitem"]',
      '[role="option"]',
      '[role="switch"]',
      '[role="slider"]',
      '[role="spinbutton"]',
      '[role="combobox"]',
      '[role="listbox"]',
      '[role="searchbox"]',
      '[role="textbox"]',
      '[onclick]',
      '[data-testid]',
      '[tabindex]:not([tabindex="-1"])',
      'label',
      'h1', 'h2', 'h3', 'h4',
      'img[alt]',
      'summary',
      '[contenteditable="true"]'
    ];
    
    selectors.forEach(function(selector) {
      try {
        var nodes = document.querySelectorAll(selector);
        nodes.forEach(function(el) {
          // Skip if already seen or not visible
          if (seen.has(el)) return;
          if (!isVisible(el)) return;
          
          // Skip testgen UI elements
          if (el.closest('#__testgen_banner')) return;
          
          seen.add(el);
          elements.push(scrapeElement(el));
        });
      } catch (e) {
        console.warn('Selector failed:', selector, e);
      }
    });
    
    // Sort by position (top to bottom, left to right)
    elements.sort(function(a, b) {
      var ay = a.element.position.y;
      var by = b.element.position.y;
      if (Math.abs(ay - by) > 20) return ay - by;
      return a.element.position.x - b.element.position.x;
    });
    
    return {
      url: window.location.href,
      title: document.title,
      timestamp: new Date().toISOString(),
      totalElements: elements.length,
      elements: elements
    };
  }
  
  // Execute and return results
  return scrapeAllElements();
})();
