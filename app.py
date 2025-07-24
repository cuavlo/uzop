import streamlit as st
import whisper
import os
import tempfile
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, vfx
import random
import string
import shutil
import numpy as np # For potential future image processing, useful with MoviePy sometimesimport streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os

st.set_page_config(page_title="PixelPy - Pixellab Alternative", layout="centered")

st.title("🎨 PixelPy - Your Simple Image Editor")
st.markdown("Upload an image, add text, and download your creation!")

# --- Session State Initialization ---
if 'original_image_bytes' not in st.session_state:
    st.session_state.original_image_bytes = None
if 'processed_image_bytes' not in st.session_state:
    st.session_state.processed_image_bytes = None
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = "output_image.png"

# --- Image Upload ---
uploaded_file = st.file_uploader("Choose an image file", type=["png", "jpg", "jpeg", "webp"])

if uploaded_file is not None:
    # Read the image bytes once and store in session state
    st.session_state.original_image_bytes = uploaded_file.getvalue()
    st.session_state.uploaded_file_name = uploaded_file.name
    # Clear processed image bytes if a new image is uploaded
    st.session_state.processed_image_bytes = None

# --- Image Processing & Display ---
if st.session_state.original_image_bytes is not None:
    original_image = Image.open(io.BytesIO(st.session_state.original_image_bytes)).convert("RGBA")
    
    st.subheader("Add Text to Your Image")

    # Text Input
    text_input = st.text_area("Enter text to add:", "Hello, PixelPy!")

    # Font Size Slider
    font_size = st.slider("Font Size", 10, 200, 50)

    # Text Color Picker
    text_color = st.color_picker("Text Color", "#FFFFFF") # Default white

    # Text Position Sliders (relative to image dimensions for responsiveness)
    img_width, img_height = original_image.size
    
    pos_x_percent = st.slider("Text Position X (%)", 0, 100, 50)
    pos_y_percent = st.slider("Text Position Y (%)", 0, 100, 50)

    # Convert percentage to pixel coordinates
    text_x = int(img_width * pos_x_percent / 100)
    text_y = int(img_height * pos_y_percent / 100)

    # --- Apply Text Button ---
    if st.button("Apply Text"):
        processed_image = original_image.copy()
        draw = ImageDraw.Draw(processed_image)

        # Attempt to load a default font (Streamlit Cloud usually has common fonts)
        # You might need to specify a path to a .ttf file for more control
        try:
            # Using a generic font that should be available on most systems/Streamlit Cloud
            font = ImageFont.truetype("arial.ttf", font_size) 
        except IOError:
            st.warning("Could not find 'arial.ttf'. Using default PIL font (may not scale well).")
            font = ImageFont.load_default()
            font_size = 16 # Reset font size for default font as it doesn't scale with number

        # Calculate text bounding box to center text if needed
        # xy=(x,y), anchor="ms" means (x,y) is the middle-bottom of the text
        # xy=(x,y), anchor="mm" means (x,y) is the middle-middle of the text
        
        # Draw the text with a black outline for better visibility
        outline_color = (0, 0, 0) # Black
        outline_width = 2
        
        for x_offset in range(-outline_width, outline_width + 1):
            for y_offset in range(-outline_width, outline_width + 1):
                if x_offset != 0 or y_offset != 0: # Don't draw main text again
                    draw.text((text_x + x_offset, text_y + y_offset), text_input, font=font, fill=outline_color, anchor="mm")

        # Draw the main text
        draw.text((text_x, text_y), text_input, font=font, fill=text_color, anchor="mm")


        # Convert processed image back to bytes for storage and download
        buffered = io.BytesIO()
        processed_image.save(buffered, format="PNG") # Save as PNG to support transparency
        st.session_state.processed_image_bytes = buffered.getvalue()
        st.success("Text applied successfully! See preview below.")

    # --- Display Preview ---
    if st.session_state.processed_image_bytes is not None:
        st.subheader("Preview")
        st.image(st.session_state.processed_image_bytes, caption="Your edited image", use_column_width=True)

        # --- Download Button ---
        st.download_button(
            label="Download Edited Image",
            data=st.session_state.processed_image_bytes,
            file_name=f"pixelpy_{st.session_state.uploaded_file_name}",
            mime="image/png"
        )
    else:
        st.subheader("Original Image Preview")
        st.image(st.session_state.original_image_bytes, caption="Original Image", use_column_width=True)

else:
    st.info("Upload an image to start editing!")

