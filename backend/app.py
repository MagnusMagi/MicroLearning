from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status
from pydantic import BaseModel
from pathlib import Path
import shutil
import tempfile
import os
from jiwer import wer
from Levenshtein import distance
import whisper
import torch
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import sqlite3
from contextlib import contextmanager

# Authentication
SECRET_KEY = "your-secret-key-here-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
UPLOADS = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "users.db"

UPLOADS.mkdir(parents=True, exist_ok=True)

# Initialize Whisper model
try:
    model = whisper.load_model("base")
    print("Whisper model loaded successfully")
except Exception as e:
    print(f"Failed to load Whisper model: {e}")
    model = None

# Initialize database
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                achievement_type TEXT NOT NULL,
                achievement_name TEXT NOT NULL,
                description TEXT NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, achievement_type)
            )
        """)
        conn.commit()

init_db()

# Database context manager
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

# Authentication models
class User(BaseModel):
    username: str
    email: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Authentication functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(username: str):
    """Get user by username from database"""
    with get_db() as conn:
        cursor = conn.execute("SELECT id, username, email FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            return {"id": row[0], "username": row[1], "email": row[2]}
        return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def check_and_award_achievements(user_id: int, progress_data: dict):
    """Check for new achievements and award them"""
    achievements = []

    # Achievement definitions
    achievement_rules = [
        {
            "type": "first_practice",
            "name": "İlk Adım",
            "description": "İlk kelime pratiğin!",
            "condition": lambda p: p["total_practice"] >= 1
        },
        {
            "type": "perfect_score",
            "name": "Mükemmel",
            "description": "İlk 1.0 skorun!",
            "condition": lambda p: p["best_score"] >= 1.0
        },
        {
            "type": "consistent_learner",
            "name": "Düzenli Öğrenci",
            "description": "10 kelime pratik ettin!",
            "condition": lambda p: p["total_practice"] >= 10
        },
        {
            "type": "improvement",
            "name": "Gelişen",
            "description": "Skorunda iyileşme var!",
            "condition": lambda p: p["improvement_trend"] > 0.1
        },
        {
            "type": "dedicated",
            "name": "Azimli",
            "description": "50 kelime pratik ettin!",
            "condition": lambda p: p["total_practice"] >= 50
        }
    ]

    with get_db() as conn:
        for rule in achievement_rules:
            # Check if achievement already unlocked
            cursor = conn.execute(
                "SELECT id FROM achievements WHERE user_id = ? AND achievement_type = ?",
                (user_id, rule["type"])
            )
            if not cursor.fetchone() and rule["condition"](progress_data):
                # Award achievement
                conn.execute(
                    "INSERT INTO achievements (user_id, achievement_type, achievement_name, description) VALUES (?, ?, ?, ?)",
                    (user_id, rule["type"], rule["name"], rule["description"])
                )
                achievements.append({
                    "name": rule["name"],
                    "description": rule["description"],
                    "type": rule["type"]
                })

        conn.commit()

    return achievements

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

async def get_current_user(token: str = Depends(lambda: None)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(username)
    if user is None:
        raise credentials_exception
    return user

# Authentication endpoints
@app.post("/auth/register", response_model=User)
async def register(user: UserCreate):
    # Check if user already exists
    if get_user(user.username):
        raise HTTPException(status_code=400, detail="Username already registered")

    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM users WHERE email = ?", (user.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash password and create user
        hashed_password = get_password_hash(user.password)
        cursor = conn.execute(
            "INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)",
            (user.username, user.email, hashed_password)
        )
        conn.commit()

        return User(username=user.username, email=user.email)

@app.post("/auth/login", response_model=Token)
async def login(user: UserLogin):
    db_user = authenticate_user(user.username, user.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user["username"]}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@app.get("/auth/me", response_model=User)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return User(username=current_user["username"], email=current_user["email"])

class ScoreOut(BaseModel):
    word: str
    target_ipa: str
    asr_accuracy: float
    phoneme_similarity: float
    prosody: float
    final: float
    feedback: list[str]
    asr_text: str  # Add transcribed text to response

# Expanded word database with levels and categories
WORDS_DATABASE = {
    "A1": {
        "greetings": [
            {"id": "w_tere", "text": "Tere", "ipa": "ˈte.re", "tr": "Merhaba", "category": "greetings"},
            {"id": "w_aitaeh", "text": "Aitäh", "ipa": "ɑi̯ˈtæh", "tr": "Teşekkürler", "category": "greetings"},
            {"id": "w_palun", "text": "Palun", "ipa": "ˈpɑ.lun", "tr": "Lütfen/Rica ederim", "category": "greetings"},
            {"id": "w_hea", "text": "Hea", "ipa": "ˈheɑ", "tr": "İyi", "category": "greetings"},
            {"id": "w_hommik", "text": "Hommik", "ipa": "ˈhomːik", "tr": "Sabah", "category": "greetings"},
        ],
        "basic": [
            {"id": "w_jah", "text": "Jah", "ipa": "jɑh", "tr": "Evet", "category": "basic"},
            {"id": "w_ei", "text": "Ei", "ipa": "ei̯", "tr": "Hayır", "category": "basic"},
            {"id": "w_mina", "text": "Mina", "ipa": "ˈmi.nɑ", "tr": "Ben", "category": "basic"},
            {"id": "w_sina", "text": "Sina", "ipa": "ˈsi.nɑ", "tr": "Sen", "category": "basic"},
            {"id": "w_tema", "text": "Tema", "ipa": "ˈte.mɑ", "tr": "O", "category": "basic"},
        ],
        "food": [
            {"id": "w_leib", "text": "Leib", "ipa": "lei̯p", "tr": "Ekmek", "category": "food"},
            {"id": "w_piim", "text": "Piim", "ipa": "ˈpiːm", "tr": "Süt", "category": "food"},
            {"id": "w_vesi", "text": "Vesi", "ipa": "ˈve.si", "tr": "Su", "category": "food"},
            {"id": "w_kala", "text": "Kala", "ipa": "ˈkɑ.lɑ", "tr": "Balık", "category": "food"},
        ]
    },
    "A2": {
        "family": [
            {"id": "w_ema", "text": "Ema", "ipa": "ˈe.mɑ", "tr": "Anne", "category": "family"},
            {"id": "w_isa", "text": "Isa", "ipa": "ˈi.sɑ", "tr": "Baba", "category": "family"},
            {"id": "w_vennad", "text": "Vennad", "ipa": "ˈvenːɑd", "tr": "Kardeşler", "category": "family"},
            {"id": "w_onu", "text": "Onu", "ipa": "ˈo.nu", "tr": "Yeğen", "category": "family"},
        ],
        "time": [
            {"id": "w_tund", "text": "Tund", "ipa": "tun̪t", "tr": "Saat", "category": "time"},
            {"id": "w_paev", "text": "Päev", "ipa": "ˈpæi̯v", "tr": "Gün", "category": "time"},
            {"id": "w_nadal", "text": "Nädala", "ipa": "ˈnæ.dɑ.lɑ", "tr": "Hafta", "category": "time"},
            {"id": "w_kuu", "text": "Kuu", "ipa": "ˈkuː", "tr": "Ay", "category": "time"},
        ]
    },
    "B1": {
        "emotions": [
            {"id": "w_rõõm", "text": "Rõõm", "ipa": "ˈrɤːm", "tr": "Mutluluk", "category": "emotions"},
            {"id": "w_kurb", "text": "Kurb", "ipa": "kurp", "tr": "Üzüntü", "category": "emotions"},
            {"id": "w_armastus", "text": "Armastus", "ipa": "ˈɑr.mɑ.stus", "tr": "Aşk", "category": "emotions"},
        ],
        "nature": [
            {"id": "w_meri", "text": "Meri", "ipa": "ˈme.ri", "tr": "Deniz", "category": "nature"},
            {"id": "w_mets", "text": "Mets", "ipa": "mets", "tr": "Orman", "category": "nature"},
            {"id": "w_lill", "text": "Lill", "ipa": "lil̪ː", "tr": "Çiçek", "category": "nature"},
        ]
    }
}

# Flatten words for backward compatibility
WORDS = []
for level, categories in WORDS_DATABASE.items():
    for category, word_list in categories.items():
        WORDS.extend(word_list)

@app.get("/daily-pack")
async def get_daily_pack(limit: int = 3, level: str = "A1", category: str = None):
    """Get a daily pack of words for practice"""
    if level not in WORDS_DATABASE:
        raise HTTPException(status_code=400, detail=f"Level {level} not found")

    available_words = []
    if category:
        # Filter by specific category
        if category in WORDS_DATABASE[level]:
            available_words = WORDS_DATABASE[level][category]
        else:
            raise HTTPException(status_code=400, detail=f"Category {category} not found in level {level}")
    else:
        # Get all words from the level
        for cat_words in WORDS_DATABASE[level].values():
            available_words.extend(cat_words)

    # Shuffle and limit
    import random
    random.shuffle(available_words)
    selected_words = available_words[:limit]

    return {
        "level": level,
        "category": category,
        "items": selected_words,
        "total_available": len(available_words)
    }

@app.get("/word-categories")
async def get_word_categories():
    """Get available word categories by level"""
    categories = {}
    for level, level_categories in WORDS_DATABASE.items():
        categories[level] = list(level_categories.keys())
    return categories

@app.get("/progress/summary")
async def get_progress_summary(current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        # Get recent progress
        cursor = conn.execute("""
            SELECT word_id, score, created_at
            FROM user_progress
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 20
        """, (current_user["id"],))
        progress = cursor.fetchall()

        # Calculate statistics
        if progress:
            scores = [row[1] for row in progress]
            avg_score = round(sum(scores) / len(scores), 2)
            best_score = max(scores)
            total_practice = len(progress)

            # Group by word
            word_stats = {}
            for row in progress:
                word_id = row[0]
                score = row[1]
                if word_id not in word_stats:
                    word_stats[word_id] = []
                word_stats[word_id].append(score)

            # Calculate improvement trends
            recent_scores = scores[:5]  # Last 5 attempts
            older_scores = scores[5:10] if len(scores) > 5 else []
            improvement = 0
            if older_scores and recent_scores:
                old_avg = sum(older_scores) / len(older_scores)
                new_avg = sum(recent_scores) / len(recent_scores)
                improvement = round(new_avg - old_avg, 2)

            # Calculate streak (consecutive days with practice)
            cursor = conn.execute("""
                SELECT DATE(created_at) as practice_date, COUNT(*) as daily_count
                FROM user_progress
                WHERE user_id = ?
                GROUP BY DATE(created_at)
                ORDER BY practice_date DESC
                LIMIT 30
            """, (current_user["id"],))
            daily_practice = cursor.fetchall()

            streak = 0
            if daily_practice:
                from datetime import datetime, timedelta
                today = datetime.now().date()
                yesterday = today - timedelta(days=1)

                # Check if practiced today or yesterday
                today_practiced = any(row[0] == str(today) for row in daily_practice)
                yesterday_practiced = any(row[0] == str(yesterday) for row in daily_practice)

                if today_practiced or yesterday_practiced:
                    # Calculate streak
                    current_date = today if today_practiced else yesterday
                    while any(row[0] == str(current_date) for row in daily_practice):
                        streak += 1
                        current_date -= timedelta(days=1)

            progress_data = {
                "total_practice": total_practice,
                "average_score": avg_score,
                "best_score": best_score,
                "improvement_trend": improvement,
                "current_streak": streak,
                "recent_progress": [
                    {
                        "word": row[0].replace("word_", ""),
                        "score": row[1],
                        "date": row[2]
                    } for row in progress[:10]
                ],
                "word_breakdown": {
                    word: {
                        "attempts": len(scores),
                        "best_score": max(scores),
                        "average_score": round(sum(scores) / len(scores), 2)
                    }
                    for word, scores in word_stats.items()
                }
            }

            # Check for new achievements
            new_achievements = check_and_award_achievements(current_user["id"], progress_data)

            # Get all achievements
            cursor = conn.execute("""
                SELECT achievement_name, description, unlocked_at
                FROM achievements
                WHERE user_id = ?
                ORDER BY unlocked_at DESC
            """, (current_user["id"],))
            all_achievements = cursor.fetchall()

            progress_data["achievements"] = [
                {
                    "name": row[0],
                    "description": row[1],
                    "unlocked_at": row[2]
                } for row in all_achievements
            ]
            progress_data["new_achievements"] = new_achievements

            return progress_data
        else:
            return {
                "total_practice": 0,
                "average_score": 0,
                "best_score": 0,
                "improvement_trend": 0,
                "current_streak": 0,
                "recent_progress": [],
                "word_breakdown": {},
                "achievements": [],
                "new_achievements": []
            }

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

def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio file using Whisper"""
    if model is None:
        raise HTTPException(status_code=500, detail="ASR model not available")

    try:
        # Load and transcribe audio
        result = model.transcribe(audio_path, language="et")  # Estonian language
        return result["text"].strip()
    except Exception as e:
        print(f"ASR Error: {e}")
        raise HTTPException(status_code=500, detail=f"ASR processing failed: {str(e)}")

