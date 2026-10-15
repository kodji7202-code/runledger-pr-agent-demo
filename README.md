# tasklite

A tiny task-tracker REST API built with Flask and SQLite.

## Setup

```sh
pip install -r requirements.txt
python scripts/migrate.py          # creates/updates tasklite.db
export TASKLITE_API_KEY=change-me
flask --app app run
```

`TASKLITE_DB` overrides the database path (default `tasklite.db`).

## API

All requests need an `X-API-Key` header matching `TASKLITE_API_KEY`.

| Method | Path                | Description                          |
|--------|---------------------|--------------------------------------|
| GET    | `/users`            | List users                           |
| POST   | `/users`            | Create user (`email`, `name`)        |
| GET    | `/users/<id>`       | Get a user                           |
| DELETE | `/users/<id>`       | Delete a user and all their tasks    |
| GET    | `/users/<id>/tasks` | List a user's tasks                  |
| POST   | `/users/<id>/tasks` | Create task (`title`)                |
| PATCH  | `/tasks/<id>`       | Update `title` and/or `done`         |

## Migrations

Add numbered `.sql` files to `migrations/`; `scripts/migrate.py` applies pending
ones in order and records them in `schema_migrations`.

## Tests

```sh
pytest
```