st.markdown("---")
st.markdown("### How this works:")
st.markdown("- Uses `Streamlit` for the web interface.")
st.markdown("- Uses `Pillow` (PIL) for image manipulation.")
st.markdown("- **Note:** This is a basic example. Pixellab offers many more advanced features (3D text, shapes, effects, etc.) which would require significantly more complex code.")

st.set_page_config(page_title="AI Clip Generator", layout="wide")

st.title("🎬 AI Clip Generator (Opus Clip Alternative)")
st.markdown("Upload your video to extract, caption, and format engaging clips!")
st.warning("⚠️ **Important:** 'Engaging part' detection is based on a simple heuristic (longest speech segments) and will not be as intelligent or accurate as commercial tools like Opus Clip. Processing on free hosting (Streamlit Community Cloud) will be slow and may have limitations (e.g., timeouts, memory errors) for longer videos due to resource intensity.")

# --- Helper Functions ---
def random_filename(ext="mp4"):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + f".{ext}"

# Whisper model (cached for performance)
@st.cache_resource
def load_whisper_model():
    with st.spinner("Loading AI transcription model... (This might take a moment the first time)"):
        # Using a smaller model like 'base' for faster loading and lower memory usage
        # 'tiny' is even smaller, 'small', 'medium', 'large' are larger/slower but more accurate.
        return whisper.load_model("base") 

# Function to transcribe the entire video and return all segments
def transcribe_full_video(video_path):
    st.info("Transcribing entire video for segment analysis...")
    temp_audio_path = os.path.join(tempfile.gettempdir(), random_filename(ext="mp3"))
    try:
        video_clip = VideoFileClip(video_path)
        audio_clip = video_clip.audio
        audio_clip.write_audiofile(temp_audio_path)
        
        # Perform transcription
        result = whisper_model.transcribe(temp_audio_path)
        return result["segments"]
    except Exception as e:
        st.error(f"Error during full video audio extraction or transcription: {e}")
        return []
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

# Function to automatically find "engaging" clips based on heuristics
def find_engaging_clips(segments, video_duration, num_clips=3, min_clip_duration=10):
    st.info(f"Looking for engaging clips (longest speech segments)...")
    candidate_clips = []
    
    # Filter segments that are primarily speech and of a reasonable length
    for i, segment in enumerate(segments):
        # Calculate the actual duration of the transcribed speech within the segment
        segment_speech_duration = segment["end"] - segment["start"]
        
        # Consider segments with actual speech duration > min_clip_duration
        if segment_speech_duration >= min_clip_duration:
            candidate_clips.append({
                "start": segment["start"],
                "end": segment["end"],
                "duration": segment_speech_duration,
                "text": segment["text"] # Store text for context
            })
            
    # Sort candidates by duration (longest first)
    candidate_clips.sort(key=lambda x: x["duration"], reverse=True)
    
    # Select top N clips
    engaging_clips = []
    for i, clip_data in enumerate(candidate_clips[:num_clips]):
        engaging_clips.append({
            "start_time": clip_data["start"],
            "end_time": clip_data["end"],
            "name": f"Auto-Clip {i+1} (approx. {clip_data['duration']:.1f}s)"
        })
    
    if not engaging_clips:
        st.warning("Could not automatically find engaging clips based on current heuristics. Please try adding clips manually.")
        # Add a default manual clip if no auto clips are found
        engaging_clips.append({"start_time": 0.0, "end_time": min(30.0, video_duration), "name": "Manual Clip 1"})
    
    return engaging_clips


