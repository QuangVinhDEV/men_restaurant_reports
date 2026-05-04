import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="MEN DATA ANALYZE - Product Insights", layout="wide")

# --- HÀM XỬ LÝ DỮ LIỆU SỐ (CHỐNG LỖI TYPEERROR) ---
def clean_numeric_column(series):
    """Chuyển đổi các chuỗi định dạng VN (179.000 hoặc 1,00) sang float chuẩn."""
    return pd.to_numeric(
        series.astype(str)
        .str.replace('.', '', regex=False)  # Xóa dấu chấm hàng nghìn
        .str.replace(',', '.', regex=False), # Đổi dấu phẩy thập phân thành chấm
        errors='coerce'
    ).fillna(0)

# --- LOAD VÀ LÀM SẠCH DỮ LIỆU ---
@st.cache_data
def load_and_preprocess_data():
    file_path = 'data/silver_layer/df_bill_detail.csv'
    if not os.path.exists(file_path):
        st.error(f"❌ Không tìm thấy file dữ liệu tại: {file_path}")
        return pd.DataFrame()

    # Đọc dữ liệu
    df = pd.read_csv(file_path, sep=';', encoding='utf-8-sig')

    # 1. Ép kiểu dữ liệu số ngay từ đầu để tránh lỗi tính toán về sau
    numeric_cols = ['quantity', 'unit_price', 'total', 'amount', 'num_people']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = clean_numeric_column(df[col])

    # 2. Xử lý ngày tháng
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # 3. Loại bỏ dữ liệu lỗi
    df = df.dropna(subset=['date', 'bill_id', 'item_name'])
    
    # 4. Feature Engineering
    df['week'] = df['date'].dt.isocalendar().week
    df['month_year'] = df['date'].dt.strftime('%m/%Y')
    # Lấy giờ từ time_range (ví dụ "21:08 - 22:33" -> 21)
    df['hour'] = df['time_range'].str.split(':').str[0].str.extract('(\d+)').fillna(0).astype(int)
    
    return df

# Khởi tạo dữ liệu
df = load_and_preprocess_data()

if df.empty:
    st.warning("⚠️ Dữ liệu trống. Vui lòng kiểm tra lại file nguồn.")
    st.stop()

# --- SIDEBAR: BỘ LỌC THÔNG MINH ---
st.sidebar.header("🔍 Bộ lọc Dashboard")

# Lọc theo Tháng/Tuần
view_mode = st.sidebar.radio("Chế độ xem:", ["Tất cả", "Theo Tháng", "Theo Tuần"])

if view_mode == "Theo Tháng":
    month_list = sorted(df['month_year'].unique(), reverse=True)
    sel_month = st.sidebar.selectbox("Chọn tháng:", month_list)
    df_filtered = df[df['month_year'] == sel_month]
elif view_mode == "Theo Tuần":
    week_list = sorted(df['week'].unique(), reverse=True)
    sel_week = st.sidebar.selectbox("Chọn tuần số:", week_list)
    df_filtered = df[df['week'] == sel_week]
else:
    df_filtered = df.copy()

# Lọc chi tiết
with st.sidebar.expander("Bộ lọc nâng cao"):
    shift_filter = st.multiselect("Ca làm việc:", options=df['shift'].unique(), default=df['shift'].unique())
    cat_filter = st.multiselect("Danh mục món:", options=df['category'].unique(), default=df['category'].unique())

f_df = df_filtered[
    (df_filtered['shift'].isin(shift_filter)) & 
    (df_filtered['category'].isin(cat_filter))
]

# --- PHẦN 1: OVERVIEW KPI CARDS ---
st.title("🍺 Phân tích Hiệu suất Sản phẩm")
st.markdown(f"**Dữ liệu đang xem:** {view_mode} | Số dòng: {len(f_df):,}")
st.divider()

# Tính toán các chỉ số cốt lõi (Đảm bảo kiểu float)
total_rev = float(f_df['amount'].sum())
total_qty = float(f_df['quantity'].sum())
unique_bills = float(f_df['bill_id'].nunique())
avg_bill = total_rev / unique_bills if unique_bills > 0 else 0

# Phân tích đồ uống (Alcohol)
alcohol_cats = ['Đồ uống', 'MEN _ ĐỒ UỐNG', 'Bia']
beer_df = f_df[f_df['category'].str.contains('Bia|Đồ uống', case=False, na=False)]
beer_rev = float(beer_df['amount'].sum())
beer_pct = (beer_rev / total_rev * 100) if total_rev > 0 else 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Tổng Doanh thu", f"{total_rev:,.0f} đ")
kpi2.metric("Số lượng bán ra", f"{total_qty:,.0f} món")
kpi3.metric("Doanh thu TB/Bill", f"{avg_bill:,.0f} đ")
kpi4.metric("Tỷ trọng Đồ uống", f"{beer_pct:.1f}%")

# --- PHẦN 2: PRODUCT PERFORMANCE MATRIX ---
st.header("📊 Ma trận Hiệu suất Sản phẩm")

# Gom nhóm dữ liệu theo món
prod_perf = f_df.groupby(['item_name', 'category']).agg({
    'amount': 'sum',
    'quantity': 'sum'
}).reset_index()

rev_median = prod_perf['amount'].median()
qty_median = prod_perf['quantity'].median()

