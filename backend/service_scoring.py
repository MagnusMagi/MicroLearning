# service_scoring.py - ASR, fonem, prosodi skor mantığı (MVP basit)

from jiwer import wer
from Levenshtein import distance
import numpy as np

def calculate_asr_accuracy(target_text: str, asr_text: str) -> float:
    """ASR doğruluğunu hesapla (1 - WER)"""
    try:
        word_error_rate = wer([target_text], [asr_text])
        return max(0.0, 1.0 - word_error_rate)
    except:
        return 0.0

def calculate_phoneme_similarity(target: str, hypothesis: str) -> float:
    """Fonem benzerliğini Levenshtein uzaklığı ile hesapla"""
    t, h = target.lower(), hypothesis.lower()
    d = distance(t, h)
    return max(0.0, 1.0 - d / max(1, len(t)))

def calculate_prosody_score(target_ipa: str, asr_text: str) -> float:
    """MVP için basit prosodi skoru - V1'de gelişmiş olacak"""
    # MVP: sabit skor, ancak ASR doğruluğuna göre hafif ayar
    base_score = 0.7
    asr_acc = calculate_asr_accuracy(target_ipa, asr_text)

    # ASR iyi ise prosodi skorunu artır
    if asr_acc > 0.8:
        return min(0.9, base_score + 0.1)
    elif asr_acc < 0.6:
        return max(0.5, base_score - 0.1)
    else:
        return base_score

def calculate_final_score(asr_accuracy: float, phoneme_similarity: float, prosody: float) -> float:
    """Final skoru hesapla: 0.4*ASR + 0.4*PhonemeSim + 0.2*Prosody"""
    return round(0.4 * asr_accuracy + 0.4 * phoneme_similarity + 0.2 * prosody, 2)

def generate_feedback(word: str, target_ipa: str, asr_accuracy: float, phoneme_similarity: float, prosody: float) -> list[str]:
    """Telaffuz geri bildirimi üret"""
    feedback = []

    if phoneme_similarity < 0.8:
        feedback.append("Fonem farklılıkları var; ilk heceyi netleştir.")

    if asr_accuracy < 0.85:
        feedback.append("Kelimenin tamamını daha net telaffuz et.")

    if prosody < 0.8:
        feedback.append("Vurguyu ilk hecede tut ve temposunu sabit tut.")

    # Özel kelimeye göre geri bildirim
    if word.lower() == "tere":
        if phoneme_similarity < 0.9:
            feedback.append("'r' titreşimi kısa — dil ucunu üst diş etlerine yakın titreştir.")
        feedback.append("İlk hece uzat: ˈte.re (vurgu ilk hecede).")

    elif word.lower() == "aitäh":
        if phoneme_similarity < 0.9:
            feedback.append("'ä' sesi Türkçe 'e' gibi değil, daha açık ve kısa.")
        feedback.append("İkinci hece vurgulu: ɑi̯ˈtæh")

    elif word.lower() == "palun":
        feedback.append("Her iki hece eşit uzunlukta: ˈpɑ.lun")

    if not feedback:
        feedback.append("Harika ilerleme!")

    return feedback