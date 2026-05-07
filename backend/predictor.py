"""
predictor.py — Inference pipeline cho 5 models
    - logistic   : Logistic Regression + TF-IDF (HF Hub)
    - random_forest: Random Forest + TF-IDF (HF Hub)
    - cnn_lstm   : CNN-LSTM (HF Hub)
    - phobert    : PhoBERT fine-tuned (HF Hub)
    - llama      : LLaMA-3.2-1B fine-tuned (HF Hub)
"""

import os
import json
import numpy as np
import joblib
import torch
from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForCausalLM
from underthesea import word_tokenize

CATEGORIES = [
    "Room_Facilities",
    "Service_Staff",
    "Location",
    "Food_Beverage",
    "Price_Value",
    "General",
]
NUM_CLASSES   = 3   # 0=None, 1=Negative, 2=Positive
SENTIMENT_VALS = ["None", "Negative", "Positive"]

# ── HuggingFace token (tranh rate limit) ────────────────────────────
HF_TOKEN = os.environ.get("HF_TOKEN", None)
if HF_TOKEN:
    from huggingface_hub import login as hf_login
    hf_login(token=HF_TOKEN, add_to_git_credential=False)

# ── HuggingFace repo IDs ─────────────────────────────────────────────
LR_REPO       = os.environ.get("LR_HUB",       "ntdat232205/lr-hotel-absa")
RF_REPO       = os.environ.get("RF_HUB",       "ntdat232205/rf-hotel-absa")
CNN_REPO      = os.environ.get("CNN_HUB",      "ntdat232205/cnn-lstm-hotel-absa")
PHOBERT_REPO  = os.environ.get("PHOBERT_HUB",  "ntdat232205/phobert-hotel-absa")
LLAMA_REPO    = os.environ.get("LLAMA_HUB",    "ntdat232205/llama-hotel-absa")

# ── Model caches ─────────────────────────────────────────────────────
_lr_models    = None
_lr_vec       = None
_rf_models    = None
_rf_vec       = None
_cnn_model    = None
_cnn_tok      = None
_cnn_cfg      = None
_pb_tokenizer = None
_pb_model     = None
_llm_tokenizer = None
_llm_model     = None


# ══════════════════════════════════════════════════════════════════════
# Load helpers
# ══════════════════════════════════════════════════════════════════════

def _load_lr():
    global _lr_models, _lr_vec
    if _lr_models is None:
        print("[Predictor] Loading Logistic Regression...")
        lr_path  = hf_hub_download(LR_REPO, "logistic_regression_models.pkl")
        vec_path = hf_hub_download(LR_REPO, "tfidf_vectorizer.pkl")
        _lr_models = joblib.load(lr_path)
        _lr_vec    = joblib.load(vec_path)
        print("[Predictor] LR loaded.")
    return _lr_models, _lr_vec


def _load_rf():
    global _rf_models, _rf_vec
    if _rf_models is None:
        print("[Predictor] Loading Random Forest...")
        rf_path  = hf_hub_download(RF_REPO, "random_forest_models.pkl")
        vec_path = hf_hub_download(RF_REPO, "tfidf_vectorizer.pkl")
        _rf_models = joblib.load(rf_path)
        _rf_vec    = joblib.load(vec_path)
        print("[Predictor] RF loaded.")
    return _rf_models, _rf_vec


