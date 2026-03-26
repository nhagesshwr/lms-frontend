from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Message, Employee
from app.schemas import MessageCreate, MessageResponse
from app.dependencies import require_employee
from datetime import datetime
from sqlalchemy import or_

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.post("/", response_model=MessageResponse)
def send_message(
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
    ).order_by(Message.sent_at.desc()).all()

    # We format them to match the frontend mock's expected format basically
    result = []
    for m in messages:
        if m.sender_id == current.id:
            # I sent this
            other_user = m.receiver
        else:
            other_user = m.sender

        result.append({
            "id": m.id,
            "sender_id": m.sender_id,
            "receiver_id": m.receiver_id,
            "from_name": m.sender.name if m.sender else "Unknown",
            "to_name": m.receiver.name if m.receiver else "Unknown",
            "role": str(m.sender.role.value) if m.sender else "system",
            "avatar": "".join([c[0] for c in str(m.sender.name or "??").split()][:2]).upper() if m.sender else "XX",  # type: ignore
            "message": m.content,
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
