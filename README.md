# 🔥 AryterLink — Remote Termux Control Panel

> **Control your entire Android phone from any browser, anywhere in the world.**
> Built for Termux. Built for power users. Built different.

---

```
  ╔═════════════════════════════════════════╗
  ║          A R Y T E R L I N K           ║
  ║      Remote Termux Control Panel        ║
  ║          — by Aryan Giri —              ║
  ╚═════════════════════════════════════════╝
```

---

## 🚀 What Is AryterLink?

AryterLink is a **self-hosted, browser-based control panel** that runs inside Termux on your Android device and exposes a sleek, secure web dashboard — accessible from **any device on the same network, or anywhere on the internet** using a tunnel.

No root. No shady APKs. No third-party servers. Just Python, your phone, and raw power.

**What can you do with it?**

| Category | Capabilities |
|---|---|
| 💬 Messaging | Read SMS inbox, send SMS to any number |
| 📞 Calls | View call history, place outgoing calls |
| 👥 Contacts | Browse and search your entire contact list |
| 🔦 Hardware | Toggle flashlight, set screen brightness |
| 🔋 Device | Real-time battery stats, health, voltage, temperature |
| 🫆 Biometrics | Trigger fingerprint authentication remotely |
| 📷 Camera | Capture photos from front or rear camera |
| 🎤 Audio | Record microphone audio, saved to your device |
| 🔊 TTS | Text-to-speech via Termux API or eSpeak-NG engine |
| 📍 Location | Get real-time GPS coordinates + Google Maps link |
| 📶 Network | Wi-Fi info, scan nearby networks, toggle Wi-Fi |
| 📋 Clipboard | Read or write phone clipboard remotely |
| 🔔 Notifications | Post or remove Android system notifications |
| 🍞 Toast | Show Android toast messages remotely |
| ⬇️ Download | Download files via termux-download or wget |
| 🗂️ Files | Browse, preview, and download all captured photos and audio |
| 💻 Terminal | Full interactive shell with `cd` navigation, command history |
| 🛡️ Security | Brute-force lockout, session auth, XSS protection, CSP headers |

Everything rendered beautifully — no raw JSON dumps, proper tables, live previews.

---

## ⚙️ Setup Guide

### Step 1 — Install Termux

Termux is a powerful terminal emulator and Linux environment for Android. You **must install it from a trusted source** — the Google Play version is outdated and unsupported.

> ⚠️ **Do NOT install Termux from the Google Play Store.** It is abandoned and broken. Always use F-Droid or the official GitHub release.

**Official sources only:**

| Source | Link |
|---|---|
| 🟦 F-Droid (recommended) | https://f-droid.org/packages/com.termux/ |
| 🐙 GitHub Releases | https://github.com/termux/termux-app/releases |

Install the APK, open Termux, and allow storage permissions if prompted.

---

### Step 2 — Install Termux:API

Termux:API is a **companion app** that bridges Termux commands to real Android hardware APIs. Without it, tools like the camera, SMS, torch, GPS, sensors, and fingerprint **will not function at all**.

**Official sources only:**

| Source | Link |
|---|---|
| 🟦 F-Droid (recommended) | https://f-droid.org/packages/com.termux.api/ |
| 🐙 GitHub Releases | https://github.com/termux/termux-api-package/releases |

> **Why do you need both Termux AND Termux:API installed together?**
>
> Think of them as two halves of the same system:
>
> - **Termux** is the terminal where you run commands like `termux-camera-photo` or `termux-sms-list`
> - **Termux:API** is the background Android app that receives those commands and actually talks to the Android hardware
>
> The flow looks like this:
>
> ```
> Your command in Termux
>       ↓
>   termux-api package (the bridge)
>       ↓
>   Termux:API Android app
>       ↓
>   Android Hardware API (Camera, SMS, GPS, etc.)
>       ↓
>   Result returned to Termux
> ```
>
> Neither works alone for hardware features. You also need to install both from the **same source** (both F-Droid, or both GitHub) — mixing signing keys from different sources causes compatibility failures.

---

### Step 3 — Grant Android Permissions

This is the most important step people skip. Without permissions, AryterLink's hardware features will silently fail or return errors.

**How to open app permissions on most modern Android devices:**