def _load_cnn():
    global _cnn_model, _cnn_tok, _cnn_cfg
    if _cnn_model is None:
        import pickle
        from tensorflow.keras.preprocessing.text import Tokenizer  # noqa
        print("[Predictor] Loading CNN-LSTM...")
        cfg_path = hf_hub_download(CNN_REPO, "cnn_cfg.json")
        tok_path = hf_hub_download(CNN_REPO, "keras_tokenizer.pkl")
        pt_path  = hf_hub_download(CNN_REPO, "cnn_lstm_best.pt")

        with open(cfg_path) as f:
            _cnn_cfg = json.load(f)
        with open(tok_path, "rb") as f:
            _cnn_tok = pickle.load(f)

        # Rebuild model architecture
        import torch.nn as nn
        import torch.nn.functional as F

        class CNN_LSTM_ABSA(nn.Module):
            def __init__(self, vocab_size, embed_dim, num_filters,
                         kernel_size, hidden_dim, num_labels, dropout):
                super().__init__()
                self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
                self.conv      = nn.Conv1d(embed_dim, num_filters, kernel_size,
                                           padding=kernel_size // 2)
                self.lstm      = nn.LSTM(num_filters, hidden_dim,
                                         batch_first=True, bidirectional=True)
                self.fc        = nn.Linear(hidden_dim * 2, num_labels)
                self.dropout   = nn.Dropout(dropout)
                self.bn        = nn.BatchNorm1d(num_filters)

            def forward(self, x):
                emb  = self.dropout(self.embedding(x))
                conv = F.relu(self.bn(self.conv(emb.permute(0, 2, 1))))
                conv = conv.permute(0, 2, 1)
                _, (h, _) = self.lstm(conv)
                h = self.dropout(torch.cat((h[-2], h[-1]), dim=1))
                return self.fc(h)

        vocab_size = min(len(_cnn_tok.word_index) + 1,
                         _cnn_cfg["max_words"] + 1)
        _cnn_model = CNN_LSTM_ABSA(
            vocab_size,
            _cnn_cfg["embed_dim"],
            _cnn_cfg["num_filters"],
            _cnn_cfg["kernel_size"],
            _cnn_cfg["hidden_dim"],
            len(CATEGORIES) * 2,   # 12 binary outputs
            _cnn_cfg["dropout"],
        )
        _cnn_model.load_state_dict(
            torch.load(pt_path, map_location="cpu")
        )
        _cnn_model.eval()
        print("[Predictor] CNN-LSTM loaded.")
    return _cnn_model, _cnn_tok, _cnn_cfg


def _load_phobert():
    global _pb_tokenizer, _pb_model
    if _pb_model is None:
        print(f"[Predictor] Loading PhoBERT from {PHOBERT_REPO}...")
        _pb_tokenizer = AutoTokenizer.from_pretrained(
            "vinai/phobert-base", use_fast=False
        )
        _pb_model = AutoModelForSequenceClassification.from_pretrained(
            PHOBERT_REPO
        )
        _pb_model.eval()
        print("[Predictor] PhoBERT loaded.")
    return _pb_tokenizer, _pb_model


def _load_llama():
    global _llm_tokenizer, _llm_model
    if _llm_model is None:
        print(f"[Predictor] Loading LLaMA from {LLAMA_REPO}...")
        _llm_tokenizer = AutoTokenizer.from_pretrained(LLAMA_REPO)
        _llm_model = AutoModelForCausalLM.from_pretrained(
            LLAMA_REPO,
            dtype=torch.float32,
            device_map="cpu",
            low_cpu_mem_usage=True,
        )
        _llm_model.eval()
        print("[Predictor] LLaMA loaded.")
    return _llm_tokenizer, _llm_model


# ══════════════════════════════════════════════════════════════════════
# Predict single
# ══════════════════════════════════════════════════════════════════════

def predict_single(text: str, model_type: str = "phobert") -> dict:
    model_type = model_type.lower()
    if model_type in ("logistic", "lr"):
        return _predict_lr(text)
    elif model_type in ("random_forest", "rf"):
        return _predict_rf(text)
    elif model_type in ("cnn_lstm", "cnn"):
        return _predict_cnn(text)
    elif model_type == "llama":
        return _predict_llama(text)
    else:
        return _predict_phobert(text)


# ── Logistic Regression ──────────────────────────────────────────────

def _predict_lr(text: str) -> dict:
    models, vec = _load_lr()
    X = vec.transform([text])
    return {cat: int(models[cat].predict(X)[0]) for cat in CATEGORIES}


# ── Random Forest ────────────────────────────────────────────────────

def _predict_rf(text: str) -> dict:
    models, vec = _load_rf()
    X = vec.transform([text])
    return {cat: int(models[cat].predict(X)[0]) for cat in CATEGORIES}


# ── CNN-LSTM ─────────────────────────────────────────────────────────

def _cnn_binary_to_class(probs: np.ndarray) -> dict:
    """probs shape (12,) → dict {cat: 0/1/2}"""
    result = {}
    for i, cat in enumerate(CATEGORIES):
        neg = probs[i * 2]
        pos = probs[i * 2 + 1]
        if pos > neg and pos > 0.5:
            result[cat] = 2
        elif neg > 0.5:
            result[cat] = 1
        else:
            result[cat] = 0
    return result


def _predict_cnn(text: str) -> dict:
    from tensorflow.keras.preprocessing.sequence import pad_sequences
    model, tok, cfg = _load_cnn()
    seq = tok.texts_to_sequences([text])
    X   = pad_sequences(seq, maxlen=cfg["max_len"])
    inp = torch.tensor(X, dtype=torch.long)
    with torch.no_grad():
        probs = torch.sigmoid(model(inp)).cpu().numpy()[0]
    return _cnn_binary_to_class(probs)


def _predict_cnn_batch(texts: list) -> list:
    from tensorflow.keras.preprocessing.sequence import pad_sequences
    model, tok, cfg = _load_cnn()
    seqs = tok.texts_to_sequences(texts)
    X    = pad_sequences(seqs, maxlen=cfg["max_len"])
    inp  = torch.tensor(X, dtype=torch.long)
    with torch.no_grad():
        probs = torch.sigmoid(model(inp)).cpu().numpy()
    return [_cnn_binary_to_class(p) for p in probs]


# ── PhoBERT ──────────────────────────────────────────────────────────

def _predict_phobert(text: str) -> dict:
    tokenizer, model = _load_phobert()
    text_seg = word_tokenize(text, format="text")
    inputs   = tokenizer(text_seg, return_tensors="pt",
                         truncation=True, max_length=256, padding=True)
    with torch.no_grad():
        logits = model(**inputs).logits.cpu().numpy()[0]
    result = {}
    for i, cat in enumerate(CATEGORIES):
        base        = i * NUM_CLASSES
        result[cat] = int(np.argmax(logits[base: base + NUM_CLASSES]))
    return result


def _predict_phobert_batch(texts: list, batch_size: int = 16) -> list:
    tokenizer, model = _load_phobert()
    all_results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i: i + batch_size]
        segs  = [word_tokenize(t, format="text") for t in batch]
        inputs = tokenizer(segs, return_tensors="pt",
                           truncation=True, max_length=256, padding=True)
        with torch.no_grad():
            logits = model(**inputs).logits.cpu().numpy()
        for row in logits:
            result = {}
            for j, cat in enumerate(CATEGORIES):
                base        = j * NUM_CLASSES
                result[cat] = int(np.argmax(row[base: base + NUM_CLASSES]))
            all_results.append(result)
    return all_results


