# app.py
import math
import requests
import streamlit as st
from urllib.parse import urlencode

st.set_page_config(page_title="Museum Collection Search", page_icon="🏛️", layout="wide")

BASE = "https://collectionapi.metmuseum.org/public/collection/v1"

@st.cache_data(ttl=60*60)
def get_departments():
    r = requests.get(f"{BASE}/departments", timeout=20)
    r.raise_for_status()
    data = r.json().get("departments", [])
    # 做成 id->name 的映射，和一个选择列表
    dept_map = {d["departmentId"]: d["displayName"] for d in data}
    choices = [{"label": d["displayName"], "value": d["departmentId"]} for d in data]
    return dept_map, choices

@st.cache_data(ttl=60)
def met_search(params: dict):
    """调用 /search 返回满足条件的 objectIDs 列表"""
    r = requests.get(f"{BASE}/search", params=params, timeout=30)
    r.raise_for_status()
    js = r.json()
    return js.get("total", 0), js.get("objectIDs", []) or []

@st.cache_data(ttl=60*10)
def get_object(obj_id: int):
    r = requests.get(f"{BASE}/objects/{obj_id}", timeout=30)
    r.raise_for_status()
    return r.json()

def querystring(**kwargs):
    """把筛选参数转成 querystring，方便展示/分享"""
    clean = {k:v for k,v in kwargs.items() if v not in (None, "", [], False)}
    return urlencode(clean, doseq=True)

st.title("🏛️ Museum Collection Search — The Met")
st.caption("搜索纽约大都会艺术博物馆（The Met）的开放藏品，支持关键词、部门、媒介、年代等筛选。数据来自官方开放 API。")

# ---------------- Sidebar: Filters ----------------
dept_map, dept_choices = get_departments()

with st.sidebar:
    st.header("🔎 搜索与筛选")
    q = st.text_input("关键词 (q)", value="cat")  # 默认给个例子，便于首次打开有结果
    colA, colB = st.columns(2)
    with colA:
        date_begin = st.number_input("起始年份 (dateBegin)", value=None, placeholder="如 1700 或 -100", step=1, format="%d", label_visibility="visible")
    with colB:
        date_end = st.number_input("结束年份 (dateEnd)", value=None, placeholder="如 1800 或 100", step=1, format="%d", label_visibility="visible")

    dept = st.selectbox("部门 (departmentId)", options=[None] + [c["value"] for c in dept_choices],
                        format_func=lambda x: "全部部门" if x is None else dept_map[x])

    has_images = st.checkbox("仅有图片的 (hasImages=true)", value=True)
    is_highlight = st.checkbox("馆藏精选 (isHighlight=true)", value=False)
    is_on_view = st.checkbox("目前在展厅展出 (isOnView=true)", value=False)
    artist_or_culture = st.checkbox("从艺术家或文化字段检索 (artistOrCulture=true)", value=False)

    medium = st.text_input("媒介 / 类型 (medium)", placeholder="Paintings|Textiles 等，| 分隔可多选")
    geo = st.text_input("地理位置 (geoLocation)", placeholder="France、China、Paris 等，| 分隔可多选")
    title_only = st.checkbox("仅在标题中搜 (title=true)", value=False)
    tags_only = st.checkbox("仅在主题标签中搜 (tags=true)", value=False)

    st.divider()
    page_size = st.select_slider("每页数量", options=[12, 24, 48], value=24)
    page = st.number_input("页码", min_value=1, value=1, step=1)

# ---------------- Build search params ----------------
search_params = {"q": q or ""}

# 可选过滤项（Met 搜索支持的参数）
# 参考官方文档：/search endpoints 的参数
if has_images: search_params["hasImages"] = "true"
if is_highlight: search_params["isHighlight"] = "true"
if is_on_view: search_params["isOnView"] = "true"
if artist_or_culture: search_params["artistOrCulture"] = "true"
if title_only: search_params["title"] = "true"
if tags_only: search_params["tags"] = "true"
if dept is not None: search_params["departmentId"] = int(dept)
if medium: search_params["medium"] = medium
if geo: search_params["geoLocation"] = geo
# 年代必须成对使用
if (date_begin is not None) and (date_end is not None):
    search_params["dateBegin"] = int(date_begin)
    search_params["dateEnd"] = int(date_end)

# ---------------- Execute search ----------------
col_left, col_right = st.columns([3, 2], gap="large")

with col_left:
    run = st.button("🚀 搜索 / 刷新", type="primary")
    if run or "last_results" not in st.session_state:
        total, ids = met_search(search_params)
        st.session_state["last_results"] = {"total": total, "ids": ids, "params": search_params}
    total = st.session_state["last_results"]["total"]
    ids = st.session_state["last_results"]["ids"]
    st.write(f"共找到 **{total}** 件相关藏品。")

    if total == 0 or not ids:
        st.info("换个关键词或放宽筛选试试～")
    else:
        # 简单分页（在 objectIDs 列表上切片）
        start = (page - 1) * page_size
        end = min(start + page_size, len(ids))
        page_ids = ids[start:end]

        # 结果宫格
        cols = st.columns(3)
        for i, oid in enumerate(page_ids):
            data = get_object(oid)
            with cols[i % 3]:
                img = data.get("primaryImageSmall") or data.get("primaryImage")
                title = data.get("title") or "(untitled)"
                artist = data.get("artistDisplayName") or data.get("culture") or "-"
                date = data.get("objectDate") or f'{data.get("objectBeginDate","")}-{data.get("objectEndDate","")}'
                dept_name = data.get("department") or "-"
                obj_url = data.get("objectURL")  # The Met 官网详情页

                if img:
                    st.image(img, use_container_width=True)
                st.markdown(f"**{title}**")
                st.caption(f"{artist} · {date}\n\n{dept_name}")
                if obj_url:
                    st.link_button("详情页（metmuseum.org）", obj_url, type="secondary", use_container_width=True)

        # 分页导航
        total_pages = max(1, math.ceil(len(ids) / page_size))
        st.write(f"第 **{page} / {total_pages}** 页（注：API 先返回全部 ID，本页仅显示所选切片）")

with col_right:
    st.subheader("当前检索参数")
    st.code(search_params, language="json")
    st.caption("（Tip）把这些参数记下来，后端可直接复用到 API 请求里。")

    st.subheader("分享链接（仅参数展示）")
    st.code(querystring(**search_params), language="bash")
    st.caption("你可以把 querystring 附在自己的说明里，或收藏常用组合。")

st.divider()
with st.expander("ℹ️ 数据来源与接口说明", expanded=False):
    st.markdown(
        """
- **The Met Collection API**：无需 API Key，速率建议≤ 80 req/s；提供 `/search`、`/objects/{id}`、`/departments` 等端点。  
- 本应用流程：先调用 **/search** 得到 `objectIDs` → 根据分页切片逐个调用 **/objects/{id}** 获取详情与图像 URL。  
        """
    )
