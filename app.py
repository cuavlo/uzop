import streamlit as st
from pytube import YouTube
import whisper
import os
import tempfile
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, vfx
import random
import string
import shutil
import numpy as np # For potential future image processing, useful with MoviePy sometimes

st.set_page_config(page_title="AI Clip Generator", layout="wide")

st.title("🎬 AI Clip Generator (Opus Clip Alternative)")
st.markdown("Extract, caption, and format engaging clips from your videos or YouTube links!")

# --- Helper Functions ---
def random_filename(ext="mp4"):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + f".{ext}"

# Whisper model
@st.cache_resource
def load_whisper_model():
    with st.spinner("Loading AI transcription model... (This might take a moment the first time)"):
        return whisper.load_model("base") # You can choose 'tiny', 'base', 'small', 'medium', 'large'

# Load the model once
whisper_model = load_whisper_model()

# Function to generate captions for a given video segment
def generate_captions_for_segment(video_path, start_time, end_time):
    st.info(f"Transcribing audio for segment [{start_time:.2f}s - {end_time:.2f}s]...")
    
    # Use moviepy to extract the audio of the segment
    temp_audio_path = os.path.join(tempfile.gettempdir(), random_filename(ext="mp3"))
    try:
        video_clip = VideoFileClip(video_path)
        audio_segment = video_clip.subclip(start_time, end_time).audio
        audio_segment.write_audiofile(temp_audio_path)
        
        result = whisper_model.transcribe(temp_audio_path)
        # Adjust segment timings relative to the original video's start time
        for segment in result["segments"]:
            segment["start"] += start_time
            segment["end"] += end_time
        return result["segments"]
    except Exception as e:
        st.error(f"Error during audio extraction or transcription: {e}")
        return []
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)


def add_captions_and_process_clip(
    video_path, segments, start_time, end_time,
    font_size=24, font_color="white",
    aspect_ratio="original", clip_name="output_clip"
):
    st.info(f"Processing clip '{clip_name}' with captions and formatting...")
    try:
        full_video = VideoFileClip(video_path)
        clip = full_video.subclip(start_time, end_time)
    except Exception as e:
        st.error(f"Error loading or sub-clipping video: {e}")
        return None

    final_width, final_height = clip.size

    # 1. Handle Aspect Ratio
    if aspect_ratio == "9:16": # Vertical - for Shorts, Reels, TikTok
        final_width = int(clip.h * 9 / 16)
        if final_width > clip.w: # If original width is too small, use original width
             final_width = clip.w
             final_height = int(clip.w * 16 / 9)

        # Center crop or pad
        if clip.w > final_width:
            x_center = clip.w / 2
            y_center = clip.h / 2
            clip = clip.crop(x_center=x_center, y_center=y_center, width=final_width, height=clip.h)
        elif clip.h > final_height: # Should not happen with current logic for 9:16 crop width first
            pass # No crop needed for height
        else: # Original is smaller, pad it
            new_clip = VideoFileClip(clip.filename, size=(final_width, final_height), bg_color=(0,0,0))
            clip = CompositeVideoClip([clip.set_position("center")], size=new_clip.size)


    elif aspect_ratio == "1:1": # Square
        side = min(clip.w, clip.h)
        clip = clip.crop(x_center=clip.w/2, y_center=clip.h/2, width=side, height=side)
        final_width, final_height = side, side
    elif aspect_ratio == "16:9": # Standard landscape (if original is not 16:9)
        final_height = int(clip.w * 9 / 16)
        if final_height > clip.h: # If original height is too small, use original height
             final_height = clip.h
             final_width = int(clip.h * 16 / 9)

        # Center crop or pad
        if clip.h > final_height:
            x_center = clip.w / 2
            y_center = clip.h / 2
            clip = clip.crop(x_center=x_center, y_center=y_center, width=clip.w, height=final_height)
        elif clip.w > final_width:
            pass # No crop needed for width
        else: # Original is smaller, pad it
            new_clip = VideoFileClip(clip.filename, size=(final_width, final_height), bg_color=(0,0,0))
            clip = CompositeVideoClip([clip.set_position("center")], size=new_clip.size)
    
    # Update clip size after aspect ratio adjustments
    final_width, final_height = clip.size


    # 2. Add Captions to the Cropped/Resized Clip
    caption_clips = []
    # Adjust segment times to be relative to the *start of the new clip*
    # However, since we transcribed the segment directly, the segment timestamps
    # are already aligned with the original video's timeline. We need to adjust
    # them to be relative to the start of the *subclip* (the current `clip` object).
    
    # Filter segments that fall within the current clip's time range
    filtered_segments = [s for s in segments if s["start"] >= start_time and s["end"] <= end_time]

    for segment in filtered_segments:
        # Calculate relative start and end times for the current subclip
        relative_start = segment["start"] - start_time
        relative_end = segment["end"] - start_time
        
        caption_text = str(segment["text"]).strip()
        if not caption_text:
            continue

        try:
            # Adjust fontsize dynamically if desired based on output size
            # current_font_size = font_size # You can make this dynamic based on final_height
            
            caption = TextClip(caption_text, 
                               fontsize=font_size, 
                               color=font_color, 
                               size=(final_width * 0.9, None), # Max 90% width, auto height
                               method='caption', 
                               align='center',
                               stroke_color='black', # Add stroke for better visibility
                               stroke_width=1.5 # Adjust stroke width
                              )
            caption = caption.set_start(relative_start).set_duration(relative_end - relative_start)
            # Position at 85% from top (15% from bottom)
            caption = caption.set_position(("center", final_height * 0.85)) 
            caption_clips.append(caption)
        except Exception as e:
            st.warning(f"Could not create text clip for segment '{caption_text}': {e}")
            continue

    final_video = CompositeVideoClip([clip] + caption_clips, size=clip.size)
    
    # Create a unique temporary directory for each output clip
    output_dir = tempfile.mkdtemp()
    temp_out_path = os.path.join(output_dir, random_filename())

    try:
        final_video.write_videofile(temp_out_path, codec="libx264", audio_codec="aac", fps=clip.fps)
        return temp_out_path
    except Exception as e:
        st.error(f"Error writing output video for '{clip_name}': {e}")
        st.error("This could be due to an issue with FFmpeg, video codecs, or insufficient disk space.")
        return None
    finally:
        # Clean up the output directory after processing if successful, or if error, leave for debugging
        # No, clean up immediately after the file is written. The caller will handle the download.
        pass # We will clean up in the main app logic after download

