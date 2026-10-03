import asyncio
import json
from datetime import datetime

import redis.asyncio as async_redis
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, get_db
from app.models.notification import Notification
from app.models.user import User
from app.utils.auth import authenticate_token, get_current_user


router = APIRouter(tags=["Notifications"])


def serialize_notification(item: Notification) -> dict:
    return {
        "id": item.id,
        "type": item.notification_type,
        "title": item.title,
        "message": item.message,
        "metadata": item.metadata_json,
        "is_read": item.is_read,
        "created_at": item.created_at.isoformat(),
    }


@router.get("/notifications")
def list_notifications(
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return [serialize_notification(item) for item in query.order_by(desc(Notification.created_at)).limit(100).all()]


@router.patch("/notifications/{notification_id}/read")
def mark_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Notification not found")
    item.is_read = True
    item.read_at = datetime.utcnow()
    db.commit()
    return serialize_notification(item)


@router.post("/notifications/read-all")
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read.is_(False)).update(
        {Notification.is_read: True, Notification.read_at: datetime.utcnow()}, synchronize_session=False
    )
    db.commit()
    return {"updated": True}


@router.websocket("/ws/notifications")
async def notification_socket(websocket: WebSocket, token: str = Query(...)):
    db = SessionLocal()
    try:
        user = authenticate_token(token, db)
        user_id = user.id
    except HTTPException:
        await websocket.close(code=4401)
        return
    finally:
        db.close()

    await websocket.accept()
    client = async_redis.from_url(get_settings().redis_url)
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(f"notifications:{user_id}")
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=20)
            if message:
                data = message["data"]
                await websocket.send_json(json.loads(data.decode() if isinstance(data, bytes) else data))
            else:
                await websocket.send_json({"type": "heartbeat"})
            await asyncio.sleep(0.1)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        await pubsub.unsubscribe(f"notifications:{user_id}")
        await pubsub.close()
        await client.close()
