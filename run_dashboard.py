"""
One-command launcher for the NFL draft predictor dashboard.

Local usage (only you can access):
    python run_dashboard.py

Share with a friend over the internet:
    python run_dashboard.py --share
    # -> prints a public URL like https://cool-words-1234.trycloudflare.com
    # Send that URL to your friend. They can browse the dashboard; simulation
    # runs still happen on YOUR machine.

Safety flags:
    --read-only          Disable POST /api/simulate (friend can view, not run sims).
    --token TOKEN        Require X-Auth-Token: TOKEN header on /api/simulate.
                         Combined with --share, protects sim from abuse.

Other options:
    --port 9000          Change the port (default 8000).
    --build              Force rebuild the frontend before launching.

Under the hood --share tries (in order):
    1. cloudflared quick-tunnel (best; install via Scoop/Winget on Windows)
    2. ssh -R with localhost.run or serveo.net (requires ssh, built into Win11)
    3. LAN-only (prints your private IP so friends on same Wi-Fi can connect)
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
STATIC_INDEX = ROOT / "src" / "api" / "static" / "index.html"


# ---------------------------------------------------------------------------
# Frontend build
# ---------------------------------------------------------------------------

def ensure_frontend_built(force: bool) -> None:
    if STATIC_INDEX.exists() and not force:
        print(f"[ok] frontend bundle present: {STATIC_INDEX.parent}")
        return
    if not (FRONTEND / "package.json").exists():
        sys.exit(f"[fatal] frontend dir missing: {FRONTEND}")
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        sys.exit("[fatal] npm not found on PATH; install Node.js >= 18")
    print("[build] running `npm run build` in frontend/…")
    subprocess.run([npm, "run", "build"], cwd=FRONTEND, check=True, shell=False)


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------

def lan_ip() -> str:
    """Best-effort local network IP (the one a friend on your Wi-Fi would use)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ---------------------------------------------------------------------------
# Tunneling — cloudflared first, then ssh-based fallback, else LAN info
# ---------------------------------------------------------------------------

CF_URL_RX = re.compile(r"https://[-a-z0-9]+\.trycloudflare\.com")
LHRUN_URL_RX = re.compile(r"https://[-a-z0-9]+\.lhr\.(?:life|domains)")
SERVEO_URL_RX = re.compile(r"https://[-a-z0-9]+\.serveo\.net")


def _find_cloudflared() -> str | None:
    """Find cloudflared on PATH, or in common Windows install locations even
    when winget hasn't refreshed PATH in the current shell."""
    candidate = shutil.which("cloudflared") or shutil.which("cloudflared.exe")
    if candidate:
        return candidate
    for path in [
        r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
        r"C:\Program Files\cloudflared\cloudflared.exe",
        r"C:\Users\colin\AppData\Local\Microsoft\WindowsApps\cloudflared.exe",
    ]:
        if Path(path).exists():
            return path
    return None


