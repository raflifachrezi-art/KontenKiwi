#!/usr/bin/env python3
"""
Create sample Test Runs, Test Executions, and link example Bugs in Kiwi TCMS.
"""

from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.sites.models import Site
from django_comments.models import Comment

# Dummy email backend to avoid connection refused logs
settings.EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'

from tcms.management.models import Product, Version, Build
from tcms.testcases.models import TestCase, BugSystem
from tcms.testplans.models import TestPlan
from tcms.testruns.models import TestRun, TestExecution, TestExecutionStatus
from tcms.bugs.models import Bug, Severity
from tcms.core.contrib.linkreference.models import LinkReference
from django.contrib.auth import get_user_model

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
current_site = Site.objects.get_current()

# 1. Pastikan BugSystem terdaftar agar Kiwi TCMS mengenali tracker URL
BugSystem.objects.get_or_create(
    name="Kiwi TCMS (8443)",
    defaults={
        "tracker_type": "tcms.issuetracker.kiwitcms.KiwiTCMS",
        "base_url": "https://localhost:8443/bugs/",
    }
)
BugSystem.objects.get_or_create(
    name="Kiwi TCMS",
    defaults={
        "tracker_type": "tcms.issuetracker.kiwitcms.KiwiTCMS",
        "base_url": "https://localhost/bugs/",
    }
)

# 2. Pastikan Severity tersedia
sev_critical, _ = Severity.objects.get_or_create(name="Critical", defaults={"weight": 10, "icon": "fa-exclamation-circle", "color": "#cc0000"})
sev_major, _ = Severity.objects.get_or_create(name="Major", defaults={"weight": 20, "icon": "fa-bug", "color": "#ec7a08"})
sev_medium, _ = Severity.objects.get_or_create(name="Medium", defaults={"weight": 30, "icon": "fa-warning", "color": "#f0ab00"})
sev_minor, _ = Severity.objects.get_or_create(name="Minor", defaults={"weight": 40, "icon": "fa-info-circle", "color": "#39a5dc"})

# Statuses
status_passed = TestExecutionStatus.objects.get(name="PASSED")
status_failed = TestExecutionStatus.objects.get(name="FAILED")
status_blocked = TestExecutionStatus.objects.get(name="BLOCKED")
status_running = TestExecutionStatus.objects.get(name="RUNNING")
status_idle = TestExecutionStatus.objects.get(name="IDLE")

# Product, Version, Build
product = Product.objects.get(name="Playwright Base")
version = Version.objects.get(product=product, value="1.0.0")
build = Build.objects.get(version=version, name="1.0.0")

# Ambil Plans
e2e_plan = TestPlan.objects.get(name="Playwright Base - E2E UI Suite")
api_plan = TestPlan.objects.get(name="Playwright Base - API Integration Suite")

now = timezone.now()

# -------------------------------------------------------------------
# Test Run 1: E2E UI Automated Regression Run
# -------------------------------------------------------------------
run_e2e, _ = TestRun.objects.get_or_create(
    plan=e2e_plan,
    summary="Playwright E2E UI - Automated Nightly Regression Run #42",
    defaults={
        "build": build,
        "manager": admin_user,
        "default_tester": admin_user,
        "notes": "Eksekusi otomatis seluruh test case E2E menggunakan Playwright headless Chromium di CI runner GitHub Actions.",
        "start_date": now - timedelta(hours=2),
        "stop_date": now - timedelta(hours=1, minutes=45),
        "planned_start": now - timedelta(hours=2),
        "planned_stop": now - timedelta(hours=1, minutes=30),
    }
)

