from actuator.utils import ssh_exec, get_creds

def handle_conpot_action(act_type, plugin):
    hp = "conpot"
    ip, username, password, port = get_creds(hp)

    allowed_plugins = {"modbus", "enip", "s7comm", "ipmi", "snmp", "bacnet", "http"}
    if plugin not in allowed_plugins:
        return False, f"❌ Plugin '{plugin}' not supported by Conpot", "N/A"

    start_cmd = (
        "cd ~/conpot-github && "
        "nohup ./bin/conpot -c ~/conpot-github/conpot.cfg "
        "-t ~/conpot-github/conpot/templates/default > ~/conpot-github/conpot.log 2>&1 &"
    )
    stop_cmd = "pkill -f 'conpot'"

    if act_type == "enable_plugin":
        cmd = start_cmd
    elif act_type == "disable_plugin":
        cmd = stop_cmd
    else:
        return False, "❌ Invalid action type", "N/A"

    success, output = ssh_exec(ip, username, password, cmd, port=port)
    return success, output, cmd