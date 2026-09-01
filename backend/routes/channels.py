from __future__ import annotations

import hmac

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response

from services.telephony_service import (
    absolute_channel_url,
    answer_phone_turn,
    build_voice_prompt,
    signed_request_url,
    to_spoken_text,
    verify_twilio_signature,
)
from services.whatsapp_service import (
    extract_whatsapp_messages,
    process_whatsapp_message,
    verify_meta_signature,
)
from settings import get_settings


router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("/whatsapp/webhook")
async def verify_whatsapp_webhook(
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
) -> Response:
    configured_token = get_settings().whatsapp_verify_token
    if (
        not configured_token
        or mode != "subscribe"
        or not hmac.compare_digest(token, configured_token)
    ):
        raise HTTPException(status_code=403, detail="Webhook verification failed.")
    return Response(content=challenge, media_type="text/plain")


@router.post("/whatsapp/webhook", status_code=200)
async def receive_whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, int | str]:
    settings = get_settings()
    if not settings.whatsapp_app_secret:
        raise HTTPException(status_code=503, detail="WhatsApp channel is not configured.")

    body = await request.body()
    if not verify_meta_signature(
        body,
        request.headers.get("x-hub-signature-256"),
        settings.whatsapp_app_secret,
    ):
        raise HTTPException(status_code=403, detail="Invalid webhook signature.")

    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc

    messages = extract_whatsapp_messages(payload)
    for message in messages:
        background_tasks.add_task(
            process_whatsapp_message,
            message,
            settings.channel_default_locale,
        )

    return {"status": "accepted", "messages": len(messages)}


async def _verified_twilio_form(request: Request) -> dict[str, str]:
    settings = get_settings()
    if not settings.twilio_auth_token:
        raise HTTPException(status_code=503, detail="Voice channel is not configured.")

    form_data = await request.form()
    form = {key: str(value) for key, value in form_data.items()}
    public_url = signed_request_url(settings.channel_public_base_url, str(request.url))
    if not verify_twilio_signature(
        public_url,
        form,
        request.headers.get("x-twilio-signature"),
        settings.twilio_auth_token,
    ):
        raise HTTPException(status_code=403, detail="Invalid webhook signature.")
    return form


@router.post("/voice/incoming")
async def receive_phone_call(request: Request) -> Response:
    await _verified_twilio_form(request)
    settings = get_settings()
    action_url = absolute_channel_url(
        settings.channel_public_base_url,
        str(request.url),
        "/channels/voice/turn",
    )
    greeting = (
        "Hola, soy Django, asistente profesional de Jeyker. ¿En qué puedo ayudarte?"
        if settings.channel_default_locale == "es"
        else "Hi, I'm Django, Jeyker's professional assistant. How can I help?"
    )
    return Response(
        build_voice_prompt(action_url, locale=settings.channel_default_locale, message=greeting),
        media_type="application/xml",
    )


@router.post("/voice/turn")
async def receive_phone_turn(request: Request) -> Response:
    form = await _verified_twilio_form(request)
    settings = get_settings()
    call_sid = form.get("CallSid", "").strip()
    speech = form.get("SpeechResult", "").strip()
    if not call_sid:
        raise HTTPException(status_code=400, detail="CallSid is required.")

    if speech:
        reply = to_spoken_text(
            await answer_phone_turn(call_sid, speech, settings.channel_default_locale)
        )
    else:
        reply = (
            "No he podido oírte. Inténtalo de nuevo."
            if settings.channel_default_locale == "es"
            else "I couldn't hear you. Please try again."
        )

    action_url = absolute_channel_url(
        settings.channel_public_base_url,
        str(request.url),
        "/channels/voice/turn",
    )
    return Response(
        build_voice_prompt(action_url, locale=settings.channel_default_locale, message=reply),
        media_type="application/xml",
    )
