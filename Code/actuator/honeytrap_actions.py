from actuator.utils import ssh_exec, get_creds

def handle_honeytrap_action(act_type, plugin):
    hp = "honeytrap"
    ip, username, password, port = get_creds(hp)

    allowed_plugins = {"tcp", "udp", "http", "mysql"}
    if plugin not in allowed_plugins:
        return False, f"❌ Plugin '{plugin}' not supported by Honeytrap", "N/A"

    if act_type == "disable_plugin":
        cmd = "docker stop honeytrap_honeytrap_1"
    elif act_type == "enable_plugin":
        cmd = "docker start honeytrap_honeytrap_1"
    elif act_type == "restart_plugin":
        cmd = "docker restart honeytrap_honeytrap_1"
    else:
        return False, f"❌ Unknown action type: {act_type}", "N/A"

    success, result = ssh_exec(ip, username, password, cmd, port)
    return success, result, cmd