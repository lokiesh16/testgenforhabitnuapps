# # -*- coding: utf-8 -*-
# """
# HabitNu Web Test Script Generator
# Run: python server.py
# Open: http://localhost:5001
# """

# import os
# import re
# import json
# import queue
# import threading
# import urllib.request
# import urllib.error
# from datetime import datetime
# from flask import Flask, request, jsonify, send_from_directory
# from flask_cors import CORS
# from flask_socketio import SocketIO, emit

# app = Flask(__name__, static_folder=".")
# CORS(app)
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# TARGET_URL         = "https://app.habitnu.com"
# OUTPUT_DIR         = "./generated_scripts"
# CAPTURED_DIR       = "./captured_screens"
# PROMPT_CONFIG_FILE = "./prompt_config.json"

# os.makedirs(OUTPUT_DIR,   exist_ok=True)
# os.makedirs(CAPTURED_DIR, exist_ok=True)

# try:
#     from playwright.sync_api import sync_playwright
#     PLAYWRIGHT_AVAILABLE = True
# except ImportError:
#     PLAYWRIGHT_AVAILABLE = False
#     print("Playwright not installed. Run: pip install playwright && playwright install chromium")


# # ── Config ────────────────────────────────────────────────────────────────────

# def load_prompt_config():
#     if os.path.exists(PROMPT_CONFIG_FILE):
#         with open(PROMPT_CONFIG_FILE, "r", encoding="utf-8") as f:
#             return json.load(f)
#     return {}


# def build_framework_context():
#     cfg = load_prompt_config()
#     if not cfg:
#         return "Python + pytest + Playwright framework."

#     ls      = cfg.get("locator_strategy", {})
#     ls_text = "\n".join(f"  {k}: {v}" for k, v in ls.items())

#     po_text = ""
#     for name, po in cfg.get("page_objects", {}).items():
#         po_text += f"\n{name} ({po.get('file', '')}):\n"
#         for loc in po.get("playwright_locators", []):
#             po_text += f"    {loc}\n"
#         for m in po.get("methods", []):
#             po_text += f"    method: {m}\n"

#     bm_text  = "\n".join(f"  {k}: {v}" for k, v in cfg.get("base_page_methods", {}).items())
#     rules    = "\n".join(f"  - {v}" for v in cfg.get("rules", {}).values())
#     imports  = "\n".join(cfg.get("imports", []))
#     po_tmpl  = cfg.get("page_object_template", "")
#     tst_tmpl = cfg.get("test_method_template", "")

#     parts = [
#         "FRAMEWORK: " + cfg.get("framework", {}).get("name", "Web Automation"),
#         "STANDARD IMPORTS (always use exactly these):\n" + imports,
#         "LOCATOR STRATEGY (Playwright only, no XPath, no CSS strings):\n" + ls_text,
#         "AVAILABLE PAGE OBJECTS (only use these, never invent others):\n" + po_text,
#         "BASEPAGE NOTES:\n" + bm_text,
#         "PAGE OBJECT TEMPLATE:\n" + po_tmpl,
#         "TEST METHOD TEMPLATE:\n" + tst_tmpl,
#         "RULES (follow all strictly):\n" + rules,
#     ]
#     return "\n\n".join(parts)


# # ── JS loader ─────────────────────────────────────────────────────────────────

# def load_js(filename):
#     path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
#     if os.path.exists(path):
#         with open(path, "r", encoding="utf-8") as f:
#             return f.read()
#     return ""


# # ── Playwright worker ─────────────────────────────────────────────────────────

# pw_queue  = queue.Queue()
# pw_result = queue.Queue()
# session   = {"captures": [], "connected": False}


# def playwright_worker():
#     pw = browser = page = context = None

#     while True:
#         cmd    = pw_queue.get()
#         action = cmd.get("action")

#         if action == "launch":
#             try:
#                 injected_js = load_js("capture_inject.js")
#                 network_js  = load_js("network_inject.js")
#                 pw      = sync_playwright().start()
#                 browser = pw.chromium.launch(headless=False)
#                 context = browser.new_context(bypass_csp=True)
#                 if network_js:
#                     context.add_init_script(network_js)
#                 page = context.new_page()

#                 def inject_on_nav(frame):
#                     if frame == page.main_frame and injected_js:
#                         try:
#                             page.wait_for_timeout(300)
#                             page.evaluate(injected_js)
#                         except Exception:
#                             pass

#                 page.on("framenavigated", inject_on_nav)
#                 page.goto(cmd["url"], wait_until="domcontentloaded", timeout=30000)
#                 if injected_js:
#                     try:
#                         page.evaluate(injected_js)
#                     except Exception:
#                         pass
#                 pw_result.put({"ok": True, "title": page.title(), "url": page.url})
#             except Exception as e:
#                 pw_result.put({"ok": False, "error": str(e)})

#         elif action == "get_captures":
#             if page is None:
#                 pw_result.put({"ok": False, "error": "No browser open"}); continue
#             try:
#                 captures = page.evaluate("() => window.__testgenCaptures || []")
#                 network  = page.evaluate("() => window.__testgenNetworkLog || []")
#                 pw_result.put({"ok": True, "captures": captures, "network": network})
#             except Exception as e:
#                 pw_result.put({"ok": False, "error": str(e)})

#         elif action == "clear_page_captures":
#             if page is None:
#                 pw_result.put({"ok": False, "error": "No browser"}); continue
#             try:
#                 page.evaluate("() => { window.__testgenCaptures = []; }")
#                 pw_result.put({"ok": True})
#             except Exception as e:
#                 pw_result.put({"ok": False, "error": str(e)})

#         elif action == "navigate":
#             if page is None:
#                 pw_result.put({"ok": False, "error": "No browser"}); continue
#             try:
#                 page.goto(cmd["url"], wait_until="domcontentloaded", timeout=30000)
#                 pw_result.put({"ok": True, "url": page.url, "title": page.title()})
#             except Exception as e:
#                 pw_result.put({"ok": False, "error": str(e)})

#         elif action == "stop":
#             try:
#                 if browser: browser.close()
#                 if pw:      pw.stop()
#             except Exception:
#                 pass
#             page = browser = pw = context = None
#             pw_result.put({"ok": True})

#         elif action == "quit":
#             try:
#                 if browser: browser.close()
#                 if pw:      pw.stop()
#             except Exception:
#                 pass
#             break


# _pw_thread = threading.Thread(target=playwright_worker, daemon=True)
# _pw_thread.start()


# def pw_call(cmd, timeout=45):
#     pw_queue.put(cmd)
#     try:
#         return pw_result.get(timeout=timeout)
#     except queue.Empty:
#         return {"ok": False, "error": "Playwright command timed out"}


# # ── Capture helpers ───────────────────────────────────────────────────────────

# def enrich_with_network(captures, network_log):
#     for cap in captures:
#         ts = cap.get("timestamp")
#         if not ts:
#             cap["networkRequests"] = []
#             continue
#         try:
#             click_ts = datetime.fromisoformat(
#                 ts.replace("Z", "+00:00")
#             ).timestamp() * 1000
#             related = [
#                 n for n in network_log
#                 if click_ts <= n.get("ts", 0) <= click_ts + 2000
#                 and any(x in (n.get("url") or "") for x in ["/api/", "/graphql", ".json", "habitnu"])
#             ]
#             cap["networkRequests"] = related
#         except Exception:
#             cap["networkRequests"] = []
#     return captures


# def save_capture_group(name, captures, network):
#     enriched  = enrich_with_network(captures, network)
#     idx       = len(session["captures"]) + 1
#     timestamp = datetime.now().strftime("%H%M%S")
#     safe      = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:50]
#     filename  = f"{CAPTURED_DIR}/{idx:03d}_{safe}_{timestamp}.json"

#     with open(filename, "w", encoding="utf-8") as f:
#         json.dump({"name": name, "captures": enriched}, f, indent=2)

#     preview = []
#     for c in enriched:
#         loc = c.get("locator", {})
#         val = loc.get("value", "")
#         if val and "page.locator(\"" not in val:
#             preview.append({
#                 "locator":    val,
#                 "strategy":   loc.get("strategy", ""),
#                 "confidence": loc.get("confidence", ""),
#                 "text":       c.get("element", {}).get("text", "")[:50],
#                 "interactive":c.get("element", {}).get("isInteractive", False),
#                 "network":    len(c.get("networkRequests", [])) > 0,
#             })

