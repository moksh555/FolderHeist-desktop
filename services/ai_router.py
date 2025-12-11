import os, re, csv
from typing import Dict, List, Tuple

try:
    from google import genai
except Exception:
    genai = None

def load_folder_catalog(csv_path: str) -> tuple[dict, dict, list]:
    label_to_id, label_desc, allowed = {}, {}, []
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        assert "label" in r.fieldnames and "folder_id" in r.fieldnames, "CSV headers must include label, folder_id"
        for row in r:
            lab = (row.get("label") or "").strip()
            if not lab: continue
            allowed.append(lab)
            fid = (row.get("folder_id") or "").strip()
            if fid: label_to_id[lab] = fid
            desc = (row.get("description") or "").strip()
            if desc: label_desc[lab] = desc
    if not allowed:
        raise RuntimeError("Folder catalog is empty.")
    return label_to_id, label_desc, allowed

_KEYWORD_MAP = [
    (re.compile(r"\b(invoice|receipt|bill|total|amount)\b", re.I), "Invoices"),
    (re.compile(r"\b(transcript|grade|gpa|assignment|lor)\b", re.I), "Academics"),
    (re.compile(r"\b(passport|driver.?s?\s*license|dl|national\s*id)\b", re.I), "IDs"),
    (re.compile(r"\b(w2|1099|tax|form\s*16)\b", re.I), "Tax Docs"),
    (re.compile(r"\b(photo|image|jpg|png|jpeg)\b", re.I), "Photos"),
    (re.compile(r"\b(offer|employment|hr)\b", re.I), "Offers & Letters"),
    (re.compile(r"\b(medical|prescription|lab|report)\b", re.I), "Healthcare"),
    (re.compile(r"\b(resume|portfolio|project|spec|doc)\b", re.I), "Work"),
]

def _heuristic_label(filename: str, text: str, allowed: List[str]) -> tuple[str, float, str]:
    hay = f"{filename}\n{text}".lower()
    for rx, label in _KEYWORD_MAP:
        if label in allowed and rx.search(hay):
            return label, 0.95, f"Matched {label} keywords"
    fallback = "Misc" if "Misc" in allowed else next(iter(allowed), None)
    return (fallback or ""), 0.4, "Fallback (no keyword match)"


def choose_folder_with_gemini(
    filename: str,
    text: str,
    allowed_labels: List[str],
    label_desc: Dict[str, str],
    temperature: float = 0.15,
) -> dict:
    if not allowed_labels:
        return {"label": "", "confidence": 0.0, "rationale": "No allowed labels configured"}
    api_key = os.getenv("GEMINI_API_KEY")
    if genai is None or not api_key:
        lab, conf, why = _heuristic_label(filename, text, allowed_labels)
        return {"label": lab, "confidence": conf, "rationale": why}

    client = genai.Client(api_key=api_key)

    labels_block = "\n".join(
        f"- {lab}: {label_desc.get(lab, '')}" if label_desc.get(lab) else f"- {lab}"
        for lab in allowed_labels
    )
    body = (text or "")[:20000]
    system = "You are a filing agent. Choose exactly ONE label from the allowed list. Respond ONLY with JSON."
    schema = {
        "type": "OBJECT",
        "properties": {
            "label": {"type": "STRING", "enum": allowed_labels},
            "confidence": {"type": "NUMBER"},
            "rationale": {"type": "STRING"},
        },
        "required": ["label", "confidence", "rationale"],
    }
    prompt = f"""Allowed labels:
{labels_block}

Filename: {filename}
Body (first 20k chars):
{body}
"""
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[system, prompt],
            config={"temperature": temperature,
                    "response_mime_type": "application/json",
                    "response_schema": schema},
        )
        parsed = getattr(resp, "parsed", None) or {}
        lab = parsed.get("label")
        conf = float(parsed.get("confidence", 0.0) or 0.0)
        why = parsed.get("rationale", "")
        if lab not in allowed_labels:
            lab, conf, why = _heuristic_label(filename, text, allowed_labels)
        return {"label": lab, "confidence": conf, "rationale": why}
    except Exception as e:
        lab, conf, why = _heuristic_label(filename, text, allowed_labels)
        return {"label": lab, "confidence": conf, "rationale": f"Heuristic fallback ({e})"}