# --- Streamlit UI ---
input_col, preview_col = st.columns([1, 2])

with input_col:
    st.header("1. Input Video")
    option = st.radio("Choose Input Method:", ["📤 Upload Video", "🔗 Paste YouTube Link"])

    video_path = None
    temp_file_dirs = [] # Store directories to clean up later

    if option == "📤 Upload Video":
        uploaded_file = st.file_uploader("Upload your video file", type=["mp4", "mov", "avi"])
        if uploaded_file:
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.read())
            video_path = temp_path
            temp_file_dirs.append(temp_dir)
            st.success("Video uploaded successfully!")

    elif option == "🔗 Paste YouTube Link":
        yt_url = st.text_input("Paste YouTube video URL")
        if yt_url:
            try:
                yt = YouTube(yt_url)
                st.info(f"Fetching YouTube video: **{yt.title}**")
                # Prefer progressive streams for direct MoviePy compatibility
                yt_stream = yt.streams.filter(file_extension='mp4', progressive=True).order_by('resolution').desc().first()
                
                if not yt_stream: # Fallback to non-progressive if no progressive found
                    st.warning("No progressive MP4 stream found. Attempting non-progressive (may cause audio/video sync issues).")
                    yt_stream = yt.streams.filter(file_extension='mp4', res="720p").first() # Try a common resolution
                if not yt_stream:
                     yt_stream = yt.streams.filter(file_extension='mp4').first() # Last resort, any MP4

                if yt_stream:
                    temp_dir = tempfile.mkdtemp()
                    temp_path = os.path.join(temp_dir, random_filename(ext="mp4")) # Ensure .mp4 extension
                    st.info(f"Downloading: {yt_stream.title} ({yt_stream.resolution}) - This might take a while...")
                    yt_stream.download(output_path=temp_dir, filename=os.path.basename(temp_path))
                    video_path = temp_path
                    temp_file_dirs.append(temp_dir)
                    st.success("YouTube video downloaded successfully!")
                else:
                    st.error("No suitable MP4 stream found for the YouTube video. Try another URL.")
            except Exception as e:
                st.error(f"Error downloading YouTube video: {e}")
                st.warning("Ensure the URL is correct and the video is publicly accessible. Videos with age restrictions or private videos may not work.")