#     capture = {
#         "name":    name,
#         "filename": filename,
#         "index":   idx,
#         "url":     enriched[0].get("url", "") if enriched else "",
#         "title":   enriched[0].get("title", "") if enriched else "",
#         "count":   len(enriched),
#         "preview": preview[:15],
#     }
#     session["captures"].append(capture)
#     return capture


# # ── Socket events ─────────────────────────────────────────────────────────────

# @socketio.on("connect")
# def on_connect():
#     emit("status", {"connected": session["connected"], "playwright": PLAYWRIGHT_AVAILABLE})


# @socketio.on("start_browser")
# def start_browser(data):
#     if not PLAYWRIGHT_AVAILABLE:
#         emit("error", {"msg": "Playwright not installed"}); return
#     url = data.get("url", TARGET_URL)
#     emit("log", {"msg": "Launching browser -> " + url})
#     res = pw_call({"action": "launch", "url": url})
#     if res["ok"]:
#         session["connected"] = True
#         emit("log",             {"msg": "Browser open - " + res.get("title", "") + ". Click any element to capture!"})
#         emit("browser_started", {"url": url, "title": res.get("title", "")})
#     else:
#         emit("error", {"msg": "Launch failed: " + res.get("error", "")})


# @socketio.on("save_captures")
# def save_captures(data):
#     name = data.get("name", "screen").strip() or "screen"
#     res  = pw_call({"action": "get_captures"})
#     if not res["ok"]:
#         emit("error", {"msg": res.get("error")}); return

#     raw = res.get("captures", [])
#     net = res.get("network", [])

#     if not raw:
#         emit("error", {"msg": "No elements clicked yet - click elements in the browser first!"}); return

#     capture = save_capture_group(name, raw, net)
#     pw_call({"action": "clear_page_captures"})

#     emit("screen_captured", {
#         "name":    capture["name"],
#         "index":   capture["index"],
#         "url":     capture["url"],
#         "title":   capture["title"],
#         "count":   capture["count"],
#         "preview": capture["preview"],
#     })
#     emit("log", {"msg": "Saved '" + name + "' - " + str(capture["count"]) + " elements captured"})


# @socketio.on("navigate")
# def navigate(data):
#     url = data.get("url", "")
#     res = pw_call({"action": "navigate", "url": url})
#     if res["ok"]:
#         emit("log",      {"msg": "-> " + res.get("url", "")})
#         emit("navigated",{"url": res.get("url"), "title": res.get("title")})
#     else:
#         emit("error", {"msg": "Navigate failed: " + res.get("error", "")})


# @socketio.on("stop_browser")
# def stop_browser():
#     pw_call({"action": "stop"})
#     session["connected"] = False
#     emit("browser_stopped", {})
#     emit("log", {"msg": "Browser closed."})


# @socketio.on("clear_captures")
# def clear_captures():
#     session["captures"] = []
#     emit("captures_cleared", {})


# # ── Extension capture ─────────────────────────────────────────────────────────

# @app.route("/api/extension-capture", methods=["POST"])
# def extension_capture():
#     data     = request.json
#     name     = data.get("name", "screen").strip() or "screen"
#     snapshot = data.get("snapshot", {})
#     if not snapshot:
#         return jsonify({"error": "No snapshot data"}), 400
#     elements = snapshot.get("elements", [])
#     capture  = save_capture_group(name, elements, [])
#     socketio.emit("screen_captured", {
#         "name":    capture["name"],
#         "index":   capture["index"],
#         "url":     capture["url"],
#         "title":   capture["title"],
#         "count":   capture["count"],
#         "preview": capture["preview"],
#     })
#     socketio.emit("log", {"msg": "[Extension] Captured: " + name})
#     return jsonify({"success": True, "index": capture["index"]})


# # ── Config endpoints ──────────────────────────────────────────────────────────

# @app.route("/api/config", methods=["GET"])
# def get_config():
#     return jsonify(load_prompt_config())


# @app.route("/api/config", methods=["POST"])
# def save_config_endpoint():
#     with open(PROMPT_CONFIG_FILE, "w", encoding="utf-8") as f:
#         json.dump(request.json, f, indent=2)
#     return jsonify({"saved": True})


# # ── REST ──────────────────────────────────────────────────────────────────────

# @app.route("/")
# def index():
#     return send_from_directory(".", "index.html")


# @app.route("/api/status")
# def status():
#     return jsonify({
#         "playwright_available": PLAYWRIGHT_AVAILABLE,
#         "connected":            session["connected"],
#         "captures":             len(session["captures"]),
#         "target_url":           TARGET_URL,
#     })


# @app.route("/api/captures/<int:idx>")
# def get_capture(idx):
#     for c in session["captures"]:
#         if c["index"] == idx:
#             return jsonify(c)
#     return "Not found", 404


# @app.route("/api/scripts/save", methods=["POST"])
# def save_scripts():
#     scripts = request.json.get("scripts", [])
#     saved   = []
#     for s in scripts:
#         path = os.path.join(OUTPUT_DIR, s["filename"])
#         with open(path, "w", encoding="utf-8") as f:
#             f.write(s["content"])
#         saved.append(path)
#     return jsonify({"saved": saved})


# @app.route("/api/generate", methods=["POST"])
# def generate():
#     data    = request.json
#     api_key = data.get("api_key", "").strip()
#     prompt  = data.get("prompt", "")

#     framework_context = build_framework_context()
#     prompt = prompt.replace("__FRAMEWORK_CONTEXT__", framework_context)

#     if not api_key:
#         return jsonify({"error": "API key required"}), 400

#     payload = json.dumps({
#         "model":      "claude-sonnet-4-20250514",
#         "max_tokens": data.get("max_tokens", 4000),
#         "messages":   [{"role": "user", "content": prompt}]
#     }).encode("utf-8")

#     req = urllib.request.Request(
#         "https://api.anthropic.com/v1/messages",
#         data    = payload,
#         headers = {
#             "Content-Type":      "application/json",
#             "x-api-key":         api_key,
#             "anthropic-version": "2023-06-01",
#         },
#         method = "POST"
#     )
#     try:
#         with urllib.request.urlopen(req) as resp:
#             return jsonify(json.loads(resp.read().decode("utf-8")))
#     except urllib.error.HTTPError as e:
#         return jsonify({"error": e.read().decode("utf-8")}), e.code
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# if __name__ == "__main__":
#     print("=" * 55)
#     print("  HabitNu Web Test Script Generator")
#     print("=" * 55)
#     print(f"  Playwright : {PLAYWRIGHT_AVAILABLE}")
#     print(f"  Target URL : {TARGET_URL}")
#     print("=" * 55)
#     print("\n  Open http://localhost:5001 in your browser\n")
#     socketio.run(app, host="0.0.0.0", port=5001, debug=False)



# # -*- coding: utf-8 -*-
# # -*- coding: utf-8 -*-
# """
# HabitNu Web Test Script Generator
# Run: python server.py
# Open: http://localhost:5001
# """

# import os
# import re
# import json
# import queue
# import threading
# import urllib.request
# import urllib.error
# from datetime import datetime
# from flask import Flask, request, jsonify, send_from_directory
# from flask_cors import CORS
# from flask_socketio import SocketIO, emit

# app = Flask(__name__, static_folder=".")
# CORS(app)
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# TARGET_URL         = "https://app.habitnu.com"
# OUTPUT_DIR         = "./generated_scripts"
# CAPTURED_DIR       = "./captured_screens"
# PROMPT_CONFIG_FILE = "./prompt_config.json"

# os.makedirs(OUTPUT_DIR,   exist_ok=True)
# os.makedirs(CAPTURED_DIR, exist_ok=True)

# try:
#     from playwright.sync_api import sync_playwright
#     PLAYWRIGHT_AVAILABLE = True
# except ImportError:
#     PLAYWRIGHT_AVAILABLE = False
#     print("Playwright not installed. Run: pip install playwright && playwright install chromium")


# # ── Config ────────────────────────────────────────────────────────────────────