def label_performance(row):
    if row['amount'] >= rev_median and row['quantity'] >= qty_median: return "⭐ Star (Bán chạy & Doanh thu cao)"
    if row['amount'] >= rev_median and row['quantity'] < qty_median: return "⚠️ Potential (Giá trị cao - Sức mua thấp)"
    if row['amount'] < rev_median and row['quantity'] >= qty_median: return "📦 Volume Driver (Sức mua cao - Giá trị thấp)"
    return "❌ Underperformer (Yếu)"

prod_perf['Phân loại'] = prod_perf.apply(label_performance, axis=1)

col_m1, col_m2 = st.columns([2, 1])

with col_m1:
    fig_matrix = px.scatter(
        prod_perf, x='quantity', y='amount', color='Phân loại',
        hover_name='item_name', size='amount',
        title="Ma trận Doanh thu vs Số lượng",
        labels={'quantity': 'Số lượng bán', 'amount': 'Doanh thu (VNĐ)'},
        color_discrete_map={
            "⭐ Star (Bán chạy & Doanh thu cao)": "#2ECC71",
            "⚠️ Potential (Giá trị cao - Sức mua thấp)": "#3498DB",
            "📦 Volume Driver (Sức mua cao - Giá trị thấp)": "#F1C40F",
            "❌ Underperformer (Yếu)": "#E74C3C"
        }
    )
    st.plotly_chart(fig_matrix, use_container_width=True)

with col_m2:
    st.markdown("### 💡 Insight Ma trận")
    top_stars = prod_perf[prod_perf['Phân loại'].str.contains("Star")].nlargest(3, 'amount')['item_name'].tolist()
    st.success(f"**Món chủ lực:** {', '.join(top_stars)}. Cần đảm bảo luôn sẵn sàng phục vụ.")
    st.info("Món **Potential** nên được nhân viên giới thiệu thêm (Upsell) để tăng doanh số.")

# --- PHẦN 3: CATEGORY & BEER ANALYTICS ---
st.divider()
c1, c2 = st.columns(2)

with c1:
    st.subheader("📁 Tỷ trọng Danh mục")
    cat_summary = f_df.groupby('category')['amount'].sum().reset_index()
    fig_pie = px.pie(cat_summary, values='amount', names='category', hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Set3)
    st.plotly_chart(fig_pie, use_container_width=True)

with c2:
    st.subheader("🍺 Top Đồ uống bán chạy")
    beer_top5 = beer_df.groupby('item_name')['quantity'].sum().nlargest(5).reset_index()
    fig_beer = px.bar(beer_top5, x='quantity', y='item_name', orientation='h',
                      title="Số lượng tiêu thụ đồ uống", text_auto=True,
                      color_discrete_sequence=['#FF8C00'])
    fig_beer.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_beer, use_container_width=True)

# --- PHẦN 4: BASKET ANALYSIS (KÈM MÓN) ---
st.divider()
st.subheader("🛒 Phân tích Cặp món ăn đi kèm (Basket Analysis)")

from collections import Counter
from itertools import combinations

# Lấy danh sách món ăn trong từng hóa đơn
basket = f_df.groupby('bill_id')['item_name'].apply(lambda x: sorted(list(set(x)))).reset_index()
combo_counts = Counter()

for items in basket['item_name']:
    if len(items) > 1:
        combo_counts.update(combinations(items, 2))

top_combos = pd.DataFrame(combo_counts.most_common(10), columns=['Combo', 'Số lần xuất hiện'])
if not top_combos.empty:
    top_combos['Món 1'] = top_combos['Combo'].apply(lambda x: x[0])
    top_combos['Món 2'] = top_combos['Combo'].apply(lambda x: x[1])
    st.table(top_combos[['Món 1', 'Món 2', 'Số lần xuất hiện']])
else:
    st.info("Không đủ dữ liệu để phân tích cặp món.")

# --- PHẦN 5: XU HƯỚNG THEO GIỜ ---
st.divider()
st.subheader("⏰ Xu hướng Doanh thu theo Giờ")

hourly_trend = f_df.groupby(['hour', 'shift'])['amount'].sum().reset_index()
fig_line = px.line(hourly_trend, x='hour', y='amount', color='shift', 
                  title="Biểu đồ Doanh thu theo khung giờ", markers=True)
st.plotly_chart(fig_line, use_container_width=True)

# --- FOOTER INSIGHTS ---
st.markdown("---")
st.subheader("🚀 PROPOSAL")
st.markdown(f"""
1. **Rủi ro tập trung:** 5 món đứng đầu chiếm **{(prod_perf['amount'].nlargest(5).sum() / total_rev * 100):.1f}%** tổng doanh thu.
2. **Hiệu suất Đồ uống:** Tỷ lệ hóa đơn có đồ uống (Beer Attach Rate) đạt **{(beer_df['bill_id'].nunique() / unique_bills * 100):.1f}%**.
3. **Vận hành:** Đỉnh điểm doanh thu rơi vào lúc **{hourly_trend.loc[hourly_trend['amount'].idxmax(), 'hour']}:00**. Hãy đảm bảo nhân sự ca {hourly_trend.loc[hourly_trend['amount'].idxmax(), 'shift']} luôn sẵn sàng.
""")