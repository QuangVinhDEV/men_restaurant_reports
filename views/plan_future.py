import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.title("🚀 Strategic Planning & Forecasting")
st.info("Sử dụng dữ liệu lịch sử để dự báo doanh thu và lập chiến lược cho tuần tới.")

# =====================
# 1. SMART FORECASTING (Dự báo thông minh)
# =====================
# =====================
# 1. SMART FORECASTING (Dự báo thông minh)
# =====================
st.subheader("🔮 Weekly Revenue Forecast")

# --- BƯỚC 1: LẤY DỮ LIỆU TUẦN TRƯỚC (LAST WEEK) ---
df_rev = pd.read_csv('data/silver_layer/df_revenue_per_date.csv', sep=';')
# 1. Đảm bảo cột date là kiểu datetime
# errors='coerce' sẽ giúp tránh lỗi nếu có dòng dữ liệu rác (trả về NaT thay vì dừng chương trình)
df_rev['date'] = pd.to_datetime(df_rev['date'], errors='coerce')

# 2. Loại bỏ các dòng có ngày tháng bị lỗi (NaT) nếu có
df_rev = df_rev.dropna(subset=['date'])

# 3. Sau đó mới thực hiện logic dự báo
last_date = df_rev['date'].max()

# Sử dụng .dt sau khi đã chắc chắn dữ liệu là datetime
last_week_num = df_rev['date'].dt.isocalendar().week.max()

# Lọc dữ liệu của tuần gần nhất có trong data
last_week_data = df_rev[df_rev['date'].dt.isocalendar().week == last_week_num]

# Tính toán các chỉ số thực tế của tuần trước
# --- CÁCH TÍNH ĐÚNG ĐỂ KHỚP SỐ ---
lw_revenue = last_week_data['revenue'].sum()
lw_tc = last_week_data['TC'].sum()

# KHÔNG dùng .mean(), hãy dùng tổng chia tổng
lw_ac = lw_revenue / lw_tc if lw_tc > 0 else 0

# --- BƯỚC 2: THIẾT LẬP KỲ VỌNG TĂNG TRƯỞNG ---
col_slider1, col_slider2 = st.columns(2)
with col_slider1:
    growth_tc = st.slider("Kỳ vọng tăng trưởng TC (%)", -20, 50, 5, help="Dự đoán số lượng khách tăng/giảm")
with col_slider2:
    growth_ac = st.slider("Kỳ vọng thay đổi AC (%)", -10, 30, 2, help="Dự đoán khách chi tiêu mạnh hơn hay không")

# --- BƯỚC 3: TÍNH TOÁN FORECAST CHO TUẦN NÀY ---
# Dự báo (Nếu slider = 0 thì forecast phải BẰNG tuần trước)
forecast_tc = lw_tc * (1 + growth_tc / 100)
forecast_ac = lw_ac * (1 + growth_ac / 100)
forecast_rev = forecast_tc * forecast_ac

# --- BƯỚC 4: HIỂN THỊ ---
c1, c2, c3 = st.columns(3)

# Doanh thu dự báo
c1.metric(
    label="Dự báo Doanh thu tuần này", 
    value=f"{forecast_rev:,.0f} VNĐ", 
    delta=f"{(forecast_rev - lw_revenue)/1_000_000:,.1f}M so với tuần trước"
)

c2.metric("Mục tiêu TC", f"{forecast_tc:,.0f} Bill", f"{growth_tc:.2f}%")
c3.metric("Mục tiêu AC", f"{forecast_ac:,.0f} VNĐ", f"{growth_ac:.2f}%")

st.write(f"💡 *Dựa trên dữ liệu thực tế Tuần {last_week_num}: Revenue {lw_revenue:,.0f} | TC {lw_tc:,.0f} | AC {lw_ac:,.0f}*")
st.divider()

# =====================
# =====================
# 3. ACTION PLAN TEMPLATE (Kế hoạch hành động)
# =====================
import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Đường dẫn lưu trữ
SILVER_PATH = 'data/silver_layer/action_plans.csv'

# 1. Hàm lưu dữ liệu
def save_action_plan(df):
    if not os.path.exists('data/silver_layer'):
        os.makedirs('data/silver_layer')
    
    # Nếu file đã tồn tại, gộp dữ liệu cũ và mới, tránh trùng lặp dựa trên Title và Week
    if os.path.exists(SILVER_PATH):
        old_df = pd.read_csv(SILVER_PATH)
        # Giữ lại các dòng cũ không trùng với tiêu đề và tuần đang lưu
        df = pd.concat([old_df, df]).drop_duplicates(subset=['title', 'week'], keep='last')
    
    df.to_csv(SILVER_PATH, index=False, encoding='utf-8-sig')