# def load_prompt_config():
#     if os.path.exists(PROMPT_CONFIG_FILE):
#         with open(PROMPT_CONFIG_FILE, "r", encoding="utf-8") as f:
#             return json.load(f)
#     return {}


# def build_framework_context():
#     cfg = load_prompt_config()
#     if not cfg:
#         return "Python + pytest + Playwright framework."

#     ls      = cfg.get("locator_strategy", {})
#     ls_text = "\n".join(f"  {k}: {v}" for k, v in ls.items())

#     po_text = ""
#     for name, po in cfg.get("page_objects", {}).items():
#         po_text += f"\n{name} ({po.get('file', '')}):\n"
#         for loc in po.get("playwright_locators", []):
#             po_text += f"    {loc}\n"
#         for m in po.get("methods", []):
#             po_text += f"    method: {m}\n"

#     bm_text  = "\n".join(f"  {k}: {v}" for k, v in cfg.get("base_page_methods", {}).items())
#     rules    = "\n".join(f"  - {v}" for v in cfg.get("rules", {}).values())
#     imports  = "\n".join(cfg.get("imports", []))
#     po_tmpl  = cfg.get("page_object_template", "")
#     tst_tmpl = cfg.get("test_method_template", "")

#     parts = [
#         "FRAMEWORK: " + cfg.get("framework", {}).get("name", "Web Automation"),
#         "STANDARD IMPORTS (always use exactly these):\n" + imports,
#         "LOCATOR STRATEGY (Playwright only, no XPath, no CSS strings):\n" + ls_text,
#         "AVAILABLE PAGE OBJECTS (only use these, never invent others):\n" + po_text,
#         "BASEPAGE NOTES:\n" + bm_text,
#         "PAGE OBJECT TEMPLATE:\n" + po_tmpl,
#         "TEST METHOD TEMPLATE:\n" + tst_tmpl,
#         "RULES (follow all strictly):\n" + rules,
#     ]
#     return "\n\n".join(parts)


# # ── JS loader ─────────────────────────────────────────────────────────────────

# def load_js(filename):
#     path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
#     if os.path.exists(path):
#         with open(path, "r", encoding="utf-8") as f:
#             return f.read()
#     return ""


# # ── Playwright worker ─────────────────────────────────────────────────────────

# pw_queue  = queue.Queue()
# pw_result = queue.Queue()
# session   = {"captures": [], "connected": False}


# def playwright_worker():
#     pw = browser = page = context = None

#     while True:
#         cmd    = pw_queue.get()
#         action = cmd.get("action")

#         if action == "launch":
#             try:
#                 injected_js = load_js("capture_inject.js")
#                 network_js  = load_js("network_inject.js")
#                 pw      = sync_playwright().start()
#                 browser = pw.chromium.launch(headless=False)
#                 context = browser.new_context(bypass_csp=True)
#                 if network_js:
#                     context.add_init_script(network_js)
#                 page = context.new_page()

#                 # Persist captures across navigations in server-side buffer
#                 server_captures = []
#                 server_network  = []

#                 def inject_on_nav(frame):
#                     nonlocal server_captures, server_network
#                     if frame == page.main_frame and injected_js:
#                         # Harvest captures from previous page before they are lost
#                         try:
#                             prev = page.evaluate("() => window.__testgenCaptures || []")
#                             prev_net = page.evaluate("() => window.__testgenNetworkLog || []")
#                             if prev:
#                                 server_captures.extend(prev)
#                                 server_network.extend(prev_net)
#                         except Exception:
#                             pass
#                         # Inject UI on new page
#                         try:
#                             page.wait_for_timeout(400)
#                             page.evaluate(injected_js)
#                         except Exception as e:
#                             if "Execution context was destroyed" not in str(e):
#                                 print(f"Inject warning: {e}")

#                 # Store references so get_captures can access them
#                 page._server_captures = server_captures
#                 page._server_network  = server_network

#                 page.on("framenavigated", inject_on_nav)
#                 page.goto(cmd["url"], wait_until="domcontentloaded", timeout=30000)
#                 if injected_js:
#                     try:
#                         page.evaluate(injected_js)
#                     except Exception:
#                         pass
#                 pw_result.put({"ok": True, "title": page.title(), "url": page.url})
#             except Exception as e:
#                 pw_result.put({"ok": False, "error": str(e)})

#         elif action == "get_captures":
#             if page is None:
#                 pw_result.put({"ok": False, "error": "No browser open"}); continue
#             try:
#                 # Get current page captures
#                 current = page.evaluate("() => window.__testgenCaptures || []")
#                 current_net = page.evaluate("() => window.__testgenNetworkLog || []")
#                 # Merge with server-side buffer (from previous pages)
#                 buf     = getattr(page, "_server_captures", [])
#                 buf_net = getattr(page, "_server_network", [])
#                 all_captures = buf + current
#                 all_network  = buf_net + current_net
#                 pw_result.put({"ok": True, "captures": all_captures, "network": all_network})
#             except Exception as e:
#                 pw_result.put({"ok": False, "error": str(e)})

#         elif action == "clear_page_captures":
#             if page is None:
#                 pw_result.put({"ok": False, "error": "No browser"}); continue
#             try:
#                 page.evaluate("() => { window.__testgenCaptures = []; window.__testgenNetworkLog = []; }")
#                 # Also clear server-side buffer
#                 if hasattr(page, "_server_captures"):
#                     page._server_captures.clear()
#                 if hasattr(page, "_server_network"):
#                     page._server_network.clear()
#                 pw_result.put({"ok": True})
#             except Exception as e:
#                 pw_result.put({"ok": False, "error": str(e)})

#         elif action == "navigate":
#             if page is None:
#                 pw_result.put({"ok": False, "error": "No browser"}); continue
#             try:
#                 page.goto(cmd["url"], wait_until="domcontentloaded", timeout=30000)
#                 pw_result.put({"ok": True, "url": page.url, "title": page.title()})
#             except Exception as e:
#                 pw_result.put({"ok": False, "error": str(e)})

#         elif action == "stop":
#             try:
#                 if browser: browser.close()
#                 if pw:      pw.stop()
#             except Exception:
#                 pass
#             page = browser = pw = context = None
#             pw_result.put({"ok": True})

#         elif action == "quit":
#             try:
#                 if browser: browser.close()
#                 if pw:      pw.stop()
#             except Exception:
#                 pass
#             break


# _pw_thread = threading.Thread(target=playwright_worker, daemon=True)
# _pw_thread.start()


# def pw_call(cmd, timeout=45):
#     pw_queue.put(cmd)
#     try:
#         return pw_result.get(timeout=timeout)
#     except queue.Empty:
#         return {"ok": False, "error": "Playwright command timed out"}


# # ── Capture helpers ───────────────────────────────────────────────────────────

# def enrich_with_network(captures, network_log):
#     for cap in captures:
#         ts = cap.get("timestamp")
#         if not ts:
#             cap["networkRequests"] = []
#             continue
#         try:
#             click_ts = datetime.fromisoformat(
#                 ts.replace("Z", "+00:00")
#             ).timestamp() * 1000
#             related = [
#                 n for n in network_log
#                 if click_ts <= n.get("ts", 0) <= click_ts + 2000
#                 and any(x in (n.get("url") or "") for x in ["/api/", "/graphql", ".json", "habitnu"])
#             ]
#             cap["networkRequests"] = related
#         except Exception:
#             cap["networkRequests"] = []
#     return captures


# def save_capture_group(name, captures, network):
#     enriched  = enrich_with_network(captures, network)
#     idx       = len(session["captures"]) + 1
#     timestamp = datetime.now().strftime("%H%M%S")
#     safe      = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:50]
#     filename  = f"{CAPTURED_DIR}/{idx:03d}_{safe}_{timestamp}.json"

#     with open(filename, "w", encoding="utf-8") as f:
#         json.dump({"name": name, "captures": enriched}, f, indent=2)

#     preview = []
#     for c in enriched:
#         loc = c.get("locator", {})
#         val = loc.get("value", "")
#         if val and "page.locator(\"" not in val:
#             preview.append({
#                 "locator":    val,
#                 "strategy":   loc.get("strategy", ""),
#                 "confidence": loc.get("confidence", ""),
#                 "text":       c.get("element", {}).get("text", "")[:50],
#                 "interactive":c.get("element", {}).get("isInteractive", False),
#                 "network":    len(c.get("networkRequests", [])) > 0,
#             })

