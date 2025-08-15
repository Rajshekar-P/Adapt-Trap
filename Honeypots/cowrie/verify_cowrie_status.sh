#!/bin/bash
echo "=== Cowrie Telnet Status ==="
grep telnet_enabled ~/cowrie/etc/cowrie.cfg

echo "=== Listening Ports (expect NO port 23) ==="
sudo ss -tulnp | grep ':23' || echo "No Telnet port open ✅"

echo "=== Cowrie Recent Logs ==="
tail -n 20 ~/cowrie/var/log/cowrie/cowrie.log | grep -i telnet || echo "No Telnet startup logs ✅"
