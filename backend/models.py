# models.py - Pydantic/DB şemaları (MVP'de hafif)

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Kelime modeli
class WordItem(BaseModel):
    id: str = Field(..., description="Kelime benzersiz ID'si")
    text: str = Field(..., description="Estonca kelime")
    ipa: str = Field(..., description="IPA fonetik gösterimi")
    tr: str = Field(..., description="Türkçe çevirisi")
    level: Optional[str] = Field("A1", description="Seviye (A1, A2, B1, vb.)")
    example: Optional[str] = Field(None, description="Örnek cümle")

# Günlük paket yanıtı
class DailyPackResponse(BaseModel):
    level: str = Field(..., description="İstenen seviye")
    items: List[WordItem] = Field(..., description="Kelime listesi")
    count: Optional[int] = Field(None, description="Toplam kelime sayısı")

# Ses yükleme yanıtı
class RecordingResponse(BaseModel):
    recording_path: str = Field(..., description="Kaydedilen dosya yolu")
    word_id: str = Field(..., description="İlgili kelime ID'si")
    file_size: Optional[int] = Field(None, description="Dosya boyutu (bytes)")
    uploaded_at: Optional[datetime] = Field(None, description="Yükleme zamanı")

# Skor hesaplama yanıtı
class PronunciationScoreResponse(BaseModel):
    word: str = Field(..., description="Değerlendirilen kelime")
    target_ipa: str = Field(..., description="Hedef IPA")
    asr_accuracy: float = Field(..., ge=0.0, le=1.0, description="ASR doğruluğu (0-1)")
    phoneme_similarity: float = Field(..., ge=0.0, le=1.0, description="Fonem benzerliği (0-1)")
    prosody: float = Field(..., ge=0.0, le=1.0, description="Prosodi skoru (0-1)")
    final: float = Field(..., ge=0.0, le=1.0, description="Final skor (0-1)")
    feedback: List[str] = Field(..., description="Geri bildirim listesi")

# İlerleme özeti (V1 için)
class ProgressSummaryResponse(BaseModel):
    total_sessions: int = Field(..., description="Toplam oturum sayısı")
    total_words: int = Field(..., description="Pratik yapılan toplam kelime")
    average_score: float = Field(..., ge=0.0, le=1.0, description="Ortalama skor")
    weak_phonemes: List[str] = Field(..., description="Zayıf fonemler")
    streak_days: int = Field(..., description="Aralıksız gün sayısı")
    last_practice: Optional[datetime] = Field(None, description="Son pratik tarihi")

# Hata yanıtı
class ErrorResponse(BaseModel):
    error: str = Field(..., description="Hata mesajı")
    code: str = Field(..., description="Hata kodu")
    details: Optional[dict] = Field(None, description="Ek detaylar")

# ASR skorlama isteği (V1 için, şu anda manuel)
class ScoreRequest(BaseModel):
    word: str = Field(..., description="Kelime")
    target_text: str = Field(..., description="Hedef metin")
    target_ipa: str = Field(..., description="Hedef IPA")
    asr_text: str = Field(..., description="ASR sonucu")
    audio_path: Optional[str] = Field(None, description="Ses dosyası yolu")

# Depolama bilgisi
class StorageInfo(BaseModel):
    uploads_dir: str
    samples_dir: str
    upload_count: int
    sample_count: int
    total_upload_size: int
    total_sample_size: int