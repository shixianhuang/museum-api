# app.py
import random
import math
import io
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import streamlit as st

# -------------------------------
# Streamlit Page Config
# -------------------------------
st.set_page_config(
    page_title="Generative Abstract Poster",
    page_icon="🎨",
    layout="wide"
)

# -------------------------------
# Utils: palette & blob geometry
# -------------------------------
def random_palette(k=6, seed=None):
    rng = random.Random(seed)
    return [(rng.random(), rng.random(), rng.random()) for _ in range(k)]

def blob(center=(0.5, 0.5), r=0.3, points=220, wobble=0.15, seed=None):
    rng = np.random.default_rng(seed)
    angles = np.linspace(0, 2*math.pi, points)
    radii = r * (1 + wobble*(rng.random(points)-0.5))
    x = center[0] + radii * np.cos(angles)
    y = center[1] + radii * np.sin(angles)
    return x, y

def draw_poster(
    width=800, height=1200, n_layers=6, wobble=0.15, base_r=0.35,
    seed=None, bg_color=(1,1,1), stroke=False, stroke_alpha=0.7
):
    dpi = 100
    fig_w = width / dpi
    fig_h = height / dpi

    # 单图，不指定配色（遵循要求：不设置特定颜色风格）
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    ax = plt.axes([0,0,1,1])
    ax.set_xlim(0,1)
    ax.set_ylim(0,1)
    ax.axis('off')
    ax.set_facecolor(bg_color)

    # 随机调色板
    palette = random_palette(k=n_layers+1, seed=seed)

    # 分层绘制“果冻”形状
    rng = np.random.default_rng(seed)
    for i in range(n_layers):
        cx = rng.uniform(0.3, 0.7)
        cy = rng.uniform(0.3, 0.7)
        r = base_r * (1 - i/(n_layers+2)) * rng.uniform(0.85, 1.15)
        x, y = blob(center=(cx, cy), r=r, wobble=wobble*rng.uniform(0.8,1.2), seed=seed+i)
        ax.fill(x, y, alpha=0.8, facecolor=palette[i], linewidth=0)
        if stroke:
            ax.plot(x, y, alpha=stroke_alpha)

    # 返回 Pillow Image
    buf = io.BytesIO()
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8).reshape(h, w, 3)
    plt.close(fig)
    return Image.fromarray(img)

# -------------------------------
# Sidebar Controls
# -------------------------------
st.sidebar.title("🎛 Controls")

seed = st.sidebar.number_input("Random Seed (可复现)", value=42, step=1)
canvas_w = st.sidebar.slider("Width (px)", 600, 2000, 900, step=50)
canvas_h = st.sidebar.slider("Height (px)", 600, 3000, 1400, step=50)
n_layers = st.sidebar.slider("Layers", 1, 20, 8, step=1)
wobble = st.sidebar.slider("Wobble (形变强度)", 0.01, 0.60, 0.18, step=0.01)
base_r = st.sidebar.slider("Base Radius (相对尺寸)", 0.10, 0.60, 0.35, step=0.01)
stroke = st.sidebar.checkbox("Outline Stroke", value=False)
stroke_alpha = st.sidebar.slider("Stroke Alpha", 0.1, 1.0, 0.6, step=0.1)

bg_white = st.sidebar.radio("Background", ["White", "Black", "Random"], index=0)
if bg_white == "White":
    bg_color = (1,1,1)
elif bg_white == "Black":
    bg_color = (0,0,0)
else:
    rng_tmp = random.Random(seed)
    bg_color = (rng_tmp.random(), rng_tmp.random(), rng_tmp.random())

# -------------------------------
# Main UI
# -------------------------------
st.title("🎨 Generative Abstract Poster")
st.caption("无需外部 API，本地/云端皆可运行。调节参数 → 生成 → 下载 PNG。")

col1, col2 = st.columns([3,2], gap="large")

with col1:
    if st.button("✨ Generate Poster", type="primary"):
        st.session_state["poster_img"] = draw_poster(
            width=canvas_w, height=canvas_h, n_layers=n_layers,
            wobble=wobble, base_r=base_r, seed=seed,
            bg_color=bg_color, stroke=stroke, stroke_alpha=stroke_alpha
        )

    poster = st.session_state.get("poster_img", None)
    if poster is not None:
        st.image(poster, caption="Preview", use_container_width=True)
        # 下载
        buf = io.BytesIO()
        poster.save(buf, format="PNG")
        st.download_button(
            label="📥 Download PNG",
            data=buf.getvalue(),
            file_name=f"poster_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            mime="image/png"
        )
    else:
        st.info("点击左侧调整参数，然后点 **Generate Poster** 生成预览。")

with col2:
    st.subheader("Tips")
    st.markdown(
        """
- **Seed** 控制随机数种子：同样的参数 + 同样的 seed → 可复现图像  
- **Layers** 越多层，效果越丰富  
- **Wobble** 控制形变程度  
- **Base Radius** 控制基础半径（越大元素越大）  
- **Background** 支持白/黑/随机色  
- **Outline Stroke** 给图形描边  
        """
    )
    st.divider()
    st.subheader("About")
    st.markdown(
        """
本应用适合作品集、课堂展示、社媒封面。你也可以把生成图作为“舞蹈/时尚品牌视觉元素”海报背景。
        """
    )