def add_captions_and_process_clip(
    video_path, all_segments, clip_start, clip_end,
    font_size=24, font_color="white",
    aspect_ratio="original", clip_name="output_clip"
):
    st.info(f"Processing clip '{clip_name}' with captions and formatting...")
    try:
        full_video = VideoFileClip(video_path)
        clip = full_video.subclip(clip_start, clip_end)
    except Exception as e:
        st.error(f"Error loading or sub-clipping video: {e}")
        return None

    # Update clip size after aspect ratio adjustments
    current_width, current_height = clip.size
    final_width, final_height = current_width, current_height

    # 1. Handle Aspect Ratio
    if aspect_ratio == "9:16": # Vertical - for Shorts, Reels, TikTok
        target_height = int(current_width * 16 / 9)
        if target_height > current_height: # Original is too short, pad height
            final_width, final_height = current_width, target_height
            clip = clip.resize(height=target_height)
            # Create a black background and composite the resized video
            bg_clip = VideoFileClip(clip.filename, size=(final_width, final_height), bg_color=(0,0,0)).set_duration(clip.duration)
            clip = CompositeVideoClip([clip.set_position(("center", "center"))], size=(final_width, final_height))
        else: # Original is too wide, crop width
            target_width = int(current_height * 9 / 16)
            clip = clip.crop(x_center=current_width/2, y_center=current_height/2, width=target_width, height=current_height)
            final_width, final_height = clip.size # Update final dimensions after crop

    elif aspect_ratio == "1:1": # Square
        side = min(current_width, current_height)
        if current_width != current_height: # Only crop if not already square
            clip = clip.crop(x_center=current_width/2, y_center=current_height/2, width=side, height=side)
        final_width, final_height = clip.size

    elif aspect_ratio == "16:9": # Standard landscape
        target_width = int(current_height * 16 / 9)
        if target_width > current_width: # Original is too narrow, pad width
            final_width, final_height = target_width, current_height
            clip = clip.resize(width=target_width)
            # Create a black background and composite the resized video
            bg_clip = VideoFileClip(clip.filename, size=(final_width, final_height), bg_color=(0,0,0)).set_duration(clip.duration)
            clip = CompositeVideoClip([clip.set_position(("center", "center"))], size=(final_width, final_height))
        else: # Original is too tall, crop height
            target_height = int(current_width * 9 / 16)
            clip = clip.crop(x_center=current_width/2, y_center=current_height/2, width=current_width, height=target_height)
            final_width, final_height = clip.size # Update final dimensions after crop
    
    # 2. Add Captions
    caption_clips = []
    # Filter segments that fall within the current clip's time range
    # and adjust their times to be relative to the start of the current `clip`
    
    # Ensure all_segments are sorted by start time for easier processing
    all_segments.sort(key=lambda s: s["start"])

    for segment in all_segments:
        # Check if the segment overlaps with the current clip
        if max(clip_start, segment["start"]) < min(clip_end, segment["end"]):
            # Calculate the portion of the segment that is within the current clip
            segment_in_clip_start = max(clip_start, segment["start"])
            segment_in_clip_end = min(clip_end, segment["end"])
            
            # Calculate relative start and end times for the current subclip
            relative_start = segment_in_clip_start - clip_start
            relative_end = segment_in_clip_end - clip_start
            
            caption_text = str(segment["text"]).strip()
            if not caption_text or relative_end <= relative_start: # Skip empty text or zero-duration
                continue

            try:
                caption = TextClip(caption_text, 
                                   fontsize=font_size, 
                                   color=font_color, 
                                   size=(final_width * 0.9, None), # Max 90% width, auto height
                                   method='caption', 
                                   align='center',
                                   stroke_color='black', 
                                   stroke_width=1.5,
                                   font="Arial" # Specify a common font
                                  )
                caption = caption.set_start(relative_start).set_duration(relative_end - relative_start)
                caption = caption.set_position(("center", final_height * 0.85)) # Position near bottom
                caption_clips.append(caption)
            except Exception as e:
                st.warning(f"Could not create text clip for segment '{caption_text}': {e}")
                continue

    final_video = CompositeVideoClip([clip] + caption_clips, size=(final_width, final_height))
    
    # Create a unique temporary directory for each output clip
    output_dir = tempfile.mkdtemp()
    temp_out_path = os.path.join(output_dir, random_filename(ext="mp4"))

    try:
        # Use a more robust codec and lower preset for faster rendering on limited resources
        final_video.write_videofile(temp_out_path, codec="libx264", audio_codec="aac", fps=clip.fps, preset="medium", threads=1)
        return temp_out_path
    except Exception as e:
        st.error(f"Error writing output video for '{clip_name}': {e}")
        st.error("This could be due to an issue with FFmpeg, video codecs, or insufficient disk space.")
        st.info("Try a shorter video or simpler settings if you encounter this frequently.")
        return None
    finally:
        pass # We will clean up in the main app logic after download

# --- Streamlit UI ---
input_col, preview_col = st.columns([1, 2])

# --- Global variables for cleanup ---
video_path = None
temp_file_dirs = [] # Store directories to clean up later
full_video_segments = [] # To store transcription results

