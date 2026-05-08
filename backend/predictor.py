"""
predictor.py — Inference pipeline dùng HuggingFace Inference API
Không load model local, gọi qua API để tiết kiệm RAM.
"""

import os
import json
import time
import logging
import requests
import numpy as np
from underthesea import word_tokenize

log = logging.getLogger(__name__)

CATEGORIES = [
    "Room_Facilities",
    "Service_Staff",
    "Location",
    "Food_Beverage",
    "Price_Value",
    "General",
]
NUM_CLASSES    = 3
SENTIMENT_VALS = ["None", "Negative", "Positive"]

HF_TOKEN  = os.environ.get("HF_TOKEN", "")
HF_API    = "https://api-inference.huggingface.co/models"

LR_REPO      = os.environ.get("LR_HUB",      "quangdao232/lr-hotel-absa")
RF_REPO      = os.environ.get("RF_HUB",      "quangdao232/rf-hotel-absa")
CNN_REPO     = os.environ.get("CNN_HUB",     "quangdao232/cnn-lstm-hotel-absa")
PHOBERT_REPO = os.environ.get("PHOBERT_HUB", "quangdao232/phobert-hotel-absa")
LLAMA_REPO   = os.environ.get("LLAMA_HUB",   "quangdao232/llama-hotel-absa")

REPO_MAP = {
    "logistic":      LR_REPO,
    "random_forest": RF_REPO,
    "cnn_lstm":      CNN_REPO,
    "phobert":       PHOBERT_REPO,
    "llama":         LLAMA_REPO,
}


def _hf_headers():
    h = {"Content-Type": "application/json"}
    if HF_TOKEN:
        h["Authorization"] = f"Bearer {HF_TOKEN}"
    return h


def _call_inference_api(repo_id: str, inputs, retries: int = 3) -> list:
    url     = f"{HF_API}/{repo_id}"
    payload = {"inputs": inputs, "options": {"wait_for_model": True}}
    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=_hf_headers(), json=payload, timeout=120)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 503:
                wait = int(resp.headers.get("X-Compute-Time", 20))
                log.warning(f"Model warming up, waiting {min(wait,30)}s...")
                time.sleep(min(wait, 30))
            elif resp.status_code == 429:
                log.warning("Rate limited, waiting 60s...")
                time.sleep(60)
            else:
                log.error(f"HF API {resp.status_code}: {resp.text[:200]}")
                break
        except Exception as e:
            log.error(f"API call error: {e}")
            if attempt < retries - 1:
                time.sleep(5)
    return []


def _parse_output(output) -> dict:
    result = {cat: 0 for cat in CATEGORIES}
    if not output:
        return result
    preds = output[0] if isinstance(output[0], list) else output
    for pred in preds:
        label = pred.get("label", "")
        score = pred.get("score", 0)
        if score < 0.5:
            continue
        parts = label.replace("LABEL_", "").split("_")
        if len(parts) >= 2:
            try:
                cat_idx  = int(parts[0])
                sent_idx = int(parts[1])
                if 0 <= cat_idx < len(CATEGORIES) and sent_idx in [1, 2]:
                    result[CATEGORIES[cat_idx]] = sent_idx
            except ValueError:
                pass
        elif len(parts) == 1:
            try:
                flat_idx = int(parts[0])
                cat_idx  = flat_idx // NUM_CLASSES
                sent_idx = flat_idx % NUM_CLASSES
                if 0 <= cat_idx < len(CATEGORIES):
                    result[CATEGORIES[cat_idx]] = sent_idx
            except ValueError:
                pass
    return result


def preprocess(text: str) -> str:
    try:
        return " ".join(word_tokenize(text, format="text").split())
    except Exception:
        return text


def predict_single(text: str, model_type: str = "phobert") -> dict:
    return predict_batch([text], model_type)[0]


def predict_batch(texts: list, model_type: str = "phobert") -> list:
    if not texts:
        return []
    repo_id   = REPO_MAP.get(model_type, PHOBERT_REPO)
    processed = [preprocess(t) for t in texts]
    results   = []
    for text in processed:
        try:
            output = _call_inference_api(repo_id, text)
            pred   = _parse_output(output)
        except Exception as e:
            log.error(f"predict error: {e}")
            pred = {cat: 0 for cat in CATEGORIES}
        results.append(pred)
    return results


def compute_absa_summary(predictions: list) -> dict:
    if not predictions:
        return {}
    totals = {cat: {"pos": 0, "neg": 0, "total": 0} for cat in CATEGORIES}
    for pred in predictions:
        for cat in CATEGORIES:
            val = pred.get(cat, 0)
            if val == 2:
                totals[cat]["pos"]   += 1
                totals[cat]["total"] += 1
            elif val == 1:
                totals[cat]["neg"]   += 1
                totals[cat]["total"] += 1
    summary      = {}
    overall_list = []
    for cat in CATEGORIES:
        t   = totals[cat]["total"]
        pos = totals[cat]["pos"]
        neg = totals[cat]["neg"]
        pct = round(pos / t * 100) if t > 0 else 0
        key = cat.lower().replace("_facilities", "").replace("_staff", "").replace("_beverage", "").replace("_value", "")
        summary[f"{cat.lower().split('_')[0]}_positive_pct"] = pct
        summary[f"{cat.lower().split('_')[0]}_negative_pct"] = round(neg / t * 100) if t > 0 else 0
        summary[f"{cat.lower().split('_')[0]}_total"]        = t
        overall_list.append(pct)
    summary["overall_score"]  = round(np.mean(overall_list)) if overall_list else 0
    summary["total_analyzed"] = len(predictions)
    return summary


def compute_match_score(scores: dict, user_request: str = "", priority_aspects: list = None) -> float:
    if not scores:
        return 0.0
    aspect_map = {
        "Room_Facilities": "room_positive_pct",
        "Service_Staff":   "staff_positive_pct",
        "Location":        "location_positive_pct",
        "Food_Beverage":   "food_positive_pct",
        "Price_Value":     "price_positive_pct",
        "General":         "general_positive_pct",
    }
    weights = {cat: 1.0 for cat in CATEGORIES}
    if priority_aspects:
        for asp in priority_aspects:
            if asp in weights:
                weights[asp] = 3.0
    total_weight = 0.0
    weighted_sum = 0.0
    for cat, key in aspect_map.items():
        pct = scores.get(key, 0)
        w   = weights.get(cat, 1.0)
        weighted_sum += pct * w
        total_weight += w
    base_score = weighted_sum / total_weight if total_weight > 0 else 0
    import math
    total      = scores.get("total_analyzed", 0)
    confidence = min(1.0, math.log(total + 1) / math.log(31)) if total > 0 else 0
    return round(base_score * (0.7 + 0.3 * confidence), 1)