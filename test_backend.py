"""
Real, executable proof that the backend works — not a description of what
it should do, an actual client hitting the actual running server.
"""
import requests
import sys

BASE = "http://localhost:8000"
passes = 0
failures = 0


def ok(label, cond, extra=""):
    global passes, failures
    if cond:
        passes += 1
        print(f"PASS {label}")
    else:
        failures += 1
        print(f"FAIL {label} {extra}")


def main():
    # ---------- HEALTH ----------
    r = requests.get(f"{BASE}/health")
    ok("health check returns 200", r.status_code == 200)

    # ---------- SIGNUP: two separate organizations ----------
    r_a = requests.post(f"{BASE}/auth/signup", json={
        "organization_name": "Grand Plaza Hotel",
        "email": "owner@grandplaza.example",
        "password": "supersecret123",
    })
    ok("org A signup returns 201", r_a.status_code == 201, r_a.text)
    data_a = r_a.json()
    token_a = data_a["access_token"]
    org_a_id = data_a["organization_id"]
    ok("org A token is a real non-empty JWT string", isinstance(token_a, str) and len(token_a) > 20)

    r_b = requests.post(f"{BASE}/auth/signup", json={
        "organization_name": "Ocean View Resort",
        "email": "owner@oceanview.example",
        "password": "anothersecret456",
    })
    ok("org B signup returns 201", r_b.status_code == 201, r_b.text)
    data_b = r_b.json()
    token_b = data_b["access_token"]
    org_b_id = data_b["organization_id"]
    ok("org A and org B got different organization IDs", org_a_id != org_b_id)

    # ---------- SIGNUP: duplicate email rejected ----------
    r_dup = requests.post(f"{BASE}/auth/signup", json={
        "organization_name": "Fake Duplicate",
        "email": "owner@grandplaza.example",
        "password": "whatever12345",
    })
    ok("duplicate email signup rejected with 400", r_dup.status_code == 400)

    # ---------- LOGIN ----------
    r_login = requests.post(f"{BASE}/auth/login", data={
        "username": "owner@grandplaza.example", "password": "supersecret123",
    })
    ok("login with correct password succeeds", r_login.status_code == 200)
    ok("login returns a usable token", "access_token" in r_login.json())

    r_bad_login = requests.post(f"{BASE}/auth/login", data={
        "username": "owner@grandplaza.example", "password": "wrongpassword",
    })
    ok("login with wrong password rejected with 401", r_bad_login.status_code == 401)

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # ---------- UNAUTHENTICATED ACCESS REJECTED ----------
    r_noauth = requests.post(f"{BASE}/facilities", json={
        "slug": "should-fail", "name": "No Auth Facility",
    })
    ok("creating a facility with no token is rejected", r_noauth.status_code == 401)

    # ---------- CREATE FACILITY FOR ORG A ----------
    r_fac_a = requests.post(f"{BASE}/facilities", headers=headers_a, json={
        "slug": "grand-plaza-downtown",
        "name": "Grand Plaza Hotel — Downtown",
        "subtitle": "Full-Service Hotel",
        "receptionist": "Ava",
        "address": "1 Plaza Way",
        "hours": "Open 24 hours",
        "city": "Chicago", "country": "USA", "category": "Corporate",
    })
    ok("org A can create its own facility", r_fac_a.status_code == 201, r_fac_a.text)
    facility_a_id = r_fac_a.json()["id"]

    # ---------- CREATE FACILITY FOR ORG B ----------
    r_fac_b = requests.post(f"{BASE}/facilities", headers=headers_b, json={
        "slug": "ocean-view-main",
        "name": "Ocean View Resort — Main",
        "subtitle": "Beachfront Resort",
        "receptionist": "Nora",
        "address": "22 Shoreline Dr",
        "hours": "Open 24 hours",
        "city": "Miami", "country": "USA", "category": "Corporate",
    })
    ok("org B can create its own facility", r_fac_b.status_code == 201, r_fac_b.text)
    facility_b_id = r_fac_b.json()["id"]
    ok("org A and org B facilities got different IDs", facility_a_id != facility_b_id)

    # ---------- DUPLICATE SLUG REJECTED ----------
    r_dup_slug = requests.post(f"{BASE}/facilities", headers=headers_b, json={
        "slug": "grand-plaza-downtown", "name": "Trying to steal a slug",
    })
    ok("duplicate slug rejected even across different orgs", r_dup_slug.status_code == 400)

    # ---------- THE CRITICAL TEST: MULTI-TENANT ISOLATION ----------
    r_cross_read = requests.put(
        f"{BASE}/facilities/{facility_a_id}", headers=headers_b,
        json={"name": "HACKED BY ORG B"},
    )
    ok(
        "org B CANNOT edit org A's facility (blocked, not just hidden)",
        r_cross_read.status_code == 404,
        f"got {r_cross_read.status_code}: {r_cross_read.text}",
    )

    r_verify_unchanged = requests.get(f"{BASE}/facilities/{facility_a_id}")
    ok(
        "org A's facility name genuinely unchanged after org B's attempted edit",
        r_verify_unchanged.json()["name"] == "Grand Plaza Hotel — Downtown",
    )

    r_cross_delete = requests.delete(f"{BASE}/facilities/{facility_a_id}", headers=headers_b)
    ok("org B CANNOT delete org A's facility", r_cross_delete.status_code == 404)

    r_still_exists = requests.get(f"{BASE}/facilities/{facility_a_id}")
    ok("org A's facility still exists after org B's attempted delete", r_still_exists.status_code == 200)

    r_list_a = requests.get(f"{BASE}/facilities", headers=headers_a)
    r_list_b = requests.get(f"{BASE}/facilities", headers=headers_b)
    ok("org A's facility list contains only its own facility", [f["id"] for f in r_list_a.json()] == [facility_a_id])
    ok("org B's facility list contains only its own facility", [f["id"] for f in r_list_b.json()] == [facility_b_id])

    # ---------- PUBLIC GUEST READ (no auth needed — this is what a QR scan hits) ----------
    r_public = requests.get(f"{BASE}/facilities/by-slug/grand-plaza-downtown")
    ok("guest can look up a facility by slug with NO auth token", r_public.status_code == 200)
    ok("public lookup returns the right facility", r_public.json()["name"] == "Grand Plaza Hotel — Downtown")

    # ---------- DIRECTORY ITEMS ----------
    r_item = requests.post(f"{BASE}/facilities/{facility_a_id}/directory", headers=headers_a, json={
        "name": "Front Desk", "category": "people", "floor": "1", "icon": "user", "status": "open",
    })
    ok("org A can add a directory item to its own facility", r_item.status_code == 201, r_item.text)
    item_id = r_item.json()["id"]

    r_item_cross = requests.post(f"{BASE}/facilities/{facility_a_id}/directory", headers=headers_b, json={
        "name": "Sneaky Item", "category": "places",
    })
    ok("org B cannot add a directory item to org A's facility", r_item_cross.status_code == 404)

    r_item_public = requests.get(f"{BASE}/facilities/{facility_a_id}/directory")
    ok("guest can read the directory with no auth", r_item_public.status_code == 200)
    ok("directory contains the item that was added", any(i["name"] == "Front Desk" for i in r_item_public.json()))

    r_item_update = requests.put(
        f"{BASE}/facilities/{facility_a_id}/directory/{item_id}", headers=headers_a,
        json={"status": "busy"},
    )
    ok("org A can update its own directory item", r_item_update.status_code == 200 and r_item_update.json()["status"] == "busy")

    # ---------- STAFF (with handles list round-tripping through JSON) ----------
    r_staff = requests.post(f"{BASE}/facilities/{facility_a_id}/staff", headers=headers_a, json={
        "name": "Priya Shah", "role": "Concierge", "department": "Guest Services",
        "handles": ["reservations", "local recommendations", "lost items"],
        "today_status": "in",
    })
    ok("org A can add a staff member", r_staff.status_code == 201, r_staff.text)
    ok("staff handles list round-trips correctly through the JSON column", r_staff.json()["handles"] == ["reservations", "local recommendations", "lost items"])
    staff_id = r_staff.json()["id"]

    r_staff_cross_delete = requests.delete(f"{BASE}/facilities/{facility_a_id}/staff/{staff_id}", headers=headers_b)
    ok("org B cannot delete org A's staff member", r_staff_cross_delete.status_code == 404)

    r_staff_still = requests.get(f"{BASE}/facilities/{facility_a_id}/staff")
    ok("staff member still exists after org B's blocked delete attempt", any(s["id"] == staff_id for s in r_staff_still.json()))

    # ---------- CAUTIONS: staff posts, guest sees it live ----------
    r_caution = requests.post(f"{BASE}/facilities/{facility_a_id}/cautions", headers=headers_a, json={
        "title": "Pool closed for maintenance", "area": "Pool Deck",
        "description": "Reopening tomorrow at 9 AM.",
    })
    ok("org A can post a live notice", r_caution.status_code == 201)

    r_caution_public = requests.get(f"{BASE}/facilities/{facility_a_id}/cautions")
    ok(
        "guest sees the notice immediately, no auth needed, no separate publish step",
        any(c["title"] == "Pool closed for maintenance" for c in r_caution_public.json()),
    )

    # ---------- CLEANUP OWNER CAN DELETE THEIR OWN FACILITY ----------
    r_own_delete = requests.delete(f"{BASE}/facilities/{facility_b_id}", headers=headers_b)
    ok("org B CAN delete its own facility", r_own_delete.status_code == 204)
    r_confirm_gone = requests.get(f"{BASE}/facilities/{facility_b_id}")
    ok("org B's facility is genuinely gone after deletion", r_confirm_gone.status_code == 404)

    # ---------- PASSWORD RESET FLOW ----------
    r_forgot = requests.post(f"{BASE}/auth/forgot-password", json={"email": "owner@grandplaza.example"})
    ok("forgot-password returns 200 for a real email", r_forgot.status_code == 200)

    r_forgot_unknown = requests.post(f"{BASE}/auth/forgot-password", json={"email": "nobody@nowhere.example"})
    ok("forgot-password ALSO returns 200 for an unknown email (doesn't leak which emails exist)", r_forgot_unknown.status_code == 200)
    ok(
        "both responses have the identical generic message (no email-enumeration signal)",
        r_forgot.json()["message"] == r_forgot_unknown.json()["message"],
    )

    # Pull the real token straight from the database — this is what a real
    # email would have delivered as a link; we don't have email sending
    # configured, so we read the same value the (stubbed) email would contain.
    import sqlite3
    conn = sqlite3.connect("findme.db")
    cur = conn.cursor()
    cur.execute("SELECT reset_token FROM users WHERE email = ?", ("owner@grandplaza.example",))
    row = cur.fetchone()
    conn.close()
    ok("a real reset token was actually generated and stored", row is not None and row[0] is not None)
    reset_token = row[0]

    r_reset_bad_token = requests.post(f"{BASE}/auth/reset-password", json={
        "token": "not-a-real-token", "new_password": "irrelevant12345",
    })
    ok("resetting with a bogus token is rejected", r_reset_bad_token.status_code == 400)

    r_reset = requests.post(f"{BASE}/auth/reset-password", json={
        "token": reset_token, "new_password": "brandNewPassword789",
    })
    ok("resetting with the real token succeeds", r_reset.status_code == 200, r_reset.text)

    r_old_login = requests.post(f"{BASE}/auth/login", data={
        "username": "owner@grandplaza.example", "password": "supersecret123",
    })
    ok("the OLD password no longer works after reset", r_old_login.status_code == 401)

    r_new_login = requests.post(f"{BASE}/auth/login", data={
        "username": "owner@grandplaza.example", "password": "brandNewPassword789",
    })
    ok("the NEW password works after reset", r_new_login.status_code == 200)

    r_reuse_token = requests.post(f"{BASE}/auth/reset-password", json={
        "token": reset_token, "new_password": "tryingAgain999",
    })
    ok("the same reset token cannot be used twice", r_reuse_token.status_code == 400)

    # ---------- RATE LIMITING ----------
    # Login is limited to 10/minute per IP. Fire 12 rapid requests and
    # confirm the rate limiter actually kicks in before all 12 succeed.
    login_statuses = []
    for _ in range(12):
        r = requests.post(f"{BASE}/auth/login", data={"username": "nobody@nowhere.example", "password": "wrong"})
        login_statuses.append(r.status_code)
    ok(
        "rate limiter actually blocks excess login attempts (429 appears before request 12)",
        429 in login_statuses,
        f"statuses seen: {login_statuses}",
    )

    print(f"\n=== {passes} passed, {failures} failed ===")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
