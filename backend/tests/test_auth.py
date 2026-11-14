from tests.conftest import (
    PASSWORD,
    auth,
    outbox,
    register,
    register_verified,
    token_from_last_email,
)

API = "/api/v1"


async def test_register_creates_user_and_workshop_and_sends_mail(client):
    body = await register(client)
    assert body["user"]["email"] == "owner@example.com"
    assert body["user"]["email_verified"] is False
    assert body["email_verification_required"] is True
    mail = outbox()[-1]
    assert mail.to == "owner@example.com"
    assert "Підтвердіть" in mail.subject  # Ukrainian template


async def test_register_rejects_duplicate_email_case_insensitive(client):
    await register(client)
    r = await client.post(
        f"{API}/auth/register",
        json={
            "email": "OWNER@example.com",
            "password": PASSWORD,
            "full_name": "X",
            "country_code": "UA",
            "workshop_name": "W",
            "accept_terms": True,
        },
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "auth.email_taken"


async def test_register_validation_errors(client):
    r = await client.post(
        f"{API}/auth/register",
        json={
            "email": "bad",
            "password": "short",
            "full_name": "X",
            "country_code": "UA",
            "workshop_name": "W",
            "accept_terms": True,
            "locale": "ru",
        },
    )
    assert r.status_code == 422
    fields = {f["field"] for f in r.json()["error"]["fields"]}
    assert {"email", "password", "locale"} <= fields


async def test_register_requires_terms_and_known_country(client):
    base = {
        "email": "a@example.com",
        "password": PASSWORD,
        "full_name": "A",
        "workshop_name": "W",
    }
    r = await client.post(
        f"{API}/auth/register", json={**base, "country_code": "UA", "accept_terms": False}
    )
    assert r.json()["error"]["code"] == "auth.terms_not_accepted"
    r = await client.post(
        f"{API}/auth/register", json={**base, "country_code": "US", "accept_terms": True}
    )
    assert r.json()["error"]["code"] == "reference.unknown_country"


async def test_login_requires_verified_email(client):
    await register(client)
    r = await client.post(
        f"{API}/auth/login", json={"email": "owner@example.com", "password": PASSWORD}
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "auth.email_not_verified"


async def test_verify_then_login_and_me(client):
    tokens = await register_verified(client)
    r = await client.get(f"{API}/users/me", headers=auth(tokens))
    assert r.status_code == 200
    me = r.json()
    assert me["user"]["email_verified"] is True
    assert me["workshops"][0]["role"] == "owner"
    assert me["workshops"][0]["workshop_name"] == "Ключі Київ"

    r = await client.post(
        f"{API}/auth/login", json={"email": "Owner@Example.com", "password": PASSWORD}
    )
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"


async def test_verify_link_is_single_use(client):
    await register(client)
    token = token_from_last_email()
    assert (await client.post(f"{API}/auth/verify-email", json={"token": token})).status_code == 200
    r = await client.post(f"{API}/auth/verify-email", json={"token": token})
    assert r.json()["error"]["code"] == "auth.invalid_or_expired_link"


async def test_resend_verification_invalidates_old_link(client):
    await register(client)
    old = token_from_last_email()
    r = await client.post(f"{API}/auth/resend-verification", json={"email": "owner@example.com"})
    assert r.status_code == 204
    new = token_from_last_email()
    assert old != new
    r = await client.post(f"{API}/auth/verify-email", json={"token": old})
    assert r.status_code == 400
    r = await client.post(f"{API}/auth/verify-email", json={"token": new})
    assert r.status_code == 200


async def test_wrong_password_and_unknown_email_look_the_same(client):
    await register_verified(client)
    a = await client.post(
        f"{API}/auth/login", json={"email": "owner@example.com", "password": "x" * 8}
    )
    b = await client.post(
        f"{API}/auth/login", json={"email": "nobody@example.com", "password": "x" * 8}
    )
    assert a.status_code == b.status_code == 401
    assert a.json()["error"]["code"] == b.json()["error"]["code"] == "auth.invalid_credentials"


async def test_no_token_and_bad_token(client):
    assert (await client.get(f"{API}/users/me")).status_code == 401
    r = await client.get(f"{API}/users/me", headers={"Authorization": "Bearer nonsense"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "auth.invalid_token"


async def test_refresh_rotation_and_reuse_detection(client):
    tokens = await register_verified(client)
    r = await client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    new = r.json()
    assert new["refresh_token"] != tokens["refresh_token"]

    # Reusing the old one → whole family revoked, including the new token.
    r = await client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401
    r = await client.post(f"{API}/auth/refresh", json={"refresh_token": new["refresh_token"]})
    assert r.status_code == 401


async def test_logout_revokes_refresh_token(client):
    tokens = await register_verified(client)
    r = await client.post(f"{API}/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 204
    r = await client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401


async def test_forgot_and_reset_password(client):
    tokens = await register_verified(client)
    r = await client.post(f"{API}/auth/forgot-password", json={"email": "owner@example.com"})
    assert r.status_code == 204
    reset_token = token_from_last_email()

    r = await client.post(
        f"{API}/auth/reset-password", json={"token": reset_token, "new_password": "new-password-2"}
    )
    assert r.status_code == 204
    # Old sessions are gone, old password does not work, new one does.
    r = await client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401
    r = await client.post(
        f"{API}/auth/login", json={"email": "owner@example.com", "password": PASSWORD}
    )
    assert r.status_code == 401
    r = await client.post(
        f"{API}/auth/login", json={"email": "owner@example.com", "password": "new-password-2"}
    )
    assert r.status_code == 200
    # Link cannot be reused.
    r = await client.post(
        f"{API}/auth/reset-password", json={"token": reset_token, "new_password": "another-pass-3"}
    )
    assert r.status_code == 400


async def test_forgot_password_unknown_email_is_silent(client):
    r = await client.post(f"{API}/auth/forgot-password", json={"email": "ghost@example.com"})
    assert r.status_code == 204
    assert outbox() == []


async def test_change_password(client):
    tokens = await register_verified(client)
    r = await client.post(
        f"{API}/auth/change-password",
        json={"current_password": "wrong-pass", "new_password": "new-password-2"},
        headers=auth(tokens),
    )
    assert r.json()["error"]["code"] == "auth.wrong_password"
    r = await client.post(
        f"{API}/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "new-password-2"},
        headers=auth(tokens),
    )
    assert r.status_code == 204
    r = await client.post(
        f"{API}/auth/login", json={"email": "owner@example.com", "password": "new-password-2"}
    )
    assert r.status_code == 200


async def test_update_me_and_delete_account(client):
    tokens = await register_verified(client)
    r = await client.patch(
        f"{API}/users/me", json={"full_name": "Mykola", "locale": "pl"}, headers=auth(tokens)
    )
    assert r.json()["user"]["full_name"] == "Mykola"
    assert r.json()["user"]["locale"] == "pl"

    r = await client.request(
        "DELETE", f"{API}/users/me", json={"password": PASSWORD}, headers=auth(tokens)
    )
    assert r.status_code == 204
    # Switched off, not erased: login says the account was deleted, sessions are gone.
    r = await client.post(
        f"{API}/auth/login", json={"email": "owner@example.com", "password": PASSWORD}
    )
    assert r.status_code == 403 and r.json()["error"]["code"] == "auth.account_deleted"
    r = await client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401


async def test_export_my_data(client):
    tokens = await register_verified(client)
    h = auth(tokens)
    wid = (await client.get(f"{API}/workshops", headers=h)).json()[0]["id"]
    inv = f"{API}/workshops/{wid}/inventory"
    item = (
        await client.post(
            f"{inv}/items", json={"kind": "blank", "name": "HU66", "quantity": 2}, headers=h
        )
    ).json()
    await client.post(
        f"{inv}/items/{item['id']}/movements",
        json={"type": "sale", "quantity": 1, "client_name": "Ivan"},
        headers=h,
    )
    r = await client.get(f"{API}/users/me/export", headers=h)
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    data = r.json()
    assert data["profile"]["email"] == "owner@example.com"
    assert data["workshops"][0]["role"] == "owner"
    assert [m["type"] for m in data["stock_changes"]] == ["initial", "sale"]
    assert data["stock_changes"][1]["client_name"] == "Ivan"
    assert data["sessions"]
    assert (await client.get(f"{API}/users/me/export")).status_code == 401
