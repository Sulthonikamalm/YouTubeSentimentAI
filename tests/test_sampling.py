from collections import Counter

from backend.services.sampling_service import get_comment_sample_for_taxonomy
from backend.storage import repository
from backend.storage.db import get_db_connection


def _sample_db(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'sampling.db'}"
    repository.init_db(db_url)
    with get_db_connection(db_url) as conn:
        owner_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()[0]
        with conn:
            conn.execute(
                "INSERT INTO projects (project_id, project_name, owner_user_id) VALUES ('sample_project', 'Sample', ?)",
                (owner_id,),
            )
            for video_id in ("video_a", "video_b"):
                conn.execute(
                    "INSERT INTO videos (video_id, video_url, video_title, channel_title, project_id) "
                    "VALUES (?, ?, ?, ?, 'sample_project')",
                    (video_id, f"https://youtu.be/{video_id}", video_id.upper(), "Channel"),
                )
            for index in range(80):
                video_id = "video_a" if index < 70 else "video_b"
                conn.execute(
                    "INSERT INTO comments (comment_id, video_id, is_reply, author_name, author_channel_id, "
                    "comment_text, published_at, updated_at, is_baseline, is_deleted) "
                    "VALUES (?, ?, ?, 'Private Name', 'Private Channel ID', ?, ?, ?, ?, 0)",
                    (
                        f"sample_{index}", video_id, int(index % 5 == 0), f"Komentar {index}",
                        f"2026-05-{(index % 28) + 1:02d}T10:00:00+00:00",
                        f"2026-05-{(index % 28) + 1:02d}T10:00:00+00:00", int(index % 2 == 0),
                    ),
                )
    return db_url


def test_sample_is_balanced_private_and_deterministic(tmp_path):
    db_url = _sample_db(tmp_path)
    first = get_comment_sample_for_taxonomy("sample_project", db_url, min_sample=20, max_sample=20)
    second = get_comment_sample_for_taxonomy("sample_project", db_url, min_sample=20, max_sample=20)

    assert first["valid"] is True
    assert first["count"] == 20
    assert first["hash"] == second["hash"]
    assert first["sample"] == second["sample"]
    assert Counter(row["video_title"] for row in first["sample"]) == {"VIDEO_A": 10, "VIDEO_B": 10}
    assert all("author_name" not in row and "author_channel_id" not in row for row in first["sample"])
    assert all(not any(key.startswith("_") for key in row) for row in first["sample"])


def test_sample_rejects_project_below_minimum(tmp_path):
    db_url = _sample_db(tmp_path)
    result = get_comment_sample_for_taxonomy("sample_project", db_url, min_sample=81, max_sample=100)

    assert result["valid"] is False
    assert result["count"] == 80
    assert "81" in result["reason"]
