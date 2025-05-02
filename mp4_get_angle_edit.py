# -*- coding: utf-8 -*-
"""
Created on Sat May  3 01:02:09 2025

@author: ktrpt
"""
import streamlit as st
import cv2
import numpy as np
import json
import tempfile
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="Angle Inspector", layout="wide")
# ---------------- Utility functions ---------------- #

def load_video_to_tempfile(uploaded_file):
    """Write the uploaded file to a NamedTemporaryFile so OpenCV can read it"""
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tfile.write(uploaded_file.getbuffer())
    return tfile.name


def get_frame(cap, frame_idx):
    """Return BGR frame at position 'frame_idx' (0‑based)"""
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    if not ret:
        st.error("Failed to read frame.")
        st.stop()
    return frame


def angle_between_lines(p1, p2, p3, p4):
    """Compute angle between line p1‑p2 and line p3‑p4 in degrees."""
    v1 = np.array(p2) - np.array(p1)
    v2 = np.array(p4) - np.array(p3)
    v1_u, v2_u = v1 / np.linalg.norm(v1), v2 / np.linalg.norm(v2)
    cosang = np.clip(np.dot(v1_u, v2_u), -1.0, 1.0)
    return np.degrees(np.arccos(cosang))


# ---------------- Sidebar: video load ---------------- #

uploaded = st.sidebar.file_uploader("Upload an MP4", type=["mp4"])
if uploaded is None:
    st.sidebar.info("👈 Upload a video to begin")
    st.stop()

video_path = load_video_to_tempfile(uploaded)
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    st.error("Could not open the uploaded video.")
    st.stop()

frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS) or 30

default_points = [
    [0.3, 0.3],  # (x, y) normalized 0‑1
    [0.7, 0.3],
    [0.3, 0.7],
    [0.7, 0.7],
]
if "points" not in st.session_state:
    st.session_state.points = default_points

# ---------------- Main UI ---------------- #

frame_idx = st.slider(
    "Frame position ({} frames, {:.1f} fps)".format(frame_count, fps),
    min_value=0,
    max_value=frame_count - 1,
    value=0,
)

bgr = get_frame(cap, frame_idx)
rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
h, w, _ = rgb.shape

# Convert current points to Fabric.js circles for the canvas
initial_objects = [
    {
        "type": "circle",
        "radius": 6,
        "fill": "rgba(255,255,255,0.8)",
        "stroke": "#ffffff",
        "left": x * w - 6,
        "top": y * h - 6,
    }
    for x, y in st.session_state.points
]

canvas = st_canvas(
    fill_color="rgba(255, 165, 0, 0.0)",  # transparent fill
    stroke_width=2,
    background_image=rgb,
    height=h,
    width=w,
    drawing_mode="transform",
    initial_drawing=json.dumps({"version": "4.6.0", "objects": initial_objects}),
    key="canvas",
)

# If the user moved the points, update state
if canvas.json_data and len(canvas.json_data.get("objects", [])) == 4:
    objs = canvas.json_data["objects"]
    st.session_state.points = [
        [ (obj["left"] + obj.get("radius", 0)) / w, (obj["top"] + obj.get("radius", 0)) / h ]
        for obj in objs
    ]

# Calculate angle using updated points
p = st.session_state.points
pix_pts = [ (x * w, y * h) for x, y in p ]
angle = angle_between_lines(pix_pts[0], pix_pts[1], pix_pts[2], pix_pts[3])

st.markdown(
    f"### Angle: **{angle:.2f}°**  (Line 1: p1‑p2, Line 2: p3‑p4)"
)

# Allow snapshot of current annotation
def snapshot():
    out = rgb.copy()
    # draw circles & lines on snapshot
    for (x, y) in pix_pts:
        cv2.circle(out, (int(x), int(y)), 6, (255, 255, 255), -1)
    cv2.line(out, pix_pts[0], pix_pts[1], (255, 255, 255), 2)
    cv2.line(out, pix_pts[2], pix_pts[3], (255, 255, 255), 2)
    fn = f"snapshot_{frame_idx}.png"
    cv2.imwrite(fn, cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
    return fn

if st.button("📸 Save snapshot"):
    filename = snapshot()
    with open(filename, "rb") as f:
        btn = st.download_button("Download image", f, file_name=filename, mime="image/png")
