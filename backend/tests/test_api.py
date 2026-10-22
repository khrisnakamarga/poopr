import base64
import json
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import email_from_easy_auth
from app.main import app


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def headers(email: str) -> dict[str, str]:
    return {"X-User-Email": email}


def test_log_and_report(client: TestClient) -> None:
    occurred_at = datetime.now(UTC).isoformat()
    response = client.post(
        "/api/v1/poop-logs",
        json={"occurred_at": occurred_at, "stool_type": 4, "urgency": 2},
        headers=headers("sam@example.com"),
    )
    assert response.status_code == 201

    report = client.get("/api/v1/reports/me", headers=headers("sam@example.com")).json()
    assert report["total_count"] == 1
    assert report["current_streak_days"] == 1
    assert report["average_per_week"] == 7.0


def test_logs_are_user_scoped(client: TestClient) -> None:
    response = client.post(
        "/api/v1/poop-logs",
        json={"occurred_at": datetime.now(UTC).isoformat()},
        headers=headers("owner@example.com"),
    )
    log_id = response.json()["id"]

    forbidden = client.patch(
        f"/api/v1/poop-logs/{log_id}",
        json={"occurred_at": datetime.now(UTC).isoformat()},
        headers=headers("other@example.com"),
    )
    assert forbidden.status_code == 404


def test_profile_autoprovision_is_idempotent(client: TestClient) -> None:
    first = client.get("/api/v1/profile/me", headers=headers("demo@example.com"))
    second = client.get("/api/v1/profile/me", headers=headers("demo@example.com"))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_easy_auth_google_email_claim_is_supported() -> None:
    principal = base64.b64encode(
        json.dumps(
            {
                "claims": [
                    {"typ": "name", "val": "Test User"},
                    {"typ": "email", "val": "Test.User@gmail.com"},
                ]
            }
        ).encode()
    ).decode()

    assert email_from_easy_auth(None, None, principal) == "test.user@gmail.com"


def test_group_invites_dashboard_and_activity(client: TestClient) -> None:
    created_group = client.post(
        "/api/v1/groups",
        json={"name": "Morning Crew"},
        headers=headers("owner@example.com"),
    ).json()

    invite = client.post(
        f"/api/v1/groups/{created_group['id']}/invite-codes",
        headers=headers("owner@example.com"),
    ).json()

    joined = client.post(
        "/api/v1/groups/join",
        json={"code": invite["code"]},
        headers=headers("friend@example.com"),
    )
    assert joined.status_code == 200

    client.post(
        "/api/v1/poop-logs",
        json={"occurred_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat()},
        headers=headers("friend@example.com"),
    )

    dashboard = client.get(
        f"/api/v1/groups/{created_group['id']}/dashboard",
        headers=headers("owner@example.com"),
    ).json()
    assert dashboard["member_count"] == 2
    assert dashboard["total_count"] == 1
    assert dashboard["leaderboards"]["most_logs"][0]["display_name"] == "Friend"
    assert dashboard["recent_activity"][0]["display_name"] == "Friend"