#     capture = {
#         "name":    name,
#         "filename": filename,
#         "index":   idx,
#         "url":     enriched[0].get("url", "") if enriched else "",
#         "title":   enriched[0].get("title", "") if enriched else "",
#         "count":   len(enriched),
#         "preview": preview[:15],
#     }
#     session["captures"].append(capture)
#     return capture


# # ── Socket events ─────────────────────────────────────────────────────────────

# @socketio.on("connect")
# def on_connect():
#     emit("status", {"connected": session["connected"], "playwright": PLAYWRIGHT_AVAILABLE})


# @socketio.on("start_browser")
# def start_browser(data):
#     if not PLAYWRIGHT_AVAILABLE:
#         emit("error", {"msg": "Playwright not installed"}); return
#     url = data.get("url", TARGET_URL)
#     emit("log", {"msg": "Launching browser -> " + url})
#     res = pw_call({"action": "launch", "url": url})
#     if res["ok"]:
#         session["connected"] = True
#         emit("log",             {"msg": "Browser open - " + res.get("title", "") + ". Click any element to capture!"})
#         emit("browser_started", {"url": url, "title": res.get("title", "")})
#     else:
#         emit("error", {"msg": "Launch failed: " + res.get("error", "")})


# @socketio.on("save_captures")
# def save_captures(data):
#     name = data.get("name", "screen").strip() or "screen"
#     res  = pw_call({"action": "get_captures"})
#     if not res["ok"]:
#         emit("error", {"msg": res.get("error")}); return

#     raw = res.get("captures", [])
#     net = res.get("network", [])

#     if not raw:
#         emit("error", {"msg": "No elements clicked yet - click elements in the browser first!"}); return

#     capture = save_capture_group(name, raw, net)
#     pw_call({"action": "clear_page_captures"})

#     emit("screen_captured", {
#         "name":    capture["name"],
#         "index":   capture["index"],
#         "url":     capture["url"],
#         "title":   capture["title"],
#         "count":   capture["count"],
#         "preview": capture["preview"],
#     })
#     emit("log", {"msg": "Saved '" + name + "' - " + str(capture["count"]) + " elements captured"})


# @socketio.on("navigate")
# def navigate(data):
#     url = data.get("url", "")
#     res = pw_call({"action": "navigate", "url": url})
#     if res["ok"]:
#         emit("log",      {"msg": "-> " + res.get("url", "")})
#         emit("navigated",{"url": res.get("url"), "title": res.get("title")})
#     else:
#         emit("error", {"msg": "Navigate failed: " + res.get("error", "")})


# @socketio.on("stop_browser")
# def stop_browser():
#     pw_call({"action": "stop"})
#     session["connected"] = False
#     emit("browser_stopped", {})
#     emit("log", {"msg": "Browser closed."})


# @socketio.on("clear_captures")
# def clear_captures():
#     session["captures"] = []
#     emit("captures_cleared", {})


# # ── Extension capture ─────────────────────────────────────────────────────────

# @app.route("/api/extension-capture", methods=["POST"])
# def extension_capture():
#     data     = request.json
#     name     = data.get("name", "screen").strip() or "screen"
#     snapshot = data.get("snapshot", {})
#     if not snapshot:
#         return jsonify({"error": "No snapshot data"}), 400
#     elements = snapshot.get("elements", [])
#     capture  = save_capture_group(name, elements, [])
#     socketio.emit("screen_captured", {
#         "name":    capture["name"],
#         "index":   capture["index"],
#         "url":     capture["url"],
#         "title":   capture["title"],
#         "count":   capture["count"],
#         "preview": capture["preview"],
#     })
#     socketio.emit("log", {"msg": "[Extension] Captured: " + name})
#     return jsonify({"success": True, "index": capture["index"]})


# # ── Config endpoints ──────────────────────────────────────────────────────────

# @app.route("/api/config", methods=["GET"])
# def get_config():
#     return jsonify(load_prompt_config())


# @app.route("/api/config", methods=["POST"])
# def save_config_endpoint():
#     with open(PROMPT_CONFIG_FILE, "w", encoding="utf-8") as f:
#         json.dump(request.json, f, indent=2)
#     return jsonify({"saved": True})


# # ── REST ──────────────────────────────────────────────────────────────────────

# @app.route("/")
# def index():
#     return send_from_directory(".", "index.html")


# @app.route("/api/status")
# def status():
#     return jsonify({
#         "playwright_available": PLAYWRIGHT_AVAILABLE,
#         "connected":            session["connected"],
#         "captures":             len(session["captures"]),
#         "target_url":           TARGET_URL,
#     })


# @app.route("/api/captures/<int:idx>")
# def get_capture(idx):
#     for c in session["captures"]:
#         if c["index"] == idx:
#             return jsonify(c)
#     return "Not found", 404


# @app.route("/api/scripts/save", methods=["POST"])
# def save_scripts():
#     scripts = request.json.get("scripts", [])
#     saved   = []
#     for s in scripts:
#         path = os.path.join(OUTPUT_DIR, s["filename"])
#         with open(path, "w", encoding="utf-8") as f:
#             f.write(s["content"])
#         saved.append(path)
#     return jsonify({"saved": saved})


# @app.route("/api/generate", methods=["POST"])
# def generate():
#     data    = request.json
#     api_key = data.get("api_key", "").strip()
#     prompt  = data.get("prompt", "")

#     framework_context = build_framework_context()
#     prompt = prompt.replace("__FRAMEWORK_CONTEXT__", framework_context)

#     if not api_key:
#         return jsonify({"error": "API key required"}), 400

#     payload = json.dumps({
#         "model":      "claude-sonnet-4-20250514",
#         "max_tokens": data.get("max_tokens", 4000),
#         "messages":   [{"role": "user", "content": prompt}]
#     }).encode("utf-8")

#     req = urllib.request.Request(
#         "https://api.anthropic.com/v1/messages",
#         data    = payload,
#         headers = {
#             "Content-Type":      "application/json",
#             "x-api-key":         api_key,
#             "anthropic-version": "2023-06-01",
#         },
#         method = "POST"
#     )
#     try:
#         with urllib.request.urlopen(req) as resp:
#             return jsonify(json.loads(resp.read().decode("utf-8")))
#     except urllib.error.HTTPError as e:
#         return jsonify({"error": e.read().decode("utf-8")}), e.code
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# if __name__ == "__main__":
#     print("=" * 55)
#     print("  HabitNu Web Test Script Generator")
#     print("=" * 55)
#     print(f"  Playwright : {PLAYWRIGHT_AVAILABLE}")
#     print(f"  Target URL : {TARGET_URL}")
#     print("=" * 55)
#     print("\n  Open http://localhost:5001 in your browser\n")
#     socketio.run(app, host="0.0.0.0", port=5001, debug=False)








# -*- coding: utf-8 -*-
"""
HabitNu Web Test Script Generator
Run: python server.py
Open: http://localhost:5001
"""

import os
import re
import json
import queue
import threading
import urllib.request
import urllib.error
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit

app = Flask(__name__, static_folder=".")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

TARGET_URL         = "https://app.habitnu.com"
OUTPUT_DIR         = "./generated_scripts"
CAPTURED_DIR       = "./captured_screens"
PROMPT_CONFIG_FILE = "./prompt_config.json"

os.makedirs(OUTPUT_DIR,   exist_ok=True)
os.makedirs(CAPTURED_DIR, exist_ok=True)

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright not installed. Run: pip install playwright && playwright install chromium")


# ── Config ────────────────────────────────────────────────────────────────────

