import hmac
import sqlite3

from flask import Blueprint, current_app, jsonify, request

from .db import get_db

bp = Blueprint("api", __name__)


class ApiError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


@bp.errorhandler(ApiError)
def handle_api_error(err):
    return jsonify(error=err.message), err.status


@bp.before_request
def require_api_key():
    expected = current_app.config.get("API_KEY")
    supplied = request.headers.get("X-API-Key", "")
    # Fail closed: with no key configured, every request is rejected.
    if not expected or not hmac.compare_digest(supplied, expected):
        raise ApiError(401, "invalid or missing API key")


def get_json_object():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "request body must be a JSON object")
    return data


def require_string(data, field):
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ApiError(400, f"'{field}' is required and must be a non-empty string")
    return value.strip()


def fetch_or_404(query, args, what):
    row = get_db().execute(query, args).fetchone()
    if row is None:
        raise ApiError(404, f"{what} not found")
    return row


def task_json(row):
    return {**dict(row), "done": bool(row["done"])}


@bp.get("/users")
def list_users():
    rows = get_db().execute("SELECT * FROM users WHERE deleted_at IS NULL ORDER BY id").fetchall()
    return jsonify([dict(r) for r in rows])


@bp.post("/users")
def create_user():
    data = get_json_object()
    email = require_string(data, "email")
    name = require_string(data, "name")
    db = get_db()
    try:
        cur = db.execute("INSERT INTO users (email, name) VALUES (?, ?)", (email, name))
    except sqlite3.IntegrityError:
        raise ApiError(409, "email already registered")
    db.commit()
    row = db.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@bp.get("/users/<int:user_id>")
def get_user(user_id):
    row = fetch_or_404("SELECT * FROM users WHERE id = ? AND deleted_at IS NULL", (user_id,), "user")
    return jsonify(dict(row))


@bp.delete("/users/<int:user_id>")
def delete_user(user_id):
    fetch_or_404("SELECT id FROM users WHERE id = ? AND deleted_at IS NULL", (user_id,), "user")
    db = get_db()
    with db:
        db.execute(
            "UPDATE users SET deleted_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (user_id,),
        )
    return "", 204


@bp.get("/users/<int:user_id>/tasks")
def list_tasks(user_id):
    fetch_or_404("SELECT id FROM users WHERE id = ? AND deleted_at IS NULL", (user_id,), "user")
    rows = get_db().execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY id", (user_id,)
    ).fetchall()
    return jsonify([task_json(r) for r in rows])


@bp.post("/users/<int:user_id>/tasks")
def create_task(user_id):
    fetch_or_404("SELECT id FROM users WHERE id = ? AND deleted_at IS NULL", (user_id,), "user")
    title = require_string(get_json_object(), "title")
    db = get_db()
    cur = db.execute("INSERT INTO tasks (user_id, title) VALUES (?, ?)", (user_id, title))
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(task_json(row)), 201


@bp.patch("/tasks/<int:task_id>")
def update_task(task_id):
    fetch_or_404("SELECT id FROM tasks WHERE id = ?", (task_id,), "task")
    data = get_json_object()
    updates = {}
    if "title" in data:
        updates["title"] = require_string(data, "title")
    if "done" in data:
        if not isinstance(data["done"], bool):
            raise ApiError(400, "'done' must be a boolean")
        updates["done"] = int(data["done"])
    if not updates:
        raise ApiError(400, "nothing to update; supply 'title' and/or 'done'")

    db = get_db()
    # Column names come from the fixed keys above, never from user input.
    assignments = ", ".join(f"{col} = ?" for col in updates)
    db.execute(f"UPDATE tasks SET {assignments} WHERE id = ?", (*updates.values(), task_id))
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return jsonify(task_json(row))
