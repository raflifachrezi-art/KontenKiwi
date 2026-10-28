# Copyright (c) 2026 Konten.com
# Integration for Monday.com Issue Tracker

import json
import logging
import requests
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from tcms.core.contrib.linkreference.models import LinkReference
from tcms.issuetracker.base import IssueTrackerType

logger = logging.getLogger(__name__)


class Monday(IssueTrackerType):
    """
    Support for Monday.com Issue Tracker via GraphQL API v2.

    Required BugSystem configuration fields:
    :base_url: Monday account URL, e.g. https://konten.monday.com
    :api_url: (Optional) Monday API endpoint. Defaults to https://api.monday.com/v2
    :api_username: Monday Board ID (e.g. 1234567890)
    :api_password: Monday Personal API Token
    :description: (Optional) JSON string with custom column mappings or group ID
    """

    @property
    def api_endpoint(self):
        return self.bug_system.api_url or getattr(
            settings, "MONDAY_API_URL", "https://api.monday.com/v2"
        )

    @property
    def api_token(self):
        _, api_password = self.rpc_credentials
        return api_password or getattr(settings, "MONDAY_API_TOKEN", "")

    @property
    def board_id(self):
        api_username, _ = self.rpc_credentials
        return api_username or getattr(settings, "MONDAY_BOARD_ID", "")

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
        return not bool(self.api_token and self.board_id)

    @classmethod
    def bug_id_from_url(cls, url):
        """
        Extract item ID from Monday item URL:
        e.g. https://company.monday.com/boards/12345/pulses/67890
        or https://company.monday.com/boards/12345/items/67890
        """
        clean = url.strip().rstrip("/")
        if "/pulses/" in clean:
            return clean.split("/pulses/")[-1].split("?")[0]
        if "/items/" in clean:
            return clean.split("/items/")[-1].split("?")[0]
        return clean.split("/")[-1].split("?")[0]

    def _execute_graphql(self, query, variables=None):
        session = self.rpc
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
        status_text = "Open"
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

    def _report_issue(self, execution, user):
        """
        Create a new Item in Monday.com Board and post an update with failure details.
        """
        summary = f"[{execution.case.summary[:80]}] Failed Test: TR-{execution.run.pk}"
        board_id = self.board_id

        # 1. Create Item
        create_query = """
        mutation ($boardId: ID!, $itemName: String!) {
            create_item (board_id: $boardId, item_name: $itemName) {
                id
            }
        }
        """
        data = self._execute_graphql(
            create_query, {"boardId": str(board_id), "itemName": summary}
        )

        if not data or not data.get("create_item"):
            raise RuntimeError("Failed to create item on Monday.com board.")

        item_id = data["create_item"]["id"]

        # 2. Add Update / Comment with reproduction details
        comment_body = self._report_comment(execution, user)
        update_query = """
        mutation ($itemId: ID!, $body: String!) {
            create_update (item_id: $itemId, body: $body) {
                id
            }
        }
        """
        self._execute_graphql(
            update_query, {"itemId": str(item_id), "body": comment_body}
        )

        base_url = (self.bug_system.base_url or "https://monday.com").rstrip("/")
        item_url = f"{base_url}/boards/{board_id}/pulses/{item_id}"

        # 3. Create LinkReference in Kiwi TCMS
        LinkReference.objects.get_or_create(
            execution=execution,
            url=item_url,
            is_defect=True,
        )

        # 4. Also create or link an internal Bug entry if bugs app is active
        try:
            from tcms.bugs.models import Bug, BugStatus
            from tcms.bugs.views import New

            bug_data = {
                "reporter": user,
                "summary": f"[Monday #{item_id}] {summary}",
                "product": execution.build.version.product,
                "version": execution.build.version,
                "build": execution.build,
                "text": f"Linked to Monday.com: {item_url}\n\n{comment_body}",
                "_execution": execution,
            }
            bug = New.create_bug(bug_data)
            bug.status_code = BugStatus.OPEN
            bug.save()
            bug.executions.add(execution)
        except Exception as exc:
            logger.warning("Could not auto-create internal Bug for Monday item: %s", exc)

        return ({"id": item_id, "url": item_url}, item_url)

    def post_comment(self, execution, bug_id):
        """
        Post confirmation comment to Monday.com item.
        """
        body = self.text(execution)
        query = """
        mutation ($itemId: ID!, $body: String!) {
            create_update (item_id: $itemId, body: $body) {
                id
            }
        }
        """
        self._execute_graphql(query, {"itemId": str(bug_id), "body": body})
