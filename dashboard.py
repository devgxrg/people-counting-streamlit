import streamlit as st
import base64

# Streamlit layout
st.set_page_config(layout="wide")
st.title("📹 People Counting Dashboard")
st.markdown("### Comparison: Raw Video vs Processed Output")

# Function to load and base64 encode video
def video_base64(path):
    with open(path, 'rb') as file:
        video_data = file.read()
    return base64.b64encode(video_data).decode()

# Get base64 video strings
input_b64 = video_base64("input_video.mp4")
output_b64 = video_base64("output_video.mp4")

# HTML + JS to sync video playback
video_html = f"""
<div style="display: flex; gap: 20px;">
    <div style="flex: 1;">
        <h4>🎥 Raw Input</h4>
        <video id="video1" width="100%" autoplay loop muted playsinline>
            <source src="data:video/mp4;base64,{input_b64}" type="video/mp4">
        </video>
    </div>
    <div style="flex: 1;">
        <h4>🧠 Processed Output (People Inside Only)</h4>
        <video id="video2" width="100%" autoplay loop muted playsinline>
            <source src="data:video/mp4;base64,{output_b64}" type="video/mp4">
        </video>
    </div>
</div>

<script>
    const v1 = document.getElementById('video1');
    const v2 = document.getElementById('video2');

    function syncVideos() {{
        v2.currentTime = v1.currentTime;
    }}

    v1.onplay = () => {{
        v2.play();
        syncVideos();
    }};
    v1.ontimeupdate = syncVideos;
</script>
"""

# Render synced videos
st.markdown(video_html, unsafe_allow_html=True)

# Optional stats section
st.markdown("---")
st.subheader("🧾 Summary")
st.markdown("- Real-time people counting inside the defined region")
st.markdown("- Output includes inflow, outflow, and current inside count")
