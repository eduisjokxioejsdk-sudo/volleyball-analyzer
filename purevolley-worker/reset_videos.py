#!/usr/bin/env python3
"""Reset READY videos with 0 points back to PROCESSING"""
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()
sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

resp = sb.table('videos').select('id,title,status,points_data').eq('status', 'READY').execute()
print(f"READY videos: {len(resp.data)}")

for v in resp.data:
    pd = v.get('points_data', [])
    if isinstance(pd, list):
        pts = len(pd)
    elif isinstance(pd, dict):
        pts = len(pd.get('points', []))
    else:
        pts = 0
    print(f"  {v['id'][:8]}... {v['title']} -> {pts} points")
    if pts == 0:
        sb.table('videos').update({'status': 'PROCESSING', 'progress': 0}).eq('id', v['id']).execute()
        print(f"    -> Reset to PROCESSING")

# Also check PROCESSING
resp2 = sb.table('videos').select('id,title,status').eq('status', 'PROCESSING').execute()
print(f"\nPROCESSING videos now: {len(resp2.data)}")
for v in resp2.data:
    print(f"  {v['id'][:8]}... {v['title']}")
