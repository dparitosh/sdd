"""Background wrapper — sets PYTHONPATH, loads .env, runs vectorize_all."""
import os, sys, subprocess, pathlib

backend = pathlib.Path(__file__).parent.parent  # backend/
root = backend.parent                            # project root

# Load .env from project root
env_file = root / ".env"
env = os.environ.copy()
env["PYTHONPATH"] = str(backend)

if env_file.is_file():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()

log_out = backend / "logs" / "vectorize_all.log"
log_err = backend / "logs" / "vectorize_err.log"
log_out.parent.mkdir(exist_ok=True)

args = sys.argv[1:]  # forward all extra args
cmd = [sys.executable, "-u", str(backend / "scripts" / "vectorize_all.py")] + args

print(f"Running: {' '.join(cmd)}", flush=True)
print(f"stdout -> {log_out}", flush=True)
print(f"stderr -> {log_err}", flush=True)

with open(log_out, "w", encoding="utf-8") as fo, open(log_err, "w", encoding="utf-8") as fe:
    r = subprocess.run(cmd, env=env, cwd=str(backend), stdout=fo, stderr=fe)

print(f"Exit code: {r.returncode}", flush=True)
sys.exit(r.returncode)
