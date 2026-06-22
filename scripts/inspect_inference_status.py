"""
inspect_inference_status.py — CLI script to inspect inference status and distributions.

Usage:
    python scripts/inspect_inference_status.py
"""

import sys
import io
from pathlib import Path

# Force UTF-8 stdout on Windows to avoid cp1252 UnicodeEncodeError.
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.storage import repository


def main():
    # Total comments
    all_ids = repository.get_all_comment_ids()
    total = len(all_ids)
    print("=" * 60)
    print("INFERENCE STATUS REPORT")
    print("=" * 60)
    print(f"\nTotal comments: {total}")

    # Status distribution
    status_counts = repository.inference_status_counts()
    print("\n--- Inference Status ---")
    for status, count in status_counts.items():
        label = status if status else "(NULL)"
        print(f"  {label:25s}: {count}")

    completed_count = status_counts.get("completed", 0)

    # Sentiment distribution
    if completed_count > 0:
        print("\n--- Sentiment Distribution ---")
        for label, count in repository.column_value_counts("sentiment").items():
            print(f"  {label:25s}: {count}")

        # Issue distribution
        print("\n--- Issue Distribution ---")
        for label, count in repository.column_value_counts("issue_label").items():
            print(f"  {label:25s}: {count}")

        # Stance distribution
        print("\n--- Stance Distribution ---")
        for label, count in repository.column_value_counts("stance_label").items():
            print(f"  {label:25s}: {count}")

        # Action intent distribution
        print("\n--- Action Intent Distribution ---")
        for label, count in repository.column_value_counts("action_intent_label").items():
            print(f"  {label:25s}: {count}")

        # Sample rows
        print("\n--- Sample Inference Results (5 random completed) ---")
        samples = repository.sample_inference_rows(limit=5)
        for i, row in enumerate(samples, 1):
            print(f"\n  [{i}] comment_id: {row.get('comment_id')}")
            txt = (row.get("comment_text") or "")[:80]
            print(f"      text: {txt}")
            print(f"      sentiment: {row.get('sentiment')} (conf={row.get('sentiment_confidence')})")
            print(f"      issue: {row.get('issue_label')}")
            print(f"      stance: {row.get('stance_label')}")
            print(f"      action_intent: {row.get('action_intent_label')}")
            interp = row.get("interpretation_short")
            if interp:
                print(f"      interpretation: {interp}")
    else:
        print("\nNo completed inferences found.")
        print("Run: python scripts/run_inference.py --pending")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
