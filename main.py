import streamlit as st




# Định nghĩa các trang
revenue_page = st.Page("views/overview.py", title="Revenue Dashboard", icon="📊", default=True)
product_page = st.Page("views/product_analyst.py", title="Product Analysis", icon="🍱")
labor_page = st.Page("views/labor.py", title="Labor Analysis", icon="👷")
plan_page = st.Page("views/plan_future.py", title="Growth Planning", icon="🚀")


# Tạo Menu với Categories
pg = st.navigation({
    "Overview": [revenue_page, product_page], # Gộp cả 2 trang vào đây
    "Labor Management": [labor_page],
    "Planning": [plan_page]
})

pg.run()