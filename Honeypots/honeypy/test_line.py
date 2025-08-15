import sys
import os

# Add the full path to the loggers/mongodb directory
sys.path.append(os.path.abspath("loggers/mongodb"))

from honeypy_mongodb import process

log_line = "2025-07-29 01:55:40,929868,+0530 [FTPProtocol,8,127.0.0.1] FTP command from 127.0.0.1: USER tester"
parts = log_line.strip().split()
time_parts = parts[1].split(",")

process(None, None, parts, time_parts)
