# Copyright (c) 2026 Konten.com
# Implementation of Monday.com Issue Tracker for Konten.com QA Workflow
# Follows rules defined in docs/mondaycom/playbookmonday.md

import json
import logging
import requests
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from tcms.core.contrib.linkreference.models import LinkReference
from tcms.issuetracker.base import IssueTrackerType

logger = logging.getLogger(__name__)

# Constants from playbookmonday.md
MONDAY_WORKSPACE_ID = "3259533"  # Konten.com: Development
MONDAY_BOARD_ID = "5030095856"  # Development Timeline
MONDAY_SUBITEM_BOARD_ID = "5030095857"
MONDAY_GROUP_ID = "group_mm82vcnt"  # QA Issues

# Parent Item IDs
MONDAY_ITEM_MOBILE_ISSUES = "2878748533"  # Konten.com Mobile App Issues
MONDAY_ITEM_WEB_ISSUES = "2878755544"  # Konten.com Web App Issues

# Owner IDs
MONDAY_OWNER_MOBILE_ID = 115783524  # Ridwan Febnur Asri Redinda
MONDAY_OWNER_MOBILE_NAME = "Ridwan Febnur Asri Redinda"


def resolve_monday_parent_and_owner(product_name):
    """
    Determine parent item ID and owner based on Product name:
    - Mobile (Android / iOS): Parent 2878748533, Owner Ridwan Febnur Asri Redinda
    - Web: Parent 2878755544, Owner None
    """
    p_lower = (product_name or "").lower()
    if "mobile" in p_lower or "android" in p_lower or "ios" in p_lower:
        return (
            MONDAY_ITEM_MOBILE_ISSUES,
            MONDAY_OWNER_MOBILE_ID,
            MONDAY_OWNER_MOBILE_NAME,
            "Mobile",
        )
    return (
        MONDAY_ITEM_WEB_ISSUES,
        None,
        "",
        "Web",
    )


def resolve_monday_phase(build_name, env_name=""):
    """
    Determine Phase following playbookmonday.md:
    - Mobile 1.x.x or Web prod -> Deployment
    - staging -> Testing 2 (Staging)
    - dev (0.2.0, 0.1.0-dev, v1.0-exploratory) -> Testing 1 (Dev)
    """
    b_lower = (build_name or "").lower()
    e_lower = (env_name or "").lower()

    if "staging" in b_lower or "staging" in e_lower:
        return "Testing 2 (Staging)"
    if "prod" in b_lower or "prod" in e_lower or (b_lower.startswith("1.") and "staging" not in b_lower and "dev" not in b_lower):
        return "Deployment"
    return "Testing 1 (Dev)"


def format_monday_html_detail(bug):
    """
    Format bug detail as HTML for Monday comment according to playbook:
    Ruang Lingkup, Lingkungan, Perangkat, Langkah Reproduksi (table), Hasil Aktual, Hasil yang Diharapkan.
    """
    severity_name = bug.severity.name if bug.severity else "Medium"
    platform = "Web" if "web" in bug.product.name.lower() else "Mobile"
    product_name = bug.product.name
    version_val = bug.version.value if bug.version else "1.0.0"
    build_val = bug.build.name if bug.build else "dev"

    # Extract first comment if available for reproduction steps
    first_comment = ""
    try:
        from django_comments.models import Comment

        cm = (
            Comment.objects.filter(object_pk=str(bug.pk))
            .order_by("submit_date")
            .first()
        )
        if cm:
            first_comment = cm.comment
    except Exception:
        pass

    html = f"""
<p><b>Detail Bug Kiwi #{bug.pk}:</b> <a href="https://qa.konten.com/bugs/{bug.pk}/">https://qa.konten.com/bugs/{bug.pk}/</a></p>
<p><b>Ruang Lingkup:</b> {product_name} · {platform} · Severity {severity_name}<br>
<b>Lingkungan:</b> {version_val} · Build {build_val}<br>
<b>Ringkasan:</b> {bug.summary}</p>
"""
    if first_comment:
        import html as pyhtml

        escaped = pyhtml.escape(first_comment).replace("\n", "<br>")
        html += f"""
<p><b>Deskripsi & Langkah Reproduksi:</b></p>
<div style="background: #f7f9fa; padding: 10px; border-left: 3px solid #0073ea; font-family: monospace;">
{escaped}
</div>
"""
    return html


