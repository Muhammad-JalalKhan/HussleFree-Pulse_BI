import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import joblib
import plotly.graph_objects as go

# ── 1. ENTERPRISE PAGE CONFIGURATION ──
st.set_page_config(page_title="HassleFree Pulse", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# ── 2. LOAD AI BRAINS (CACHED FOR SPEED) ──
@st.cache_resource
def load_models():
    try:
        demand = joblib.load('D:\HassleFree_Pulse\models\hasslefree_demand_brain.pkl')
        churn = joblib.load('D:\HassleFree_Pulse\models\hasslefree_churn_brain30per.pkl')
        return demand, churn
    except Exception as e:
        st.error(f"⚠️ System Boot Error: Missing ML models in 'models/' folder. {e}")
        return None, None

demand_model, churn_model = load_models()

# ── 3. LIVE DATABASE CONNECTION (GOOGLE SHEETS) ──
@st.cache_data(ttl=60) # Refreshes automatically every 60 seconds
def get_live_data():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        # Reads securely from Streamlit Cloud Secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Connect to Master Ledger
        URL = "https://docs.google.com/spreadsheets/d/1Ou6ix0k6cmX9gnpZjRHbnx9eAuHH_zO9Av_CaEnGMB4/edit"
        sheet = client.open_by_url(URL).worksheet("Sales Ledger")
        
        df = pd.DataFrame(sheet.get_all_records())
        return df, sheet
    except Exception as e:
        st.error(f"Database Connection Failed. Check your Streamlit Secrets. Error: {e}")
        return pd.DataFrame(), None

df_sales, worksheet = get_live_data()

# Clean live data
if not df_sales.empty:
    df_sales.columns = df_sales.columns.str.strip()
    df_sales['Date'] = pd.to_datetime(df_sales['Date'], errors='coerce')
    df_sales['TOTAL AMOUNT'] = pd.to_numeric(df_sales['TOTAL AMOUNT'], errors='coerce').fillna(0)
    df_sales['Pages Qty'] = pd.to_numeric(df_sales['Pages Qty'], errors='coerce').fillna(0)

# ── 4. SIDEBAR NAVIGATION ──
st.sidebar.title("⚡ HassleFree Pulse")
st.sidebar.caption("Enterprise Analytics Engine v1.0")
st.sidebar.divider()

page = st.sidebar.radio("Main Menu", [
    "📝 Point of Sale (Enter Order)", 
    "📊 Live Business Ledger", 
    "🔮 AI Command Center"
])

# ── PAGE 1: DATA ENTRY (Write to Sheets in Real-Time) ──
if page == "📝 Point of Sale (Enter Order)":
    st.title("📝 Point of Sale System")
    st.write("Log a new order. This will instantly update the cloud database and AI models.")
    
    with st.form("new_order_form", clear_on_submit=True):
        # --- Row 1: Core Details ---
        col1, col2, col3, col4 = st.columns(4)
        date = col1.date_input("Order Date", datetime.date.today())
        order_id = col2.text_input("Order ID / Invoice No")
        student_name = col3.text_input("Student Name")
        program = col4.selectbox("Program", ["BS AI", "BS CS", "BE CE", "BBA", "Other"])
        
        # --- Row 2: Order Specifics ---
        col5, col6, col7, col8 = st.columns(4)
        student_status = col5.selectbox("Student Status", ["Hostellite", "Day scholar"])
        pages = col6.number_input("Pages Qty", min_value=1, value=10)
        amount = col7.number_input("Total Amount (Rs)", min_value=0, value=100)
        due_date = col8.date_input("Due Date", datetime.date.today() + datetime.timedelta(days=2))
        
        # --- Row 3: Payment & Tracking ---
        col9, col10, col11 = st.columns(3)
        amount_received = col9.number_input("Amount Received", min_value=0, value=0)
        status = col10.selectbox("Payment Status", ["Pending", "PAID"])
        sales_rep = col11.selectbox("Sold By", ["J2", "M3", "A1"])
        
        submitted = st.form_submit_button("💳 Submit Order to Ledger", use_container_width=True)
        
        if submitted:
            if student_name == "":
                st.error("Please enter a student name.")
            elif order_id == "":
                st.error("Please enter an Order ID / Invoice No.")
            elif worksheet is not None:
                with st.spinner("Syncing to Google Cloud and applying formatting..."):
                    
                    # 1. Map data exactly to your 11 Google Sheet columns
                    new_row = [
                        date.strftime("%m/%d/%Y"),               # Date
                        order_id,                                # ORDER ID
                        student_name,                            # STUDENT NAME/Description
                        program,                                 # Program
                        student_status,                          # Student Status
                        pages,                                   # Pages Qty
                        amount,                                  # TOTAL AMOUNT
                        due_date.strftime("%m/%d/%Y"),           # DUE DATE
                        amount_received if amount_received > 0 else "", # Amount Received
                        status,                                  # STATUS
                        sales_rep                                # Sold By
                    ] 
                    
                    # 2. Append the new row to the bottom of the sheet
                    worksheet.append_row(new_row)
                    
                    # 3. Calculate the row number we just inserted
                    last_row = len(worksheet.get_all_values())
                    
                    # 4. Apply Enterprise Formatting (Size 12, Centered)
                    cell_range = f"A{last_row}:K{last_row}"
                    worksheet.format(cell_range, {
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "textFormat": {
                            "fontSize": 12
                        }
                    })
                    
                    st.cache_data.clear() # Force immediate refresh
                    st.success(f"✅ Order {order_id} for {student_name} logged and formatted successfully! AI models updated.")
# ── PAGE 2: LIVE LEDGER (Read from Sheets) ──
elif page == "📊 Live Business Ledger":
    st.title("📊 Live Operations Ledger")
    
    if df_sales.empty:
        st.warning("No data found in ledger.")
    else:
        col1, col2, col3 = st.columns(3)
        total_rev = df_sales['TOTAL AMOUNT'].sum()
        pending_rev = df_sales[df_sales['STATUS'].str.upper() == 'PENDING']['TOTAL AMOUNT'].sum()
        
        col1.metric("Total Lifetime Revenue", f"Rs. {total_rev:,.0f}")
        col2.metric("Pending Dues (At Risk)", f"Rs. {pending_rev:,.0f}", delta="-Collect ASAP", delta_color="inverse")
        col3.metric("Total Lifetime Orders", len(df_sales))
        
        st.divider()
        st.subheader("Recent Transactions")
        st.dataframe(df_sales.sort_values(by='Date', ascending=False).head(25), use_container_width=True)
        
        if st.button("🔄 Force Cloud Sync"):
            st.cache_data.clear()
            st.rerun()

# ── PAGE 3: AI COMMAND CENTER (Live Predictions) ──
elif page == "🔮 AI Command Center":
    st.title("🔮 AI Predictive Analytics")
    
    tab1, tab2 = st.tabs(["📦 Demand Forecaster", "🏃 AI Churn Prevention"])
    
    # --- TAB 1: DEMAND FORECASTING ---
    with tab1:
        st.subheader("14-Day Supply & Demand Outlook")
        if demand_model and not df_sales.empty:
            st.write("Using Meta's Prophet AI to predict future printing volume.")
            
            future = demand_model.make_future_dataframe(periods=14)
            forecast = demand_model.predict(future)
            
            today = pd.to_datetime(datetime.date.today())
            future_forecast = forecast[forecast['ds'] >= today].head(14)
            total_pages = int(future_forecast['yhat'].sum())
            
            col_a, col_b = st.columns([1, 3])
            col_a.metric("Expected Volume (14 Days)", f"{total_pages} Pages")
            
            if total_pages > 1500:
                col_a.error("🔴 High volume expected. Order toner today.")
            else:
                col_a.success("🟢 Stock levels stable.")
                
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=future_forecast['ds'], y=future_forecast['yhat'], mode='lines+markers', line=dict(color='blue', width=3)))
            fig.update_layout(xaxis_title="Date", yaxis_title="Predicted Pages")
            col_b.plotly_chart(fig, use_container_width=True)
            
    # --- TAB 2: LIVE CHURN DETECTION ---
    with tab2:
        st.subheader("🏃 Real-Time Student Churn Scanner")
        
        if churn_model and not df_sales.empty:
            st.write("Scanning the live database for regular students showing signs of abandoning the service...")
            
            # Live Feature Engineering
            current_date = df_sales['Date'].max()
            student_features = []
            
            for student, group in df_sales.groupby('STUDENT NAME/Description'):
                name = str(student).strip()
                if name == 'nan' or name == '': continue
                if len(group) < 2: continue # Only analyze returning customers
                
                total_orders = len(group)
                total_spent = group['TOTAL AMOUNT'].sum()
                avg_order_value = total_spent / total_orders
                
                gaps = group['Date'].sort_values().diff().dt.days.dropna()
                avg_gap = gaps.mean() if len(gaps) > 0 else 0
                std_gap = gaps.std() if len(gaps) > 1 else 0
                
                orders_last_30 = len(group[group['Date'] >= (current_date - pd.Timedelta(days=30))])
                orders_prev_30 = len(group[(group['Date'] < (current_date - pd.Timedelta(days=30))) & 
                                           (group['Date'] >= (current_date - pd.Timedelta(days=60)))])
                velocity_trend = orders_last_30 - orders_prev_30
                
                days_since_last = (current_date - group['Date'].max()).days
                
                student_features.append({
                    'Student Name': name,
                    'Days Silent': days_since_last,
                    'Total Orders': total_orders,
                    'Total Spent': total_spent,
                    'Avg Order Value': avg_order_value,
                    'Avg Gap (Days)': avg_gap,
                    'Gap Volatility (Std)': std_gap,
                    'Velocity Trend': velocity_trend
                })
            
            df_features = pd.DataFrame(student_features)
            
            if not df_features.empty:
                # Prepare data for model (Matching exact training columns)
                X_live = df_features[['Total Orders', 'Total Spent', 'Avg Order Value', 'Avg Gap (Days)', 'Gap Volatility (Std)', 'Velocity Trend']]
                
                # Predict!
                probabilities = churn_model.predict_proba(X_live)[:, 1]
                df_features['Churn Probability'] = probabilities
                
                # Apply our 30% Business Threshold
                at_risk = df_features[df_features['Churn Probability'] >= 0.30].copy()
                
            if not at_risk.empty:
                    # Sort by most valuable students first
                    at_risk = at_risk.sort_values(by='Total Spent', ascending=False)
                    st.error(f"⚠️ FOUND {len(at_risk)} VIP STUDENTS AT RISK OF CHURNING!")
                    
                    # ── THE UPGRADE: Generate Plain-English Insights ──
                    def generate_insight(row):
                        if row['Days Silent'] > 30:
                            return "🚨 Long-term inactive (>30 days)"
                        elif row['Velocity Trend'] < 0:
                            return f"📉 Slowing down (Dropped by {abs(int(row['Velocity Trend']))} orders)"
                        elif row['Days Silent'] > (row['Avg Gap (Days)'] * 1.5) and row['Avg Gap (Days)'] > 0:
                            return f"⏳ Overdue (Usually prints every {row['Avg Gap (Days)']:.1f} days)"
                        else:
                            return "⚠️ High-risk behavioral shift detected"

                    at_risk['AI Insight'] = at_risk.apply(generate_insight, axis=1)
                    
                    # ── Select and Format the Columns for the Dashboard ──
                    display_df = at_risk[['Student Name', 'Churn Probability', 'AI Insight', 'Days Silent', 'Avg Gap (Days)', 'Total Orders', 'Total Spent']].copy()
                    
                    display_df['Churn Probability'] = (display_df['Churn Probability'] * 100).round(1).astype(str) + "%"
                    display_df['Total Spent'] = "Rs. " + display_df['Total Spent'].astype(int).astype(str)
                    display_df['Avg Gap (Days)'] = display_df['Avg Gap (Days)'].round(1).astype(str) + " days"
                    
                    # Rename for business readability
                    display_df = display_df.rename(columns={'Avg Gap (Days)': 'Normal Print Cycle'})
                    
                    # Use st.dataframe instead of st.table so you can sort the columns by clicking them!
                    st.dataframe(display_df.reset_index(drop=True), use_container_width=True)
                    
                    st.info("💡 Action: Send these students a friendly WhatsApp message today offering a slight discount on their next print!")
            else:
                    st.success("✅ All regular students are currently active and ordering on their normal schedules.")