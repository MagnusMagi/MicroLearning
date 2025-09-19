# Estonian Pronunciation Learning App

Estonca odaklı Dil Öğrenme Back‑end + Streamlit ön yüz tek makinede (localhost) çalışır. FastAPI (8000) API'yi sunar; Streamlit (8501) UI'de günlük kelime paketi, ses yükleme, telaffuz skoru ve geri bildirim gösterir. MVP basit, genişlemeye açık ve tamamen offline akışa uygundur.

## Mimari (Localhost)
- **Backend**: FastAPI, uçlar: /daily-pack, /recordings, /pronunciation/score, /progress/summary.
- **Frontend**: Streamlit, kelime listesi, ses yükleme, skor ve geri bildirim.
- **Depolama**: SQLite ve data/ klasörü (ses dosyaları, örnekler).
- **ASR (MVP)**: Metin tabanlı simülasyon (kullanıcı ASR sonucunu elle girer). Sonraki adımda Whisper/Vosk entegre edilecek.
- **Portlar**: API → http://localhost:8000, UI → http://localhost:8501.

Akış: GET /daily-pack → kullanıcı sesini yükler → POST /pronunciation/score → skor + geri bildirim → ilerleme özetleri.

## Teknoloji Seçimleri (Metin)
- **API/Framework**: FastAPI (async I/O, otomatik OpenAPI), Uvicorn (dev), opsiyonel Gunicorn (prod).
- **Kimlik/Yetki (V1+)**: JWT access/refresh, RBAC (user/admin), HMAC imzalı webhook.
- **ASR**: MVP'de simülasyon; V1'de Whisper (tiny/base/small). Alternatif: Vosk (tamamı offline).
- **Fonem/Prosodi**: Espeak‑NG (Estonca modu) + hafif hizalama; librosa, numpy, scipy ile tempo/süre.
- **Veritabanı**: SQLite (MVP), V1'de PostgreSQL + SQLAlchemy + Alembic.
- **Dosya Depolama**: data/uploads/ (MVP); V1'de MinIO/S3 + CDN.
- **Önbellek/Kuyruk (V1+)**: Redis + Celery (transcribe/skor işlemleri için background task).
- **Gözlemlenebilirlik**: logging + (V1) Prometheus/Grafana, OpenTelemetry.

## Klasör Yapısı

```
estonian-pronunciation/
├─ backend/
│  ├─ app.py                  # FastAPI ana dosyası
│  ├─ service_scoring.py      # ASR, fonem, prosodi skor mantığı (MVP basit)
│  ├─ storage.py              # dosya kayıt/yol yönetimi
│  ├─ models.py               # Pydantic/DB şemaları (MVP'de hafif)
│  ├─ requirements.txt
│  └─ db.sqlite3              # SQLite (otomatik oluşur)
├─ frontend/
│  ├─ app.py                  # Streamlit UI
│  └─ requirements.txt
├─ data/
│  ├─ uploads/                # kullanıcı sesleri
│  └─ samples/                # örnek sesler
└─ README.md
```

## Kurulum (Adım Adım)

### 1. Sanal Ortam
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Bağımlılıklar

#### Backend
```bash
pip install fastapi uvicorn pydantic librosa numpy soundfile python-multipart jiwer python-Levenshtein
```

#### Frontend
```bash
pip install streamlit requests
```

### 3. Backend'i başlat
```bash
cd backend
uvicorn app:app --reload --port 8000
# Swagger: http://localhost:8000/docs
```

### 4. Frontend'i başlat
```bash
cd ../frontend
streamlit run app.py --server.port 8501
# UI: http://localhost:8501
```

## API Tasarımı (MVP)

### Uçlar
- `GET /daily-pack?level=A1&limit=10` → Günün kelimeleri.
- `POST /recordings` (multipart: file, form: word_id) → dosyayı data/uploads/ içine kaydeder.
- `POST /pronunciation/score` (query/body: word, target_text, target_ipa, asr_text) → skor ve geri bildirim döner.
- `GET /progress/summary` (V1) → haftalık performans ve zayıf fonemler.

### Örnek Yanıt (score)
```json
{
  "word": "Tere",
  "target_ipa": "ˈte.re",
  "asr_accuracy": 0.87,
  "phoneme_similarity": 0.79,
  "prosody": 0.72,
  "final": 0.80,
  "feedback": [
    "'r' titreşimi kısa — dil ucunu üst diş etlerine yakın titreştir.",
    "İlk hece uzat: ˈte.re (vurgu ilk hecede)."
  ]
}
```

## Skorlama Mantığı (MVP)
- **Final** = 0.4*ASR + 0.4*PhonemeSim + 0.2*Prosody.
- **ASR doğruluğu**: wer(target_text, asr_text) → 1 − WER.
- **Fonem benzerliği**: Levenshtein benzeri uzaklık → 1 − (d/len).
- **Prosodi**: MVP'de sabit/heuristic; V1'de hece süreleri, vurgu ve tempo sapmaları (DTW benzeri ölçüm).

## Estonca İçerik (A1 örneği)
- **Tere** (merhaba) — IPA: ˈte.re — Cümle: "Tere! Kuidas läheb?"
- **Aitäh** (teşekkürler) — IPA: ɑi̯ˈtæh — Cümle: "Aitäh abi eest."
- **Palun** (lütfen/rica ederim) — IPA: ˈpɑ.lun — Cümle: "Palun, tulge siia."
- **Jah / Ei** (evet/hayır) — IPA: jɑh / ei̯ — Cümle: "Jah, olen valmis."

## Çalıştırma ve Test
1. Backend'i 8000'de başlat. http://localhost:8000/docs üzerinden uçları doğrula.
2. Frontend'i 8501'de başlat. "Günlük Paketi Getir" ile kayıtları aç.
3. Bir kelime için ses dosyası yükle. MVP'de "ASR metni"ni elle gir ve Skorla.
4. Final skor, alt metrikler ve geri bildirimleri Streamlit'te gör.

## Geliştirme Yol Haritası
- **ASR Entegrasyonu**: Whisper (tiny/base) ekle; asr_text backend'de üret.
- **Fonem Hizalama**: Espeak‑NG + hafif aligner, IPA tabanlı hata tespiti.
- **Prosodi**: Hece süreleri, vurgu, tempo ölçümü; DTW tabanlı sapma skoru.
- **Kullanıcı/İlerleme**: JWT auth, /progress/summary, streak/rozet motoru.
- **Depolama**: SQLite → PostgreSQL; dosya sistemi → MinIO/S3; CDN.
- **Arka Plan İşleri**: Celery + Redis ile transcribe/score işlerini kuyrukla.
- **Gözlemlenebilirlik**: Prometheus metrikleri, OpenTelemetry tracing.

## SSS (Kısa)
- **Gerçek ASR yok mu?** MVP'de akış onayı için manuel; V1'de Whisper eklenir.
- **Tarayıcıdan kayıt mümkün mü?** Evet, Streamlit‑WebRTC ile eklenebilir.
- **Günlük paket sabit mi?** Başlangıçta 10; performansa göre dinamik yapılabilir.# MicroLearning