def try_cloudflared(port: int) -> subprocess.Popen | None:
    cf = _find_cloudflared()
    if not cf:
        return None
    print("[share] starting cloudflared quick-tunnel…")
    proc = subprocess.Popen(
        [cf, "tunnel", "--url", f"http://localhost:{port}",
         "--no-autoupdate", "--loglevel", "info"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    # Tail output in a daemon thread so we can extract the URL + keep logs flowing
    def _reader() -> None:
        assert proc.stdout is not None
        seen_url = False
        for line in proc.stdout:
            line = line.rstrip()
            m = CF_URL_RX.search(line)
            if m and not seen_url:
                seen_url = True
                print("\n" + "=" * 68)
                print(f"  PUBLIC URL:  {m.group(0)}")
                print("=" * 68 + "\n")
            # Show cloudflared errors clearly; suppress the noisy INFO chatter.
            if "ERR" in line or "error" in line.lower():
                print(f"[cloudflared] {line}")
    threading.Thread(target=_reader, daemon=True).start()
    return proc


def try_ssh_tunnel(port: int) -> subprocess.Popen | None:
    ssh = shutil.which("ssh") or shutil.which("ssh.exe")
    if not ssh:
        return None
    # Try localhost.run first (no account needed), then serveo as fallback.
    # localhost.run: ssh -R 80:localhost:PORT nokey@localhost.run
    print("[share] starting ssh tunnel via localhost.run…")
    proc = subprocess.Popen(
        [ssh, "-o", "StrictHostKeyChecking=accept-new",
         "-o", "ServerAliveInterval=30",
         "-R", f"80:localhost:{port}",
         "-T", "nokey@localhost.run"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    def _reader() -> None:
        assert proc.stdout is not None
        seen_url = False
        for line in proc.stdout:
            line = line.rstrip()
            m = LHRUN_URL_RX.search(line) or SERVEO_URL_RX.search(line)
            if m and not seen_url:
                seen_url = True
                print("\n" + "=" * 68)
                print(f"  PUBLIC URL:  {m.group(0)}")
                print("=" * 68 + "\n")
    threading.Thread(target=_reader, daemon=True).start()
    return proc


def start_tunnel(port: int) -> subprocess.Popen | None:
    proc = try_cloudflared(port)
    if proc is not None:
        return proc
    print("[share] cloudflared not found — falling back to ssh tunnel")
    proc = try_ssh_tunnel(port)
    if proc is not None:
        return proc
    return None


def print_share_help(port: int) -> None:
    ip = lan_ip()
    print("\n" + "=" * 68)
    print("  SHARE FALLBACK")
    print("=" * 68)
    print("  No tunneling tool available. Options:")
    print()
    print(f"  A. Same Wi-Fi as your friend? Send them:  http://{ip}:{port}")
    print("     (Only works when you're on the same network.)")
    print()
    print("  B. Install cloudflared for a public URL:")
    print("       winget install --id Cloudflare.cloudflared")
    print("     Then rerun:  python run_dashboard.py --share")
    print("=" * 68 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=None,
                        help="Bind host (default 127.0.0.1, or 0.0.0.0 with --share)")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--build", action="store_true",
                        help="Force frontend rebuild before launching")
    parser.add_argument("--reload", action="store_true",
                        help="Enable uvicorn --reload (dev only)")
    parser.add_argument("--share", action="store_true",
                        help="Expose via a public tunnel (cloudflared or ssh)")
    parser.add_argument("--read-only", action="store_true",
                        help="Disable POST /api/simulate")
    parser.add_argument("--token", default=None,
                        help="Require this token as X-Auth-Token on /api/simulate")
    args = parser.parse_args()

    host = args.host or ("0.0.0.0" if args.share else "127.0.0.1")

    ensure_frontend_built(args.build)

    # Pass flags to the FastAPI app through environment variables.
    if args.read_only:
        os.environ["DRAFT_READ_ONLY"] = "1"
        print("[auth] read-only mode: POST /api/simulate disabled")
    if args.token:
        os.environ["DRAFT_AUTH_TOKEN"] = args.token
        print(f"[auth] token required for /api/simulate (len={len(args.token)})")

    tunnel_proc: subprocess.Popen | None = None
    if args.share:
        tunnel_proc = start_tunnel(args.port)
        if tunnel_proc is None:
            print_share_help(args.port)

    import uvicorn
    try:
        print(f"[serve] local: http://{lan_ip() if host == '0.0.0.0' else host}:{args.port}")
        uvicorn.run(
            "src.api.app:app",
            host=host,
            port=args.port,
            reload=args.reload,
        )
    finally:
        if tunnel_proc is not None and tunnel_proc.poll() is None:
            print("[share] shutting down tunnel")
            tunnel_proc.terminate()
            try:
                tunnel_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                tunnel_proc.kill()


if __name__ == "__main__":
    main()
