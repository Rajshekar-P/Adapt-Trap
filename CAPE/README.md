# CAPE (configs & customizations for Capstone 2)

Included:
- `conf/` (runtime config)
- `analyzer/windows/analysis.conf`
- `modules/*/custom/` (our custom signatures/processing/reporting)
- `data/yara/{custom,local}` (our custom/local YARA rules)
- `systemd/` (service units if used)
- `utils/submit.py` (if customized)

Excluded:
- storage, logs, samples, pcaps, sqlite DBs, virtualenvs.

Note: If any sensitive values are present in conf files, replace them with placeholders before committing,
or generate sanitized `.example.conf` files.
