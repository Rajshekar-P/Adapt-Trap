from actuator.utils import ssh_exec, get_creds

def handle_honeypy_action(act_type, plugin):
    hp = "honeypy"
    ip, username, password, port = get_creds(hp)

    config_path = "~/honeypy/HoneyPy/etc/services.cfg"

    plugin_section = {
        "ftp": "FTP",
        "http": "HTTP",
        "echo": "Echo",
        "motd": "MOTD"
    }.get(plugin.lower())

    if not plugin_section:
        return False, f"❌ Plugin '{plugin}' not supported by HoneyPy", "N/A"

    if act_type == "disable_plugin":
        sed_cmd = f"sed -i '/\\[{plugin_section}\\]/,/enabled/s/enabled *= *Yes/enabled = No/' {config_path}"
    elif act_type == "enable_plugin":
        sed_cmd = f"sed -i '/\\[{plugin_section}\\]/,/enabled/s/enabled *= *No/enabled = Yes/' {config_path}"
    else:
        return False, f"❌ Unknown action type: {act_type}", "N/A"

    cmd = (
        f"{sed_cmd} && sudo systemctl restart honeypy-mongo-logger && "
        f"~/honeypy/HoneyPy/stop_honeypy.sh && sleep 2 && "
        f"nohup python3 ~/honeypy/HoneyPy/Honey.py > ~/honeypy/HoneyPy/logs/honeypy.log 2>&1 &"
    )

    success, output = ssh_exec(ip, username, password, cmd, port=port)
    return success, output, cmd