import pytest
import sqlite3

def test_sampling_order_logic():
    # Simulasikan logika database ordering: ORDER BY is_baseline DESC, published_at DESC
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE comments (comment_text TEXT, is_baseline INTEGER, published_at TEXT)")
    
    # Insert data
    conn.execute("INSERT INTO comments VALUES ('C1', 0, '2023-01-01')")
    conn.execute("INSERT INTO comments VALUES ('C2', 1, '2023-01-02')")
    conn.execute("INSERT INTO comments VALUES ('C3', 1, '2023-01-05')")
    conn.execute("INSERT INTO comments VALUES ('C4', 0, '2023-01-10')")
    
    rows = conn.execute("SELECT comment_text FROM comments ORDER BY is_baseline DESC, published_at DESC").fetchall()
    
    # Expected order: C3 (baseline, newest), C2 (baseline, older), C4 (non-baseline, newest), C1 (non-baseline, older)
    assert rows[0][0] == 'C3'
    assert rows[1][0] == 'C2'
    assert rows[2][0] == 'C4'
    assert rows[3][0] == 'C1'
    
    conn.close()
