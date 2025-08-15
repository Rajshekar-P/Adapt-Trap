from actuator.utils import ssh_exec, get_creds

def handle_cowrie_action(act_type, plugin):
    hp = "cowrie"
    ip, username, password, port = get_creds(hp)

    allowed_plugins = {"telnet", "ssh"}  # ✅ Cowrie only supports these
    if plugin not in allowed_plugins:
        return False, f"❌ Plugin '{plugin}' not supported by Cowrie", "N/A"

    if act_type == "disable_plugin":
        cmd = "rm -f ~/cowrie/etc/enable_telnet.flag && ~/cowrie/bin/cowrie restart"
    elif act_type == "enable_plugin":
        cmd = "touch ~/cowrie/etc/enable_telnet.flag && ~/cowrie/bin/cowrie restart"
    else:
        return False, f"❌ Unknown action {act_type}", "N/A"

    return ssh_exec(ip, username, password, cmd, port) + (cmd,)