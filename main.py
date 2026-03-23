#!/usr/bin/env python3
"""
AryterLink - Remote Termux Control Panel
Author: Aryan Giri
Run: python main.py
"""

import os, json, subprocess, threading, secrets, time, re, html, shlex, mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from pathlib import Path
from collections import defaultdict

# ══════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════
PORT         = 8080
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
AUTH_FILE    = os.path.join(BASE_DIR, "auth.txt")
RES_DIR      = os.path.join(BASE_DIR, "res")   # photos + audio saved here

SESSION_TTL  = 3600
SESSIONS     = {}
SESSION_LOCK = threading.Lock()

MAX_ATTEMPTS   = 5
LOCKOUT_SECS   = 300
LOGIN_ATTEMPTS = defaultdict(list)
ATTEMPT_LOCK   = threading.Lock()

TERMUX_HOME = os.path.expanduser("~")

# Allowed extensions to serve from /res/
ALLOWED_EXT = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".3gp":  "audio/3gpp",
    ".mp4":  "video/mp4",
    ".m4a":  "audio/mp4",
    ".aac":  "audio/aac",
    ".mp3":  "audio/mpeg",
    ".wav":  "audio/wav",
}


# ══════════════════════════════════════════════
#  STARTUP
# ══════════════════════════════════════════════
def startup():
    os.makedirs(RES_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "static"), exist_ok=True)
    load_creds()


# ══════════════════════════════════════════════
#  SECURITY HELPERS
# ══════════════════════════════════════════════
def esc(s):
    return html.escape(str(s), quote=True)

def is_locked(ip):
    now = time.time()
    with ATTEMPT_LOCK:
        attempts = [t for t in LOGIN_ATTEMPTS[ip] if now - t < LOCKOUT_SECS]
        LOGIN_ATTEMPTS[ip] = attempts
        return len(attempts) >= MAX_ATTEMPTS

def record_fail(ip):
    with ATTEMPT_LOCK:
        LOGIN_ATTEMPTS[ip].append(time.time())

def record_ok(ip):
    with ATTEMPT_LOCK:
        LOGIN_ATTEMPTS[ip] = []

def lockout_eta(ip):
    now = time.time()
    with ATTEMPT_LOCK:
        a = sorted(LOGIN_ATTEMPTS[ip])
        if len(a) < MAX_ATTEMPTS:
            return 0
        return max(0, int(LOCKOUT_SECS - (now - a[-MAX_ATTEMPTS])))

def valid_token(s):
    return bool(s and re.fullmatch(r'[0-9a-f]{64}', s))

def clean(s, max_len=500):
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', str(s))[:max_len]

def safe_filename(name):
    """Strip any path traversal from a filename."""
    return os.path.basename(name)


# ══════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════
def load_creds():
    if not os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, "w") as f:
            f.write("username=admin\npassword=admin123\n")
        print("[!] auth.txt created — change the default password!")
    c = {}
    with open(AUTH_FILE) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                c[k.strip()] = v.strip()
    return c

def verify_login(u, p):
    c = load_creds()
    return (secrets.compare_digest(c.get("username", ""), u) and
            secrets.compare_digest(c.get("password", ""), p))

def create_session():
    tok = secrets.token_hex(32)
    with SESSION_LOCK:
        SESSIONS[tok] = {"expires": time.time() + SESSION_TTL,
                         "cwd": TERMUX_HOME, "prev_cwd": TERMUX_HOME}
    return tok

def get_session(tok):
    if not valid_token(tok):
        return None
    with SESSION_LOCK:
        s = SESSIONS.get(tok)
        if s and time.time() < s["expires"]:
            s["expires"] = time.time() + SESSION_TTL
            return s
        SESSIONS.pop(tok, None)
        return None

def save_cwd(tok, cwd, prev):
    with SESSION_LOCK:
        if tok in SESSIONS:
            SESSIONS[tok]["cwd"] = cwd
            SESSIONS[tok]["prev_cwd"] = prev


# ══════════════════════════════════════════════
#  COMMAND RUNNER
# ══════════════════════════════════════════════
def run_cmd(cmd, timeout=15, cwd=None):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, timeout=timeout, cwd=cwd or TERMUX_HOME)
        out = r.stdout.strip()
        err = r.stderr.strip()
        return {"success": r.returncode == 0, "output": out or err, "code": r.returncode}
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "Command timed out", "code": -1}
    except Exception as e:
        return {"success": False, "output": str(e), "code": -1}

