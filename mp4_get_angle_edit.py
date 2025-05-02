# -*- coding: utf-8 -*-
"""
Created on Sat May  3 01:02:09 2025

@author: ktrpt
"""
import streamlit as st
import cv2
import numpy as np
import tempfile
from PIL import Image
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="Angle Inspector", layout="wide")

def load_video_to_tempfile(uploaded_file):
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tfile.write(uploaded_file.getbuffer())
    return tfile.name

def get_frame(cap, frame_idx):
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    if not ret:
        st.error("Failed to read frame.")
        st.stop()
    return frame

def angle_between_lines(p1, p2, p3, p4):
    v1 = np.array(p2) - np.array(p1)
    v2 = np.array(p4) - np.array(p3)
    v1_u, v2_u = v1 / np.linalg.norm(v1), v2 / np.linalg.norm(v2)
    cosang = np.clip(np.dot(v1_u, v2_u), -1.0, 1.0)
    return np.degrees(np.arccos(cosang))

uploaded = st.sidebar.file_uploader("Upload an MP4", type=["mp4"])
if uploaded is None:
    st.sidebar.info("👈 Upload a video to begin")
    st.stop()

video_path = load_video_to_tempfile(uploaded)
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    st.error("Could not open the uploaded video.")
    st.stop()

frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS) or 30

if "points" not in st.session_state or len(st.session_state.points) != 4:
    st.session_state.points = [[0.3, 0.3], [0.7, 0.3], [0.3, 0.7], [0.7, 0.7]]

frame_idx = st.slider(
    f"Frame position ({frame_count} frames, {fps:.1f} fps)",
    min_value=0,
    max_value=frame_count - 1,
    value=0,
)

bgr = get_frame(cap, frame_idx)
rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
image_pil = Image.fromarray(rgb)

max_width = 800
scale = min(1.0, max_width / image_pil.width)
new_w, new_h = int(image_pil.width * scale), int(image_pil.height * scale)
image_pil = image_pil.resize((new_w, new_h))
w, h = image_pil.size

# 点オブジェクト作成
initial_objects = []
for i, (x, y) in enumerate(st.session_state.points):
    initial_objects.append({
        "type": "circle",
        "radius": 6,
        "fill": "rgba(255,255,255,0.8)",
        "stroke": "#ffffff",
        "left": x * w - 6,
        "top": y * h - 6,
        "name": f"pt{i+1}",
    })

# 線オブジェクト作成（点1-2, 点3-4）
px = [x * w for x, y in st.session_state.points]
py = [y * h for x, y in st.session_state.points]
initial_objects.append({
    "type": "line",
    "x1": px[0], "y1": py[0], "x2": px[1], "y2": py[1],
    "stroke": "#ffffff", "strokeWidth": 2,
})
initial_objects.append({
    "type": "line",
    "x1": px[2], "y1": py[2], "x2": px[3], "y2": py[3],
    "stroke": "#ffffff", "strokeWidth": 2,
})

canvas = st_canvas(
    fill_color="rgba(255, 165, 0, 0.0)",
    stroke_width=2,
    background_image=image_pil,
    height=h,
    width=w,
    drawing_mode="transform",
    initial_drawing={"version": "4.6.0", "objects": initial_objects},
    key=f"canvas_{frame_idx}",
)

# 座標更新（円のみ）
if canvas.json_data:
    objs = [obj for obj in canvas.json_data.get("objects", []) if obj["type"] == "circle"]
    if len(objs) == 4:
        st.session_state.points = [
            [(obj["left"] + obj.get("radius", 0)) / w, (obj["top"] + obj.get("radius", 0)) / h]
            for obj in objs
        ]

# 角度計算
p = st.session_state.points
pix_pts = [(x * w, y * h) for x, y in p]
angle = angle_between_lines(pix_pts[0], pix_pts[1], pix_pts[2], pix_pts[3])

st.markdown(f"### Angle: **{angle:.2f}°**  (Line 1: p1-p2, Line 2: p3-p4)")

def snapshot():
    out = np.array(image_pil).copy()
    for (x, y) in pix_pts:
        cv2.circle(out, (int(x), int(y)), 6, (255, 255, 255), -1)
    cv2.line(out, tuple(map(int, pix_pts[0])), tuple(map(int, pix_pts[1])), (255, 255, 255), 2)
    cv2.line(out, tuple(map(int, pix_pts[2])), tuple(map(int, pix_pts[3])), (255, 255, 255), 2)
    fn = f"snapshot_{frame_idx}.png"
    cv2.imwrite(fn, cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
    return fn

if st.button("📸 Save snapshot"):
    filename = snapshot()
    with open(filename, "rb") as f:
        st.download_button("Download image", f, file_name=filename, mime="image/png")
