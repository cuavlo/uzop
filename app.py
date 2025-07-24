import streamlit as st
import os

# --- Configuration ---
# No longer strictly needed for just uploads, but good practice if you were to process them
# TEMP_DIR = "temp_videos"
# if not os.path.exists(TEMP_DIR):
#     os.makedirs(TEMP_DIR)

# --- Streamlit App Layout ---
st.set_page_config(
    page_title="Simple Video Uploader",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 Video Uploader")
st.write("Upload a video file from your device.")

# --- Video Upload Section ---
st.header("Upload Your Video File")
uploaded_file = st.file_uploader(
    "Choose a video file",
    type=["mp4", "mov", "avi", "mkv"],
    help="Supports MP4, MOV, AVI, and MKV formats."
)

if uploaded_file is not None:
    st.subheader("Uploaded Video:")
    st.video(uploaded_file)
    st.success("Video uploaded successfully!")

    # Offer download button for the uploaded video (it's already on the user's device,
    # but this button would allow them to re-download if needed after viewing in the app)
    # For a true "export to phone" after processing, you'd add processing logic here.
    st.download_button(
        label="Download Video",
        data=uploaded_file,
        file_name=uploaded_file.name,
        mime=uploaded_file.type
    )

# --- About Section ---
st.sidebar.markdown("---")
st.sidebar.markdown("### About This App")
st.sidebar.info("This is a basic Streamlit application for uploading and displaying video files.")
st.sidebar.markdown("No advanced AI features (like automatic clip detection or dynamic captions) are included in this basic example. For those features, significant programming and AI/ML expertise are required.")

# You might want a more sophisticated cleanup mechanism for a production app
# For Streamlit Community Cloud, temporary files are usually cleared between sessions.