def run_in_session(cmd, sess, tok):
    cwd  = sess.get("cwd", TERMUX_HOME)
    prev = sess.get("prev_cwd", TERMUX_HOME)
    m = re.fullmatch(r'\s*cd\s*(.*)', cmd.strip())
    if m:
        target = m.group(1).strip().strip('"').strip("'") or TERMUX_HOME
        if target == "~":   target = TERMUX_HOME
        elif target == "-": target = prev
        elif not os.path.isabs(target):
            target = os.path.normpath(os.path.join(cwd, target))
        if os.path.isdir(target):
            save_cwd(tok, target, cwd)
            return {"success": True, "output": "", "cwd": target}
        return {"success": False, "output": f"cd: {target}: No such directory", "cwd": cwd}
    result = run_cmd(cmd, timeout=30, cwd=cwd)
    result["cwd"] = cwd
    return result


# ══════════════════════════════════════════════
#  TTS ENGINE CACHE (detect once at first call)
# ══════════════════════════════════════════════
_tts_engines_cache = None

def get_tts_engines():
    global _tts_engines_cache
    if _tts_engines_cache is not None:
        return _tts_engines_cache
    engines = []
    # Try termux-tts-engines
    tr = run_cmd("termux-tts-engines", timeout=5)
    try:
        for e in json.loads(tr["output"]):
            name  = e.get("name",  str(e))
            label = e.get("label", name)
            engines.append({"id": name, "label": label, "type": "termux"})
    except:
        engines.append({"id": "termux", "label": "Termux TTS", "type": "termux"})
    # Check for espeak-ng
    er = run_cmd("which espeak-ng 2>/dev/null || which espeak 2>/dev/null", timeout=3)
    if er["success"] and er["output"].strip():
        engines.append({"id": "espeak", "label": "eSpeak-NG", "type": "espeak"})
    _tts_engines_cache = engines
    return engines


# ══════════════════════════════════════════════
#  RES DIR HELPERS
# ══════════════════════════════════════════════
def res_path(fname):
    """Absolute path inside RES_DIR, no traversal."""
    return os.path.join(RES_DIR, safe_filename(fname))

def next_res_name(prefix, ext):
    ts = time.strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}{ext}"

def list_res_files():
    files = []
    for name in sorted(os.listdir(RES_DIR), reverse=True):
        ext = os.path.splitext(name)[1].lower()
        if ext in ALLOWED_EXT:
            full = os.path.join(RES_DIR, name)
            stat = os.stat(full)
            files.append({
                "name": name,
                "size": stat.st_size,
                "mtime": int(stat.st_mtime),
                "type": "image" if ext in (".jpg",".jpeg",".png") else "audio",
                "mime": ALLOWED_EXT[ext],
            })
    return files


