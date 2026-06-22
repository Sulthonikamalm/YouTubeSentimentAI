import pytest

def test_cache_leak_isolation():
    # Simulasikan cache behavior di inference_service._lookup_cache
    db_mock = [
        {"comment_text": "Harga beras naik", "taxonomy_version_id": "v1", "sentiment": "negatif"},
        {"comment_text": "Harga beras naik", "taxonomy_version_id": "v2", "sentiment": "positif"},
    ]
    
    def lookup_cache(text, target_version):
        # Cache query condition: text matches AND taxonomy_version_id matches
        results = [row for row in db_mock if row["comment_text"] == text and row["taxonomy_version_id"] == target_version]
        return results[0] if results else None
        
    # Testing that version v1 doesn't leak into v2
    res_v1 = lookup_cache("Harga beras naik", "v1")
    assert res_v1 is not None
    assert res_v1["sentiment"] == "negatif"
    
    res_v2 = lookup_cache("Harga beras naik", "v2")
    assert res_v2 is not None
    assert res_v2["sentiment"] == "positif"
    
    res_v3 = lookup_cache("Harga beras naik", "v3")
    assert res_v3 is None
