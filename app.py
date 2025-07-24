import streamlit as st
from pytube import YouTube
import whisper
import os
import tempfile
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import random
import string
import shutil # Added for robust temp file cleanup

st.set_page_config(page_title="Clip Captioner", layout="centered")

st.title("🎬 Auto Clip Captioner")
st.markdown("Upload a video or paste a YouTube link. Captions will be added automatically!")

def random_filename(ext="mp4"):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + f".{ext}"

# Whisper model
@st.cache_resource
def load_model():
    # Ensure the model directory exists and has write permissions if needed
    # Whisper models are typically downloaded to ~/.cache/whisper
    # For Streamlit Cloud, this cache is usually persistent per deployment.
    return whisper.load_model("base")

model = load_model()

def generate_captions(video_path):
    st.info("Transcribing audio... This might take a while for longer videos.")
    result = model.transcribe(video_path)
    return result["segments"]

def add_captions_to_video(video_path, segments, font_size=24, font_color="white"):
    st.info("Adding captions to video...")
    try:
        video = VideoFileClip(video_path)
    except Exception as e:
        st.error(f"Error loading video file with MoviePy: {e}")
        st.error("Ensure the video file is not corrupted and compatible with MoviePy/FFmpeg.")
        return None

    clips = []

    # Basic error handling for empty segments or no text
    if not segments:
        st.warning("No captions were generated for the video.")
        return video_path # Return original if no captions

    for segment in segments:
        # Sanitize text to avoid issues with TextClip if needed (e.g., special characters)
        caption_text = str(segment["text"]).strip()
        if not caption_text:
            continue # Skip empty captions

        try:
            caption = TextClip(caption_text, fontsize=font_size, color=font_color, size=video.size, method='caption', align='center')
            caption = caption.set_start(segment["start"]).set_duration(segment["end"] - segment["start"])
            caption = caption.set_position(("center", "bottom"))
            clips.append(caption)
        except Exception as e:
            st.warning(f"Could not create text clip for segment '{caption_text}': {e}")
            continue

    if not clips:
        st.warning("No valid caption clips were created. Returning original video.")
        return video_path

    final = CompositeVideoClip([video] + clips)
    
    # Ensure a unique temporary directory for output to avoid conflicts
    output_dir = tempfile.mkdtemp()
    temp_out = os.path.join(output_dir, random_filename())

    try:
        final.write_videofile(temp_out, codec="libx264", audio_codec="aac", fps=video.fps)
        return temp_out
    except Exception as e:
        st.error(f"Error writing output video: {e}")
        st.error("This could be due to an issue with FFmpeg or video codecs.")
        return None
    finally:
        # Clean up the temporary directory for output
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)


# Input section
option = st.radio("Choose Input Method:", ["📤 Upload Video", "🔗 Paste YouTube Link"])

video_path = None
temp_file_paths = [] # To keep track of temporary files for cleanup

if option == "📤 Upload Video":
    uploaded_file = st.file_uploader("Upload your video file", type=["mp4", "mov", "avi"])
    if uploaded_file:
        # Create a temporary file and write the uploaded content to it
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())
        video_path = temp_path
        temp_file_paths.append(temp_dir) # Add the directory to cleanup list

elif option == "🔗 Paste YouTube Link":
    yt_url = st.text_input("Paste YouTube video URL")
    if yt_url:
        try:
            yt = YouTube(yt_url)
            # Get the highest resolution stream with video and audio
            yt_stream = yt.streams.filter(file_extension='mp4', progressive=True).order_by('resolution').desc().first()
            if not yt_stream:
                st.error("Could not find a suitable MP4 stream for this YouTube video.")
                yt_stream = yt.streams.filter(file_extension='mp4').first() # Fallback

            if yt_stream:
                temp_dir = tempfile.mkdtemp()
                temp_path = os.path.join(temp_dir, random_filename())
                st.info(f"Downloading YouTube video: {yt.title}...")
                yt_stream.download(output_path=temp_dir, filename=os.path.basename(temp_path))
                video_path = temp_path
                temp_file_paths.append(temp_dir) # Add the directory to cleanup list
                st.success("YouTube video downloaded successfully!")
            else:
                st.error("No MP4 stream found for the YouTube video. Try another URL.")
        except Exception as e:
            st.error(f"Error downloading YouTube video: {e}")
            st.warning("Ensure the URL is correct and the video is publicly accessible.")

if video_path:
    st.success("Video loaded successfully!")

    st.markdown("### 🎨 Customize Captions")
    font_size = st.slider("Font Size", 12, 60, 24)
    font_color = st.color_picker("Font Color", "#FFFFFF")

    if st.button("Generate Captions and Export Video"):
        with st.spinner("Generating captions and rendering video..."):
            segments = generate_captions(video_path)
            if segments:
                out_video_path = add_captions_to_video(video_path, segments, font_size, font_color)
                if out_video_path:
                    st.success("Video ready!")
                    with open(out_video_path, "rb") as file:
                        st.download_button(label="📥 Download Captioned Video", data=file, file_name="captioned_video.mp4", mime="video/mp4")
                    # Clean up the output video file after download button is presented
                    if os.path.exists(os.path.dirname(out_video_path)):
                        shutil.rmtree(os.path.dirname(out_video_path))
                else:
                    st.error("Failed to add captions to the video.")
            else:
                st.error("Failed to generate captions for the video.")

# Cleanup of input temporary files (important for resource management)
for d_path in temp_file_paths:
    if os.path.exists(d_path):
        try:
            shutil.rmtree(d_path)
        except OSError as e:
            st.warning(f"Error cleaning up temporary directory {d_path}: {e}")
