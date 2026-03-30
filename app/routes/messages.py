from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Message, Employee
from app.schemas import MessageCreate, MessageResponse
from app.dependencies import require_employee
from datetime import datetime
from sqlalchemy import or_
from typing import Dict, List, Optional
import json

from app.auth import decode_token
import os

router = APIRouter(prefix="/messages", tags=["Messages"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active_connections and websocket in self.active_connections[user_id]:
            self.active_connections[user_id].remove(websocket)

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            # Create a localized dictionary
            send_payload = {**message}
            if message["sender_id"] == user_id:
                send_payload["is_mine"] = True
            else:
                send_payload["is_mine"] = False
            
            for connection in self.active_connections[user_id]:
                await connection.send_json(send_payload)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    payload = decode_token(token) if token else None
    if not payload:
        await websocket.close(code=1008)
        return
        
    user_id: int = payload.get("id")
    if user_id is None:
        await websocket.close(code=1008)
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            # We just ping-pong or keep connection alive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)


@router.post("/", response_model=MessageResponse)
async def send_message(
    data: MessageCreate,
    db: Session = Depends(get_db),
    current: Employee = Depends(require_employee)
):
    receiver = db.query(Employee).filter(Employee.id == data.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")

    message = Message(
        sender_id=current.id,
        receiver_id=data.receiver_id,
        content=data.content
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    # Format exactly like GET /messages
    formatted = {
        "id": message.id,
        "sender_id": message.sender_id,
        "receiver_id": message.receiver_id,
        "from_name": current.name,
        "to_name": receiver.name,
        "from_role": str(current.role.value),
        "to_role": str(receiver.role.value),
        "avatar": "".join(w[0] for w in str(current.name or "??").split()[:2]).upper(),
        "to_avatar": "".join(w[0] for w in str(receiver.name or "??").split()[:2]).upper(),
        "content": message.content,
        "time": message.sent_at.isoformat(),
        "unread": True
    }
    
    # Broadcast to receiver (chat sync)
    await manager.send_personal_message(formatted, data.receiver_id)
    # Broadcast to sender (so sender's other tabs sync)
    await manager.send_personal_message(formatted, current.id)

    # Push a real-time notification to the receiver's bell
    from app.routes.notifications import get_notif_manager
    notif_mgr = get_notif_manager()
    await notif_mgr.push(data.receiver_id, {
        "id": f"msg-{message.id}",
        "type": "message",
        "icon": "💬",
        "message": f"New message from {current.name}",
        "time": "Just now",
        "read": False
    })

    return message


@router.get("/", response_model=list[dict])
def get_my_messages(
    db: Session = Depends(get_db),
    current: Employee = Depends(require_employee)
):
    """Get all messages involving current user, formatted nicely."""
    messages = db.query(Message).options(
        joinedload(Message.sender),
        joinedload(Message.receiver)
    ).filter(
        or_(Message.sender_id == current.id, Message.receiver_id == current.id)
    ).order_by(Message.sent_at.asc()).all()

    result = []
    for m in messages:
        is_mine = (m.sender_id == current.id)
        other_user = m.receiver if is_mine else m.sender
        
        if not hasattr(m, "content"):
            continue

        result.append({
            "id": m.id,
            "sender_id": m.sender_id,
            "receiver_id": m.receiver_id,
            "is_mine": is_mine,
            "from_name": m.sender.name if m.sender else "Unknown",
            "to_name": m.receiver.name if m.receiver else "Unknown",
            "from_role": str(m.sender.role.value) if m.sender else "system",
            "to_role": str(m.receiver.role.value) if m.receiver else "system",
            "avatar": "".join(w[0] for w in str(m.sender.name or "??").split()[:2]).upper() if m.sender else "XX",
            "to_avatar": "".join(w[0] for w in str(m.receiver.name or "??").split()[:2]).upper() if m.receiver else "XX",
            "content": m.content,
            "time": m.sent_at.isoformat(),
            "unread": not m.is_read and m.receiver_id == current.id
        })
    return result


@router.put("/{message_id}/read")
def mark_read(
    message_id: int,
    db: Session = Depends(get_db),
    current: Employee = Depends(require_employee)
):
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.receiver_id != current.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    message.is_read = True
    db.commit()
    return {"message": "Message marked as read"}


@router.put("/read-thread/{sender_id}")
async def mark_thread_read(
    sender_id: int,
    db: Session = Depends(get_db),
    current: Employee = Depends(require_employee)
):
    db.query(Message).filter(
        Message.receiver_id == current.id,
        Message.sender_id == sender_id,
        Message.is_read == False
    ).update({"is_read": True})
    db.commit()

    # Tell the notification bell to refresh
    try:
        from app.routes.notifications import get_notif_manager
        notif_mgr = get_notif_manager()
        await notif_mgr.push(current.id, {"type": "refresh_notifications"})
    except Exception:
        pass  # Non-critical — don't fail the request if push fails

    return {"message": "Thread marked as read"}
