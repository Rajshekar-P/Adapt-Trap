# utils/remote_health.py
from __future__ import annotations
from pathlib import Path
import json, shlex, subprocess

ROOT = Path(__file__).resolve().parents[2]  # .../Code
CREDS_PATH = ROOT / "configs" / "honeypot_creds.json"
HOSTS_PATH = ROOT / "configs" / "honeypot_hosts.json"

def _load(name: str):
    with open(CREDS_PATH, "r") as f: creds = json.load(f)[name]
    with open(HOSTS_PATH, "r") as f: host = json.load(f)[name]
    return host["ip"], int(host["ssh_port"]), creds["username"], creds["password"]

def _ssh(hp: str, cmd: str, timeout: int = 8):
    ip, port, user, pwd = _load(hp)
    ssh_cmd = (
        f"sshpass -p {shlex.quote(pwd)} ssh -p {port} "
        "-o StrictHostKeyChecking=no "
        "-o ConnectTimeout=5 "
        "-oHostKeyAlgorithms=+ssh-rsa "
        "-oPubkeyAcceptedAlgorithms=+ssh-rsa "
        f"{shlex.quote(user)}@{ip} {shlex.quote(cmd)}"
    )
    try:
        out = subprocess.check_output(ssh_cmd, shell=True, stderr=subprocess.STDOUT, timeout=timeout)
        return 0, out.decode().strip()
    except subprocess.CalledProcessError as e:
        return e.returncode, e.output.decode(errors="ignore").strip()
    except Exception as e:
        return 255, str(e)

def _ok(ok: bool, good="✅ Open", bad="❌ Closed"):
    return (good if ok else bad, "green" if ok else "red")

def _pgrep(hp: str, pattern: str) -> bool:
    code, _ = _ssh(hp, f"pgrep -f {shlex.quote(pattern)} >/dev/null && echo ok || echo no")
    return code == 0

def _port(hp: str, port: int, proto="tcp") -> bool:
    if proto == "udp":
        cmd = f"ss -lun | awk '{{print $5}}' | grep -q ':{port}$'"
    else:
        cmd = f"ss -ltn | awk '{{print $4}}' | grep -q ':{port}$'"
    code, _ = _ssh(hp, cmd)
    return code == 0

def _systemd_active(hp: str, unit: str) -> bool:
    code, out = _ssh(hp, f"systemctl is-active {unit} || true")
    return out.strip() == "active"

def _docker_up(hp: str, name_substr: str) -> bool:
    # considers any container whose name contains the substring
    cmd = (
        "docker ps --format '{{.Names}} {{.Status}}' | "
        f"awk 'index($1, \"{name_substr}\")>0 {{print $2}}' | grep -qi '^Up'"
    )
    code, _ = _ssh(hp, cmd)
    return code == 0

# ---- Per-honeypot checks (same logic as your bash script) ----

def cowrie():
    running = _pgrep("cowrie", "twistd.*cowrie")
    ssh_ok  = _port("cowrie", 22, "tcp")
    tel_ok  = _port("cowrie", 23, "tcp")
    return _ok(running and (ssh_ok or tel_ok))

def honeypy():
    logger = _systemd_active("honeypy", "honeypy-mongo-logger")
    ftp_ok = _port("honeypy", 2244, "tcp")
    return _ok(logger and ftp_ok)

def honeytrap():
    up = _docker_up("honeytrap", "honeytrap")  # matches honeytrap, honeytrap_1, etc.
    # Honeytrap often binds one of these TCP ports in your setup
    p21  = _port("honeytrap", 21, "tcp")
    p22  = _port("honeytrap", 22, "tcp")
    p23  = _port("honeytrap", 23, "tcp")
    any_tcp = p21 or p22 or p23
    return _ok(up and any_tcp)

def conpot():
    running = _pgrep("conpot", "conpot")
    modbus  = _port("conpot", 502, "tcp")
    bacnet  = _port("conpot", 47808, "udp")
    http    = _port("conpot", 8800, "tcp")
    ok = running and (modbus or bacnet or http)
    return ("✅ Active", "green") if ok else ("❌ Down", "red")

def nodepot_lite():
    up   = _docker_up("nodepot-lite", "nodepot")
    http = _port("nodepot-lite", 80, "tcp")
    return _ok(up and http)