1. Long-press the **Termux** app icon on your home screen or app drawer
2. Tap **App Info** (or the ⓘ icon that appears)
3. Tap **Permissions**
4. Allow the permissions for the features you want to use

Repeat the exact same steps for the **Termux:API** app.

**Permission map — what each AryterLink feature needs:**

| Android Permission | AryterLink Features |
|---|---|
| 📱 SMS | Read SMS inbox, Send SMS |
| 📞 Phone / Call Logs | View call history, Make outgoing calls |
| 👥 Contacts | Browse and search contacts |
| 📷 Camera | Capture photos (front/rear) |
| 🎤 Microphone | Record audio |
| 📍 Location | GPS coordinates, Google Maps link |
| 💾 Storage / Files & Media | Save captured photos and audio to `res/` folder |
| 🔔 Notifications | Post and remove system notifications |

> You can grant only the permissions for features you actually use. AryterLink handles missing permissions gracefully — denied features return an error in the dashboard without crashing anything else.

---

### ✅ Is This Safe?

**Yes — as long as you install from official sources.**

Termux and Termux:API are **fully open-source** projects maintained by a large active community. Their source code is publicly audited on GitHub. They do not collect data, have no analytics, and make no network connections on their own.

The only way this becomes unsafe is if you:
- Install Termux or Termux:API from **unofficial, unknown, or modified APKs** (random websites, Telegram, etc.)
- Run **unknown scripts** inside Termux without understanding what they do
- Share your AryterLink credentials or tunnel URL with untrusted people

Stick to F-Droid or the official GitHub releases and you have nothing to worry about. The Android permission system also protects you — no app can access your camera, SMS, or location without you explicitly approving it.

---

### Step 4 — Update Termux Packages

Open Termux and run:

```bash
pkg update && pkg upgrade -y
```

This updates all system packages to their latest versions. Always do this before installing anything new.

---

### Step 5 — Install AryterLink

```bash
# Install git
pkg install git -y

# Clone the repository
git clone https://github.com/giriaryan694-a11y/AryterLink

# Enter the project folder
cd AryterLink

# Make the installer executable
chmod +x install.sh

# Run the installer
./install.sh
```

The installer automatically handles everything:
- Installs `python`, `wget`, `curl`, `termux-api`, `espeak-ng` via `apt`
- Upgrades `pip`
- Creates the `res/` directory for captured files
- Creates `auth.txt` with default credentials if missing
- Verifies all project files are in place
- Checks if Termux:API app is responding

---

### Step 6 — Launch AryterLink

```bash
python main.py
```

You'll see output like this:

```
  ╔═════════════════════════════════════╗
  ║   ARYTERLINK  —  by Aryan Giri      ║
  ╚═════════════════════════════════════╝
  [+] http://0.0.0.0:8080
  [+] Termux home : /data/data/com.termux/files/home
  [+] Res dir     : /data/data/com.termux/files/home/AryterLink/res
  [+] Brute guard : 5 attempts / 300s lockout
```

**Boom. AryterLink is running.** 🎉

Open your browser and go to:

```
http://localhost:8080          ← from the phone itself
http://<your-phone-ip>:8080   ← from another device on same Wi-Fi
```

Default login credentials:
```
Username: admin
Password: admin123
```

> 🔴 Change these in `auth.txt` before using on any network.

---

## 🌐 Access AryterLink From Anywhere in the World

To access your AryterLink panel from outside your home network — from any browser, anywhere on earth — use a free tunnel. These create a temporary public HTTPS URL that forwards traffic to your local server.

### Why Choose Tailscale Over Cloudflare Tunnel?

| Feature/Aspect         | **Tailscale**                          | **Cloudflare Tunnel**                |
|------------------------|----------------------------------------|---------------------------------------|
| **Privacy & Security** | Your data is encrypted and only accessible to devices you authorize. | Your data passes through Cloudflare’s infrastructure, even if it’s encrypted. |
| **Sensitive Data**     | SMS, contacts, and other sensitive data stay on your personal network, not exposed to third parties. | SMS, contacts, and other data may be exposed to Cloudflare’s servers during transit. |
| **Control**            | You control the entire network; no third-party involvement. | Requires trusting Cloudflare with your traffic. |
| **Ease of Use**        | Simple setup, no need to open ports or manage DNS. | Requires managing tunnels and DNS records. |

