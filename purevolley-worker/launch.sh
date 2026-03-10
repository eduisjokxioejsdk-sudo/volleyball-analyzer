#!/bin/bash
cd /root/purevolley-worker
pkill -f "python3.*worker.py" 2>/dev/null || true
sleep 1
nohup python3 worker.py > worker_output.log 2>&1 &
echo "Worker PID: $!"
sleep 3
tail -20 worker_output.log