@app.post("/pronunciation/score", response_model=ScoreOut)
async def score(
    word: str,
    target_text: str,
    target_ipa: str,
    asr_text: str = None,
    audio_file: UploadFile = File(None),
    current_user: dict = Depends(get_current_user)
):
    # If audio file is provided, use ASR to get text
    if audio_file is not None:
        # Save uploaded audio temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            shutil.copyfileobj(audio_file.file, temp_file)
            temp_path = temp_file.name

        try:
            # Transcribe audio
            asr_text = transcribe_audio(temp_path)
            print(f"ASR Result: '{asr_text}'")
        finally:
            # Clean up temp file
            os.unlink(temp_path)
    elif asr_text is None:
        raise HTTPException(status_code=400, detail="Either asr_text or audio_file must be provided")

    # Calculate scores
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

    # Save progress to database
    with get_db() as conn:
        conn.execute(
            "INSERT INTO user_progress (user_id, word_id, score, asr_text) VALUES (?, ?, ?, ?)",
            (current_user["id"], f"word_{word.lower()}", final, asr_text)
        )
        conn.commit()

    return ScoreOut(
        word=word,
        target_ipa=target_ipa,
        asr_accuracy=round(asr_acc, 2),
        phoneme_similarity=round(phon_sim, 2),
        prosody=round(prosody, 2),
        final=final,
        feedback=feedback or ["Harika ilerleme!"],
        asr_text=asr_text  # Include the transcribed text in response
    )