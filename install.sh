#!/data/data/com.termux/files/usr/bin/bash
# ─────────────────────────────────────────────────────────
#  AryterLink — Installer
#  Author: Aryan Giri
# ─────────────────────────────────────────────────────────

# ── Colors ──
R='\033[0;31m'  # red
G='\033[0;32m'  # green
Y='\033[0;33m'  # yellow
C='\033[0;36m'  # cyan
B='\033[1;34m'  # blue bold
W='\033[1;37m'  # white bold
N='\033[0m'     # reset
TICK="${G}✔${N}"
CROSS="${R}✘${N}"
ARROW="${C}→${N}"

# ── Banner ──
clear
echo ""
echo -e "${C}  ╔═════════════════════════════════════════╗${N}"
echo -e "${C}  ║${W}          A R Y T E R L I N K            ${C}║${N}"
echo -e "${C}  ║${N}        Remote Termux Control Panel      ${C}║${N}"
echo -e "${C}  ║${N}          Installer — by Aryan Giri      ${C}║${N}"
echo -e "${C}  ╚═════════════════════════════════════════╝${N}"
echo ""

# ── Helpers ──
info()    { echo -e "  ${ARROW} ${W}$*${N}"; }
ok()      { echo -e "  ${TICK}  $*"; }
warn()    { echo -e "  ${Y}⚠${N}  $*"; }
err()     { echo -e "  ${CROSS} ${R}$*${N}"; }
section() { echo ""; echo -e "${B}  ══ $* ══${N}"; echo ""; }
die()     { err "$*"; echo ""; exit 1; }

# ── Check we are inside Termux ──
if [ -z "$TERMUX_VERSION" ] && [ ! -d "/data/data/com.termux" ]; then
  die "This script must be run inside Termux."
fi

# ── Check internet ──
section "CHECKING CONNECTIVITY"
if ping -c1 -W3 8.8.8.8 &>/dev/null; then
  ok "Internet reachable"
else
  die "No internet connection. Connect and retry."
fi

# ── Step 1 — Update apt ──
section "UPDATING PACKAGE INDEX"
info "Running apt update..."
if apt update -y &>/dev/null; then
  ok "Package index updated"
else
  warn "apt update had warnings — continuing anyway"
fi

# ── Step 2 — Core system packages ──
section "INSTALLING SYSTEM PACKAGES"

APT_PACKAGES=(
  "python"            # Python 3
  "wget"              # wget download method
  "curl"              # general HTTP utility
  "termux-api"        # termux-* commands (battery, sms, torch, etc.)
)

for pkg in "${APT_PACKAGES[@]}"; do
  # Skip if already installed
  if dpkg -s "$pkg" &>/dev/null; then
    ok "$pkg (already installed)"
    continue
  fi
  info "Installing $pkg..."
  if apt install -y "$pkg" &>/dev/null; then
    ok "$pkg"
  else
    err "Failed to install $pkg"
    FAILED_APT="$FAILED_APT $pkg"
  fi
done

# ── Step 3 — espeak-ng for TTS ──
section "INSTALLING TTS ENGINES"
info "Checking espeak-ng (eSpeak TTS engine)..."
if dpkg -s espeak-ng &>/dev/null; then
  ok "espeak-ng (already installed)"
else
  info "Installing espeak-ng..."
  if apt install -y espeak-ng &>/dev/null; then
    ok "espeak-ng installed"
  else
    warn "espeak-ng install failed — Termux TTS will still work"
  fi
fi

# ── Step 4 — pip packages ──
section "INSTALLING PYTHON PACKAGES"

# AryterLink only uses stdlib — but upgrade pip cleanly
info "Upgrading pip..."
if python -m pip install --upgrade pip --quiet 2>/dev/null; then
  ok "pip up to date"
else
  warn "pip upgrade had issues — stdlib usage unaffected"
fi

ok "No third-party pip packages required (pure stdlib)"

# ── Step 5 — Termux:API companion app check ──
section "TERMUX:API APP CHECK"
info "Checking if Termux:API app is installed..."

# Try a quick harmless termux-api call (clipboard get is safe)
if termux-clipboard-get &>/dev/null 2>&1; then
  ok "Termux:API app is installed and working"
else
  echo ""
  warn "Termux:API app may NOT be installed or may need permissions."
  echo ""
  echo -e "  ${Y}ACTION REQUIRED:${N}"
  echo -e "  1. Install ${W}Termux:API${N} from F-Droid:"
  echo -e "     ${C}https://f-droid.org/packages/com.termux.api/${N}"
  echo -e "  2. Grant all permissions to the Termux:API app in Android Settings"
  echo -e "  3. Grant Termux itself: Storage, SMS, Contacts, Camera, Microphone, Location"
  echo ""
  read -r -p "  Press ENTER once you have installed Termux:API to continue..." _
