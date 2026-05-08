"""
predictor.py — Load model từ HF Hub, chạy inference local trên Railway
RAM Railway Hobby: 8GB — đủ cho PhoBERT(500MB) + LR/RF/CNN
"""

import os, json, logging, joblib, numpy as np
import torch
from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from underthesea import word_tokenize

log = logging.getLogger(__name__)

CATEGORIES = ["Room_Facilities","Service_Staff","Location","Food_Beverage","Price_Value","General"]
NUM_CLASSES = 3

HF_TOKEN     = os.environ.get("HF_TOKEN", None)
LR_REPO      = os.environ.get("LR_HUB",      "quangdao232/lr-hotel-absa")
CNN_REPO     = os.environ.get("CNN_HUB",     "quangdao232/cnn-lstm-hotel-absa")
PHOBERT_REPO = os.environ.get("PHOBERT_HUB", "quangdao232/phobert-hotel-absa")

if HF_TOKEN:
    from huggingface_hub import login as hf_login
    hf_login(token=HF_TOKEN, add_to_git_credential=False)

# Cache
_lr_models=_lr_vec=_cnn_model=_cnn_tok=_cnn_cfg=None
_pb_tok=_pb_model=None


def preprocess(text):
    try: return " ".join(word_tokenize(text, format="text").split())
    except: return text


# ── Load helpers ─────────────────────────────────────────────────────

def _load_lr():
    global _lr_models, _lr_vec
    if _lr_models is None:
        log.info("Loading LR model...")
        _lr_vec    = joblib.load(hf_hub_download(LR_REPO, "tfidf_vectorizer.pkl", token=HF_TOKEN))
        _lr_models = joblib.load(hf_hub_download(LR_REPO, "logistic_regression_models.pkl", token=HF_TOKEN))
    return _lr_vec, _lr_models

