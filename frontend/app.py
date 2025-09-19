import streamlit as st
import requests
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av
import numpy as np
import queue
from typing import List, Optional
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

API = "http://localhost:8001"

# Session state for authentication
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user' not in st.session_state:
    st.session_state.user = None

# Authentication functions
def login(username, password):
    try:
        response = requests.post(f"{API}/auth/login", json={"username": username, "password": password})
        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data["access_token"]
            # Get user info
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            user_response = requests.get(f"{API}/auth/me", headers=headers)
            if user_response.status_code == 200:
                st.session_state.user = user_response.json()
            return True
        else:
            st.error("Login failed")
            return False
    except Exception as e:
        st.error(f"Login error: {e}")
        return False

def register(username, email, password):
    try:
        response = requests.post(f"{API}/auth/register", json={
            "username": username,
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            st.success("Registration successful! Please login.")
            return True
        else:
            st.error(f"Registration failed: {response.json().get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        st.error(f"Registration error: {e}")
        return False

def logout():
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.pack = None

def get_auth_headers():
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}

# Main app
if st.session_state.user is None:
    # Authentication page
    st.title("🇪🇪 Estonca Telaffuz Pratiği")
    st.subheader("Giriş Yap veya Kayıt Ol")

    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Kullanıcı Adı")
            password = st.text_input("Şifre", type="password")
            submitted = st.form_submit_button("Giriş Yap")

            if submitted:
                if login(username, password):
                    st.success("Giriş başarılı!")
                    st.rerun()

    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Kullanıcı Adı")
            new_email = st.text_input("E-posta")
            new_password = st.text_input("Şifre", type="password")
            confirm_password = st.text_input("Şifre Tekrar", type="password")
            submitted = st.form_submit_button("Kayıt Ol")

            if submitted:
                if new_password != confirm_password:
                    st.error("Şifreler eşleşmiyor")
                elif len(new_password) < 6:
                    st.error("Şifre en az 6 karakter olmalı")
                else:
                    register(new_username, new_email, new_password)

else:
    # Theme toggle
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False

    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Ayarlar")
        dark_mode = st.toggle("🌙 Koyu Mod", value=st.session_state.dark_mode)
        if dark_mode != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_mode
            st.rerun()

        st.divider()
        st.caption("🇪🇪 Estonca Telaffuz Pratiği")
        st.caption("v1.0.0")

    # Apply theme
    if st.session_state.dark_mode:
        st.markdown("""
        <style>
        .stApp {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        .stTextInput, .stSelectbox, .stButton button {
            background-color: #2d2d2d !important;
            color: #ffffff !important;
            border-color: #555555 !important;
        }
        .metric-container {
            background-color: #2d2d2d !important;
            border-color: #555555 !important;
        }
        </style>
        """, unsafe_allow_html=True)

    # Main app for authenticated users
    st.title(f"🇪🇪 Merhaba, {st.session_state.user['username']}!")

    # Logout button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption("Estonca Telaffuz Pratiği - Günlük kelime paketi, ses kaydı ve anlık skor.")
    with col2:
        if st.button("Çıkış Yap"):
            logout()
            st.rerun()

    # Progress summary
    if st.button("İlerleme Özetini Göster"):
        try:
            response = requests.get(f"{API}/progress/summary", headers=get_auth_headers())
            if response.status_code == 200:
                progress = response.json()
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Toplam Pratık", progress["total_practice"])
                with col2:
                    st.metric("Ortalama Skor", f"{progress['average_score']:.2f}")
                with col3:
                    st.metric("En İyi Skor", f"{progress['best_score']:.2f}")
                with col4:
                    st.metric("Gelişme", f"{progress['improvement_trend']:+.2f}")

                # Streak display
                if "current_streak" in progress:
                    st.subheader("🔥 Seri")
                    streak_col, desc_col = st.columns([1, 3])
                    with streak_col:
                        # Visual streak indicator
                        flame_intensity = min(progress['current_streak'] // 5, 5)  # 0-5 levels
                        flames = "🔥" * (flame_intensity + 1) if progress['current_streak'] > 0 else "💤"
                        st.markdown(f"<h1 style='text-align: center; font-size: 3em;'>{flames}</h1>", unsafe_allow_html=True)
                        st.metric("Güncel Seri", f"{progress['current_streak']} gün")
                    with desc_col:
                        if progress['current_streak'] > 0:
                            st.success(f"Harika! {progress['current_streak']} gündür düzenli pratik yapıyorsun! 🔥")
                            if progress['current_streak'] >= 7:
                                st.info("💪 Haftalık şampiyon! Bu ritmi koru!")
                            elif progress['current_streak'] >= 30:
                                st.info("👑 Ay şampiyonu! Muhteşem disiplin!")
                        else:
                            st.info("Yarın tekrar pratik yaparak serini başlat! 💪")

                # Achievements
                if "achievements" in progress and progress["achievements"]:
                    st.subheader("🏆 Başarılar")
                    achievement_cols = st.columns(min(len(progress["achievements"]), 3))

                    for i, achievement in enumerate(progress["achievements"][:3]):
                        with achievement_cols[i]:
                            st.markdown(f"""
                            <div style="border: 2px solid #FFD700; border-radius: 10px; padding: 10px; text-align: center; background-color: #FFF8DC;">
                                <h4>🏆 {achievement['name']}</h4>
                                <p style="font-size: 12px; margin: 5px 0;">{achievement['description']}</p>
                                <p style="font-size: 10px; color: #666;">{achievement['unlocked_at'][:10]}</p>
                            </div>
                            """, unsafe_allow_html=True)

                # New achievements notification
                if "new_achievements" in progress and progress["new_achievements"]:
                    st.success("🎉 Yeni başarılar kazandın!")
                    for achievement in progress["new_achievements"]:
                        st.balloons()
                        st.markdown(f"**🏆 {achievement['name']}**: {achievement['description']}")

                if progress["recent_progress"]:
                    st.subheader("Son Aktiviteler")
                    for item in progress["recent_progress"][:5]:
                        st.write(f"• {item['word']}: {item['score']:.2f} ({item['date']})")

                    # Progress visualization
                    st.subheader("📊 İlerleme Grafikleri")

                    # Prepare data for charts
                    recent_data = progress["recent_progress"][:20]  # Last 20 attempts
                    if recent_data:
                        # Score over time chart
                        dates = [item['date'][:10] for item in recent_data]  # Extract date part
                        scores = [item['score'] for item in recent_data]
                        words = [item['word'] for item in recent_data]

                        # Line chart for scores over time
                        fig_scores = px.line(
                            x=list(range(len(scores))),
                            y=scores,
                            title="Skor Geçmişi (Son 20 Deneme)",
                            labels={'x': 'Deneme #', 'y': 'Skor'},
                            markers=True
                        )
                        fig_scores.update_traces(line_color='#1f77b4')
                        st.plotly_chart(fig_scores, use_container_width=True)

                        # Word performance breakdown
                        if progress["word_breakdown"]:
                            st.subheader("📝 Kelime Bazlı Performans")

                            words_list = []
                            avg_scores = []
                            attempt_counts = []

                            for word_key, stats in progress["word_breakdown"].items():
                                word_name = word_key.replace("word_", "")
                                words_list.append(word_name)
                                avg_scores.append(stats["average_score"])
                                attempt_counts.append(stats["attempts"])

                            # Bar chart for word performance
                            fig_words = px.bar(
                                x=words_list,
                                y=avg_scores,
                                title="Kelime Başına Ortalama Skor",
                                labels={'x': 'Kelime', 'y': 'Ortalama Skor'},
                                text=[f"{score:.1f}" for score in avg_scores],
                                color=avg_scores,
                                color_continuous_scale='Blues'
                            )
                            fig_words.update_traces(textposition='outside')
                            st.plotly_chart(fig_words, use_container_width=True)

                            # Scatter plot: attempts vs average score
                            fig_attempts = px.scatter(
                                x=attempt_counts,
                                y=avg_scores,
                                text=words_list,
                                title="Deneme Sayısı vs Ortalama Skor",
                                labels={'x': 'Deneme Sayısı', 'y': 'Ortalama Skor'},
                                size=[count*10 for count in attempt_counts],
                                color=avg_scores,
                                color_continuous_scale='Viridis'
                            )
                            fig_attempts.update_traces(textposition='top center')
                            st.plotly_chart(fig_attempts, use_container_width=True)

            else:
                st.warning("İlerleme verisi alınamadı")
        except Exception as e:
            st.error(f"İlerleme hatası: {e}")

    # Practice section
    st.header("🎯 Günlük Pratık")

    # Get available categories
    try:
        categories_resp = requests.get(f"{API}/word-categories")
        available_categories = categories_resp.json()
    except:
        available_categories = {"A1": ["greetings", "food"], "A2": ["family"], "B1": ["time", "emotions", "nature"]}

    # Level and category selection
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        selected_level = st.selectbox("Seviye", list(available_categories.keys()), index=0)
    with col2:
        selected_category = st.selectbox("Kategori", ["Tümü"] + available_categories.get(selected_level, []))
    with col3:
        pack_size = st.selectbox("Kelime Sayısı", [3, 5, 10], index=0)

    # 1) Günlük paket
    if st.button("Günlük Paketi Getir"):
        params = {"limit": pack_size, "level": selected_level}
        if selected_category != "Tümü":
            params["category"] = selected_category
        resp = requests.get(f"{API}/daily-pack", params=params)
        st.session_state["pack"] = resp.json()["items"]

    pack = st.session_state.get("pack", [])
    for item in pack:
        with st.expander(f"{item['text']} — {item['tr']}  | IPA: {item['ipa']}"):
            st.write("🎤 **Ses Kaydet** veya **Dosya Yükle**:")

            # Audio recording section
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write("**Mikrofonla Kaydet:**")
                audio_processor = AudioProcessor()

                webrtc_ctx = webrtc_streamer(
                    key=f"audio_recorder_{item['id']}",
                    mode=WebRtcMode.SENDRECV,
                    rtc_configuration=RTC_CONFIGURATION,
                    media_stream_constraints={"audio": True, "video": False},
                    audio_processor_factory=lambda: audio_processor,
                    async_processing=True,
                )

                if st.button(f"Kaydı İşle: {item['text']}", key=f"process_{item['id']}"):
                    if audio_processor.audio_frames:
                        # Convert frames to audio bytes
                        audio_bytes = get_audio_bytes(audio_processor.audio_frames)

                        if audio_bytes:
                            # Send audio to backend for ASR and scoring
                            files = {"audio_file": ("recording.wav", audio_bytes, "audio/wav")}
                            data = {
                                "word": item["text"],
                                "target_text": item["text"],
                                "target_ipa": item["ipa"]
                            }

                            try:
                                res = requests.post(f"{API}/pronunciation/score", files=files, data=data, headers=get_auth_headers())
                                if res.ok:
                                    s = res.json()
                                    st.success("🎉 Otomatik ASR ile skorlandı!")

                                    # Display results
                                    col_score, col_details = st.columns([1, 2])
                                    with col_score:
                                        st.metric("Final Skor", s["final"])
                                    with col_details:
                                        st.write(f"**ASR Doğruluk:** {s['asr_accuracy']}")
                                        st.write(f"**Fonem Benzerliği:** {s['phoneme_similarity']}")
                                        st.write(f"**Prosodi:** {s['prosody']}")

                                    st.write(f"**Algılanan Metin:** '{s.get('asr_text', 'N/A')}'")
                                    st.write("**Geri Bildirim:**")
                                    for f in s["feedback"]:
                                        st.write(f"- {f}")

                                    # Clear audio frames after processing
                                    audio_processor.audio_frames = []
                                else:
                                    st.error(f"Skor alınamadı: {res.status_code}")
                            except Exception as e:
                                st.error(f"Hata: {str(e)}")
                        else:
                            st.warning("Ses verisi işlenemedi. Tekrar kaydedin.")
                    else:
                        st.warning("Önce ses kaydedin!")

            with col2:
                st.write("**Veya Dosya Yükle:**")
                audio = st.file_uploader(f"Ses yükle: {item['text']}", type=["wav","mp3","m4a"], key=item["id"])
                if audio and st.button(f"Yükle ve Kaydet: {item['text']}", key=item["id"]+"_btn"):
                    files = {"file": (audio.name, audio.read(), audio.type)}
                    data = {"word_id": item["id"]}
                    r = requests.post(f"{API}/recordings", files=files, data=data)
                    if r.ok:
                        st.success("Ses yüklendi.")
                    else:
                        st.error("Yükleme başarısız.")

            # Manual ASR input (fallback)
            st.write("**Alternatif: Manuel ASR Metni** (eğer otomatik çalışmazsa):")
            asr_text = st.text_input("ASR metni", key=item["id"]+"_asr", value=item["text"])

            if st.button(f"Manuel Skorla: {item['text']}", key=item["id"]+"_score"):
                payload = {
                    "word": item["text"],
                    "target_text": item["text"],
                    "target_ipa": item["ipa"],
                    "asr_text": asr_text
                }
                res = requests.post(f"{API}/pronunciation/score", params=payload, headers=get_auth_headers())
                if res.ok:
                    s = res.json()
                    st.metric("Final Skor", s["final"])
                    st.write(f"ASR Doğruluk: {s['asr_accuracy']}, Fonem Benzerliği: {s['phoneme_similarity']}, Prosodi: {s['prosody']}")
                    st.write("Geri Bildirim:")
                    for f in s["feedback"]:
                        st.write("- ", f)
                else:
                    st.error("Skor alınamadı.")
st.caption("Günlük kelime paketi, ses kaydı ve anlık skor.")

# WebRTC configuration for audio recording
RTC_CONFIGURATION = RTCConfiguration({
    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
})

# Audio recording callback
class AudioProcessor:
    def __init__(self):
        self.audio_frames = []

    def recv(self, frame):
        audio = frame.to_ndarray()
        self.audio_frames.append(audio)
        return av.AudioFrame.from_ndarray(audio, layout="mono")

def get_audio_bytes(frames: List[np.ndarray]) -> bytes:
    """Convert audio frames to WAV bytes"""
    if not frames:
        return b""

    # Combine all frames
    audio_data = np.concatenate(frames, axis=0)

    # Convert to 16-bit PCM
    audio_data = (audio_data * 32767).astype(np.int16)

    # Create WAV header
    import io
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(16000)  # 16kHz sample rate
        wav_file.writeframes(audio_data.tobytes())

    return buffer.getvalue()

# 1) Günlük paket
if st.button("Günlük Paketi Getir"):
    resp = requests.get(f"{API}/daily-pack", params={"limit": 3, "level": "A1"})
    st.session_state["pack"] = resp.json()["items"]

pack = st.session_state.get("pack", [])
for item in pack:
    with st.expander(f"{item['text']} — {item['tr']}  | IPA: {item['ipa']}"):
        st.write("🎤 **Ses Kaydet** veya **Dosya Yükle**:")

        # Audio recording section
        col1, col2 = st.columns([2, 1])

        with col1:
            st.write("**Mikrofonla Kaydet:**")
            audio_processor = AudioProcessor()

            webrtc_ctx = webrtc_streamer(
                key=f"audio_recorder_{item['id']}",
                mode=WebRtcMode.SENDRECV,
                rtc_configuration=RTC_CONFIGURATION,
                media_stream_constraints={"audio": True, "video": False},
                audio_processor_factory=lambda: audio_processor,
                async_processing=True,
            )

            if st.button(f"Kaydı İşle: {item['text']}", key=f"process_{item['id']}"):
                if audio_processor.audio_frames:
                    # Convert frames to audio bytes
                    audio_bytes = get_audio_bytes(audio_processor.audio_frames)

                    if audio_bytes:
                        # Send audio to backend for ASR and scoring
                        files = {"audio_file": ("recording.wav", audio_bytes, "audio/wav")}
                        data = {
                            "word": item["text"],
                            "target_text": item["text"],
                            "target_ipa": item["ipa"]
                        }

                        try:
                            res = requests.post(f"{API}/pronunciation/score", files=files, data=data)
                            if res.ok:
                                s = res.json()
                                st.success("🎉 Otomatik ASR ile skorlandı!")

                                # Display results
                                col_score, col_details = st.columns([1, 2])
                                with col_score:
                                    st.metric("Final Skor", s["final"])
                                with col_details:
                                    st.write(f"**ASR Doğruluk:** {s['asr_accuracy']}")
                                    st.write(f"**Fonem Benzerliği:** {s['phoneme_similarity']}")
                                    st.write(f"**Prosodi:** {s['prosody']}")

                                st.write(f"**Algılanan Metin:** '{s.get('asr_text', 'N/A')}'")
                                st.write("**Geri Bildirim:**")
                                for f in s["feedback"]:
                                    st.write(f"- {f}")

                                # Clear audio frames after processing
                                audio_processor.audio_frames = []
                            else:
                                st.error(f"Skor alınamadı: {res.status_code}")
                        except Exception as e:
                            st.error(f"Hata: {str(e)}")
                    else:
                        st.warning("Ses verisi işlenemedi. Tekrar kaydedin.")
                else:
                    st.warning("Önce ses kaydedin!")

        with col2:
            st.write("**Veya Dosya Yükle:**")
            audio = st.file_uploader(f"Ses yükle: {item['text']}", type=["wav","mp3","m4a"], key=item["id"])
            if audio and st.button(f"Yükle ve Kaydet: {item['text']}", key=item["id"]+"_btn"):
                files = {"file": (audio.name, audio.read(), audio.type)}
                data = {"word_id": item["id"]}
                r = requests.post(f"{API}/recordings", files=files, data=data)
                if r.ok:
                    st.success("Ses yüklendi.")
                else:
                    st.error("Yükleme başarısız.")

        # Manual ASR input (fallback)
        st.write("**Alternatif: Manuel ASR Metni** (eğer otomatik çalışmazsa):")
        asr_text = st.text_input("ASR metni", key=item["id"]+"_asr", value=item["text"])

        if st.button(f"Manuel Skorla: {item['text']}", key=item["id"]+"_score"):
            payload = {
                "word": item["text"],
                "target_text": item["text"],
                "target_ipa": item["ipa"],
                "asr_text": asr_text
            }
            res = requests.post(f"{API}/pronunciation/score", params=payload)
            if res.ok:
                s = res.json()
                st.metric("Final Skor", s["final"])
                st.write(f"ASR Doğruluk: {s['asr_accuracy']}, Fonem Benzerliği: {s['phoneme_similarity']}, Prosodi: {s['prosody']}")
                st.write("Geri Bildirim:")
                for f in s["feedback"]:
                    st.write("- ", f)
            else:
                st.error("Skor alınamadı.")