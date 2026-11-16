"""Food advertisement storyboard builder for MoneyPrinterTurbo.

This Streamlit page creates editable production instructions. Rendering remains
in the existing MoneyPrinterTurbo video workflow.
"""
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import streamlit as st

st.set_page_config(page_title="AI Food Advertisement Generator", page_icon="🍜", layout="wide")
st.title("🍜 AI Food Advertisement Generator")
st.caption("Build a product-focused storyboard and production prompts for MoneyPrinterTurbo.")

with st.form("food_ad"):
    name = st.text_input("Product name", value="Bagus Sambal Belacan")
    description = st.text_area("Product description", value="Ready-to-eat sambal belacan in a bottle")
    audience = st.text_input("Target audience", value="Singapore food lovers")
    cta = st.text_input("Call to action", value="Shop at bagusmart.sg")
    language = st.selectbox("Voiceover language", ["English", "Malay", "Chinese", "Tamil"])
    duration = st.selectbox("Duration (seconds)", [10, 15, 20, 30], index=0)
    format_name = st.selectbox("Format", ["9:16 vertical", "16:9 landscape", "1:1 square"])
    style = st.selectbox("Visual style", ["Premium studio", "Foodie close-up", "Energetic TikTok", "Minimalist"])
    reference = st.file_uploader("Product reference photo (for visual reference only)", type=["png", "jpg", "jpeg"])
    submitted = st.form_submit_button("Create storyboard")

if submitted:
    if not name.strip() or not description.strip() or not cta.strip():
        st.error("Product name, description, and call to action are required.")
        st.stop()
    # Divide duration into three complete, contiguous phases.
    cuts = [0, round(duration * 0.3), round(duration * 0.7), duration]
    phases = [
        ("Product reveal", "Reveal the real product packaging in controlled studio lighting."),
        ("Food demonstration", "Show realistic texture and a serving suggestion; keep the product recognizable."),
        ("Hero shot and CTA", "End on the product pack with a clean, readable call to action."),
    ]
    scenes = []
    for i, (title, direction) in enumerate(phases):
        scenes.append({
            "start_seconds": cuts[i],
            "end_seconds": cuts[i + 1],
            "title": title,
            "visual_prompt": (
                f"{style} commercial, {format_name}, for {name}. {direction} "
                f"Product context: {description}. Target audience: {audience}. "
                "Preserve exact branding, packaging and label from the supplied reference; "
                "do not invent ingredients, certifications, prices or health claims. "
                "Use natural food texture, premium lighting and realistic motion."
            ),
        })
    project = {
        "product": name.strip(),
        "description": description.strip(),
        "audience": audience.strip(),
        "duration_seconds": duration,
        "aspect_ratio": format_name,
        "style": style,
        "voiceover_language": language,
        "voiceover_direction": (
            f"Warm, energetic {language} voice. Introduce {name}, highlight only "
            f"verified details: {description}. Close with: {cta}."
        ),
        "cta": cta.strip(),
        "reference_image_uploaded": reference is not None,
        "scenes": scenes,
    }
    st.success("Storyboard ready. Review prompts before generating footage.")
    for scene in scenes:
        with st.expander(f"{scene['start_seconds']}–{scene['end_seconds']}s · {scene['title']}", expanded=True):
            st.write(scene["visual_prompt"])
    st.subheader("Voiceover direction")
    st.write(project["voiceover_direction"])
    st.download_button(
        "Download production plan (JSON)",
        data=json.dumps(project, indent=2, ensure_ascii=False),
        file_name="food_ad_storyboard.json",
        mime="application/json",
    )
    st.info(
        "This page creates production prompts, not an MP4. "
        "Use the existing MoneyPrinterTurbo generation workflow to render scenes. "
        "Uploaded reference photos are not sent to a video provider by this page."
    )

st.divider()
st.subheader("Render a 10-second Bagus commercial")
st.write("1080 × 1920 MP4 with the real bottle, nasi putih, Malay female voice, music, captions and Bagusmart CTA.")

root = Path(__file__).resolve().parents[2]
assets = root / "assets/food_ads"
mode = st.selectbox("Food visuals", ["Animate supplied images (no paid video API)", "Seedance image-to-video (paid Ark credits)"])
bottle_upload = st.file_uploader("Bottle photo for the commercial", type=["png", "jpg", "jpeg"], key="render_bottle")
meal_upload = st.file_uploader("Meal reference (default: AI nasi putih serving illustration)", type=["png", "jpg", "jpeg"], key="render_meal")
render_cta = st.text_input("End-card website", value="bagusmart.sg", max_chars=80)
st.caption("The supplied bottle is composited directly. The food reference is sent to Ark only when Seedance is selected. The cached Malay narration says Bagus Sambal Belacan and Bagusmart.")
if st.button("Generate MP4", type="primary"):
    st.session_state.pop("bagus_render", None)
    if mode.startswith("Seedance") and not os.getenv("VOLCENGINE_ARK_API_KEY", "").strip():
        st.error("Configure VOLCENGINE_ARK_API_KEY in the server environment and fund Ark video credits first.")
    else:
        with tempfile.TemporaryDirectory(prefix="bagus-ad-") as temp:
            work = Path(temp)
            bottle = assets / "bsb.png"
            meal = assets / "nasi_putih_ulam_fried_fish.png"
            if bottle_upload:
                bottle = work / ("bottle" + Path(bottle_upload.name).suffix.lower())
                bottle.write_bytes(bottle_upload.getvalue())
            if meal_upload:
                meal = work / ("meal" + Path(meal_upload.name).suffix.lower())
                meal.write_bytes(meal_upload.getvalue())
            output = work / "bagus_sambal_belacan_10s.mp4"
            command = [sys.executable, str(root / "scripts/render_bagus_food_ad.py"),
                       "--bottle", str(bottle), "--meal", str(meal), "--output", str(output),
                       "--voice-audio", str(assets / "bagus_ms_Yasmin.mp3"),
                       "--subtitles", str(assets / "bagus_ms_Yasmin.words.srt"),
                       "--cta", render_cta, "--provider", "seedance" if mode.startswith("Seedance") else "stills"]
            try:
                with st.spinner("Rendering commercial. Seedance may take several minutes…"):
                    result = subprocess.run(command, capture_output=True, text=True, timeout=1000)
                if result.returncode:
                    st.error("Render failed. Check the server logs, media inputs and provider task receipt.")
                    # Server logs are available to the operator; never render provider responses/keys in the UI.
                    import logging
                    logging.getLogger(__name__).error("Food ad render failed: %s", result.stderr[-3000:])
                else:
                    st.session_state["bagus_render"] = (output.read_bytes(), output.with_suffix(".srt").read_bytes())
            except subprocess.TimeoutExpired:
                st.error("Local wait ended. Check the saved Seedance task receipt before retrying; a paid task may still be running.")
if "bagus_render" in st.session_state:
    video_data, subtitle_data = st.session_state["bagus_render"]
    st.video(video_data)
    st.download_button("Download commercial MP4", video_data, "bagus_sambal_belacan_10s.mp4", "video/mp4")
    st.download_button("Download Malay subtitles", subtitle_data, "bagus_sambal_belacan_10s.srt", "application/x-subrip")
