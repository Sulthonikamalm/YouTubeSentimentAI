import json

import pytest
from flask import Flask
from werkzeug.security import generate_password_hash

import backend.routes as route_helpers
import backend.routes.comments as comments_routes
import backend.routes.dashboard as dashboard_routes
import backend.routes.projects as projects_routes
import backend.routes.taxonomy as taxonomy_routes
from backend.routes.comments import comments_bp
from backend.routes.dashboard import dashboard_bp
from backend.routes.projects import projects_bp
from backend.routes.taxonomy import taxonomy_bp
from backend.storage import repository
from backend.storage.db import get_db_connection


def _labels(prefix, count, required):
    labels = [
        {"key": f"{prefix}_{index}", "name": f"{prefix} {index}", "description": f"Deskripsi {index}", "examples": []}
        for index in range(count)
    ]
    labels[-1] = {"key": required, "name": required, "description": "Fallback", "examples": []}
    return labels


def _config():
    return {
        "prompt_context": "Baca komentar sesuai tujuan project.",
        "issue_labels": _labels("issue", 5, "lainnya"),
        "stance_labels": _labels("stance", 3, "tidak_terdeteksi"),
        "action_labels": _labels("action", 4, "tidak_terdeteksi"),
    }


@pytest.fixture
def taxonomy_api(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'routes.db'}"
    repository.init_db(db_url)
    with get_db_connection(db_url) as conn:
        owner_one = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()[0]
        with conn:
            owner_two = conn.execute(
                "INSERT INTO users (username, display_name, password_hash) VALUES ('other', 'Other', ?)",
                (generate_password_hash("password"),),
            ).lastrowid
            conn.execute(
                "INSERT INTO projects (project_id, project_name, owner_user_id, status) VALUES ('owner_project', 'Owner', ?, 'draft')",
                (owner_one,),
            )
            conn.execute(
                "INSERT INTO projects (project_id, project_name, owner_user_id, status) VALUES ('other_project', 'Other', ?, 'draft')",
                (owner_two,),
            )
            conn.execute(
                "INSERT INTO videos (video_id, video_url, project_id) VALUES ('owner_video', 'https://youtu.be/owner_video', 'owner_project')"
            )
            conn.execute(
                "INSERT INTO videos (video_id, video_url, project_id) VALUES ('other_video', 'https://youtu.be/other_video', 'other_project')"
            )
            for comment_id, video_id in (("owner_comment", "owner_video"), ("other_comment", "other_video")):
                conn.execute(
                    "INSERT INTO comments (comment_id, video_id, is_reply, comment_text, published_at, updated_at, "
                    "is_baseline, is_deleted, inference_status, sentiment, is_manually_corrected) "
                    "VALUES (?, ?, 0, ?, '2026-06-01T00:00:00Z', '2026-06-01T00:00:00Z', 0, 0, 'completed', ?, 0)",
                    (comment_id, video_id, comment_id, "positive" if video_id == "owner_video" else "negative"),
                )

    for module in (route_helpers, projects_routes, taxonomy_routes, comments_routes, dashboard_routes):
        monkeypatch.setattr(module, "get_db_url", lambda url=db_url: url)

    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    app.register_blueprint(projects_bp)
    app.register_blueprint(taxonomy_bp)
    app.register_blueprint(comments_bp)
    app.register_blueprint(dashboard_bp)
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = owner_one
    return client, db_url, owner_one, owner_two


def test_project_creation_generates_id_and_scopes_list(taxonomy_api):
    client, db_url, owner_one, _ = taxonomy_api
    response = client.post("/api/projects", json={
        "project_name": "Respons Produk Baru",
        "goal_type": "keluhan",
        "goal_text": "Temukan keluhan utama",
    })
    assert response.status_code == 200
    project_id = response.get_json()["project_id"]
    assert project_id.startswith("respons-produk-baru_")

    listed = client.get("/api/projects").get_json()["projects"]
    assert {project["project_id"] for project in listed} >= {"default_politik", "owner_project", project_id}
    assert "other_project" not in {project["project_id"] for project in listed}
    with get_db_connection(db_url) as conn:
        stored = conn.execute("SELECT owner_user_id, status FROM projects WHERE project_id = ?", (project_id,)).fetchone()
    assert stored["owner_user_id"] == owner_one
    assert stored["status"] == "draft"


def test_other_users_project_returns_404_and_comments_do_not_leak(taxonomy_api):
    client, _, _, _ = taxonomy_api
    assert client.get("/api/projects/other_project").status_code == 404
    assert client.get("/api/projects/other_project/taxonomy/versions").status_code == 404

    comments = client.get("/api/comments?limit=10").get_json()["comments"]
    assert [comment["comment_id"] for comment in comments] == ["owner_comment"]
    assert client.get("/api/comments?project_id=other_project").get_json()["comments"] == []


def test_dashboard_distributions_are_owner_scoped(taxonomy_api):
    client, _, _, _ = taxonomy_api
    response = client.get("/api/dashboard/distributions")

    assert response.status_code == 200
    assert response.get_json()["sentiment"] == {"positive": 1}
    assert client.get("/api/dashboard/distributions?project_id=other_project").status_code == 404


def test_manual_draft_activation_and_reprocess_are_project_scoped(taxonomy_api):
    client, db_url, _, _ = taxonomy_api
    created = client.post("/api/projects/owner_project/taxonomy/versions", json=_config())
    assert created.status_code == 201
    version_id = created.get_json()["version_id"]

    activated = client.post(
        f"/api/projects/owner_project/taxonomy/versions/{version_id}/activate",
        json={"reprocess_all": True},
    )
    assert activated.status_code == 200
    assert activated.get_json()["comments_queued"] == 1

    with get_db_connection(db_url) as conn:
        project = conn.execute("SELECT * FROM projects WHERE project_id = 'owner_project'").fetchone()
        owner_comment = conn.execute("SELECT inference_status FROM comments WHERE comment_id = 'owner_comment'").fetchone()[0]
        other_comment = conn.execute("SELECT inference_status FROM comments WHERE comment_id = 'other_comment'").fetchone()[0]
    assert project["active_taxonomy_version_id"] == version_id
    assert project["status"] == "active"
    assert owner_comment == "pending"
    assert other_comment == "completed"


def test_invalid_draft_cannot_archive_current_active_version(taxonomy_api):
    client, db_url, owner_one, _ = taxonomy_api
    first = client.post("/api/projects/owner_project/taxonomy/versions", json=_config()).get_json()["version_id"]
    assert client.post(f"/api/projects/owner_project/taxonomy/versions/{first}/activate", json={}).status_code == 200

    with get_db_connection(db_url) as conn:
        with conn:
            conn.execute(
                "INSERT INTO project_taxonomy_versions "
                "(version_id, project_id, status, source, prompt_context, issue_labels, stance_labels, action_labels, created_by) "
                "VALUES ('invalid_draft', 'owner_project', 'draft', 'manual', 'x', '[]', '[]', '[]', ?)",
                (owner_one,),
            )

    rejected = client.post("/api/projects/owner_project/taxonomy/versions/invalid_draft/activate", json={})
    assert rejected.status_code == 400
    with get_db_connection(db_url) as conn:
        status = conn.execute(
            "SELECT status FROM project_taxonomy_versions WHERE version_id = ?", (first,)
        ).fetchone()[0]
    assert status == "active"