if video_path:
    with preview_col:
        st.header("2. Video Preview & Clip Selection")
        st.video(video_path)

        st.markdown("---")
        st.subheader("Define Your Clips:")
        if 'clips_data' not in st.session_state:
            st.session_state.clips_data = []

        # Add new clip button
        if st.button("➕ Add New Clip"):
            st.session_state.clips_data.append({"start_time": 0.0, "end_time": 10.0, "name": f"Clip {len(st.session_state.clips_data) + 1}"})

        # Display and edit existing clips
        if st.session_state.clips_data:
            st.warning("Please note: Precise timing can be challenging with Streamlit's video player. Use the video's actual duration as a guide.")
            for i, clip_data in enumerate(st.session_state.clips_data):
                st.markdown(f"**Clip {i+1} Settings**")
                clip_data["name"] = st.text_input(f"Clip {i+1} Name", value=clip_data["name"], key=f"clip_name_{i}")
                
                col_start, col_end = st.columns(2)
                with col_start:
                    clip_data["start_time"] = st.number_input(
                        "Start (seconds)", 
                        min_value=0.0, 
                        max_value=VideoFileClip(video_path).duration, 
                        value=min(clip_data["start_time"], VideoFileClip(video_path).duration), 
                        step=0.5, 
                        key=f"start_time_{i}"
                    )
                with col_end:
                    clip_data["end_time"] = st.number_input(
                        "End (seconds)", 
                        min_value=clip_data["start_time"], # End must be after start
                        max_value=VideoFileClip(video_path).duration, 
                        value=min(clip_data["end_time"], VideoFileClip(video_path).duration), 
                        step=0.5, 
                        key=f"end_time_{i}"
                    )
                
                # Validation
                if clip_data["start_time"] >= clip_data["end_time"]:
                    st.error("Clip end time must be greater than start time.")
                
                # Delete clip button
                if st.button(f"➖ Delete Clip {i+1}", key=f"delete_clip_{i}"):
                    st.session_state.clips_data.pop(i)
                    st.rerun() # Rerun to update the list immediately


    st.header("3. Caption & Output Settings")
    font_size = st.slider("Caption Font Size", 12, 60, 36)
    font_color = st.color_picker("Caption Font Color", "#FFFFFF")
    aspect_ratio_option = st.selectbox(
        "Output Aspect Ratio",
        options=["original", "16:9 (Landscape)", "1:1 (Square)", "9:16 (Vertical)"],
        format_func=lambda x: x.split(" ")[0] if " " in x else x # Display "16:9" instead of "16:9 (Landscape)"
    )
    
    # Map selection to actual aspect ratio string for function
    aspect_ratio_map = {
        "original": "original",
        "16:9 (Landscape)": "16:9",
        "1:1 (Square)": "1:1",
        "9:16 (Vertical)": "9:16"
    }
    selected_aspect_ratio = aspect_ratio_map[aspect_ratio_option]


    if st.button("✨ Generate All Clips"):
        if not st.session_state.clips_data:
            st.error("Please add at least one clip to generate.")
        else:
            with st.spinner("Generating clips... This may take a while depending on video length and number of clips."):
                generated_clips_paths = []
                for i, clip_data in enumerate(st.session_state.clips_data):
                    clip_start = clip_data["start_time"]
                    clip_end = clip_data["end_time"]
                    clip_name = clip_data["name"]

                    if clip_start >= clip_end:
                        st.error(f"Skipping '{clip_name}': Invalid time range.")
                        continue

                    # Generate captions specifically for this segment
                    segment_captions = generate_captions_for_segment(video_path, clip_start, clip_end)
                    
                    if segment_captions is not None:
                        output_clip_path = add_captions_and_process_clip(
                            video_path, segment_captions, clip_start, clip_end,
                            font_size, font_color, selected_aspect_ratio, clip_name
                        )
                        if output_clip_path:
                            generated_clips_paths.append((clip_name, output_clip_path))
                        else:
                            st.error(f"Failed to process clip: '{clip_name}'")
                    else:
                        st.error(f"Failed to generate captions for clip: '{clip_name}'")

                if generated_clips_paths:
                    st.success("All selected clips generated!")
                    st.subheader("Download Your Clips:")
                    for clip_name, path in generated_clips_paths:
                        with open(path, "rb") as file:
                            st.download_button(
                                label=f"📥 Download '{clip_name}.mp4'",
                                data=file,
                                file_name=f"{clip_name}.mp4",
                                mime="video/mp4",
                                key=f"download_{clip_name}"
                            )
                        # Clean up the individual output clip file and its temporary directory
                        if os.path.exists(path):
                            os.remove(path)
                        if os.path.exists(os.path.dirname(path)):
                            shutil.rmtree(os.path.dirname(path))
                else:
                    st.warning("No clips were successfully generated.")


# --- Cleanup of input temporary files (important for resource management) ---
# This cleanup happens after the script reruns.
# For Streamlit Cloud, tempfile usually handles cleanup somewhat, but explicit is better.
for d_path in temp_file_dirs:
    if os.path.exists(d_path):
        try:
            shutil.rmtree(d_path)
        except OSError as e:
            st.warning(f"Error cleaning up input temporary directory {d_path}: {e}")