with input_col:
    st.header("1. Upload Video")
    uploaded_file = st.file_uploader("Upload your video file", type=["mp4", "mov", "avi", "mkv"])
    
    if uploaded_file:
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())
        video_path = temp_path
        temp_file_dirs.append(temp_dir)
        st.success("Video uploaded successfully!")

        # Transcribe the entire video immediately after upload for segment analysis
        with st.spinner("Transcribing video for engaging clip detection..."):
            full_video_segments = transcribe_full_video(video_path)
            st.session_state['full_video_segments'] = full_video_segments
            
            # Autogenerate engaging clips suggestions
            video_duration = VideoFileClip(video_path).duration
            suggested_clips = find_engaging_clips(full_video_segments, video_duration)
            
            # Initialize or update session state for clips data
            if 'clips_data' not in st.session_state or not st.session_state.clips_data:
                 st.session_state.clips_data = suggested_clips
            else:
                 # If user has already added clips, just add suggestions
                 # Or you could replace them based on a button click
                 pass # For now, let's keep it simple and just populate if empty

if video_path:
    with preview_col:
        st.header("2. Video Preview & Clip Selection")
        st.video(video_path)
        
        # Display full video duration
        video_clip_for_duration = VideoFileClip(video_path)
        full_duration = video_clip_for_duration.duration
        st.info(f"Full video duration: {full_duration:.2f} seconds")
        video_clip_for_duration.close() # Release the file

        st.markdown("---")
        st.subheader("Define Your Clips:")
        if 'clips_data' not in st.session_state:
            st.session_state.clips_data = [] # Initialize if no video was uploaded yet

        # Add new clip button
        if st.button("➕ Add New Manual Clip"):
            st.session_state.clips_data.append({"start_time": 0.0, "end_time": min(10.0, full_duration), "name": f"Manual Clip {len(st.session_state.clips_data) + 1}"})
            st.rerun() # Rerun to show new clip immediately

        # Display and edit existing clips
        if st.session_state.clips_data:
            st.info("Suggested clips are initialized automatically. Adjust or add new ones below.")
            for i, clip_data in enumerate(st.session_state.clips_data):
                st.markdown(f"**Clip {i+1} Settings**")
                clip_data["name"] = st.text_input(f"Clip {i+1} Name", value=clip_data["name"], key=f"clip_name_{i}")
                
                col_start, col_end = st.columns(2)
                with col_start:
                    clip_data["start_time"] = st.number_input(
                        "Start (seconds)", 
                        min_value=0.0, 
                        max_value=full_duration, 
                        value=min(clip_data["start_time"], full_duration), # Ensure value is within bounds
                        step=0.5, 
                        key=f"start_time_{i}"
                    )
                with col_end:
                    clip_data["end_time"] = st.number_input(
                        "End (seconds)", 
                        min_value=clip_data["start_time"], 
                        max_value=full_duration, 
                        value=min(clip_data["end_time"], full_duration), 
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
        elif 'full_video_segments' not in st.session_state or not st.session_state['full_video_segments']:
            st.error("Video transcription not complete or failed. Please re-upload the video.")
        else:
            with st.spinner("Generating clips... This may take a while depending on video length and number of clips."):
                generated_clips_paths = []
                all_segments_for_processing = st.session_state['full_video_segments']

                for i, clip_data in enumerate(st.session_state.clips_data):
                    clip_start = clip_data["start_time"]
                    clip_end = clip_data["end_time"]
                    clip_name = clip_data["name"]

                    if clip_start >= clip_end:
                        st.error(f"Skipping '{clip_name}': Invalid time range (End time must be greater than start time).")
                        continue

                    output_clip_path = add_captions_and_process_clip(
                        video_path, all_segments_for_processing, clip_start, clip_end,
                        font_size, font_color, selected_aspect_ratio, clip_name
                    )
                    if output_clip_path:
                        generated_clips_paths.append((clip_name, output_clip_path))
                    else:
                        st.error(f"Failed to process clip: '{clip_name}'")

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
                        # Remove the parent directory of the generated clip
                        # Make sure not to remove the main temp_dir if other files are there
                        if os.path.exists(os.path.dirname(path)) and os.path.isdir(os.path.dirname(path)):
                             try:
                                 shutil.rmtree(os.path.dirname(path))
                             except OSError as e:
                                 st.warning(f"Error cleaning up output temporary directory {os.path.dirname(path)}: {e}")

                else:
                    st.warning("No clips were successfully generated.")


# --- Cleanup of input temporary files (important for resource management) ---
# This part runs whenever the script is re-executed (e.g., on widget interaction).
# For a more robust cleanup in a deployed app, consider using st.session_state to track files
# and clean them up when the user leaves the session or starts a new upload.
# For simplicity here, we rely on tempfile's general cleanup and Streamlit's session behavior.
for d_path in temp_file_dirs:
    if os.path.exists(d_path):
        try:
            shutil.rmtree(d_path)
        except OSError as e:
            st.warning(f"Error cleaning up input temporary directory {d_path}: {e}")
