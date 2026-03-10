#!/bin/bash
cd /root/purevolley-worker

# Reset ERROR videos back to PROCESSING
python3 -c "
from supabase import create_client
from dotenv import load_dotenv
import os
load_dotenv()
sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
resp = sb.table('videos').select('id,title').eq('status','ERROR').execute()
print(f'Resetting {len(resp.data)} ERROR videos...')
for v in resp.data:
    sb.table('videos').update({'status':'PROCESSING','progress':0}).eq('id',v['id']).execute()
    print(f'  Reset: {v[\"title\"]}')
resp2 = sb.table('videos').select('id,title').eq('status','PROCESSING').execute()
print(f'PROCESSING videos: {len(resp2.data)}')
"

# Kill old worker and launch new one
pkill -f "python3.*worker.py" 2>/dev/null || true
sleep 2
nohup python3 worker.py > worker_output.log 2>&1 &
echo "Worker PID: $!"
sleep 5
tail -30 worker_output.log