# ══════════════════════════════════════════════
#  HTTP HANDLER
# ══════════════════════════════════════════════
class Handler(BaseHTTPRequestHandler):
    server_version = "AryterLink"
    sys_version    = ""

    def log_message(self, fmt, *args):
        print(f"  [{self.client_address[0]}] {fmt % args}")

    def tok(self):
        for part in self.headers.get("Cookie", "").split(";"):
            part = part.strip()
            if part.startswith("aryterlink_token="):
                t = part.split("=", 1)[1].strip()
                return t if valid_token(t) else None
        return None

    def ip(self):
        return self.client_address[0]

    def sec(self, is_html=False):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store, no-cache")
        if is_html:
            self.send_header("Content-Security-Policy",
                "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src https://fonts.gstatic.com; img-src 'self' data: blob:; "
                "media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none';")

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.sec()
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, content, status=200):
        body = content.encode() if isinstance(content, str) else content
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.sec(is_html=True)
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        n = int(self.headers.get("Content-Length", 0))
        if n > 65536:
            return ""
        return self.rfile.read(n).decode("utf-8", errors="replace")

    # ── GET ──────────────────────────────────
    def do_GET(self):
        p = urlparse(self.path).path

        if p in ("/", "/index.html"):
            t = self.tok()
            s = get_session(t)
            try:
                self.send_html(self._dash(s["cwd"]) if s else self._login())
            except Exception:
                import traceback
                self.send_html(f"<pre style='color:red;padding:20px'>{esc(traceback.format_exc())}</pre>", 500)
            return

        if p == "/logout":
            t = self.tok()
            if t:
                with SESSION_LOCK: SESSIONS.pop(t, None)
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Set-Cookie", "aryterlink_token=; Max-Age=0; Path=/; HttpOnly; SameSite=Strict")
            self.sec()
            self.end_headers()
            return

        # ── Serve files from res/ (requires auth) ──
        if p.startswith("/res/"):
            t = self.tok()
            if not get_session(t):
                self.send_json({"error": "Unauthorized"}, 401)
                return
            fname = safe_filename(p[5:])   # strip /res/
            fpath = os.path.join(RES_DIR, fname)
            ext   = os.path.splitext(fname)[1].lower()
            if not fname or ext not in ALLOWED_EXT or not os.path.isfile(fpath):
                self.send_json({"error": "Not found"}, 404)
                return
            data = open(fpath, "rb").read()
            dl   = "attachment" if "download" in urlparse(self.path).query else "inline"
            self.send_response(200)
            self.send_header("Content-Type", ALLOWED_EXT[ext])
            self.send_header("Content-Length", len(data))
            self.send_header("Content-Disposition", f'{dl}; filename="{fname}"')
            self.sec()
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_json({"error": "Not found"}, 404)

    # ── POST ─────────────────────────────────
    def do_POST(self):
        p = urlparse(self.path).path

        # ── Login ──
        if p == "/api/login":
            if is_locked(self.ip()):
                secs = lockout_eta(self.ip())
                self.send_html(self._login(f"Too many attempts. Wait {secs}s."), 429)
                return
            raw = self.body()
            d   = parse_qs(raw)
            u   = clean(d.get("username", [""])[0], 64)
            pw  = d.get("password", [""])[0][:128]
            if verify_login(u, pw):
                record_ok(self.ip())
                tok = create_session()
                self.send_response(302)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie",
                    f"aryterlink_token={tok}; Max-Age={SESSION_TTL}; Path=/; HttpOnly; SameSite=Strict")
                self.sec()
                self.end_headers()
            else:
                record_fail(self.ip())
                left = max(0, MAX_ATTEMPTS - len(LOGIN_ATTEMPTS[self.ip()]))
                self.send_html(self._login(f"Invalid credentials. {left} attempt(s) left."), 401)
            return

        # ── Auth guard ──
        tok  = self.tok()
        sess = get_session(tok)
        if not sess:
            self.send_json({"error": "Unauthorized"}, 401)
            return

        try:    payload = json.loads(self.body())
        except: payload = {}

        # ── Terminal ──
        if p == "/api/terminal":
            cmd = str(payload.get("cmd", "")).strip()
            if not cmd:
                self.send_json({"success": False, "output": "No command", "cwd": sess["cwd"]}); return
            result = run_in_session(cmd, sess, tok)
            self.send_json(result); return

        # ── Battery ──
        if p == "/api/battery":
            r = run_cmd("termux-battery-status")
            try:    self.send_json({"success": True, "data": json.loads(r["output"])})
            except: self.send_json(r)
            return

        # ── Fingerprint ──
        if p == "/api/fingerprint":
            r = run_cmd("termux-fingerprint", timeout=30)
            try:
                data = json.loads(r["output"])
                result = data.get("auth_result", "")
                success = result == "AUTH_RESULT_SUCCESS"
                self.send_json({
                    "success": True,
                    "auth_result": result,
                    "authenticated": success,
                    "failed_attempts": data.get("failed_attempts", 0),
                    "errors": data.get("errors", []),
                })
            except:
                self.send_json({"success": False, "output": r["output"]})
            return

        # ── Brightness ──
        if p == "/api/brightness":
            level = payload.get("level", None)
            if level is not None:
                level = max(0, min(int(level), 255))
                r = run_cmd(f"termux-brightness {level}")
                self.send_json({"success": r["success"], "level": level, "output": r["output"]})
            else:
                # No level → just query (brightness doesn't have a get cmd; return current via settings)
                r = run_cmd("settings get system screen_brightness 2>/dev/null || echo unknown")
                self.send_json({"success": True, "output": r["output"].strip()})
            return

        # ── SMS list ──
        if p == "/api/sms/list":
            limit = min(int(payload.get("limit", 20)), 200)
            r = run_cmd(f"termux-sms-list -l {limit}")
            try:    self.send_json({"success": True, "data": json.loads(r["output"])})
            except: self.send_json(r)
            return

        # ── SMS send ──
        if p == "/api/sms/send":
            number  = clean(payload.get("number", ""), 20)
            message = clean(payload.get("message", ""), 500)
            if not re.fullmatch(r'[\+\d\s\-\(\)]+', number):
                self.send_json({"success": False, "output": "Invalid phone number"}); return
            r = run_cmd(f'termux-sms-send -n {shlex.quote(number)} {shlex.quote(message)}')
            self.send_json(r); return

        # ── Torch ──
        if p == "/api/torch":
            state = "on" if payload.get("state") == "on" else "off"
            r = run_cmd(f"termux-torch {state}")
            self.send_json({"success": True, "state": state}); return

        # ── Call log ──
        if p == "/api/call-log":
            r = run_cmd("termux-call-log")
            try:    self.send_json({"success": True, "data": json.loads(r["output"])})
            except: self.send_json(r)
            return

        # ── Make call ──
        if p == "/api/call":
            number = clean(payload.get("number", ""), 20)
            if not re.fullmatch(r'[\+\d\s\-\(\)]+', number):
                self.send_json({"success": False, "output": "Invalid number"}); return
            r = run_cmd(f"termux-telephony-call {shlex.quote(number)}")
            self.send_json(r); return

        # ── Camera photo (saves to res/) ──
        if p == "/api/camera/photo":
            cam   = int(payload.get("camera", 0)) % 2
            fname = next_res_name("photo", ".jpg")
            fpath = res_path(fname)
            r = run_cmd(f"termux-camera-photo -c {cam} {shlex.quote(fpath)}", timeout=20)
            self.send_json({"success": r["success"], "file": fname, "output": r["output"]}); return

        # ── Location ──
        if p == "/api/location":
            r = run_cmd("termux-location", timeout=20)
            try:    self.send_json({"success": True, "data": json.loads(r["output"])})
            except: self.send_json(r)
            return

        # ── Clipboard get ──
        if p == "/api/clipboard/get":
            r = run_cmd("termux-clipboard-get")
            self.send_json({"success": True, "content": r["output"]}); return

        # ── Clipboard set ──
        if p == "/api/clipboard/set":
            text = clean(payload.get("text", ""), 4096)
            run_cmd(f"echo {shlex.quote(text)} | termux-clipboard-set")
            self.send_json({"success": True}); return

        # ── Contacts ──
        if p == "/api/contacts":
            r = run_cmd("termux-contact-list")
            try:    self.send_json({"success": True, "data": json.loads(r["output"])})
            except: self.send_json(r)
            return

        # ── WiFi info ──
        if p == "/api/wifi/info":
            r = run_cmd("termux-wifi-connectioninfo")
            try:    self.send_json({"success": True, "data": json.loads(r["output"])})
            except: self.send_json(r)
            return

        # ── WiFi toggle ──
        if p == "/api/wifi/toggle":
            state = "true" if str(payload.get("state", "")) in ("true", "1") else "false"
            run_cmd(f"termux-wifi-enable {state}")
            self.send_json({"success": True}); return

        # ── WiFi scan ──
        if p == "/api/wifi/scan":
            r = run_cmd("termux-wifi-scaninfo")
            try:    self.send_json({"success": True, "data": json.loads(r["output"])})
            except: self.send_json(r)
            return

        # ── Notification ──
        if p == "/api/notification":
            title   = clean(payload.get("title", "AryterLink"), 100)
            content = clean(payload.get("content", ""), 300)
            nid     = max(1, min(int(payload.get("id", 42)), 9999))
            run_cmd(f'termux-notification -t {shlex.quote(title)} -c {shlex.quote(content)} -i {nid}')
            self.send_json({"success": True}); return

        # ── Notification remove ──
        if p == "/api/notification/remove":
            nid = max(1, min(int(payload.get("id", 42)), 9999))
            run_cmd(f"termux-notification-remove {nid}")
            self.send_json({"success": True}); return

        # ── TTS ──
        if p == "/api/tts":
            text   = clean(payload.get("text", ""), 1000)
            rate   = max(0.1, min(float(payload.get("rate", 1.0)), 3.0))
            engine = payload.get("engine", "termux")
            if engine == "espeak":
                espeak_rate = int(80 + (rate - 0.1) / 2.9 * 270)
                r = run_cmd(f'espeak-ng -s {espeak_rate} {shlex.quote(text)}')
            else:
                r = run_cmd(f'termux-tts-speak -r {rate} {shlex.quote(text)}')
            self.send_json({"success": r["success"], "engine": engine, "output": r["output"]}); return

        # ── TTS engines ──
        if p == "/api/tts/engines":
            self.send_json({"success": True, "engines": get_tts_engines()}); return

        # ── Toast ──
        if p == "/api/toast":
            msg = clean(payload.get("message", ""), 200)
            bg  = payload.get("bg", "gray")
            if bg not in ("gray","red","green","blue","black","white","yellow"):
                bg = "gray"
            run_cmd(f'termux-toast -b {bg} {shlex.quote(msg)}')
            self.send_json({"success": True}); return

        # ── Vibrate ──
        if p == "/api/vibrate":
            ms    = max(50, min(int(payload.get("ms", 1000)), 5000))
            force = "-f" if payload.get("force", True) else ""
            run_cmd(f"termux-vibrate -d {ms} {force}".strip())
            self.send_json({"success": True}); return

        # ── Record audio (saves to res/) ──
        if p == "/api/audio/record":
            secs  = max(1, min(int(payload.get("seconds", 5)), 120))
            fname = next_res_name("audio", ".3gp")
            fpath = res_path(fname)
            r = run_cmd(f"termux-record-audio -l {secs} {shlex.quote(fpath)}", timeout=secs + 10)
            self.send_json({"success": r["success"], "file": fname, "output": r["output"]}); return

        # ── Res file list ──
        if p == "/api/res/list":
            self.send_json({"success": True, "files": list_res_files()}); return

        # ── Res file delete ──
        if p == "/api/res/delete":
            fname = safe_filename(payload.get("name", ""))
            fpath = os.path.join(RES_DIR, fname)
            if os.path.isfile(fpath):
                os.remove(fpath)
                self.send_json({"success": True}); return
            self.send_json({"success": False, "output": "File not found"}); return

        # ── Sensor list ──
        if p == "/api/sensor/list":
            r = run_cmd("termux-sensor -l")
            try:
                parsed = json.loads(r["output"])
                # Output is {"sensors": ["name1", "name2", ...]}
                sensors = parsed.get("sensors", parsed) if isinstance(parsed, dict) else parsed
                self.send_json({"success": True, "sensors": sensors})
            except:
                # Fallback: plain text list, one per line
                lines = [l.strip() for l in r["output"].splitlines() if l.strip()]
                self.send_json({"success": True, "sensors": lines})
            return

        # ── Wake lock ──
        if p == "/api/wakelock":
            cmd = "termux-wake-lock" if payload.get("action") == "lock" else "termux-wake-unlock"
            run_cmd(cmd)
            self.send_json({"success": True}); return

        # ── Open URL ──
        if p == "/api/open-url":
            url = clean(payload.get("url", ""), 2048)
            if not re.match(r'https?://', url):
                self.send_json({"success": False, "output": "Only http/https URLs allowed"}); return
            run_cmd(f'termux-open-url {shlex.quote(url)}')
            self.send_json({"success": True}); return

        # ── Download ──
        if p == "/api/download":
            url    = clean(payload.get("url", ""), 2048)
            method = payload.get("method", "termux")  # "termux" | "wget"
            if not re.match(r'https?://', url):
                self.send_json({"success": False, "output": "Only http/https URLs allowed"}); return
            if method == "wget":
                r = run_cmd(f'wget -q --show-progress -P /sdcard/Download {shlex.quote(url)}', timeout=60)
            else:
                r = run_cmd(f'termux-download {shlex.quote(url)}', timeout=30)
            self.send_json(r); return

        self.send_json({"error": "Unknown endpoint"}, 404)

    # ══════════════════════════════════════════
    #  HTML TEMPLATES
    # ══════════════════════════════════════════
    def _login(self, error=None):
        err = f'<div class="err">&#9888; {esc(error)}</div>' if error else ""
        return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AryterLink</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#0a0c10;--sf:#0d1117;--bd:#1e2936;--ac:#00d4ff;--ac2:#7c3aed;--tx:#e2e8f0;--mu:#4a5568;--er:#ff4d6d;--fm:'Share Tech Mono',monospace;--fu:'Rajdhani',sans-serif}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--tx);font-family:var(--fu);min-height:100vh;display:flex;align-items:center;justify-content:center}}
