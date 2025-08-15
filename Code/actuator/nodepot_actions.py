from actuator.utils import ssh_exec, get_creds

def handle_nodepot_action(act_type, plugin):
    honeypot = "nodepot-lite"
    ip, username, password, port = get_creds(honeypot)

    allowed_plugins = {"node-web"}
    if plugin not in allowed_plugins:
        return False, f"❌ Plugin '{plugin}' not supported by Nodepot-lite", "N/A"

    if act_type == "disable_plugin":
        cmd = "docker stop nodepot-lite"
    elif act_type == "enable_plugin":
        cmd = (
            "docker start nodepot-lite || "
            "cd ~/nodepot-lite && "
            "docker run -d --name nodepot-lite -p 80:80 -v ~/nodepot-lite/uploads:/app/uploads nodepot-lite"
        )
    elif act_type == "restart_plugin":
        cmd = (
            "docker restart nodepot-lite || "
            "cd ~/nodepot-lite && "
            "docker run -d --name nodepot-lite -p 80:80 -v ~/nodepot-lite/uploads:/app/uploads nodepot-lite"
        )
    else:
        return False, f"❌ Unknown action type: {act_type}", "N/A"

    success, output = ssh_exec(ip, username, password, cmd, port=port)
    return success, output, cmd