**Recommendation:** For applications handling sensitive data (like SMS and contacts), Tailscale is the safer and more private option.

### Option A — TailScale
download from here : https://tailscale.com/download

### Option B — Cloudflare Tunnel

# Install cloudflared
```
pkg install cloudflared -y
```
# Start tunnel (AryterLink must be running on port 8080)
```
cloudflared tunnel --url http://localhost:8080


You get a URL like: `https://something-random.trycloudflare.com`
```
### Option C — ngrok

```bash
# Install ngrok
pkg install ngrok -y

# Start tunnel
ngrok http 8080
```

You get a URL like: `https://abc123.ngrok-free.app`

> **🔒 Privacy note:** Both Cloudflare and ngrok generate randomized URLs that are **completely invisible to search engines and web crawlers**. Nobody can stumble across your panel by Googling. The URL simply doesn't exist in any index. Only someone you directly share the URL with can access it.
>
> Still — always use strong, unique credentials and restart the tunnel periodically to rotate the URL if you're concerned.

**Before making AryterLink accessible over the internet, always:**
1. Edit `auth.txt` and change username and password from the defaults
2. Use a strong password (mix of letters, numbers, symbols)
3. Only share the tunnel URL with people you explicitly trust
4. Close the tunnel (Ctrl+C) when you're done using it remotely

---

## 📁 Project Structure

```
AryterLink/
├── main.py              ← Python HTTP server — run this to start
├── install.sh           ← One-command installer for all dependencies
├── auth.txt             ← Login credentials (edit before going online!)
├── res/                 ← All photos and audio captured by AryterLink
└── static/
    └── dashboard.html   ← The entire web dashboard UI
```

---

## 🛠️ Requirements at a Glance

| Requirement | How to get it |
|---|---|
| Android 7.0+ | Your phone |
| Termux app | [F-Droid](https://f-droid.org/packages/com.termux/) / [GitHub](https://github.com/termux/termux-app/releases) |
| Termux:API app | [F-Droid](https://f-droid.org/packages/com.termux.api/) / [GitHub](https://github.com/termux/termux-api-package/releases) |
| Python 3 | auto-installed by `install.sh` |
| termux-api package | auto-installed by `install.sh` |
| wget | auto-installed by `install.sh` |
| espeak-ng | auto-installed by `install.sh` |

---

## ⚖️ Ethical & Legal Disclaimer

> **Please read this before using AryterLink.**

AryterLink is an **open-source personal device management tool** built for legitimate use cases:

- Remotely controlling **your own Android device** when you can't physically reach it
- Accessibility and convenience for power users and developers
- Educational exploration of Android APIs and Termux capabilities
- Personal automation, remote file access, and device monitoring

### The developer (Aryan Giri) is not responsible for any misuse, unauthorized access, privacy violations, or illegal activity carried out using this tool.

By using AryterLink, you agree that:

- You will only use it on **devices you own or have explicit written permission to access**
- You will not use it to access another person's SMS, camera, location, or contacts without their full knowledge and consent
- You understand that **unauthorized access to another person's device or data is a criminal offense** in virtually every country in the world
- You take full personal and legal responsibility for how you deploy and use this software

### Why AryterLink is inherently hard to abuse

Unlike typical surveillance apps or spyware that can be silently installed with one tap, AryterLink requires a long and fully visible technical setup that the device owner must actively perform themselves:

1. **Manually installing Termux** from F-Droid (requires enabling unknown sources or using F-Droid app)
2. **Manually installing Termux:API** from the same trusted source
3. **Manually granting each Android permission** — Android pops up a permission dialog for every single one. The user cannot miss this.
4. **Consciously running a Python server** from inside the Termux terminal
5. **Setting up a tunnel** (cloudflared or ngrok) with additional commands
6. **Knowing the login credentials** to access the dashboard

This is not a "install APK → accept all permissions → done" scenario. Every step requires the device owner's deliberate, informed action. There is no silent installation, no background persistence, no stealth mode. When AryterLink is running, there is a visible Termux session active on the device.

**Use this tool the way it was intended — to control your own phone, your own way.**

---

*Made with ❤️ by Aryan Giri*