class CNN_LSTM_ABSA(torch.nn.Module):
    def __init__(self, cfg, vocab_size):
        super().__init__()
        embed_dim   = cfg.get("embed_dim",    128)
        num_filters = cfg.get("num_filters",  128)
        kernel_size = cfg.get("kernel_size",  3)
        hidden_dim  = cfg.get("hidden_dim",   256)
        dropout     = cfg.get("dropout",      0.3)
        n_classes   = len(CATEGORIES) * NUM_CLASSES  # 18

        self.embedding = torch.nn.Embedding(vocab_size + 1, embed_dim, padding_idx=0)
        self.conv      = torch.nn.Conv1d(embed_dim, num_filters, kernel_size, padding=kernel_size//2)
        self.relu      = torch.nn.ReLU()
        self.lstm      = torch.nn.LSTM(num_filters, hidden_dim, batch_first=True, bidirectional=True)
        self.dropout   = torch.nn.Dropout(dropout)
        self.fc        = torch.nn.Linear(hidden_dim * 2, n_classes)

    def forward(self, x):
        emb  = self.embedding(x)                        # [B, L, E]
        emb  = emb.permute(0, 2, 1)                     # [B, E, L]
        conv = self.relu(self.conv(emb))                 # [B, F, L]
        conv = conv.permute(0, 2, 1)                     # [B, L, F]
        out, _ = self.lstm(conv)                         # [B, L, H*2]
        out  = self.dropout(out[:, -1, :])               # [B, H*2]
        return self.fc(out)                              # [B, 18]


def _load_cnn():
    global _cnn_model, _cnn_tok, _cnn_cfg
    if _cnn_model is None:
        print("[CNN] Loading CNN-LSTM model...", flush=True)
        import pickle, json as _json
        cfg_path = hf_hub_download(CNN_REPO, "cnn_cfg.json", token=HF_TOKEN)
        with open(cfg_path) as f:
            _cnn_cfg = _json.load(f)
        tok_path = hf_hub_download(CNN_REPO, "keras_tokenizer.pkl", token=HF_TOKEN)
        with open(tok_path, "rb") as f:
            _cnn_tok = pickle.load(f)
        vocab_size = _cnn_cfg.get("max_words", 15000)
        model_path = hf_hub_download(CNN_REPO, "cnn_lstm_best.pt", token=HF_TOKEN)
        state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
        _cnn_model = CNN_LSTM_ABSA(_cnn_cfg, vocab_size)
        _cnn_model.load_state_dict(state_dict)
        _cnn_model.eval()
        print("[CNN] Model loaded!", flush=True)
    return _cnn_tok, _cnn_model, _cnn_cfg


def _load_phobert():
    global _pb_tok, _pb_model
    if _pb_model is None:
        print(f"[PhoBERT] Loading from {PHOBERT_REPO}...", flush=True)
        _pb_tok   = AutoTokenizer.from_pretrained(PHOBERT_REPO, token=HF_TOKEN)
        print("[PhoBERT] Tokenizer loaded", flush=True)
        _pb_model = AutoModelForSequenceClassification.from_pretrained(PHOBERT_REPO, token=HF_TOKEN)
        _pb_model.eval()
        print("[PhoBERT] Model loaded!", flush=True)
    return _pb_tok, _pb_model


# ── Predict functions ────────────────────────────────────────────────

def _predict_lr(text):
    vec, models = _load_lr()
    x = vec.transform([preprocess(text)])
    if isinstance(models, dict):
        return {c: int(models[c].predict(x)[0]) for c in CATEGORIES}
    elif isinstance(models, list):
        return {c: int(models[i].predict(x)[0]) for i, c in enumerate(CATEGORIES)}
    return {c: 0 for c in CATEGORIES}

def _predict_phobert(text):
    try:
        tok, model = _load_phobert()
        inputs = tok(preprocess(text), return_tensors="pt", truncation=True, max_length=256, padding=True)
        with torch.no_grad():
            logits = model(**inputs).logits  # shape [1, 18]
        # 18 = 6 categories x 3 classes
        result = {}
        for i, c in enumerate(CATEGORIES):
            cls_logits = logits[0][i*NUM_CLASSES:(i+1)*NUM_CLASSES]
            result[c] = int(torch.argmax(cls_logits).item())
        return result
    except Exception as e:
        print(f"[PhoBERT] ERROR: {e}", flush=True)
        return {c: 0 for c in CATEGORIES}

def _predict_cnn(text):
    try:
        tok, model, cfg = _load_cnn()
        max_len = cfg.get("max_len", 100)
        # Tokenize
        seq = tok.texts_to_sequences([preprocess(text)])
        from torch.nn.functional import pad as F_pad
        import numpy as _np
        x = _np.zeros((1, max_len), dtype=_np.int32)
        s = seq[0][:max_len]
        x[0, :len(s)] = s
        x_t = torch.tensor(x, dtype=torch.long)
        with torch.no_grad():
            out = model(x_t)  # shape [1, num_classes] or [1, 6*3]
        out = out.squeeze(0)
        n_cats = len(CATEGORIES)
        if out.shape[0] == n_cats * 3:
            result = {}
            for i, c in enumerate(CATEGORIES):
                logits = out[i*3:(i+1)*3]
                result[c] = int(torch.argmax(logits).item())
            return result
        elif out.shape[0] == n_cats:
            return {c: int(out[i].round().clamp(0,2).item()) for i, c in enumerate(CATEGORIES)}
        return _predict_lr(text)
    except Exception as e:
        log.warning(f"CNN predict failed: {e}, fallback to LR")
        return _predict_lr(text)


# ── Public API ───────────────────────────────────────────────────────

def predict_single(text, model_type="phobert"):
    return predict_batch([text], model_type)[0]

def predict_batch(texts, model_type="phobert"):
    fn = {
        "logistic":      _predict_lr,
        "phobert":       _predict_phobert,
        "cnn_lstm":      _predict_cnn,
    }.get(model_type, _predict_phobert)
    print(f"[predict_batch] model={model_type}, texts={len(texts)}", flush=True)

    results = []
    for text in texts:
        try:
            results.append(fn(text))
        except Exception as e:
            log.error(f"predict error: {e}")
            results.append({c: 0 for c in CATEGORIES})
    return results


def compute_absa_summary(predictions):
    if not predictions: return {}
    totals = {c: {"pos":0,"neg":0,"total":0} for c in CATEGORIES}
    for pred in predictions:
        for c in CATEGORIES:
            v = pred.get(c, 0)
            if v == 2: totals[c]["pos"] += 1; totals[c]["total"] += 1
            elif v == 1: totals[c]["neg"] += 1; totals[c]["total"] += 1
    summary = {}
    scores  = []
    key_map = {"Room_Facilities":"room","Service_Staff":"staff","Location":"location",
               "Food_Beverage":"food","Price_Value":"price","General":"general"}
    for c in CATEGORIES:
        t   = totals[c]["total"]
        pos = totals[c]["pos"]
        neg = totals[c]["neg"]
        pct = round(pos/t*100) if t > 0 else 0
        k   = key_map[c]
        summary[f"{k}_positive_pct"] = pct
        summary[f"{k}_negative_pct"] = round(neg/t*100) if t > 0 else 0
        summary[f"{k}_total"]        = t
        scores.append(pct)
    summary["overall_score"]  = round(np.mean(scores)) if scores else 0
    summary["total_analyzed"] = len(predictions)
    return summary


def compute_match_score(scores, user_request="", priority_aspects=None):
    if not scores: return 0.0
    aspect_map = {
        "Room_Facilities":"room_positive_pct","Service_Staff":"staff_positive_pct",
        "Location":"location_positive_pct","Food_Beverage":"food_positive_pct",
        "Price_Value":"price_positive_pct","General":"general_positive_pct",
    }
    weights = {c: 1.0 for c in CATEGORIES}
    if priority_aspects:
        for a in priority_aspects:
            if a in weights: weights[a] = 3.0
    ws = tw = 0
    for c, k in aspect_map.items():
        pct = scores.get(k, 0)
        w   = weights.get(c, 1.0)
        ws += pct * w; tw += w
    base = ws / tw if tw > 0 else 0
    import math
    total = scores.get("total_analyzed", 0)
    conf  = min(1.0, math.log(total+1)/math.log(31)) if total > 0 else 0
    return round(base * (0.7 + 0.3*conf), 1)