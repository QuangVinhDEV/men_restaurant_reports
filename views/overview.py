import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import os
from datetime import datetime

# =====================
# CONFIG & STYLE
# =====================

# CSS để dashboard chuyên nghiệp hơn
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    /* 1. Ép màu nền của từng ô Metric sang màu xám đen rất đậm */
    [data-testid="stMetric"] {
        background-color: #121212 !important;
        border: 1px solid #333333 !important;
        padding: 20px !important;
        border-radius: 12px !important;
    }

    /* 2. Ép màu chữ tiêu đề (Label) sang màu xám bạc để dễ đọc */
    [data-testid="stMetricLabel"] p {
        color: #BCBCBC !important;
        font-size: 16px !important;
    }

    /* 3. Ép màu chỉ số chính (Value) sang màu TRẮNG tinh hoặc XANH NEON */
    [data-testid="stMetricValue"] div {
        color: #FFFFFF !important; /* Bạn có thể đổi thành #00FFCC nếu muốn màu xanh neon */
        font-weight: bold !important;
    }

    /* 4. Tùy chỉnh phần Delta (phần trăm tăng giảm) để không bị nhòe */
    [data-testid="stMetricDelta"] svg {
        fill: currentColor !important;
    }
    
    /* Làm cho các ô cách nhau ra một chút nhìn cho thoáng */
    [data-testid="column"] {
        padding: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# =====================
# LOAD & PROCESS DATA
# =====================
@st.cache_data
def load_revenue_data():
    # 1. Đọc dữ liệu
    df = pd.read_csv('data/silver_layer/df_revenue_per_date.csv', sep=';')

    # 2. Chuyển đổi date (quan trọng nhất)
    df['date'] = pd.to_datetime(df['date'])

    # 3. Làm sạch số liệu (Xử lý trường hợp nếu revenue/vat bị đọc nhầm thành chuỗi)
    for col in ['revenue', 'vat']:
        if df[col].dtype == 'object':
            df[col] = df[col].str.replace('.', '', regex=False).astype(float)
    
    # 4. Tính toán các chỉ số bổ sung
    df['gross_revenue'] = df['revenue'] + df['vat']
    df['weekday_num'] = df['date'].dt.weekday
    
    # 5. Đảm bảo các cột thời gian có sẵn (đề phòng file CSV thiếu)
    df['week'] = df['date'].dt.isocalendar().week
    df['year'] = df['date'].dt.year

    return df

try:
    df_rev = load_revenue_data()
except Exception as e:
    st.error(f"Lỗi khi đọc file dữ liệu: {e}")
    st.stop()

# =====================
# SIDEBAR
# =====================

# Lấy danh sách tuần dựa trên năm hiện tại để tránh lẫn lộn các năm
available_weeks = sorted(df_rev['week'].unique())
current_week_num = max(available_weeks) if available_weeks else 0


#===================================


# =====================
# MTD SEQUENTIAL LOGIC
# =====================
def get_mtd_metrics(df):
    # Lấy ngày cuối cùng có dữ liệu trong df
    today = df['date'].max()
    current_day = today.day
    current_month = today.month
    current_year = today.year
    
    # Tính ngày tương ứng tháng trước
    last_month_date = today - pd.DateOffset(months=1)
    last_month = last_month_date.month
    last_month_year = last_month_date.year

    # 1. Lọc dữ liệu MTD (Từ đầu tháng hiện tại đến ngày today)
    mtd_data = df[(df['date'].dt.month == current_month) & 
                  (df['date'].dt.year == current_year) & 
                  (df['date'].dt.day <= current_day)]

    # 2. Lọc dữ liệu LMTD (Từ đầu tháng trước đến cùng ngày current_day của tháng trước)
    lmtd_data = df[(df['date'].dt.month == last_month) & 
                   (df['date'].dt.year == last_month_year) & 
                   (df['date'].dt.day <= current_day)]

    def calc_stats(data):
        rev = data['revenue'].sum()
        tc = data['TC'].sum()
        ac = rev / tc if tc > 0 else 0
        return rev, tc, ac

    mtd_rev, mtd_tc, mtd_ac = calc_stats(mtd_data)
    lmtd_rev, lmtd_tc, lmtd_ac = calc_stats(lmtd_data)

    return (mtd_rev, lmtd_rev), (mtd_tc, lmtd_tc), (mtd_ac, lmtd_ac)

(m_rev, l_rev), (m_tc, l_tc), (m_ac, l_ac) = get_mtd_metrics(df_rev)

# =====================
# MTD LABELS (METRICS)
# =====================


# =====================
# TARGET ANALYSIS (BIG LABEL)
# =====================
# =====================
# FILTER: CHỌN THÁNG/NĂM
# =====================

# =====================
# FILTER: CHỌN THÁNG/NĂM
# =====================
df_rev['month_year'] = df_rev['date'].dt.strftime('%m/%Y')
available_months = sorted(df_rev['month_year'].unique(), reverse=True)

st.sidebar.header("📍 Cấu hình báo cáo")
selected_month_year = st.sidebar.selectbox(
    "Choose the month to analysis:",
    options=available_months,
    index=0
)

# 1. Xác định ngày tối đa của tháng được chọn (MTD logic)
# Nếu chọn tháng hiện tại, ngày max là ngày cuối cùng có dữ liệu. 
# Nếu chọn tháng cũ trong quá khứ, ngày max là ngày cuối cùng của tháng đó.
df_selected_full = df_rev[df_rev['month_year'] == selected_month_year]
max_day_in_selected = df_selected_full['date'].dt.day.max() 

# Lọc dữ liệu MTD cho tháng được chọn (từ ngày 1 đến ngày max_day_in_selected)
df_selected = df_selected_full[df_selected_full['date'].dt.day <= max_day_in_selected]

m_rev = df_selected['revenue'].sum()
m_tc = df_selected['TC'].sum()
m_ac = m_rev / m_tc if m_tc > 0 else 0

# 2. XỬ LÝ THÁNG TRƯỚC (LMTD Logic - Lấy ngày tương đương)
current_month_dt = pd.to_datetime(selected_month_year, format='%m/%Y')
last_month_dt = current_month_dt - pd.DateOffset(months=1)
last_month_year_str = last_month_dt.strftime('%m/%Y')

# Lọc dữ liệu tháng trước nhưng CHỈ LẤY đến ngày tương đương (max_day_in_selected)
df_last_month_full = df_rev[df_rev['month_year'] == last_month_year_str]
df_last_month_mtd = df_last_month_full[df_last_month_full['date'].dt.day <= max_day_in_selected]

if not df_last_month_mtd.empty:
    l_rev = df_last_month_mtd['revenue'].sum()
    l_tc = df_last_month_mtd['TC'].sum()
    l_ac = l_rev / l_tc if l_tc > 0 else 0
else:
    l_rev, l_tc, l_ac = 0, 0, 0

# (Tùy chọn) Tính toán dữ liệu tháng trước đó để hiển thị Delta
# Ở đây bạn cần logic tìm tháng liền kề tháng đã chọn trong dữ liệu
# Giả sử bạn đã có l_rev, l_tc, l_ac từ logic lọc tháng trước đó...

# =====================
# TARGET ANALYSIS (BIG LABEL)
# =====================
# Bạn có thể tạo một dictionary để gán target riêng cho từng tháng nếu cần
TARGET_CONFIG = {
    "04/2024": 1260000000,
    "05/2024": 1260000000,
}
# Lấy target theo tháng, nếu không có thì dùng mặc định 1.26 tỷ
target_month = TARGET_CONFIG.get(selected_month_year, 1260000000)

progress_pct = min(m_rev / target_month, 1.0)
actual_pct = (m_rev / target_month) * 100

st.subheader(f"📅 MTD Sequential Analysis (From the beginning of the month until {selected_month_year})")

st.markdown(f"""
    <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 10px solid #1A5276; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 25px;">
        <h3 style="margin: 0; color: #7F8C8D; font-size: 16px; text-transform: uppercase;">Monthly progress targets (Target: {target_month:,.0f} VNĐ)</h3>
        <div style="display: flex; align-items: baseline; gap: 15px; margin: 10px 0;">
            <span style="font-size: 48px; font-weight: bold; color: #1A5276;">{m_rev:,.0f}</span>
            <span style="font-size: 24px; color: #1A5276;">VNĐ</span>
            <span style="font-size: 32px; font-weight: bold; color: {'#27AE60' if actual_pct >= 100 else '#E67E22'}; margin-left: auto;">{actual_pct:.1f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.progress(progress_pct, text=f"Đã hoàn thành {actual_pct:.1f}% kế hoạch tháng {selected_month_year}")
st.write(f"👉 Còn thiếu **{max(target_month - m_rev, 0):,.0f} VNĐ** để đạt mục tiêu.")
st.divider()

col1, col2, col3 = st.columns(3)

def format_delta(current, last, period="month"):
    if last > 0:
        perc = ((current - last) / last) * 100
        return f"{perc:.1f}% vs {period} previous"
    return "N/A"

with col1:
    st.metric(
        label="💰 MTD Revenue (Gross)",
        value=f"{m_rev:,.0f} VNĐ",
        delta=format_delta(m_rev, l_rev, period="month")
    )

with col2:
    st.metric(
        label="🧾 MTD Transaction Count",
        value=f"{m_tc:,.0f} Bill",
        delta=format_delta(m_tc, l_tc, period="month")
    )

with col3:
    st.metric(
        label="🍽️ MTD Average Check",
        value=f"{m_ac:,.0f} VNĐ",
        delta=format_delta(m_ac, l_ac, period="month")
    )

st.divider()

#===================================




# =====================
# MAIN DASHBOARD
# =====================
st.title("📊 Weekly Analysis")


# --- PHẦN TÍNH TOÁN KPI TUẦN (BỔ SUNG) ---
def get_weekly_kpis(df, current_w):
    last_w = current_w - 1
    
    def get_stats(w_num):
        data = df[df['week'] == w_num]
        rev = data['revenue'].sum()
        tc = data['TC'].sum()
        ac = rev / tc if tc > 0 else 0
        return rev, tc, ac

    curr_stats = get_stats(current_w)
    last_stats = get_stats(last_w)
    
    return curr_stats, last_stats

# Lấy dữ liệu cho tuần hiện tại (hoặc tuần lớn nhất có trong data)
c_stats, l_stats = get_weekly_kpis(df_rev, current_week_num)

# Hiển thị Metric cho tuần hiện tại
w_col1, w_col2, w_col3 = st.columns(3)

with w_col1:
    st.metric(
        label=f"💰 Weekly Revenue (W{current_week_num})",
        value=f"{c_stats[0]:,.0f} VNĐ",
        delta=format_delta(c_stats[0], l_stats[0], period="Week")
    )

with w_col2:
    st.metric(
        label=f"🧾 Weekly TC (W{current_week_num})",
        value=f"{c_stats[1]:,.0f} Bill",
        delta=format_delta(c_stats[1], l_stats[1], period="Week")
    )

with w_col3:
    st.metric(
        label=f"🍽️ Weekly AC (W{current_week_num})",
        value=f"{c_stats[2]:,.0f} VNĐ",
        delta=format_delta(c_stats[2], l_stats[2], period="Week")
    )
st.divider()

###############################################################

selected_weeks = st.multiselect(
    "Choose weeks to compare revenue", 
    options=available_weeks, 
    default=[current_week_num, current_week_num - 1] if len(available_weeks) > 1 else [current_week_num]
)

if selected_weeks:
    # Tạo 3 tab để so sánh 3 chỉ số khác nhau
    tab1, tab2, tab3 = st.tabs(["💰 Revenue", "🧾 Transaction Count (TC)", "🍽️ Average Check (AC)"])

    days_label = ['Monday', 'Tuesday', 'Wednesday', 'Thusday', 'Friday', 'Saturday', 'Sun']
    colors = ['#BDC3C7', '#85C1E9', '#F7DC6F', '#76D7C4', '#BB8FCE']
    main_color = '#1A5276'

    # Hàm vẽ biểu đồ chung cho cả 3 tab
    def draw_weekly_chart(metric_column, title, unit_suffix=""):
        fig, ax = plt.subplots(figsize=(14, 6), facecolor='white')
        
        for i, w_num in enumerate(selected_weeks):
            week_data = df_rev[df_rev['week'] == w_num]
            
            # Đảm bảo đủ 7 ngày bằng reindex
            daily_series = week_data.set_index('weekday_num')[metric_column].reindex(range(7), fill_value=0)
            daily_values = daily_series.values
            
            is_latest = (w_num == max(selected_weeks))
            line_style = '-' if is_latest else '--'
            line_color = main_color if is_latest else colors[i % len(colors)]
            
            ax.plot(days_label, daily_values, marker='o', linestyle=line_style, 
                     color=line_color, label=f'Tuần {w_num}', 
                     linewidth=4 if is_latest else 2, alpha=1 if is_latest else 0.5)

            if is_latest:
                for x, y in enumerate(daily_values):
                    if y > 0:
                        # Định dạng label: nếu là triệu thì chia 1M, nếu là TC thì để nguyên
                        display_val = f"{y/1_000_000:.1f}M" if y > 1000000 else f"{y:,.0f}"
                        ax.text(x, y + (max(daily_values)*0.05), display_val + unit_suffix, 
                                color=line_color, fontweight='bold', ha='center')

        ax.grid(False)
        for spine in ['top', 'right', 'left']: ax.spines[spine].set_visible(False)
        ax.get_yaxis().set_visible(False)
        ax.set_title(title, fontsize=15, pad=20)
        ax.legend(frameon=False, loc='upper left')
        return fig

    with tab1:
        st.pyplot(draw_weekly_chart('revenue', 'COMPARE REVENUE'))
        
    with tab2:
        st.pyplot(draw_weekly_chart('TC', 'COMPARE TRANSACTION COUNT (TC)'))
        
    with tab3:
        # Lưu ý: AC thường biến động mạnh nếu TC thấp, nên chú ý quan sát
        st.pyplot(draw_weekly_chart('ac', 'COMPARE AVERAGE CHECK (AC)'))

    # --- PHẦN BẢNG DỮ LIỆU TRIỆT ĐỂ LỖI ---
    st.divider()
    metric_to_show = st.selectbox("Select the index to display in the detailed table.:", ["revenue", "TC", "ac"])
    
    summary_table = df_rev[df_rev['week'].isin(selected_weeks)].pivot_table(
        index='week', columns='weekday_num', values=metric_to_show, aggfunc='mean' if metric_to_show == 'ac' else 'sum'
    ).fillna(0)

    # Reindex triệt để 7 cột
    summary_table = summary_table.reindex(columns=range(7), fill_value=0)
    summary_table.columns = days_label
    
    st.write(f"### 📝 Detail {metric_to_show} follow date")
    st.dataframe(summary_table.style.format("{:,.0f}"), use_container_width=True)

else:
    st.info("Please select the week to start.")


######################################################################
