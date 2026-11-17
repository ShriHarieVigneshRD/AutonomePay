"""N6: server-side conversations. Clients send only the new customer message; the server keeps
the history, so earlier turns can't be forged and the token budget belongs to the conversation."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.chat import load_case, run_turn
from app.api.deps import chat_rate_limit
from app.api.scenarios import get_all_50_formatted_scenarios
from app.core.database import Conversation, ConversationMessage, get_db

router = APIRouter()
MAX_MESSAGES = 40


class NewConversation(BaseModel):
    scenario_id: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,64}$")


class NewMessage(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


def _view(conversation: Conversation) -> dict:
    return {
        "conversation_id": conversation.conversation_id,
        "scenario_id": conversation.scenario_id,
        "messages": [{"role": m.role, "content": m.content, "meta": m.meta} for m in conversation.messages],
    }


def _get(db: Session, conversation_id: str) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


@router.post("/conversations", status_code=201, dependencies=[Depends(chat_rate_limit)])
def start_conversation(payload: NewConversation, db: Session = Depends(get_db)):
    scenario = next((s for s in get_all_50_formatted_scenarios(db) if s["id"] == payload.scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail="Unknown scenario.")
    conversation = Conversation(
        conversation_id=f"conv_{uuid.uuid4().hex}",
        scenario_id=scenario["id"],
        merchant_id=scenario["merchant_id"],
        customer_id=scenario["customer_id"],
        invoice_id=scenario["invoice_id"],
        messages=[ConversationMessage(role="assistant", content=scenario["initial_message"])],
    )
    db.add(conversation)
    db.commit()
    return _view(conversation)


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    return _view(_get(db, conversation_id))


@router.post("/conversations/{conversation_id}/messages", dependencies=[Depends(chat_rate_limit)])
def send_message(conversation_id: str, payload: NewMessage, db: Session = Depends(get_db)):
    conversation = _get(db, conversation_id)
    if len(conversation.messages) + 2 > MAX_MESSAGES:
        raise HTTPException(status_code=409, detail="This conversation is full. Please start a new one.")
    merchant, customer, invoice = load_case(
        db, conversation.merchant_id, conversation.customer_id, conversation.invoice_id
    )
    history = [{"role": m.role, "content": m.content} for m in conversation.messages]
    history.append({"role": "user", "content": payload.content})

    turn = run_turn(merchant, customer, invoice, history, session_id=conversation.conversation_id)

    # Stored only after a successful turn, so a failed request leaves the history unchanged.
    conversation.messages.append(ConversationMessage(role="user", content=payload.content))
    conversation.messages.append(
        ConversationMessage(role="assistant", content=turn.final_response, meta=turn.model_dump(mode="json"))
    )
    db.commit()
    return {**turn.model_dump(mode="json"), "conversation_id": conversation.conversation_id}
