import streamlit as st
from pytube import YouTube
import whisper
import os
import tempfile
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import random
import string

st.set_page_config(page_title="Clip Captioner", layout="centered")

st.title("🎬 Auto Clip Captioner")
st.markdown("Upload a video or paste a YouTube link. Captions will be added automatically!")

def random_filename(ext="mp4"):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + f".{ext}"

# Whisper model
@st.cache_resource
def load_model():
    return whisper.load_model("base")

model = load_model()

def generate_captions(video_path):
    result = model.transcribe(video_path)
    return result["segments"]

def add_captions_to_video(video_path, segments, font_size=24, font_color="white"):
    video = VideoFileClip(video_path)
    clips = []

    for segment in segments:
        caption = TextClip(segment["text"], fontsize=font_size, color=font_color, size=video.size)
        caption = caption.set_start(segment["start"]).set_duration(segment["end"] - segment["start"])
        caption = caption.set_position(("center", "bottom"))
        clips.append(caption)

    final = CompositeVideoClip([video] + clips)
    temp_out = os.path.join(tempfile.gettempdir(), random_filename())
    final.write_videofile(temp_out, codec="libx264", audio_codec="aac")
    return temp_out

# Input section
option = st.radio("Choose Input Method:", ["📤 Upload Video", "🔗 Paste YouTube Link"])

video_path = None

if option == "📤 Upload Video":
    uploaded_file = st.file_uploader("Upload your video file", type=["mp4", "mov", "avi"])
    if uploaded_file:
        temp_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())
        video_path = temp_path

elif option == "🔗 Paste YouTube Link":
    yt_url = st.text_input("Paste YouTube video URL")
    if yt_url:
        yt = YouTube(yt_url)
        yt_stream = yt.streams.filter(file_extension='mp4').get_highest_resolution()
        temp_path = os.path.join(tempfile.gettempdir(), random_filename())
        yt_stream.download(filename=temp_path)
        video_path = temp_path

if video_path:
    st.success("Video loaded successfully!")

    st.markdown("### 🎨 Customize Captions")
    font_size = st.slider("Font Size", 12, 60, 24)
    font_color = st.color_picker("Font Color", "#FFFFFF")

    if st.button("Generate Captions and Export Video"):
        with st.spinner("Generating captions and rendering video..."):
            segments = generate_captions(video_path)
            out_video_path = add_captions_to_video(video_path, segments, font_size, font_color)
            st.success("Video ready!")
            with open(out_video_path, "rb") as file:
                st.download_button(label="📥 Download Captioned Video", data=file, file_name="captioned_video.mp4", mime="video/mp4")