def load_prompt_config():
    if os.path.exists(PROMPT_CONFIG_FILE):
        with open(PROMPT_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def build_framework_context():
    cfg = load_prompt_config()
    if not cfg:
        return "Python + pytest + Playwright framework."

    ls      = cfg.get("locator_strategy", {})
    ls_text = "\n".join(f"  {k}: {v}" for k, v in ls.items())

    po_text = ""
    for name, po in cfg.get("page_objects", {}).items():
        po_text += f"\n{name} ({po.get('file', '')}):\n"
        for loc in po.get("playwright_locators", []):
            po_text += f"    {loc}\n"
        for m in po.get("methods", []):
            po_text += f"    method: {m}\n"

    bm_text  = "\n".join(f"  {k}: {v}" for k, v in cfg.get("base_page_methods", {}).items())
    rules    = "\n".join(f"  - {v}" for v in cfg.get("rules", {}).values())
    imports  = "\n".join(cfg.get("imports", []))
    po_tmpl  = cfg.get("page_object_template", "")
    tst_tmpl = cfg.get("test_method_template", "")

    parts = [
        "FRAMEWORK: " + cfg.get("framework", {}).get("name", "Web Automation"),
        "STANDARD IMPORTS (always use exactly these):\n" + imports,
        "LOCATOR STRATEGY (Playwright only, no XPath, no CSS strings):\n" + ls_text,
        "AVAILABLE PAGE OBJECTS (only use these, never invent others):\n" + po_text,
        "BASEPAGE NOTES:\n" + bm_text,
        "PAGE OBJECT TEMPLATE:\n" + po_tmpl,
        "TEST METHOD TEMPLATE:\n" + tst_tmpl,
        "RULES (follow all strictly):\n" + rules,
    ]
    return "\n\n".join(parts)


# ── JS loader ─────────────────────────────────────────────────────────────────

def load_js(filename):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


# ── Network helpers ───────────────────────────────────────────────────────────

def is_api_url(url):
    """Check if URL is likely an API call (not static asset)"""
    if not url:
        return False
    url_lower = url.lower()
    # Skip static assets
    skip_patterns = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', 
                     '.woff', '.woff2', '.ttf', '.eot', 'fonts.googleapis', 'cdn.']
    if any(p in url_lower for p in skip_patterns):
        return False
    # API patterns
    api_patterns = ['/api/', '/graphql', '/v1/', '/v2/', '/v3/', '/rest/', '.json', 
                    '/auth/', '/login', '/logout', '/users', '/data', '/query', 
                    '/mutation', '/search', '/gql', '/rpc', 'amazonaws.com', 
                    'firebase', 'supabase', 'hasura']
    return any(p in url_lower for p in api_patterns)


# ── Playwright worker ─────────────────────────────────────────────────────────

pw_queue  = queue.Queue()
pw_result = queue.Queue()
session   = {"captures": [], "connected": False}