# ── LLaMA ────────────────────────────────────────────────────────────

INFER_TMPL = (
    "Bạn là chuyên gia phân tích cảm xúc đánh giá khách sạn tiếng Việt.\n"
    "Phân tích đánh giá dưới đây và cho biết sentiment của từng aspect.\n"
    "Sentiment: None (không đề cập), Negative (tiêu cực), Positive (tích cực).\n\n"
    "Đánh giá: {review}\n\n"
    "Kết quả (JSON):\n"
)


def _parse_llama_json(raw: str) -> dict:
    result = {cat: 0 for cat in CATEGORIES}
    try:
        s = raw.find("{")
        e = raw.rfind("}") + 1
        if s == -1 or e == 0:
            return result
        parsed = json.loads(raw[s:e])
        for cat in CATEGORIES:
            v = str(parsed.get(cat, "")).strip()
            if v in SENTIMENT_VALS:
                result[cat] = SENTIMENT_VALS.index(v)
    except Exception as ex:
        print(f"[LLaMA parse error] {ex} | raw: {raw[:100]}")
    return result


def _predict_llama(text: str) -> dict:
    tokenizer, model = _load_llama()
    prompt = INFER_TMPL.format(review=text.strip())
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=128,
            do_sample=False,
            use_cache=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    new_tok = out[0][inputs["input_ids"].shape[1]:]
    raw     = tokenizer.decode(new_tok, skip_special_tokens=True).strip()
    return _parse_llama_json(raw)


