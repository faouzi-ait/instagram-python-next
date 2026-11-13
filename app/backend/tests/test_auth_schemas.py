from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from schemas.auth import LoginRequest, RegisterRequest
from schemas.user import UserResponse

def registration_data(**changes):
    return {
        "email": "Alex@example.com",
        "username": " Alex ",
        "password": "A sufficiently long password!",
        **changes,
    }

def test_registration_normalizes_email_and_username():
    request = RegisterRequest(**registration_data())

    assert request.email == "alex@example.com"
    assert request.username == "alex"
    assert request.display_name is None
    assert request.password == "A sufficiently long password!"

@pytest.mark.parametrize(
    "changes",
    [
        {"email": "invalid-email"},
        {"username": "ab"},
        {"username": "invalid username"},
        {"password": "short"},
        {"password": "a" * 73},
        {"password": "é" * 37},
        {"is_email_verified": True},
    ],
)
def test_registration_rejects_invalid_input(changes):
    with pytest.raises(ValidationError):
        RegisterRequest(**registration_data(**changes))

def test_login_preserves_password_and_normalizes_email():
    request = LoginRequest(
        email="Alex@example.com",
        password=" Keep My Spaces ",
    )

    assert request.email == "alex@example.com"
    assert request.password == " Keep My Spaces "

def test_login_rejects_missing_password():
    with pytest.raises(ValidationError):
        LoginRequest(email="alex@example.com")

def test_user_response_reads_attributes_and_excludes_password_hash():
    now = datetime.now(timezone.utc)

    user = SimpleNamespace(
        id=1,
        email="alex@example.com",
        username="alex",
        password_hash="example-hash",
        display_name="Alex",
        bio=None,
        avatar_url=None,
        website_url=None,
        is_private=False,
        is_email_verified=False,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    response = UserResponse.model_validate(user)
    data = response.model_dump(mode="json")

    assert data["id"] == 1
    assert data["username"] == "alex"
    assert data["is_active"] is True
    assert "password_hash" not in data
    assert isinstance(data["created_at"], str)
    assert isinstance(data["updated_at"], str)