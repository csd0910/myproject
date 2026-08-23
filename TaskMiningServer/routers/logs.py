"""
routers/logs.py - クライアントログ受信用ルーター
===================================================
役割:
  - クライアントソフトからの単一/バルクログ受信
  - DBへの保存 (database.insert_log 経由)
"""

from fastapi import APIRouter, Request
from database import insert_log

router = APIRouter(tags=["Logs"])

@router.post("/api/v1/logs")
async def receive_logs(request: Request):
    """単一ログデータの受信"""
    try:
        data = await request.json()
        user_id = data.get("user_id", "anonymous_user")
        log_type = data.get("type", "unknown")
        insert_log(user_id, log_type, data)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/api/v1/logs/bulk")
async def receive_logs_bulk(request: Request):
    """バルクログデータの受信"""
    try:
        data = await request.json()
        logs = data.get("logs", [])
        success_count = 0
        for log in logs:
            try:
                user_id = log.get("user_id", "anonymous_user")
                log_type = log.get("type", "unknown")
                insert_log(user_id, log_type, log)
                success_count += 1
            except Exception as e:
                print(f"Error inserting log: {e}")
        return {"status": "success", "inserted": success_count}
    except Exception as e:
        return {"status": "error", "message": str(e)}
