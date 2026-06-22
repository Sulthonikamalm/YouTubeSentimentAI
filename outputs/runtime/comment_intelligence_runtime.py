
import re, html, json, joblib
import pandas as pd
from pathlib import Path

MODEL_PATH = Path("BEST_MODEL_LATEST.joblib")
TAXONOMY_PATH = Path("taxonomy_config_latest.json")

def normalize_text(text):
    if text is None:
        return ""
    text = html.unescape(str(text)).lower()
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"<.*?>", " ", text)
    text = re.sub(r"[@#]\S+", " ", text)
    text = re.sub(r"[^0-9a-zA-ZÀ-ÿĀ-ž\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def keyword_score(text, keywords):
    return sum((2 if " " in kw else 1) for kw in keywords if kw in text)

def assign_multilabel(text, taxonomy, min_score=1, max_labels=3):
    scores = {label: keyword_score(text, kws) for label, kws in taxonomy.items()}
    selected = [k for k, v in sorted(scores.items(), key=lambda x: x[1], reverse=True) if v >= min_score]
    return selected[:max_labels] if selected else ["lainnya"]

def assign_single_label(text, taxonomy, default_label="tidak_terdeteksi", min_score=1):
    scores = {label: keyword_score(text, kws) for label, kws in taxonomy.items() if kws}
    if not scores:
        return default_label
    best_label, best_score = max(scores.items(), key=lambda x: x[1])
    return best_label if best_score >= min_score else default_label

class CommentIntelligenceRuntime:
    def __init__(self, model_path=MODEL_PATH, taxonomy_path=TAXONOMY_PATH):
        self.model = joblib.load(model_path)
        with open(taxonomy_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.issue_taxonomy = cfg["issue_taxonomy"]
        self.stance_taxonomy = cfg["stance_taxonomy"]
        self.action_taxonomy = cfg["action_taxonomy"]

    def predict_one(self, text, like_count=0, reply_count=0, is_reply=False):
        clean = normalize_text(text)
        try:
            sentiment = self.model.predict([clean])[0]
        except Exception:
            X = pd.DataFrame([{
                "context_text_model": clean,
                "like_count": like_count,
                "reply_count": reply_count,
                "is_reply_numeric": int(bool(is_reply))
            }])
            sentiment = self.model.predict(X)[0]
        issues = assign_multilabel(clean, self.issue_taxonomy)
        return {
            "clean_text": clean,
            "sentiment": str(sentiment),
            "issues": issues,
            "primary_issue": issues[0],
            "stance": assign_single_label(clean, self.stance_taxonomy),
            "action_intent": assign_single_label(clean, self.action_taxonomy),
            "note": "Sentiment from joblib; issue/stance/action from taxonomy rules."
        }