.gbg{{position:fixed;inset:0;z-index:0;background-image:linear-gradient(rgba(0,212,255,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,212,255,.03) 1px,transparent 1px);background-size:40px 40px;animation:drift 20s linear infinite}}
@keyframes drift{{to{{background-position:40px 40px}}}}
.wrap{{position:relative;z-index:1;width:100%;max-width:400px;padding:20px}}
.logo{{text-align:center;margin-bottom:28px}}
.logo h1{{font-family:var(--fm);font-size:2rem;color:var(--ac);text-shadow:0 0 20px rgba(0,212,255,.5);letter-spacing:4px;animation:fl 4s infinite}}
@keyframes fl{{0%,95%,100%{{opacity:1}}96%{{opacity:.8}}98%{{opacity:.7}}}}
.logo p{{font-family:var(--fm);font-size:.7rem;color:var(--mu);letter-spacing:3px;margin-top:6px}}
.card{{background:var(--sf);border:1px solid var(--bd);border-radius:12px;padding:32px;position:relative;overflow:hidden}}
.card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--ac),transparent)}}
.hdr{{font-family:var(--fm);font-size:.72rem;color:var(--mu);letter-spacing:2px;margin-bottom:22px;display:flex;align-items:center;gap:8px}}
.hdr::before{{content:'>';color:var(--ac);animation:blink 1s infinite}}
@keyframes blink{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
label{{display:block;font-size:.75rem;font-family:var(--fm);color:var(--mu);letter-spacing:2px;margin-bottom:7px}}
input{{width:100%;background:rgba(0,212,255,.04);border:1px solid var(--bd);border-radius:6px;padding:11px 13px;color:var(--tx);font-family:var(--fm);font-size:.9rem;outline:none;transition:border-color .2s;margin-bottom:16px}}
input:focus{{border-color:var(--ac)}}
.btn{{width:100%;padding:12px;background:linear-gradient(135deg,var(--ac),var(--ac2));border:none;border-radius:6px;color:#fff;font-family:var(--fu);font-size:.95rem;font-weight:700;letter-spacing:3px;cursor:pointer;transition:opacity .2s}}
.btn:hover{{opacity:.9}}
.err{{background:rgba(255,77,109,.12);border:1px solid rgba(255,77,109,.3);color:var(--er);font-family:var(--fm);font-size:.78rem;padding:9px 13px;border-radius:6px;margin-bottom:14px}}
.ft{{text-align:center;margin-top:18px;font-family:var(--fm);font-size:.62rem;color:var(--mu);letter-spacing:2px}}
</style></head><body>
<div class="gbg"></div>
<div class="wrap">
  <div class="logo"><h1>ARYTERLINK</h1><p>REMOTE TERMUX CONTROL PANEL</p></div>
  <div class="card">
    <div class="hdr">AUTHENTICATE TO CONTINUE</div>
    {err}
    <form method="POST" action="/api/login" autocomplete="off">
      <label>USERNAME</label>
      <input type="text" name="username" spellcheck="false" maxlength="64" required>
      <label>PASSWORD</label>
      <input type="password" name="password" maxlength="128" required>
      <button class="btn" type="submit">ACCESS SYSTEM</button>
    </form>
  </div>
  <div class="ft">MADE BY ARYAN GIRI</div>
</div>
</body></html>"""

    def _dash(self, cwd):
        for fpath in [os.path.join(BASE_DIR, "static", "dashboard.html"),
                      os.path.join(os.getcwd(), "static", "dashboard.html")]:
            if os.path.isfile(fpath):
                raw = open(fpath, "r", encoding="utf-8").read()
                raw = raw.replace("__INITIAL_CWD__", esc(cwd))
                raw = raw.replace("__TERMUX_HOME__", esc(TERMUX_HOME))
                return raw
        return f"<pre style='color:red;padding:20px'>dashboard.html not found — expected: {esc(os.path.join(BASE_DIR,'static','dashboard.html'))}</pre>"


# ══════════════════════════════════════════════
#  ENTRY
# ══════════════════════════════════════════════
if __name__ == "__main__":
    startup()
    # Pre-warm TTS engine cache in background so first click is instant
    import threading as _t
    _t.Thread(target=get_tts_engines, daemon=True).start()
    dash = os.path.join(BASE_DIR, "static", "dashboard.html")
    print(f"""
  ╔═════════════════════════════════════╗
  ║   ARYTERLINK  —  by Aryan Giri      ║
  ╚═════════════════════════════════════╝
  [+] http://0.0.0.0:{PORT}
  [+] Termux home : {TERMUX_HOME}
  [+] Res dir     : {RES_DIR}
  [{'+'if os.path.isfile(dash)else'!'}] Dashboard  : {dash}
  [+] Brute guard : {MAX_ATTEMPTS} attempts / {LOCKOUT_SECS}s lockout
""")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
