# Copyright (c) 2026 Konten.com
# Webhook handler for Monday.com two-way status synchronization

import json
import logging
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext_lazy as _

from tcms.bugs.models import Bug, BugStatus
from tcms.core.contrib.linkreference.models import LinkReference
from tcms.core.helpers.comments import add_comment

logger = logging.getLogger(__name__)


def map_monday_status_to_kiwi(label_text):
    """
    Map Monday.com status text to Kiwi TCMS BugStatus.
    """
    if not label_text:
        return None

    clean = str(label_text).strip().lower()
    if any(k in clean for k in ["stuck", "blocked", "macet", "kendala", "hold"]):
        return BugStatus.STUCK
    if any(k in clean for k in ["working", "in progress", "progres", "ongoing", "dev"]):
        return BugStatus.IN_PROGRESS
    if any(k in clean for k in ["done", "resolved", "selesai", "fixed", "ready for test"]):
        return BugStatus.RESOLVED
    if any(k in clean for k in ["closed", "tutup"]):
        return BugStatus.CLOSED
    if any(k in clean for k in ["won't fix", "wont fix", "invalid", "batal", "reject"]):
        return BugStatus.WONT_FIX
    if any(k in clean for k in ["to do", "open", "new", "baru", "backlog"]):
        return BugStatus.OPEN

    return None


@csrf_exempt
def monday_webhook_view(request):
    """
    Monday.com Webhook endpoint.
    Handles:
    1. Monday Challenge Handshake: {"challenge": "string"}
    2. Column / Status Change Events: updates Kiwi TCMS Bug.status_code
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception as exc:
        logger.warning("Invalid JSON received from Monday webhook: %s", exc)
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # 1. Monday Challenge Handshake
    if "challenge" in body:
        return JsonResponse({"challenge": body["challenge"]})

    # 2. Process Event
    event = body.get("event")
    if not event:
        return JsonResponse({"status": "no event"})

    pulse_id = str(event.get("pulseId", ""))
    if not pulse_id:
        return JsonResponse({"status": "missing pulseId"})

    # Extract status label text
    val = event.get("value", {})
    label_text = None
    if isinstance(val, dict):
        label_text = val.get("label", {}).get("text") or val.get("text")
    elif isinstance(val, str):
        label_text = val

    if not label_text:
        return JsonResponse({"status": "no label change"})

    kiwi_status = map_monday_status_to_kiwi(label_text)
    if not kiwi_status:
        return JsonResponse({"status": "unmapped status", "label": label_text})

    # Find matching bugs via LinkReference URL or Bug summary/text
    matched_bugs = set()

    # Search via LinkReference URLs containing the pulseId
    matching_links = LinkReference.objects.filter(url__icontains=pulse_id)
    for link in matching_links:
        if hasattr(link, "execution") and link.execution:
            for bug in link.execution.bugs.all():
                matched_bugs.add(bug)

    # Also search directly in Bug summary or text
    direct_bugs = Bug.objects.filter(summary__icontains=f"#{pulse_id}")
    for bug in direct_bugs:
        matched_bugs.add(bug)

    user = get_user_model().objects.filter(is_superuser=True).first()

    updated_count = 0
    for bug in matched_bugs:
        old_status = bug.status_code
        if old_status != kiwi_status:
            bug.status_code = kiwi_status
            if kiwi_status in [BugStatus.CLOSED, BugStatus.RESOLVED, BugStatus.WONT_FIX]:
                bug.status = False
            else:
                bug.status = True
            bug.save()

            log_msg = f"*Sync dari Monday.com (Item #{pulse_id}): Status diubah '{label_text}' ➔ {kiwi_status}*"
            add_comment([bug], log_msg, user or bug.reporter)
            updated_count += 1

    return JsonResponse({
        "status": "success",
        "pulse_id": pulse_id,
        "monday_label": label_text,
        "kiwi_status": kiwi_status,
        "updated_bugs": updated_count,
    })
