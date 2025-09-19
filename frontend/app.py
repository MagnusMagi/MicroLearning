import streamlit as st
import requests

API = "http://localhost:8000"

st.title("Estonca Telaffuz Pratiği (Localhost MVP)")
st.caption("Günlük kelime paketi, ses yükleme ve anlık skor.")

# 1) Günlük paket
if st.button("Günlük Paketi Getir"):
    resp = requests.get(f"{API}/daily-pack", params={"limit": 3, "level": "A1"})
    st.session_state["pack"] = resp.json()["items"]

pack = st.session_state.get("pack", [])
for item in pack:
    with st.expander(f"{item['text']} — {item['tr']}  | IPA: {item['ipa']}"):
        st.write("Ses dosyanı yükle (wav/mp3):")
        audio = st.file_uploader(f"Ses yükle: {item['text']}", type=["wav","mp3","m4a"], key=item["id"])
        if audio and st.button(f"Yükle ve Kaydet: {item['text']}", key=item["id"]+"_btn"):
            files = {"file": (audio.name, audio.read(), audio.type)}
            data = {"word_id": item["id"]}
            r = requests.post(f"{API}/recordings", files=files, data=data)
            if r.ok:
                st.success("Ses yüklendi.")
            else:
                st.error("Yükleme başarısız.")

        st.write("ASR sonucu (MVP için manuel gir):")
        asr_text = st.text_input("ASR metni", key=item["id"]+"_asr", value=item["text"])

        if st.button(f"Skorla: {item['text']}", key=item["id"]+"_score"):
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