# 2. Lấy số tuần hiện tại
current_week = datetime.now().isocalendar()[1]
current_year = datetime.now().year

# 3. Khởi tạo session_state từ file CSV (nếu có)
if 'tasks' not in st.session_state:
    if os.path.exists(SILVER_PATH):
        saved_df = pd.read_csv(SILVER_PATH)
        # Chỉ lấy các task của tuần hiện tại và chưa bị đánh dấu 'Đã xóa'
        current_tasks = saved_df[(saved_df['week'] == current_week) & 
                                 (saved_df['year'] == current_year) & 
                                 (saved_df['status'] != 'Đã xóa')]
        st.session_state.tasks = current_tasks.to_dict('records')
    else:
        st.session_state.tasks = []

# --- GIAO DIỆN CHÍNH ---
st.subheader("🎯 Kế hoạch hành động Tuần " + str(current_week))

# Nút thêm task mới
if st.button("➕ Thêm ô nhiệm vụ mới"):
    st.session_state.tasks.append({
        "priority": "🔵 Thấp", "category": "Mới", "title": "", 
        "content": "", "status": "Chưa bắt đầu", "progress": 0,
        "week": current_week, "year": current_year
    })

# Hiển thị các ô vuông (Cards)
for i, task in enumerate(st.session_state.tasks):
    if task.get('status') == 'Đã xóa': continue
    
    if i % 2 == 0: cols = st.columns(2)
    with cols[i % 2]:
        with st.container(border=True):
            task['priority'] = st.selectbox(f"Ưu tiên", ["🔴 Cao", "🟡 Trung bình", "🔵 Thấp"], 
                                            index=["🔴 Cao", "🟡 Trung bình", "🔵 Thấp"].index(task['priority']), key=f"pri_{i}")
            task['title'] = st.text_input(f"Tiêu đề", task['title'], key=f"ttl_{i}")
            task['content'] = st.text_area(f"Chi tiết", task['content'], key=f"cont_{i}")
            
            c1, c2 = st.columns(2)
            task['status'] = c1.selectbox(f"Trạng thái", ["Chưa bắt đầu", "Đang làm", "Hoàn thành", "Tạm hoãn"], 
                                          index=["Chưa bắt đầu", "Đang làm", "Hoàn thành", "Tạm hoãn"].index(task['status']), key=f"stat_{i}")
            task['progress'] = c2.slider(f"Tiến độ %", 0, 100, task['progress'], key=f"prog_{i}")
            
            if st.button(f"🗑️ Xóa nhiệm vụ", key=f"del_{i}"):
                task['status'] = 'Đã xóa' # Đánh dấu xóa thay vì pop khỏi list
                st.rerun()

# Nút Lưu vào thư mục Silver
if st.button("💾 Lưu toàn bộ kế hoạch hành động", type="primary", use_container_width=True):
    final_df = pd.DataFrame(st.session_state.tasks)
    save_action_plan(final_df)
    st.success(f"Đã lưu kế hoạch tuần {current_week} vào hệ thống Silver!")

# --- PHẦN TRA CỨU LỊCH SỬ ---
st.write("---")
st.subheader("📜 Tra cứu kế hoạch tuần cũ")

if os.path.exists(SILVER_PATH):
    history_df = pd.read_csv(SILVER_PATH)
    # Lấy danh sách các tuần cũ (không bao gồm tuần hiện tại)
    past_weeks = history_df[history_df['week'] < current_week]['week'].unique()
    
    if len(past_weeks) > 0:
        selected_past_week = st.selectbox("Chọn tuần muốn xem lại:", sorted(past_weeks, reverse=True))
        view_df = history_df[history_df['week'] == selected_past_week]
        
        # Hiển thị bảng lịch sử chuyên nghiệp
        st.dataframe(
            view_df[['priority', 'category', 'title', 'status', 'progress', 'content']],
            column_config={
                "progress": st.column_config.ProgressColumn("Tiến độ", format="%d%%"),
                "priority": "Mức độ",
                "title": "Nhiệm vụ"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Chưa có dữ liệu lịch sử của các tuần trước.")