fi

# ── Step 6 — Android permissions reminder ──
section "ANDROID PERMISSIONS REQUIRED"
echo -e "  Grant these permissions to ${W}Termux${N} and ${W}Termux:API${N} in Android Settings:"
echo ""
echo -e "  ${C}Termux:${N}"
echo -e "    ${ARROW} Storage     — for saving photos/audio to res/"
echo -e "    ${ARROW} SMS         — termux-sms-list / termux-sms-send"
echo -e "    ${ARROW} Contacts    — termux-contact-list"
echo -e "    ${ARROW} Camera      — termux-camera-photo"
echo -e "    ${ARROW} Microphone  — termux-record-audio"
echo -e "    ${ARROW} Location    — termux-location (GPS)"
echo -e "    ${ARROW} Phone       — termux-telephony-call / termux-call-log"
echo ""
echo -e "  ${C}Termux:API app:${N}"
echo -e "    ${ARROW} Same permissions as above"
echo ""

# ── Step 7 — Create res/ dir ──
section "SETTING UP DIRECTORIES"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RES_DIR="$SCRIPT_DIR/res"

if [ -d "$RES_DIR" ]; then
  ok "res/ directory exists: $RES_DIR"
else
  mkdir -p "$RES_DIR"
  ok "res/ directory created: $RES_DIR"
fi

# ── Step 8 — Check auth.txt ──
AUTH_FILE="$SCRIPT_DIR/auth.txt"
if [ -f "$AUTH_FILE" ]; then
  ok "auth.txt exists"
  # Warn if still using defaults
  if grep -q "password=admin123" "$AUTH_FILE"; then
    warn "You are using the default password (admin123) — change it in auth.txt!"
  fi
else
  info "Creating default auth.txt..."
  printf "username=admin\npassword=admin123\n" > "$AUTH_FILE"
  ok "auth.txt created with defaults — CHANGE THE PASSWORD before exposing to network"
fi

# ── Step 9 — Check main.py and dashboard.html ──
section "VERIFYING ARYTERLINK FILES"

if [ -f "$SCRIPT_DIR/main.py" ]; then
  ok "main.py found"
else
  err "main.py NOT found in $SCRIPT_DIR"
  err "Make sure install.sh is in the same folder as main.py"
fi

if [ -f "$SCRIPT_DIR/static/dashboard.html" ]; then
  ok "static/dashboard.html found"
else
  err "static/dashboard.html NOT found"
  err "Make sure the static/ folder is next to main.py"
fi

# ── Step 10 — Summary ──
section "INSTALL SUMMARY"

echo -e "  ${G}Python:${N}        $(python --version 2>&1)"
echo -e "  ${G}wget:${N}          $(wget --version 2>&1 | head -1)"
echo -e "  ${G}termux-api:${N}    $(dpkg -s termux-api 2>/dev/null | grep Version | awk '{print $2}')"
echo -e "  ${G}espeak-ng:${N}     $(dpkg -s espeak-ng 2>/dev/null | grep Version | awk '{print $2}' || echo 'not installed')"
echo -e "  ${G}res/ dir:${N}      $RES_DIR"
echo -e "  ${G}auth.txt:${N}      $AUTH_FILE"

if [ -n "$FAILED_APT" ]; then
  echo ""
  warn "Some packages failed to install:$FAILED_APT"
  warn "Try manually: apt install$FAILED_APT"
fi

# ── Done ──
echo ""
echo -e "${C}  ╔═════════════════════════════════════════╗${N}"
echo -e "${C}  ║${G}         INSTALLATION COMPLETE!          ${C}║${N}"
echo -e "${C}  ╚═════════════════════════════════════════╝${N}"
echo ""
echo -e "  ${W}To start AryterLink:${N}"
echo -e "  ${C}  cd $(dirname "$SCRIPT_DIR/main.py")${N}"
echo -e "  ${C}  python main.py${N}"
echo ""
echo -e "  ${W}Then open in browser:${N}"
echo -e "  ${C}  http://localhost:8080${N}"
echo -e "  ${Y}  (or your phone's IP from another device)${N}"
echo ""
echo -e "  ${W}Default login:${N}  admin / admin123"
echo -e "  ${R}  ← Change this in auth.txt before using on a network!${N}"
echo ""
