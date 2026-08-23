import sys
import os

def main():
    with open('c:/Users/フォーレスト026/MyProject/TaskMiningServer/app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    header = '''"""
routers/dashboard.py - ダッシュボード用APIルーター
"""
from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse, StreamingResponse
import os
import io
import csv
import json
import random
import time
from datetime import datetime
from database import get_connection
from utils import ADMIN_TOKEN_SECRET, resolve_user_id, parse_datetime_to_timestamp, global_staff_map, global_staff_counter
from services.trend_service import get_historical_trend

router = APIRouter(tags=['Dashboard'])

'''

    # L733 is lines[732]
    target_lines = lines[732:]
    
    filtered_lines = []
    i = 0
    while i < len(target_lines):
        line = target_lines[i]
        if line.startswith('@app.get("/api/admin/generate_report")'):
            while i < len(target_lines) and not target_lines[i].startswith('@app.post("/api/dashboard/analyze")'):
                i += 1
            continue
        filtered_lines.append(line)
        i += 1

    processed_lines = []
    for line in filtered_lines:
        if line.startswith('@app.'):
            processed_lines.append(line.replace('@app.', '@router.'))
        else:
            processed_lines.append(line)

    final_lines = []
    for line in processed_lines:
        if 'global global_staff_map' in line or 'global global_staff_counter' in line:
            continue
        final_lines.append(line)

    with open('c:/Users/フォーレスト026/MyProject/TaskMiningServer/routers/dashboard.py', 'w', encoding='utf-8') as out:
        out.write(header)
        out.writelines(final_lines)

if __name__ == '__main__':
    main()