# -------------------------------------------------------------------
# Test Run 2: API Integration Pipeline Run
# -------------------------------------------------------------------
run_api, _ = TestRun.objects.get_or_create(
    plan=api_plan,
    summary="Playwright API - Continuous Integration Run #108",
    defaults={
        "build": build,
        "manager": admin_user,
        "default_tester": admin_user,
        "notes": "Eksekusi otomatis pengujian integrasi API (Healthcheck, Token Auth, CRUD Lifecycle, Contract Schema, Query Filtering).",
        "start_date": now - timedelta(minutes=45),
        "stop_date": now - timedelta(minutes=10),
        "planned_start": now - timedelta(minutes=45),
        "planned_stop": now - timedelta(minutes=15),
    }
)

# Helper function to add comment to execution
def add_execution_comment(execution, comment_text):
    Comment.objects.create(
        content_object=execution,
        site=current_site,
        user=admin_user,
        user_name=admin_user.username,
        user_email=admin_user.email,
        comment=comment_text,
        submit_date=now - timedelta(minutes=30),
        is_public=True,
    )

def link_bug_reference(execution, bug):
    execution.bugs.add(bug)
    LinkReference.objects.get_or_create(
        execution=execution,
        url=f"https://localhost:8443/bugs/{bug.id}/",
        defaults={
            "name": bug.summary[:64],
            "is_defect": True,
        }
    )

# -------------------------------------------------------------------
# Populate Executions for Run 1 (E2E)
# -------------------------------------------------------------------
print("Creating Executions for Run 1 (E2E UI)...")
e2e_cases = list(e2e_plan.cases.all().order_by("id"))

for i, tc in enumerate(e2e_cases):
    exec_obj = TestExecution.objects.filter(run=run_e2e, case=tc).first()
    if not exec_obj:
        created_res = run_e2e.create_execution(case=tc, assignee=admin_user, build=build, sortkey=i)
        exec_obj = created_res[0] if isinstance(created_res, list) else created_res

    exec_obj.tested_by = admin_user
    exec_obj.start_date = now - timedelta(hours=2, minutes=-i*2)
    exec_obj.stop_date = now - timedelta(hours=2, minutes=-(i*2 + 1))

    if "[E2E-AUTH-05]" in tc.summary:
        exec_obj.status = status_failed
        exec_obj.save()

        # Buat Bug 1
        bug1, _ = Bug.objects.get_or_create(
            summary="[BUG-001] Locked Out User login returns HTTP 500 Internal Server Error instead of friendly UI message",
            defaults={
                "reporter": admin_user,
                "assignee": admin_user,
                "product": product,
                "version": version,
                "build": build,
                "severity": sev_critical,
                "status": True,  # Open
            }
        )
        link_bug_reference(exec_obj, bug1)

        add_execution_comment(exec_obj, """[Playwright Test Runner Failure Log]
Error: expect(received).toContain(expected)

Expected: "Epic sadface: Sorry, this user has been locked out."
Received: "500 Internal Server Error - NullPointerException in UserLockoutHandler.java:142"

Call log:
  - locator.waitFor(selector='.error-message-container')
  - locator resolved to <div class="error-message-container">...</div>
  - unexpected crash in backend authentication service

Environment: Staging Server
Browser: Chromium 128.0.6613.18""")

    elif "[E2E-CART-01]" in tc.summary:
        exec_obj.status = status_failed
        exec_obj.save()

        # Buat Bug 2
        bug2, _ = Bug.objects.get_or_create(
            summary="[BUG-002] Product catalogue sorting 'Price (high to low)' fails on decimal price comparisons",
            defaults={
                "reporter": admin_user,
                "assignee": admin_user,
                "product": product,
                "version": version,
                "build": build,
                "severity": sev_medium,
                "status": True,  # Open
            }
        )
        link_bug_reference(exec_obj, bug2)

        add_execution_comment(exec_obj, """[Playwright Test Runner Failure Log]
AssertionError: expect(pricesDesc[i]).toBeGreaterThanOrEqual(pricesDesc[i + 1])

Index: 2
Price at index 2: $15.99 ("Sauce Labs Bolt T-Shirt")
Price at index 3: $49.99 ("Sauce Labs Fleece Jacket")
Condition evaluated: 15.99 >= 49.99 -> false

Root Cause Analysis:
JavaScript array sort comparator is evaluating price strings alphabetically rather than parsing numeric floating-point values.""")

    else:
        exec_obj.status = status_passed
        exec_obj.save()