class Monday(IssueTrackerType):
    """
    Support for Monday.com Issue Tracker via GraphQL API v2.
    """

    @property
    def api_endpoint(self):
        return self.bug_system.api_url or getattr(
            settings, "MONDAY_API_URL", "https://api.monday.com/v2"
        )

    @property
    def api_token(self):
        # 1. User profile token (from self.user or self.request.user)
        user = getattr(self, "user", None)
        if not user and self.request and hasattr(self.request, "user") and self.request.user.is_authenticated:
            user = self.request.user

        if user:
            profile = getattr(user, "profile", None)
            if profile and profile.monday_api_token:
                return profile.monday_api_token.strip()

        # 2. BugSystem credentials
        _, api_password = self.rpc_credentials
        if api_password:
            return api_password.strip()

        # 3. Settings / environment variable fallback
        token = getattr(
            settings,
            "MONDAY_API_TOKEN",
            getattr(self.bug_system, "api_password", ""),
        )
        return str(token).strip()

    @property
    def board_id(self):
        api_username, _ = self.rpc_credentials
        return (
            api_username
            or getattr(settings, "MONDAY_BOARD_ID", "")
            or MONDAY_BOARD_ID
        )

    def _rpc_connection(self):
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": self.api_token,
                "Content-Type": "application/json",
                "API-Version": "2024-10",
            }
        )
        return session

    def is_adding_testcase_to_issue_disabled(self):
        return not bool(self.api_token)

    @classmethod
    def bug_id_from_url(cls, url):
        clean = url.strip().rstrip("/")
        if "/pulses/" in clean:
            return clean.split("/pulses/")[-1].split("?")[0]
        if "/items/" in clean:
            return clean.split("/items/")[-1].split("?")[0]
        return clean.split("/")[-1].split("?")[0]

    def _execute_graphql(self, query, variables=None):
        session = self.rpc
        if not session:
            logger.warning("Monday API session unavailable (missing token)")
            return None

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            resp = session.post(self.api_endpoint, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data and data["errors"]:
                logger.error("Monday.com GraphQL errors: %s", data["errors"])
                return None
            return data.get("data")
        except Exception as exc:
            logger.exception("Failed to communicate with Monday.com: %s", exc)
            return None

    def details(self, url):
        item_id = self.bug_id_from_url(url)
        query = """
        query ($ids: [ID!]) {
            items (ids: $ids) {
                id
                name
                state
                board {
                    id
                    name
                }
                column_values {
                    id
                    text
                    type
                }
            }
        }
        """
        data = self._execute_graphql(query, {"ids": [item_id]})
        if not data or not data.get("items"):
            return {
                "id": item_id,
                "title": f"Monday Item #{item_id}",
                "status": "Unknown",
                "url": url,
                "description": "Item details unavailable from Monday.com",
            }

        item = data["items"][0]
        board_name = item.get("board", {}).get("name", "Board")
        status_text = "Belum dimulai"
        for col in item.get("column_values", []):
            if col.get("type") in ["status", "color"] and col.get("text"):
                status_text = col.get("text")
                break

        return {
            "id": item_id,
            "title": item.get("name", f"Monday Item #{item_id}"),
            "status": status_text,
            "url": url,
            "description": f"Monday.com [{board_name}] - Status: {status_text}",
        }

    def push_bug_to_monday(self, bug, user=None):
        """
        Executes full playbookmonday.md flow:
        Creates a subitem under the designated parent item (Mobile Ridwan vs Web),
        sets Phase, writes Comment 1 (Link) & Comment 2 (Detail),
        and updates the Bug model.
        """
        if user:
            self.user = user

        if not self.api_token:
            raise RuntimeError(
                "Token Monday.com belum diatur di profil Anda! Silakan buka menu [My Profile] > tab [Integrasi Monday.com] untuk memasukkan Personal API Token Anda."
            )

        parent_id, owner_id, owner_name, platform = (
            resolve_monday_parent_and_owner(bug.product.name)
        )
        phase = resolve_monday_phase(
            bug.build.name if bug.build else "",
            bug.version.value if bug.version else "",
        )

        column_values = {}
        if owner_id:
            column_values["person"] = {
                "personsAndTeams": [{"id": owner_id, "kind": "person"}]
            }
        if phase:
            column_values["color_mm5fnray"] = {"label": phase}

        # 1. Create Subitem
        create_query = """
        mutation ($parentId: ID!, $itemName: String!, $columnVals: JSON) {
            create_subitem (
                parent_item_id: $parentId,
                item_name: $itemName,
                column_values: $columnVals
            ) {
                id
                board {
                    id
                }
            }
        }
        """
        variables = {
            "parentId": str(parent_id),
            "itemName": bug.summary,
            "columnVals": json.dumps(column_values),
        }
        data = self._execute_graphql(create_query, variables)

        subitem_id = None
        if data and data.get("create_subitem"):
            subitem_id = data["create_subitem"]["id"]
        else:
            # Fallback if create_subitem mutation varies in target workspace
            subitem_id = f"sub_{bug.pk}_{parent_id}"
            logger.warning(
                "Could not create live subitem, using ref: %s", subitem_id
            )

        base_url = (
            self.bug_system.base_url or "https://konten.monday.com"
        ).rstrip("/")
        subitem_url = f"{base_url}/boards/{MONDAY_SUBITEM_BOARD_ID}/pulses/{subitem_id}"

        # 2. Add Comments to Monday subitem
        if not subitem_id.startswith("sub_"):
            # Comment 1: Direct link
            link_comment = f'<p><a href="https://qa.konten.com/bugs/{bug.pk}/">https://qa.konten.com/bugs/{bug.pk}/</a></p>'
            self._post_update(subitem_id, link_comment)

            # Comment 2: Detailed bug specification
            detail_comment = format_monday_html_detail(bug)
            self._post_update(subitem_id, detail_comment)

        # 3. Update Bug model fields
        bug.monday_subitem_id = str(subitem_id)
        bug.monday_parent_id = str(parent_id)
        bug.monday_url = subitem_url
        bug.monday_phase = phase
        bug.monday_status = "Belum dimulai"
        bug.monday_owner = owner_name or ""
        bug.save()

        # 4. Add LinkReference for test executions if linked
        for execution in bug.executions.all():
            LinkReference.objects.get_or_create(
                execution=execution,
                url=subitem_url,
                is_defect=True,
            )

        return {
            "subitem_id": subitem_id,
            "url": subitem_url,
            "phase": phase,
            "owner": owner_name,
            "platform": platform,
        }

    def _post_update(self, item_id, body_html):
        query = """
        mutation ($itemId: ID!, $body: String!) {
            create_update (item_id: $itemId, body: $body) {
                id
            }
        }
        """
        return self._execute_graphql(
            query, {"itemId": str(item_id), "body": body_html}
        )

    def _report_issue(self, execution, user):
        from tcms.bugs.models import Bug, BugStatus
        from tcms.bugs.views import New

        summary = f"[{execution.case.summary[:80]}] Failed Test: TR-{execution.run.pk}"
        bug_data = {
            "reporter": user,
            "summary": summary,
            "product": execution.build.version.product,
            "version": execution.build.version,
            "build": execution.build,
            "text": self._report_comment(execution, user),
            "_execution": execution,
        }
        bug = New.create_bug(bug_data)
        bug.status_code = BugStatus.OPEN
        bug.save()
        bug.executions.add(execution)

        # Push to Monday subitem
        res = self.push_bug_to_monday(bug, user)
        return (res, res["url"])

    def post_comment(self, execution, bug_id):
        body = f"<p><b>Confirmed via test execution:</b> TR-{execution.run.pk}: {execution.run.summary}</p>"
        self._post_update(bug_id, body)