def playwright_worker():
    pw = browser = page = context = None

    while True:
        cmd    = pw_queue.get()
        action = cmd.get("action")

        if action == "launch":
            try:
                injected_js = load_js("capture_inject.js")
                network_js  = load_js("network_inject.js")
                pw      = sync_playwright().start()
                browser = pw.chromium.launch(headless=False)
                context = browser.new_context(bypass_csp=True)
                if network_js:
                    context.add_init_script(network_js)
                page = context.new_page()

                # Persist captures across navigations in server-side buffer
                server_captures = []
                server_network  = []
                
                # Native Playwright network interception (more reliable)
                playwright_network_log = []
                
                def on_request(request):
                    try:
                        entry = {
                            "type": "playwright",
                            "url": request.url,
                            "method": request.method,
                            "requestHeaders": dict(request.headers) if request.headers else {},
                            "requestBody": request.post_data[:2000] if request.post_data else None,
                            "ts": int(datetime.now().timestamp() * 1000),
                            "timestamp": datetime.now().isoformat(),
                            "resourceType": request.resource_type,
                            "isApi": is_api_url(request.url),
                            "status": None,
                            "responseHeaders": {},
                            "responseBody": None,
                            "duration": None
                        }
                        playwright_network_log.append(entry)
                        if len(playwright_network_log) > 200:
                            playwright_network_log.pop(0)
                    except Exception as e:
                        print(f"Request capture error: {e}")
                
                def on_response(response):
                    try:
                        # Find matching request
                        for entry in reversed(playwright_network_log):
                            if entry.get("url") == response.url and entry.get("status") is None:
                                entry["status"] = response.status
                                entry["statusText"] = response.status_text
                                entry["responseHeaders"] = dict(response.headers) if response.headers else {}
                                try:
                                    body = response.text()
                                    entry["responseBody"] = body[:2000] if body else None
                                except:
                                    entry["responseBody"] = "[unable to read]"
                                break
                    except Exception as e:
                        print(f"Response capture error: {e}")
                
                page.on("request", on_request)
                page.on("response", on_response)
                page._playwright_network_log = playwright_network_log

                def inject_on_nav(frame):
                    nonlocal server_captures, server_network
                    if frame == page.main_frame and injected_js:
                        # Harvest captures from previous page before they are lost
                        try:
                            prev = page.evaluate("() => window.__testgenCaptures || []")
                            prev_net = page.evaluate("() => window.__testgenNetworkLog || []")
                            if prev:
                                server_captures.extend(prev)
                                server_network.extend(prev_net)
                        except Exception:
                            pass
                        # Inject UI on new page
                        try:
                            page.wait_for_timeout(400)
                            page.evaluate(injected_js)
                        except Exception as e:
                            if "Execution context was destroyed" not in str(e):
                                print(f"Inject warning: {e}")

                # Store references so get_captures can access them
                page._server_captures = server_captures
                page._server_network  = server_network

                page.on("framenavigated", inject_on_nav)
                page.goto(cmd["url"], wait_until="domcontentloaded", timeout=30000)
                if injected_js:
                    try:
                        page.evaluate(injected_js)
                    except Exception:
                        pass
                pw_result.put({"ok": True, "title": page.title(), "url": page.url})
            except Exception as e:
                pw_result.put({"ok": False, "error": str(e)})

        elif action == "get_captures":
            if page is None:
                pw_result.put({"ok": False, "error": "No browser open"}); continue
            try:
                # Get current page captures
                current = page.evaluate("() => window.__testgenCaptures || []")
                current_net = page.evaluate("() => window.__testgenNetworkLog || []")
                # Merge with server-side buffer (from previous pages)
                buf     = getattr(page, "_server_captures", [])
                buf_net = getattr(page, "_server_network", [])
                all_captures = buf + current
                all_network  = buf_net + current_net
                pw_result.put({"ok": True, "captures": all_captures, "network": all_network})
            except Exception as e:
                pw_result.put({"ok": False, "error": str(e)})

        elif action == "clear_page_captures":
            if page is None:
                pw_result.put({"ok": False, "error": "No browser"}); continue
            try:
                page.evaluate("() => { window.__testgenCaptures = []; window.__testgenNetworkLog = []; }")
                # Also clear server-side buffer
                if hasattr(page, "_server_captures"):
                    page._server_captures.clear()
                if hasattr(page, "_server_network"):
                    page._server_network.clear()
                pw_result.put({"ok": True})
            except Exception as e:
                pw_result.put({"ok": False, "error": str(e)})

        elif action == "scrape_all":
            if page is None:
                pw_result.put({"ok": False, "error": "No browser open"}); continue
            try:
                scrape_js = load_js("scrape_all_inject.js")
                if not scrape_js:
                    pw_result.put({"ok": False, "error": "scrape_all_inject.js not found"}); continue
                result = page.evaluate(scrape_js)
                pw_result.put({"ok": True, "result": result})
            except Exception as e:
                pw_result.put({"ok": False, "error": str(e)})

        elif action == "get_network_log":
            if page is None:
                pw_result.put({"ok": False, "error": "No browser open"}); continue
            try:
                # Use Playwright's native network log (more reliable)
                network = getattr(page, "_playwright_network_log", [])
                # Also try to get from injected JS as fallback
                try:
                    js_network = page.evaluate("() => window.__testgenNetworkLog || []")
                    if js_network:
                        # Merge, avoiding duplicates by URL+timestamp
                        seen = set((n.get("url"), n.get("ts")) for n in network)
                        for n in js_network:
                            key = (n.get("url"), n.get("ts"))
                            if key not in seen:
                                network.append(n)
                                seen.add(key)
                except:
                    pass
                # Filter to only API calls if requested
                if cmd.get("api_only", False):
                    network = [n for n in network if n.get("isApi", False)]
                # Sort by timestamp
                network = sorted(network, key=lambda x: x.get("ts", 0))
                pw_result.put({"ok": True, "network": network})
            except Exception as e:
                pw_result.put({"ok": False, "error": str(e)})

        elif action == "clear_network_log":
            if page is None:
                pw_result.put({"ok": False, "error": "No browser open"}); continue
            try:
                page.evaluate("() => { window.__testgenNetworkLog = []; }")
                # Also clear Playwright native log
                if hasattr(page, "_playwright_network_log"):
                    page._playwright_network_log.clear()
                pw_result.put({"ok": True})
            except Exception as e:
                pw_result.put({"ok": False, "error": str(e)})

        elif action == "navigate":
            if page is None:
                pw_result.put({"ok": False, "error": "No browser"}); continue
            try:
                page.goto(cmd["url"], wait_until="domcontentloaded", timeout=30000)
                pw_result.put({"ok": True, "url": page.url, "title": page.title()})
            except Exception as e:
                pw_result.put({"ok": False, "error": str(e)})

        elif action == "run_test_step":
            if page is None:
                pw_result.put({"ok": False, "error": "No browser open"}); continue
            try:
                step = cmd.get("step", {})
                step_type = step.get("type", "")
                selector = step.get("selector", "")
                value = step.get("value", "")
                timeout = step.get("timeout", 10000)
                
                result = {"ok": True, "step": step}
                
                # Helper function to get locator from various formats
                def get_locator(sel):
                    """Convert Playwright locator string to actual locator object"""
                    if not sel:
                        return None
                    sel = sel.strip()
                    
                    import re as regex
                    
                    # get_by_placeholder("...")
                    m = regex.match(r'page\.get_by_placeholder\(["\'](.+?)["\']\)', sel)
                    if m:
                        return page.get_by_placeholder(m.group(1))
                    
                    # get_by_role("...", name="...")
                    m = regex.match(r'page\.get_by_role\(["\'](\w+)["\'],?\s*name=["\'](.+?)["\']\)', sel)
                    if m:
                        return page.get_by_role(m.group(1), name=m.group(2))
                    
                    # get_by_role("...") without name
                    m = regex.match(r'page\.get_by_role\(["\'](\w+)["\']\)', sel)
                    if m:
                        return page.get_by_role(m.group(1))
                    
                    # get_by_text("...")
                    m = regex.match(r'page\.get_by_text\(["\'](.+?)["\']\)', sel)
                    if m:
                        return page.get_by_text(m.group(1))
                    
                    # get_by_label("...")
                    m = regex.match(r'page\.get_by_label\(["\'](.+?)["\']\)', sel)
                    if m:
                        return page.get_by_label(m.group(1))
                    
                    # get_by_test_id("...")
                    m = regex.match(r'page\.get_by_test_id\(["\'](.+?)["\']\)', sel)
                    if m:
                        return page.get_by_test_id(m.group(1))
                    
                    # get_by_alt_text("...")
                    m = regex.match(r'page\.get_by_alt_text\(["\'](.+?)["\']\)', sel)
                    if m:
                        return page.get_by_alt_text(m.group(1))
                    
                    # get_by_title("...")
                    m = regex.match(r'page\.get_by_title\(["\'](.+?)["\']\)', sel)
                    if m:
                        return page.get_by_title(m.group(1))
                    
                    # page.locator("...")
                    m = regex.match(r'page\.locator\(["\'](.+?)["\']\)', sel)
                    if m:
                        return page.locator(m.group(1))
                    
                    # Default: treat as CSS/XPath selector
                    return page.locator(sel)
                
                if step_type == "goto":
                    page.goto(value, wait_until="domcontentloaded", timeout=30000)
                    result["url"] = page.url
                    
                elif step_type == "click":
                    element = get_locator(selector).first
                    element.wait_for(state="visible", timeout=timeout)
                    element.click()
                    
                elif step_type == "fill":
                    element = get_locator(selector).first
                    element.wait_for(state="visible", timeout=timeout)
                    element.fill(value)
                    
                elif step_type == "type":
                    element = get_locator(selector).first
                    element.wait_for(state="visible", timeout=timeout)
                    element.type(value, delay=50)
                    
                elif step_type == "press":
                    if selector:
                        get_locator(selector).first.press(value)
                    else:
                        page.keyboard.press(value)
                    
                elif step_type == "select":
                    element = get_locator(selector).first
                    element.select_option(value)
                    
                elif step_type == "check":
                    element = get_locator(selector).first
                    element.check()
                    
                elif step_type == "uncheck":
                    element = get_locator(selector).first
                    element.uncheck()
                    
                elif step_type == "wait":
                    page.wait_for_timeout(int(value) if value else 1000)
                    
                elif step_type == "wait_for":
                    get_locator(selector).first.wait_for(state="visible", timeout=timeout)
                    
                elif step_type == "wait_for_url":
                    page.wait_for_url(value, timeout=timeout)
                    
                elif step_type == "assert_visible":
                    element = get_locator(selector).first
                    is_visible = element.is_visible()
                    if not is_visible:
                        raise AssertionError(f"Element not visible: {selector}")
                    
                elif step_type == "assert_text":
                    element = get_locator(selector).first
                    text = element.text_content() or ""
                    if value not in text:
                        raise AssertionError(f"Expected text '{value}' not found in '{text[:100]}'")
                    
                elif step_type == "assert_value":
                    element = get_locator(selector).first
                    actual = element.input_value()
                    if actual != value:
                        raise AssertionError(f"Expected value '{value}', got '{actual}'")
                    
                elif step_type == "assert_url":
                    if value not in page.url:
                        raise AssertionError(f"Expected URL to contain '{value}', got '{page.url}'")
                    
                elif step_type == "assert_title":
                    if value not in page.title():
                        raise AssertionError(f"Expected title to contain '{value}', got '{page.title()}'")
                    
                elif step_type == "screenshot":
                    screenshots_dir = "./test_screenshots"
                    os.makedirs(screenshots_dir, exist_ok=True)
                    filename = f"{screenshots_dir}/{value or 'step'}_{datetime.now().strftime('%H%M%S')}.png"
                    page.screenshot(path=filename)
                    result["screenshot"] = filename
                    
                else:
                    raise ValueError(f"Unknown step type: {step_type}")
                
                result["url"] = page.url
                result["title"] = page.title()
                pw_result.put(result)
                
            except Exception as e:
                pw_result.put({"ok": False, "error": str(e), "step": cmd.get("step", {})})

        elif action == "stop":
            try:
                if browser: browser.close()
                if pw:      pw.stop()
            except Exception:
                pass
            page = browser = pw = context = None
            pw_result.put({"ok": True})

        elif action == "quit":
            try:
                if browser: browser.close()
                if pw:      pw.stop()
            except Exception:
                pass
            break


_pw_thread = threading.Thread(target=playwright_worker, daemon=True)
_pw_thread.start()


def pw_call(cmd, timeout=45):
    pw_queue.put(cmd)
    try:
        return pw_result.get(timeout=timeout)
    except queue.Empty:
        return {"ok": False, "error": "Playwright command timed out"}


# ── Capture helpers ───────────────────────────────────────────────────────────

def enrich_with_network(captures, network_log):
    for cap in captures:
        ts = cap.get("timestamp")
        if not ts:
            cap["networkRequests"] = []
            continue
        try:
            click_ts = datetime.fromisoformat(
                ts.replace("Z", "+00:00")
            ).timestamp() * 1000
            related = [
                n for n in network_log
                if click_ts <= n.get("ts", 0) <= click_ts + 2000
                and any(x in (n.get("url") or "") for x in ["/api/", "/graphql", ".json", "habitnu"])
            ]
            cap["networkRequests"] = related
        except Exception:
            cap["networkRequests"] = []
    return captures


def save_capture_group(name, captures, network):
    enriched  = enrich_with_network(captures, network)
    idx       = len(session["captures"]) + 1
    timestamp = datetime.now().strftime("%H%M%S")
    safe      = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:50]
    filename  = f"{CAPTURED_DIR}/{idx:03d}_{safe}_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump({"name": name, "captures": enriched}, f, indent=2)

    preview = []
    for c in enriched:
        loc = c.get("locator", {})
        val = loc.get("value", "")
        if val and "page.locator(\"" not in val:
            preview.append({
                "locator":    val,
                "strategy":   loc.get("strategy", ""),
                "confidence": loc.get("confidence", ""),
                "text":       c.get("element", {}).get("text", "")[:50],
                "interactive":c.get("element", {}).get("isInteractive", False),
                "network":    len(c.get("networkRequests", [])) > 0,
            })

    capture = {
        "name":    name,
        "filename": filename,
        "index":   idx,
        "url":     enriched[0].get("url", "") if enriched else "",
        "title":   enriched[0].get("title", "") if enriched else "",
        "count":   len(enriched),
        "preview": preview[:15],
    }
    session["captures"].append(capture)
    return capture


