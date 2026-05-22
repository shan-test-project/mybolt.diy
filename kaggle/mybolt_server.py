# ==========================================
# MyBolt.diy — bolt.diy on Kaggle
# NO VNC. Direct web URL via ngrok.
# ==========================================
import subprocess
import time
import re
import os

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.stdout.strip():
        print(r.stdout.strip()[-300:])
    if r.returncode != 0 and r.stderr.strip():
        print("WARN:", r.stderr.strip()[-200:])
    return r.returncode == 0

# ==========================================
# STEP 1 — Node.js 20 + pnpm
# ==========================================
print("=== [1/6] Installing Node.js 20 + pnpm ===")
run("curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1")
run("apt-get install -y nodejs > /dev/null 2>&1")
run("npm install -g pnpm > /dev/null 2>&1")

node_ver = subprocess.check_output("node --version", shell=True).decode().strip()
pnpm_ver = subprocess.check_output("pnpm --version", shell=True).decode().strip()
print(f"node: {node_ver}  |  pnpm: {pnpm_ver}")

# ==========================================
# STEP 2 — Clone bolt.diy
# ==========================================
print("\n=== [2/6] Cloning bolt.diy ===")
run("rm -rf bolt_diy")
run("git clone --depth 1 https://github.com/stackblitz-labs/bolt.diy.git bolt_diy 2>&1 | tail -3")
print("Cloned!")

# ==========================================
# STEP 3 — Patch for tunnel + configure
# ==========================================
print("\n=== [3/6] Patching bolt.diy ===")

# Allow all hosts (required for ngrok tunnel to reach the dev server)
run("cd bolt_diy && sed -i 's/server: {/server: { allowedHosts: true,/' vite.config.ts 2>/dev/null || true")

# Minimal .env.local
with open("bolt_diy/.env.local", "w") as f:
    f.write("VITE_LOG_LEVEL=debug\n")

print("Patched vite.config.ts — allowedHosts: true")

# ==========================================
# STEP 4 — Install dependencies
# ==========================================
print("\n=== [4/6] Installing dependencies (2-4 min) ===")
run("cd bolt_diy && pnpm install 2>&1 | tail -5")
print("Dependencies installed!")

# ==========================================
# STEP 5 — Start bolt.diy dev server
# ==========================================
print("\n=== [5/6] Starting bolt.diy server ===")

bolt_proc = subprocess.Popen(
    ["pnpm", "run", "dev"],
    cwd="/kaggle/working/bolt_diy",
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

print("Waiting for bolt.diy on port 5173...")
booted = False
for i in range(90):
    check = subprocess.run(
        "curl -sf http://localhost:5173 > /dev/null 2>&1",
        shell=True,
    )
    if check.returncode == 0:
        print(f"bolt.diy is UP on :5173  (took {i}s)")
        booted = True
        break
    time.sleep(1)
    if i > 0 and i % 20 == 0:
        print(f"  Still booting... {i}s elapsed")

if not booted:
    print("Warning: server may not have fully started — continuing anyway")

# ==========================================
# STEP 6 — ngrok tunnel to port 5173
# ==========================================
print("\n=== [6/6] Creating ngrok tunnel ===")

run("pip install pyngrok -q")
from pyngrok import ngrok, conf

NGROK_TOKEN = "3E2STeo9KDykxWCTVVlDyAZ97Gv_vbY8c19bcXuQjLoFx3SF"
ngrok.set_auth_token(NGROK_TOKEN)

# Tunnel directly to bolt.diy web server (port 5173)
tunnel = ngrok.connect(5173, "http")
PUBLIC_URL = tunnel.public_url

print()
print("=" * 60)
print("  bolt.diy IS LIVE — NO VNC!")
print("=" * 60)
print(f"  >>> YOUR URL: {PUBLIC_URL}")
print()
print("  Open this URL on your phone browser.")
print("  Add your LLM API key in bolt.diy settings (top-right gear).")
print("  Kaggle does ALL the work — your phone is just the screen.")
print("=" * 60)

# ==========================================
# KEEP-ALIVE — do NOT stop this cell
# ==========================================
print("\nSession live. Keep this cell running.")
try:
    while True:
        time.sleep(30)
        check = subprocess.run(
            "curl -sf http://localhost:5173 > /dev/null 2>&1",
            shell=True,
        )
        status = "OK" if check.returncode == 0 else "DOWN"
        print(f"[{time.strftime('%H:%M:%S')}] bolt.diy={status}  ngrok={PUBLIC_URL}")
except KeyboardInterrupt:
    bolt_proc.terminate()
    ngrok.disconnect(PUBLIC_URL)
    ngrok.kill()
    print("Stopped cleanly.")
