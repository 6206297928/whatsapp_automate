
import os
import httpx
import base64
from typing import Any, Dict
from google.adk.tools.tool_context import ToolContext
from google import genai
from .database import get_db_session, Person, Ticket, TicketVendor, generate_ticket_number
from .prompts import IMAGE_EXTRACTOR_INSTRUCTION, CUSTOMER_CLASSIFIER_INSTRUCTION, VENDOR_VALIDATOR_INSTRUCTION

async def _llm_tool_call(contents, system_instruction):
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    response = await client.aio.models.generate_content(
        model=os.environ.get("ADK_MODEL", "gemini-2.5-flash-lite"),
        contents=contents,
        config=genai.types.GenerateContentConfig(system_instruction=system_instruction)
    )
    return response.text or ""

async def fetch_user(tool_context: ToolContext, phone: str) -> Dict[str, Any]:
    session = get_db_session()
    user = session.query(Person).filter(Person.phone == phone).first()
    session.close()
    if user:
        return {"linked": True, "linked_to": user.linked_to, "entity_id": user.entity_id, "user_id": user.user_id, "name": user.name}
    return {"linked": False, "linked_to": "unknown"}

async def register_user(tool_context: ToolContext, phone: str, name: str = "WhatsApp Customer") -> Dict[str, Any]:
    """Save a new sender as a customer so they are recognized on future messages.

    Idempotent: if the phone already exists, returns the existing record instead of
    creating a duplicate. Returns the entity_id/user_id needed to create a ticket.
    """
    session = get_db_session()
    try:
        existing = session.query(Person).filter(Person.phone == phone).first()
        if existing:
            return {"status": "already_registered", "linked_to": existing.linked_to,
                    "entity_id": existing.entity_id, "user_id": existing.user_id, "name": existing.name}
        person = Person(phone=phone, name=name, linked=True, linked_to="customer")
        session.add(person)
        session.commit()
        return {"status": "registered", "linked_to": "customer",
                "entity_id": person.entity_id, "user_id": person.user_id, "name": person.name}
    finally:
        session.close()

async def extract_text_from_image(tool_context: ToolContext) -> str:
    image_b64 = tool_context.state.get("media:image_base64")
    if not image_b64: return "No image found."
    raw_bytes = base64.decodebytes(image_b64.encode())
    return await _llm_tool_call([genai.types.Part.from_bytes(data=raw_bytes, mime_type="image/jpeg")], IMAGE_EXTRACTOR_INSTRUCTION)

async def classify_customer_message(tool_context: ToolContext, message_text: str) -> str:
    return await _llm_tool_call(message_text, CUSTOMER_CLASSIFIER_INSTRUCTION)

async def validate_vendor_reply(tool_context: ToolContext, vendor_reply: str, quoted_message: str) -> str:
    return await _llm_tool_call(f"Vendor: {vendor_reply}\nQuoted: {quoted_message}", VENDOR_VALIDATOR_INSTRUCTION)

async def create_ticket(tool_context: ToolContext, customer_id: str, linked_user_id: str, customer_message: str, ticket_type: str = "rfq", query_type: str = "normal") -> Dict[str, Any]:
    session = get_db_session()
    try:
        t_num = generate_ticket_number(session)
        ticket = Ticket(ticket_number=t_num, customer_id=customer_id, linked_user_id=linked_user_id, customer_message=customer_message, type=ticket_type)
        session.add(ticket)
        session.flush()  # assign ticket.id before creating vendor assignments

        # Broadcast: assign this ticket to EVERY vendor (status = Pending)
        vendors = session.query(Person).filter(Person.linked_to == "vendor").all()
        assigned = []
        for v in vendors:
            session.add(TicketVendor(ticket_id=ticket.id, vendor_entity_id=v.entity_id, status="Pending"))
            assigned.append(v.name)
        session.commit()
        return {"ticket_number": t_num, "status": "Created",
                "broadcast_to_vendors": len(assigned), "vendors": assigned}
    finally: session.close()

async def fetch_ticket_by_number(tool_context: ToolContext, ticket_number: str) -> Dict[str, Any]:
    session = get_db_session()
    ticket = session.query(Ticket).filter(Ticket.ticket_number == ticket_number).first()
    if not ticket:
        session.close()
        return {"error": "Not found"}
    res = {"ticket_number": ticket.ticket_number, "vendors": [{"id": v.id, "vendor_entity_id": v.vendor_entity_id} for v in ticket.vendors]}
    session.close()
    return res

async def update_ticket_vendor(tool_context: ToolContext, ticket_vendor_id: str, vendor_response: str, delivery_info: str) -> Dict[str, Any]:
    session = get_db_session()
    tv = session.query(TicketVendor).filter(TicketVendor.id == ticket_vendor_id).first()
    if not tv:
        session.close()
        return {"error": "Assignment not found"}
    tv.vendor_response = vendor_response
    tv.delivery_info = delivery_info
    tv.status = "Responded"
    session.commit()
    session.close()
    return {"status": "Success"}

async def send_whatsapp_message(tool_context: ToolContext, phone_or_group_id: str, message: str) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post("http://host.docker.internal:3002/api/send", json={"to": phone_or_group_id, "message": message})
            return resp.json()
        except: return {"error": "API Unreachable"}
