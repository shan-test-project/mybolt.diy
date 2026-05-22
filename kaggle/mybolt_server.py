import subprocess, time, os

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.stdout.strip(): print(r.stdout.strip()[-300:])
    if r.returncode != 0 and r.stderr.strip(): print("WARN:", r.stderr.strip()[-200:])
    return r.returncode == 0

# ── [1/6] Node.js 20 + pnpm ──────────────────────────────
print("=== [1/6] Node.js 20 + pnpm ===")
run("curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1")
run("apt-get install -y nodejs > /dev/null 2>&1")
run("npm install -g pnpm > /dev/null 2>&1")
print("node:", subprocess.check_output("node --version", shell=True).decode().strip(),
      "| pnpm:", subprocess.check_output("pnpm --version", shell=True).decode().strip())

# ── [2/6] Clone bolt.diy ─────────────────────────────────
print("\n=== [2/6] Clone bolt.diy ===")
run("rm -rf bolt_diy")
run("git clone --depth 1 https://github.com/stackblitz-labs/bolt.diy.git bolt_diy 2>&1 | tail -3")
print("Cloned!")

# ── [3/6] Patch vite.config.ts for tunnel ────────────────
print("\n=== [3/6] Patch vite.config.ts ===")
run("cd bolt_diy && sed -i 's/server: {/server: { allowedHosts: true,/' vite.config.ts 2>/dev/null || true")
with open("bolt_diy/.env.local", "w") as f:
    f.write("VITE_LOG_LEVEL=debug\n")
print("Patched — allowedHosts: true")

# ── [4/6] Install dependencies ───────────────────────────
print("\n=== [4/6] pnpm install (takes 2-4 min) ===")
run("cd bolt_diy && pnpm install 2>&1 | tail -5")
print("Dependencies ready!")

# ── [5/6] Start bolt.diy dev server ─────────────────────
print("\n=== [5/6] Start bolt.diy on port 5173 ===")
bolt_proc = subprocess.Popen(
    ["pnpm", "run", "dev"],
    cwd="/kaggle/working/bolt_diy",
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
)
booted = False
for i in range(90):
    r = subprocess.run("curl -sf http://localhost:5173 > /dev/null 2>&1", shell=True)
    if r.returncode == 0:
        print(f"bolt.diy UP on :5173  ({i}s)"); booted = True; break
    time.sleep(1)
    if i > 0 and i % 20 == 0: print(f"  ...{i}s elapsed")
if not booted:
    print("Warning: may not have started — continuing anyway")

# ── [6/6] ngrok tunnel → port 5173  (NO VNC!) ───────────
print("\n=== [6/6] ngrok tunnel ===")
run("pip install pyngrok -q")
from pyngrok import ngrok

NGROK_TOKEN = "3E2STeo9KDykxWCTVVlDyAZ97Gv_vbY8c19bcXuQjLoFx3SF"
ngrok.set_auth_token(NGROK_TOKEN)
tunnel = ngrok.connect(5173, "http")
PUBLIC_URL = tunnel.public_url

print()
print("=" * 60)
print("  bolt.diy IS LIVE  —  NO VNC!")
print("=" * 60)
print(f"  >>> {PUBLIC_URL}")
print()
print("  Open this URL on your phone.")
print("  bolt.diy Settings (gear icon) → add your LLM API key.")
print("  Kaggle handles ALL inference — your phone is just the screen.")
print("=" * 60)

# ── Keep-alive (do NOT stop this cell) ───────────────────
print("\nSession live. Keep this cell running.")
try:
    while True:
        time.sleep(30)
        ok = subprocess.run(
            "curl -sf http://localhost:5173 > /dev/null 2>&1", shell=True
        ).returncode == 0
        print(f"[{time.strftime('%H:%M:%S')}] bolt={'OK' if ok else 'DOWN'}  {PUBLIC_URL}")
except KeyboardInterrupt:
    bolt_proc.terminate()
    ngrok.disconnect(PUBLIC_URL)
    ngrok.kill()
    print("Stopped.")
