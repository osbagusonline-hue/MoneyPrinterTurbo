"""Food advertisement storyboard builder for MoneyPrinterTurbo.

This Streamlit page creates editable production instructions. Rendering remains
in the existing MoneyPrinterTurbo video workflow.
"""
import json
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