# ── Socket events ─────────────────────────────────────────────────────────────

@socketio.on("connect")
def on_connect():
    emit("status", {"connected": session["connected"], "playwright": PLAYWRIGHT_AVAILABLE})


@socketio.on("start_browser")
def start_browser(data):
    if not PLAYWRIGHT_AVAILABLE:
        emit("error", {"msg": "Playwright not installed"}); return
    url = data.get("url", TARGET_URL)
    emit("log", {"msg": "Launching browser -> " + url})
    res = pw_call({"action": "launch", "url": url})
    if res["ok"]:
        session["connected"] = True
        emit("log",             {"msg": "Browser open - " + res.get("title", "") + ". Click any element to capture!"})
        emit("browser_started", {"url": url, "title": res.get("title", "")})
    else:
        emit("error", {"msg": "Launch failed: " + res.get("error", "")})


@socketio.on("save_captures")
def save_captures(data):
    name = data.get("name", "screen").strip() or "screen"
    res  = pw_call({"action": "get_captures"})
    if not res["ok"]:
        emit("error", {"msg": res.get("error")}); return

    raw = res.get("captures", [])
    net = res.get("network", [])

    if not raw:
        emit("error", {"msg": "No elements clicked yet - click elements in the browser first!"}); return

    capture = save_capture_group(name, raw, net)
    pw_call({"action": "clear_page_captures"})

    emit("screen_captured", {
        "name":    capture["name"],
        "index":   capture["index"],
        "url":     capture["url"],
        "title":   capture["title"],
        "count":   capture["count"],
        "preview": capture["preview"],
    })
    emit("log", {"msg": "Saved '" + name + "' - " + str(capture["count"]) + " elements captured"})


@socketio.on("navigate")
def navigate(data):
    url = data.get("url", "")
    res = pw_call({"action": "navigate", "url": url})
    if res["ok"]:
        emit("log",      {"msg": "-> " + res.get("url", "")})
        emit("navigated",{"url": res.get("url"), "title": res.get("title")})
    else:
        emit("error", {"msg": "Navigate failed: " + res.get("error", "")})


@socketio.on("stop_browser")
def stop_browser():
    pw_call({"action": "stop"})
    session["connected"] = False
    emit("browser_stopped", {})
    emit("log", {"msg": "Browser closed."})


@socketio.on("clear_captures")
def clear_captures():
    session["captures"] = []
    emit("captures_cleared", {})


@socketio.on("scrape_all_elements")
def scrape_all_elements(data):
    name = data.get("name", "all_elements").strip() or "all_elements"
    return_only = data.get("returnOnly", False)
    
    res  = pw_call({"action": "scrape_all"})
    if not res["ok"]:
        emit("error", {"msg": res.get("error")}); return

    result = res.get("result", {})
    elements = result.get("elements", [])

    if not elements:
        emit("error", {"msg": "No interactive elements found on this page!"}); return

    # If returnOnly, just emit the scanned data for Test Runner
    if return_only:
        emit("page_scanned", {
            "elements": elements,
            "url": result.get("url", ""),
            "title": result.get("title", "")
        })
        return

    # Convert scraped elements to capture format
    capture = save_capture_group(name, elements, [])

    emit("screen_captured", {
        "name":    capture["name"],
        "index":   capture["index"],
        "url":     capture["url"],
        "title":   capture["title"],
        "count":   capture["count"],
        "preview": capture["preview"],
    })
    emit("log", {"msg": "Scraped '" + name + "' - " + str(capture["count"]) + " elements found automatically"})


@socketio.on("get_network_log")
def get_network_log(data):
    api_only = data.get("api_only", False) if data else False
    res = pw_call({"action": "get_network_log", "api_only": api_only})
    if not res["ok"]:
        emit("error", {"msg": res.get("error")}); return
    emit("network_log", {"network": res.get("network", [])})


@socketio.on("clear_network_log")
def clear_network_log():
    res = pw_call({"action": "clear_network_log"})
    if res["ok"]:
        emit("log", {"msg": "Network log cleared"})
        emit("network_log", {"network": []})
    else:
        emit("error", {"msg": res.get("error")})


# ── Test Execution ────────────────────────────────────────────────────────────

test_results = []

@socketio.on("run_test_case")
def run_test_case(data):
    """Run a complete test case with multiple steps"""
    global test_results
    
    test_name = data.get("name", "Unnamed Test")
    steps = data.get("steps", [])
    credentials = data.get("credentials", {})
    
    if not steps:
        emit("error", {"msg": "No test steps provided"}); return
    
    emit("test_started", {"name": test_name, "total_steps": len(steps)})
    emit("log", {"msg": f"🧪 Starting test: {test_name}"})
    
    results = {
        "name": test_name,
        "steps": [],
        "passed": True,
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "credentials_used": list(credentials.keys()) if credentials else []
    }
    
    for i, step in enumerate(steps):
        step_num = i + 1
        step_type = step.get("type", "")
        
        # Replace credential placeholders
        if credentials:
            for key, val in credentials.items():
                if step.get("value") == f"${{{key}}}":
                    step["value"] = val
                if step.get("selector") and f"${{{key}}}" in step.get("selector", ""):
                    step["selector"] = step["selector"].replace(f"${{{key}}}", val)
        
        emit("test_step_started", {
            "step_num": step_num,
            "total": len(steps),
            "step": step
        })
        
        res = pw_call({"action": "run_test_step", "step": step})
        
        step_result = {
            "step_num": step_num,
            "step": step,
            "ok": res.get("ok", False),
            "error": res.get("error"),
            "url": res.get("url"),
            "title": res.get("title")
        }
        results["steps"].append(step_result)
        
        if res["ok"]:
            emit("test_step_passed", {
                "step_num": step_num,
                "total": len(steps),
                "step": step,
                "url": res.get("url"),
                "title": res.get("title")
            })
            emit("log", {"msg": f"  ✅ Step {step_num}/{len(steps)}: {step_type} - PASSED"})
        else:
            results["passed"] = False
            emit("test_step_failed", {
                "step_num": step_num,
                "total": len(steps),
                "step": step,
                "error": res.get("error")
            })
            emit("log", {"msg": f"  ❌ Step {step_num}/{len(steps)}: {step_type} - FAILED: {res.get('error')}"})
            break  # Stop on first failure
    
    results["end_time"] = datetime.now().isoformat()
    test_results.append(results)
    
    if results["passed"]:
        emit("test_passed", {"name": test_name, "results": results})
        emit("log", {"msg": f"✅ Test PASSED: {test_name}"})
    else:
        emit("test_failed", {"name": test_name, "results": results})
        emit("log", {"msg": f"❌ Test FAILED: {test_name}"})


@socketio.on("run_single_step")
def run_single_step(data):
    """Run a single test step"""
    step = data.get("step", {})
    credentials = data.get("credentials", {})
    
    if not step:
        emit("error", {"msg": "No step provided"}); return
    
    # Replace credential placeholders
    if credentials:
        for key, val in credentials.items():
            if step.get("value") == f"${{{key}}}":
                step["value"] = val
            if step.get("selector") and f"${{{key}}}" in step.get("selector", ""):
                step["selector"] = step["selector"].replace(f"${{{key}}}", val)
    
    res = pw_call({"action": "run_test_step", "step": step})
    
    if res["ok"]:
        emit("step_result", {
            "ok": True,
            "step": step,
            "url": res.get("url"),
            "title": res.get("title")
        })
        emit("log", {"msg": f"✅ Step executed: {step.get('type')}"})
    else:
        emit("step_result", {
            "ok": False,
            "step": step,
            "error": res.get("error")
        })
        emit("log", {"msg": f"❌ Step failed: {res.get('error')}"})


@socketio.on("get_test_results")
def get_test_results():
    """Get all test results"""
    emit("test_results", {"results": test_results})