# ══════════════════════════════════════════════════════════════════════
# Predict batch
# ══════════════════════════════════════════════════════════════════════

def predict_batch(texts: list, model_type: str = "phobert") -> list:
    model_type = model_type.lower()
    if model_type in ("logistic", "lr"):
        return [_predict_lr(t) for t in texts]
    elif model_type in ("random_forest", "rf"):
        return [_predict_rf(t) for t in texts]
    elif model_type in ("cnn_lstm", "cnn"):
        return _predict_cnn_batch(texts)
    elif model_type == "llama":
        return [_predict_llama(t) for t in texts]
    else:
        return _predict_phobert_batch(texts)


# ══════════════════════════════════════════════════════════════════════
# ABSA summary + match score
# ══════════════════════════════════════════════════════════════════════

def compute_absa_summary(predictions: list) -> dict:
    if not predictions:
        return {}

    col_map = {
        "Room_Facilities": ("room_positive_pct",     "room_negative_pct"),
        "Service_Staff":   ("staff_positive_pct",    "staff_negative_pct"),
        "Location":        ("location_positive_pct", "location_negative_pct"),
        "Food_Beverage":   ("food_positive_pct",     "food_negative_pct"),
        "Price_Value":     ("price_positive_pct",    "price_negative_pct"),
        "General":         ("general_positive_pct",  "general_negative_pct"),
    }

    scores       = {}
    positive_pcts = []

    for cat, (pos_key, neg_key) in col_map.items():
        vals      = [p[cat] for p in predictions]
        mentioned = sum(1 for v in vals if v != 0)
        pos_count = sum(1 for v in vals if v == 2)
        neg_count = sum(1 for v in vals if v == 1)

        pos_pct = round(pos_count / max(mentioned, 1) * 100, 1)
        neg_pct = round(neg_count / max(mentioned, 1) * 100, 1)

        scores[pos_key] = pos_pct
        scores[neg_key] = neg_pct

        if mentioned > 0:
            positive_pcts.append(pos_pct)

    scores["overall_score"]  = round(np.mean(positive_pcts), 1) if positive_pcts else 0
    scores["total_analyzed"] = len(predictions)
    return scores


def compute_match_score(absa_scores: dict, user_request: str,
                        priority_aspects: list = None) -> float:
    aspect_score_map = {
        "Room_Facilities": absa_scores.get("room_positive_pct", 0),
        "Service_Staff":   absa_scores.get("staff_positive_pct", 0),
        "Location":        absa_scores.get("location_positive_pct", 0),
        "Food_Beverage":   absa_scores.get("food_positive_pct", 0),
        "Price_Value":     absa_scores.get("price_positive_pct", 0),
        "General":         absa_scores.get("general_positive_pct", 0),
    }

    total      = absa_scores.get("total_analyzed", 0)
    confidence = min(1.0, np.log(total + 1) / np.log(31))

    if priority_aspects:
        weights = {
            cat: (1.0 if cat in priority_aspects else 0.2)
            for cat in CATEGORIES
        }
    else:
        weights = {cat: 1.0 for cat in CATEGORIES}

    total_weight = sum(weights.values())
    weighted_sum = sum(aspect_score_map[cat] * weights[cat] for cat in CATEGORIES)
    match_score  = (weighted_sum / total_weight) * confidence

    return round(match_score, 1)