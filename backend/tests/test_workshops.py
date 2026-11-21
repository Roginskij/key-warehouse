from tests.conftest import PASSWORD, auth, register_verified, token_from_last_email

API = "/api/v1"


async def _my_workshop_id(client, tokens) -> str:
    r = await client.get(f"{API}/workshops", headers=auth(tokens))
    return r.json()[0]["id"]


async def _invite(client, tokens, wid, email, **extra):
    r = await client.post(
        f"{API}/workshops/{wid}/invitations", json={"email": email, **extra}, headers=auth(tokens)
    )
    assert r.status_code == 201, r.text
    return token_from_last_email(email)


async def test_workshop_defaults_from_country(client):
    tokens = await register_verified(client, country_code="PL")
    r = await client.get(f"{API}/workshops", headers=auth(tokens))
    w = r.json()[0]
    assert (w["country_code"], w["base_currency"], w["trade_zone"]) == ("PL", "PLN", "EU")
    assert w["sharing_level"] == "none"
    assert w["my_role"] == "owner"


async def test_owner_can_create_second_workshop_and_change_currency(client):
    tokens = await register_verified(client)
    r = await client.post(
        f"{API}/workshops", json={"name": "Філія Львів", "country_code": "UA"}, headers=auth(tokens)
    )
    assert r.status_code == 201
    wid = r.json()["id"]
    r = await client.patch(
        f"{API}/workshops/{wid}", json={"base_currency": "usd"}, headers=auth(tokens)
    )
    assert r.json()["base_currency"] == "USD"
    assert len((await client.get(f"{API}/workshops", headers=auth(tokens))).json()) == 2


async def test_other_users_cannot_see_workshop(client):
    a = await register_verified(client, "a@example.com")
    b = await register_verified(client, "b@example.com")
    wid = await _my_workshop_id(client, a)
    r = await client.get(f"{API}/workshops/{wid}", headers=auth(b))
    assert r.status_code == 404
    r = await client.get(f"{API}/workshops/{wid}/members", headers=auth(b))
    assert r.status_code == 404


async def test_invite_new_master_creates_account(client):
    owner = await register_verified(client)
    wid = await _my_workshop_id(client, owner)
    token = await _invite(client, owner, wid, "master@example.com")

    r = await client.post(f"{API}/invitations/preview", json={"token": token})
    assert r.json() == {
        "workshop_name": "Ключі Київ",
        "email": "master@example.com",
        "role": "master",
        "account_exists": False,
    }

    r = await client.post(
        f"{API}/invitations/accept",
        json={"token": token, "full_name": "Master", "password": PASSWORD, "accept_terms": True},
    )
    assert r.status_code == 200, r.text
    master = r.json()["tokens"]
    me = (await client.get(f"{API}/users/me", headers=auth(master))).json()
    assert me["user"]["email_verified"] is True
    assert me["workshops"][0]["role"] == "master"

    # Master cannot manage the workshop.
    r = await client.post(
        f"{API}/workshops/{wid}/invitations", json={"email": "x@example.com"}, headers=auth(master)
    )
    assert r.status_code == 403
    r = await client.patch(f"{API}/workshops/{wid}", json={"name": "X"}, headers=auth(master))
    assert r.status_code == 403

    # Invitation is single-use.
    r = await client.post(f"{API}/invitations/preview", json={"token": token})
    assert r.json()["error"]["code"] == "invitations.invalid_or_expired"


async def test_existing_user_must_log_in_to_accept(client):
    owner = await register_verified(client)
    other = await register_verified(client, "master@example.com")
    stranger = await register_verified(client, "stranger@example.com")
    wid = await _my_workshop_id(client, owner)
    token = await _invite(client, owner, wid, "master@example.com")

    r = await client.post(f"{API}/invitations/accept", json={"token": token})
    assert r.json()["error"]["code"] == "invitations.login_required"
    r = await client.post(
        f"{API}/invitations/accept", json={"token": token}, headers=auth(stranger)
    )
    assert r.json()["error"]["code"] == "invitations.wrong_account"
    r = await client.post(f"{API}/invitations/accept", json={"token": token}, headers=auth(other))
    assert r.status_code == 200
    assert r.json()["tokens"] is None
    # Master now belongs to two workshops: their own and the owner's.
    me = (await client.get(f"{API}/users/me", headers=auth(other))).json()
    assert {w["role"] for w in me["workshops"]} == {"owner", "master"}


async def test_member_permissions_and_last_owner_rules(client):
    owner = await register_verified(client)
    wid = await _my_workshop_id(client, owner)
    token = await _invite(client, owner, wid, "m@example.com")
    master = (
        await client.post(
            f"{API}/invitations/accept",
            json={"token": token, "full_name": "M", "password": PASSWORD, "accept_terms": True},
        )
    ).json()["tokens"]

    members = (await client.get(f"{API}/workshops/{wid}/members", headers=auth(owner))).json()
    owner_m = next(m for m in members if m["role"] == "owner")
    master_m = next(m for m in members if m["role"] == "master")

    # The only owner cannot demote themself or leave.
    r = await client.patch(
        f"{API}/workshops/{wid}/members/{owner_m['membership_id']}",
        json={"role": "master"},
        headers=auth(owner),
    )
    assert r.json()["error"]["code"] == "workshops.last_owner"
    r = await client.delete(
        f"{API}/workshops/{wid}/members/{owner_m['membership_id']}", headers=auth(owner)
    )
    assert r.status_code == 409

    # Master can leave on their own.
    r = await client.delete(
        f"{API}/workshops/{wid}/members/{master_m['membership_id']}", headers=auth(master)
    )
    assert r.status_code == 204


async def test_sole_owner_of_shared_workshop_cannot_delete_account(client):
    owner = await register_verified(client)
    wid = await _my_workshop_id(client, owner)
    token = await _invite(client, owner, wid, "m@example.com")
    await client.post(
        f"{API}/invitations/accept",
        json={"token": token, "full_name": "M", "password": PASSWORD, "accept_terms": True},
    )
    r = await client.request(
        "DELETE", f"{API}/users/me", json={"password": PASSWORD}, headers=auth(owner)
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "users.transfer_ownership_first"
    assert r.json()["error"]["params"]["workshop_ids"] == [wid]


async def test_reference_endpoints(client):
    countries = (await client.get(f"{API}/reference/countries")).json()
    assert len(countries) == 28
    assert {
        "code": "UA",
        "name": "Ukraine",
        "default_currency": "UAH",
        "trade_zone": "UA",
    } in countries
    langs = {lang["code"] for lang in (await client.get(f"{API}/reference/languages")).json()}
    assert langs == {"uk", "en", "pl", "de", "fr", "es", "it"}