print(f"Executions for E2E Run: {run_e2e.executions.count()}")

# -------------------------------------------------------------------
# Populate Executions for Run 2 (API)
# -------------------------------------------------------------------
print("Creating Executions for Run 2 (API Integration)...")
api_cases = list(api_plan.cases.all().order_by("id"))

for i, tc in enumerate(api_cases):
    exec_obj = TestExecution.objects.filter(run=run_api, case=tc).first()
    if not exec_obj:
        created_res = run_api.create_execution(case=tc, assignee=admin_user, build=build, sortkey=i)
        exec_obj = created_res[0] if isinstance(created_res, list) else created_res

    exec_obj.tested_by = admin_user
    exec_obj.start_date = now - timedelta(minutes=45, seconds=-i*60)
    exec_obj.stop_date = now - timedelta(minutes=45, seconds=-(i*60 + 40))

    if "[API-SCHEMA-04]" in tc.summary:
        exec_obj.status = status_failed
        exec_obj.save()

        # Buat Bug 3
        bug3, _ = Bug.objects.get_or_create(
            summary="[BUG-003] POST /booking accepts malformed payload and creates corrupted booking with null dates",
            defaults={
                "reporter": admin_user,
                "assignee": admin_user,
                "product": product,
                "version": version,
                "build": build,
                "severity": sev_major,
                "status": True,  # Open
            }
        )
        link_bug_reference(exec_obj, bug3)

        add_execution_comment(exec_obj, """[API Contract Test Failure Log]
Error: expect([400, 500]).toContain(response.status())

Expected: 400 Bad Request or 500 Server Error
Received: 200 OK

Request Payload:
{
  "firstname": "John",
  "lastname": "Doe",
  "totalprice": 100,
  "depositpaid": true
}

Response Body:
{
  "bookingid": 9182,
  "booking": {
    "firstname": "John",
    "lastname": "Doe",
    "totalprice": 100,
    "depositpaid": true,
    "bookingdates": null
  }
}

Security & Integrity Risk: Null date bookings cause calendar collision in room scheduling engine.""")

    elif "[API-SCHEMA-05]" in tc.summary:
        exec_obj.status = status_blocked
        exec_obj.save()

        # Buat Bug 4
        bug4, _ = Bug.objects.get_or_create(
            summary="[BUG-004] PUT /booking/:id endpoint allows unauthenticated modifications without auth token cookie",
            defaults={
                "reporter": admin_user,
                "assignee": admin_user,
                "product": product,
                "version": version,
                "build": build,
                "severity": sev_critical,
                "status": True,  # Open
            }
        )
        link_bug_reference(exec_obj, bug4)

        add_execution_comment(exec_obj, """[Security Contract Test Failure Log]
Error: expect(updateRes.status()).toBe(403)

Expected: 403 Forbidden
Received: 200 OK

Vulnerability Description:
Endpoint PUT /booking/1 did not require valid auth cookie 'token=...'. The update request was processed successfully and modified booking records without administrative credentials.""")

    elif "[API-QUERY-03]" in tc.summary:
        exec_obj.status = status_running
        exec_obj.stop_date = None
        exec_obj.save()
    else:
        exec_obj.status = status_passed
        exec_obj.save()

print(f"Executions for API Run: {run_api.executions.count()}")

print("-------------------------------------------------------------------")
print("🎉 Test Runs, Executions, and Example Bugs created successfully!")
print(f"Total Test Runs: {TestRun.objects.count()}")
print(f"Total Test Executions: {TestExecution.objects.count()}")
print(f"Total Bugs Created: {Bug.objects.count()}")
print(f"Total LinkReferences: {LinkReference.objects.count()}")
print("-------------------------------------------------------------------")
