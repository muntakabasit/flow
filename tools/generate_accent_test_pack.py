# /Users/kulturestudios/BelawuOS/flow/tools/generate_accent_test_pack.py

from __future__ import annotations

import csv
import json
from pathlib import Path

OUT_DIR = Path("/Users/kulturestudios/BelawuOS/flow/accent_test_pack")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_PHRASES = [
    "I think this will work.",
    "Do you know where the station is?",
    "Please tell them I will come tomorrow.",
    "Can you help me with this problem?",
    "I need to go to the hospital today.",
    "What are you doing there?",
    "I will call them later.",
    "Where did you put the money?",
    "Do you want to go with me?",
    "Please tell the driver to stop.",
    "I am trying to figure out how this works.",
    "Have you had anything to eat today?",
    "What have you been doing this week?",
    "Please, I really need your help.",
    "I cannot come to work today.",
    "How much does this cost?",
    "Can you speak a little slower?",
    "I haven't eaten anything yet.",
    "Do you know where the hospital is?",
    "Where are you going today?",
]

def mutate_th_stopping(text: str) -> str:
    replacements = {
        "the ": "de ",
        "The ": "De ",
        "this": "dis",
        "This": "Dis",
        "that": "dat",
        "That": "Dat",
        "them": "dem",
        "Them": "Dem",
        "think": "tink",
        "Think": "Tink",
        "three": "tree",
        "Three": "Tree",
        "there": "dere",
        "There": "Dere",
        "with": "wit",
        "With": "Wit",
    }
    out = text
    for old, new in replacements.items():
        out = out.replace(old, new)
    return out

def mutate_cluster_reduction(text: str) -> str:
    replacements = {
        "asked": "ask",
        "helped": "help",
        "worked": "work",
        "found": "foun",
        "first": "firs",
        "next": "nex",
    }
    out = text
    for old, new in replacements.items():
        out = out.replace(old, new).replace(old.capitalize(), new.capitalize())
    return out

def mutate_vowel_shift(text: str) -> str:
    replacements = {
        "live": "leave",
        "Live": "Leave",
        "sit": "seat",
        "Sit": "Seat",
        "been": "bean",
        "Been": "Bean",
    }
    out = text
    for old, new in replacements.items():
        out = out.replace(old, new)
    return out

def mutate_global_english_casual(text: str) -> str:
    replacements = {
        "going to": "gonna",
        "want to": "wanna",
        "cannot": "can't",
        "I am": "I'm",
        "I will": "I'll",
        "do not": "don't",
    }
    out = text
    for old, new in replacements.items():
        out = out.replace(old, new)
    return out

def build_variants(text: str) -> dict[str, str]:
    return {
        "base": text,
        "th_stopping": mutate_th_stopping(text),
        "cluster_reduction": mutate_cluster_reduction(text),
        "vowel_shift": mutate_vowel_shift(text),
        "casual_global_english": mutate_global_english_casual(text),
        "combined_light": mutate_global_english_casual(mutate_th_stopping(text)),
    }

def main() -> None:
    rows = []
    json_rows = []

    for idx, phrase in enumerate(BASE_PHRASES, start=1):
        variants = build_variants(phrase)
        for variant_name, variant_text in variants.items():
            clip_id = f"en_accent_{idx:02d}_{variant_name}"
            row = {
                "clip_id": clip_id,
                "family": "english_accent_stress",
                "variant": variant_name,
                "expected_text": phrase,
                "spoken_text": variant_text,
                "notes": "",
            }
            rows.append(row)
            json_rows.append(row)

    csv_path = OUT_DIR / "accent_test_pack.csv"
    json_path = OUT_DIR / "accent_test_pack.json"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["clip_id", "family", "variant", "expected_text", "spoken_text", "notes"],
        )
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(json_rows, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(rows)} test rows to:")
    print(csv_path)
    print(json_path)

if __name__ == "__main__":
    main()