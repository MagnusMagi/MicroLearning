from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from pathlib import Path
import shutil
from jiwer import wer
from Levenshtein import distance

app = FastAPI()
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
UPLOADS = DATA_DIR / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)

class ScoreOut(BaseModel):
    word: str
    target_ipa: str
    asr_accuracy: float
    phoneme_similarity: float
    prosody: float
    final: float
    feedback: list[str]

# Basit mock: günlük paket
WORDS = [
    {"id": "w_tere", "text": "Tere", "ipa": "ˈte.re", "tr": "Merhaba"},
    {"id": "w_aitaeh", "text": "Aitäh", "ipa": "ɑi̯ˈtæh", "tr": "Teşekkürler"},
    {"id": "w_palun", "text": "Palun", "ipa": "ˈpɑ.lun", "tr": "Lütfen/Rica ederim"},
]

@app.get("/daily-pack")
def daily_pack(limit: int = 10, level: str = "A1"):
    return {"level": level, "items": WORDS[:limit]}

@app.post("/recordings")
async def upload_recording(word_id: str = Form(...), file: UploadFile = File(...)):
    dest = UPLOADS / f"{word_id}_{file.filename}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"recording_path": str(dest)}


def simple_phoneme_similarity(target: str, hypothesis: str) -> float:
    t, h = target.lower(), hypothesis.lower()
    d = distance(t, h)
    return max(0.0, 1.0 - d / max(1, len(t)))

@app.post("/pronunciation/score", response_model=ScoreOut)
def score(word: str, target_text: str, target_ipa: str, asr_text: str):
    asr_acc = max(0.0, 1.0 - wer([target_text], [asr_text]))  # 0..1
    phon_sim = simple_phoneme_similarity(target_text, asr_text)  # 0..1
    prosody  = 0.7  # MVP: sabit
    final = round(0.4*asr_acc + 0.4*phon_sim + 0.2*prosody, 2)

    feedback = []
    if phon_sim < 0.8:
        feedback.append("Fonem farklılıkları var; ilk heceyi netleştir.")
    if asr_acc < 0.85:
        feedback.append("Kelimenin tamamını daha net telaffuz et.")
    if prosody < 0.8:
        feedback.append("Vurguyu ilk hecede tut ve temposunu sabit tut.")

    return ScoreOut(
        word=word,
        target_ipa=target_ipa,
        asr_accuracy=round(asr_acc, 2),
        phoneme_similarity=round(phon_sim, 2),
        prosody=round(prosody, 2),
        final=final,
        feedback=feedback or ["Harika ilerleme!"]
    )