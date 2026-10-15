from app.db import apply_migrations, connect


def test_auth_required(app):
    anon = app.test_client()
    assert anon.get("/users").status_code == 401
    assert anon.get("/users", headers={"X-API-Key": "wrong"}).status_code == 401
    assert anon.get("/users", headers={"X-API-Key": "test-key"}).status_code == 200


def test_auth_fails_closed_without_configured_key(app):
    app.config["API_KEY"] = None
    assert app.test_client().get("/users", headers={"X-API-Key": ""}).status_code == 401


def test_create_and_get_user(client):
    resp = client.post("/users", json={"email": "a@example.com", "name": "A"})
    assert resp.status_code == 201
    created = resp.get_json()
    assert created["email"] == "a@example.com" and created["created_at"]
    assert client.get(f"/users/{created['id']}").get_json() == created
    assert client.get("/users").get_json() == [created]


def test_create_user_validation(client, user):
    assert client.post("/users", json={"name": "x"}).status_code == 400
    assert client.post("/users", data="nope").status_code == 400
    dup = client.post("/users", json={"email": user["email"], "name": "Other"})
    assert dup.status_code == 409


def test_get_missing_user_404(client):
    assert client.get("/users/999").status_code == 404


def test_create_and_list_tasks(client, user):
    resp = client.post(f"/users/{user['id']}/tasks", json={"title": "write tests"})
    assert resp.status_code == 201
    task = resp.get_json()
    assert task["title"] == "write tests" and task["done"] is False
    assert client.get(f"/users/{user['id']}/tasks").get_json() == [task]


def test_tasks_for_missing_user_404(client):
    assert client.get("/users/999/tasks").status_code == 404
    assert client.post("/users/999/tasks", json={"title": "x"}).status_code == 404


def test_patch_task(client, user):
    task = client.post(f"/users/{user['id']}/tasks", json={"title": "old"}).get_json()
    resp = client.patch(f"/tasks/{task['id']}", json={"done": True, "title": "new"})
    assert resp.status_code == 200
    assert resp.get_json()["done"] is True
    assert resp.get_json()["title"] == "new"


def test_patch_task_validation(client, user):
    task = client.post(f"/users/{user['id']}/tasks", json={"title": "t"}).get_json()
    url = f"/tasks/{task['id']}"
    assert client.patch(url, json={}).status_code == 400
    assert client.patch(url, json={"done": "yes"}).status_code == 400
    assert client.patch("/tasks/999", json={"done": True}).status_code == 404


def test_delete_user_is_soft_and_keeps_tasks(client, app, user):
    other = client.post("/users", json={"email": "b@example.com", "name": "B"}).get_json()
    client.post(f"/users/{user['id']}/tasks", json={"title": "one"})
    client.post(f"/users/{user['id']}/tasks", json={"title": "two"})
    client.post(f"/users/{other['id']}/tasks", json={"title": "keep"})

    assert client.delete(f"/users/{user['id']}").status_code == 204
    assert client.get(f"/users/{user['id']}").status_code == 404
    assert [u["id"] for u in client.get("/users").get_json()] == [other["id"]]
    assert client.get(f"/users/{user['id']}/tasks").status_code == 404
    assert client.post(f"/users/{user['id']}/tasks", json={"title": "x"}).status_code == 404
    assert client.delete(f"/users/{user['id']}").status_code == 404

    conn = connect(app.config["DATABASE"])
    titles = sorted(r["title"] for r in conn.execute("SELECT title FROM tasks"))
    deleted_at = conn.execute(
        "SELECT deleted_at FROM users WHERE id = ?", (user["id"],)
    ).fetchone()[0]
    conn.close()
    assert titles == ["keep", "one", "two"]
    assert deleted_at


def test_delete_missing_user_404(client):
    assert client.delete("/users/999").status_code == 404


def test_migrations_are_recorded_and_idempotent(tmp_path):
    conn = connect(tmp_path / "m.db")
    assert apply_migrations(conn) == ["001_init.sql", "002_users_soft_delete.sql"]
    assert apply_migrations(conn) == []
    names = [r["name"] for r in conn.execute("SELECT name FROM schema_migrations")]
    conn.close()
    assert names == ["001_init.sql", "002_users_soft_delete.sql"]