@socketio.on("clear_test_results")
def clear_test_results():
    """Clear test results"""
    global test_results
    test_results = []
    emit("test_results", {"results": []})
    emit("log", {"msg": "Test results cleared"})


@socketio.on("generate_test_steps")
def generate_test_steps(data):
    """Generate test steps from description using AI"""
    description = data.get("description", "")
    api_key = data.get("api_key", "")
    credentials = data.get("credentials", {})
    frontend_locators = data.get("locators", [])
    
    if not description:
        emit("error", {"msg": "Test description required"}); return
    if not api_key:
        emit("error", {"msg": "API key required"}); return
    
    # Helper to extract locator string
    def extract_locator(raw_locator):
        if isinstance(raw_locator, dict):
            return raw_locator.get("value", str(raw_locator))
        return str(raw_locator) if raw_locator else ""
    
    def extract_element_data(el):
        element_data = el.get("element", el)
        return {
            "tag": element_data.get("tag", ""),
            "type": element_data.get("type", ""),
            "text": (element_data.get("text", "") or "")[:100],
            "id": element_data.get("id", ""),
            "name": element_data.get("name", ""),
            "placeholder": element_data.get("placeholder", ""),
            "aria_label": element_data.get("ariaLabel", element_data.get("aria_label", ""))
        }
    
    # Build locators list
    all_locators = []
    if frontend_locators:
        for el in frontend_locators:
            elem_data = extract_element_data(el)
            all_locators.append({
                "screen": "current_page",
                "url": el.get("url", ""),
                "locator": extract_locator(el.get("locator", "")),
                **elem_data
            })
    
    # Fallback to captures
    if not all_locators:
        for cap in session.get("captures", []):
            for el in cap.get("elements", cap.get("preview", [])):
                elem_data = extract_element_data(el)
                all_locators.append({
                    "screen": cap.get("name", ""),
                    "url": cap.get("url", ""),
                    "locator": extract_locator(el.get("locator", "")),
                    **elem_data
                })
    
    # Try scraping current page if still empty
    if not all_locators:
        emit("log", {"msg": "Scraping current page for locators..."})
        res = pw_call({"action": "scrape_all"})
        if res.get("ok") and res.get("result", {}).get("elements"):
            for el in res.get("result", {}).get("elements", []):
                elem_data = extract_element_data(el)
                all_locators.append({
                    "screen": "current_page",
                    "url": el.get("url", ""),
                    "locator": extract_locator(el.get("locator", "")),
                    **elem_data
                })
    
    if not all_locators:
        emit("error", {"msg": "No locators available. Scan a page first!"}); return
    
    emit("log", {"msg": f"🤖 Generating test steps using {len(all_locators)} locators..."})
    emit("test_generation_started", {})
    
    # Build prompt
    locators_text = "\n".join([
        f"- Locator: {l['locator']}, Tag: {l['tag']}, Type: {l['type']}, Text: {l['text']}, ID: {l['id']}, Name: {l['name']}, Placeholder: {l['placeholder']}"
        for l in all_locators[:100]
    ])
    
    cred_keys = list(credentials.keys()) if credentials else ["username", "password"]
    
    prompt = f"""You are a test automation expert. Generate executable test steps based on the test description and available locators.

AVAILABLE LOCATORS:
{locators_text}

CREDENTIAL PLACEHOLDERS: {', '.join([f'${{{k}}}' for k in cred_keys])}

TEST DESCRIPTION:
{description}

Generate a JSON array of test steps. Each step should have:
- "type": one of: goto, fill, click, type, press, wait, wait_for, assert_visible, assert_text, assert_url, assert_title
- "selector": the locator string (use from available locators above)
- "value": the value to use (use credential placeholders like ${{username}} for sensitive data)
- "description": brief description of what this step does

RULES:
1. Use ONLY locators from the available locators list when possible
2. For login forms, use ${{username}} and ${{password}} placeholders
3. Add appropriate waits between navigation steps
4. Include assertions to verify expected outcomes

Return ONLY a valid JSON array, no explanation. Example:
[
  {{"type": "goto", "selector": "", "value": "https://example.com", "description": "Navigate to login page"}},
  {{"type": "fill", "selector": "page.get_by_placeholder(\\"Email\\")", "value": "${{username}}", "description": "Enter username"}},
  {{"type": "fill", "selector": "page.get_by_placeholder(\\"Password\\")", "value": "${{password}}", "description": "Enter password"}},
  {{"type": "click", "selector": "page.get_by_role(\\"button\\", name=\\"Login\\")", "value": "", "description": "Click login button"}},
  {{"type": "wait", "selector": "", "value": "2000", "description": "Wait for page load"}},
  {{"type": "assert_url", "selector": "", "value": "dashboard", "description": "Verify redirected to dashboard"}}
]"""

    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")
        
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
        )
        
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result.get("content", [{}])[0].get("text", "")
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                steps = json.loads(json_match.group())
                emit("test_steps_generated", {"steps": steps})
                emit("log", {"msg": f"✅ Generated {len(steps)} test steps"})
            else:
                emit("error", {"msg": "Could not parse AI response"})
                
    except urllib.error.HTTPError as e:
        emit("error", {"msg": f"API error: {e.code} - {e.reason}"})
    except Exception as e:
        emit("error", {"msg": f"Generation failed: {str(e)}"})


# ── Extension capture ─────────────────────────────────────────────────────────

@app.route("/api/extension-capture", methods=["POST"])
def extension_capture():
    data     = request.json
    name     = data.get("name", "screen").strip() or "screen"
    snapshot = data.get("snapshot", {})
    if not snapshot:
        return jsonify({"error": "No snapshot data"}), 400
    elements = snapshot.get("elements", [])
    capture  = save_capture_group(name, elements, [])
    socketio.emit("screen_captured", {
        "name":    capture["name"],
        "index":   capture["index"],
        "url":     capture["url"],
        "title":   capture["title"],
        "count":   capture["count"],
        "preview": capture["preview"],
    })
    socketio.emit("log", {"msg": "[Extension] Captured: " + name})
    return jsonify({"success": True, "index": capture["index"]})


# ── Config endpoints ──────────────────────────────────────────────────────────

@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_prompt_config())


@app.route("/api/config", methods=["POST"])
def save_config_endpoint():
    with open(PROMPT_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(request.json, f, indent=2)
    return jsonify({"saved": True})


# ── REST ──────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/status")
def status():
    return jsonify({
        "playwright_available": PLAYWRIGHT_AVAILABLE,
        "connected":            session["connected"],
        "captures":             len(session["captures"]),
        "target_url":           TARGET_URL,
    })


@app.route("/api/captures/<int:idx>")
def get_capture(idx):
    for c in session["captures"]:
        if c["index"] == idx:
            return jsonify(c)
    return "Not found", 404


@app.route("/api/scripts/save", methods=["POST"])
def save_scripts():
    scripts = request.json.get("scripts", [])
    saved   = []
    for s in scripts:
        path = os.path.join(OUTPUT_DIR, s["filename"])
        with open(path, "w", encoding="utf-8") as f:
            f.write(s["content"])
        saved.append(path)
    return jsonify({"saved": saved})


@app.route("/api/generate", methods=["POST"])
def generate():
    data    = request.json
    api_key = data.get("api_key", "").strip()
    prompt  = data.get("prompt", "")

    framework_context = build_framework_context()
    prompt = prompt.replace("__FRAMEWORK_CONTEXT__", framework_context)

    if not api_key:
        return jsonify({"error": "API key required"}), 400

    payload = json.dumps({
        "model":      "claude-sonnet-4-20250514",
        "max_tokens": data.get("max_tokens", 4000),
        "messages":   [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data    = payload,
        headers = {
            "Content-Type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
        },
        method = "POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return jsonify(json.loads(resp.read().decode("utf-8")))
    except urllib.error.HTTPError as e:
        return jsonify({"error": e.read().decode("utf-8")}), e.code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 55)
    print("  HabitNu Web Test Script Generator")
    print("=" * 55)
    print(f"  Playwright : {PLAYWRIGHT_AVAILABLE}")
    print(f"  Target URL : {TARGET_URL}")
    print("=" * 55)
    print("\n  Open http://localhost:5001 in your browser\n")
    socketio.run(app, host="0.0.0.0", port=5001, debug=False)