import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import traceback
from receipt_engine import generate_receipt_image

st.set_page_config(page_title="HassleFree Pulse", page_icon="📈", layout="wide")
st.title("📈 HassleFree Pulse: Live Operations")

# --- 1. DATA CONNECTION ---
@st.cache_data(ttl=60) # Caches data for 60 seconds so you don't hit Google API limits
def load_business_data():
    # ⚠️ Using your provided JSON file name
    KEY_FILE = 'involuted-shine-494407-e6-67c4a3a4d454.json' 
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(KEY_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    
    # ⚠️ Using your provided Master Ledger URL
    URL = "https://docs.google.com/spreadsheets/d/1Ou6ix0k6cmX9gnpZjRHbnx9eAuHH_zO9Av_CaEnGMB4/edit?resourcekey=&gid=1522633768#gid=1522633768" 
    sheet = client.open_by_url(URL)
    
    # Fetch specific tabs by their exact names!
    sales_data = sheet.worksheet("Sales Ledger").get_all_records()
    expense_data = sheet.worksheet("Expense Ledger").get_all_records()
    
    # Convert raw data into Pandas DataFrames immediately so we can clean it
    df_sales = pd.DataFrame(sales_data)
    df_expenses = pd.DataFrame(expense_data)

    # 🛠️ UPDATE 1: Strip invisible spaces from column headers
    # Why? Google Sheets often have trailing spaces (e.g., "Program "). 
    # This strips the space so Python finds exactly "Program" and prevents the KeyError.
    df_sales.columns = df_sales.columns.str.strip()
    df_expenses.columns = df_expenses.columns.str.strip()
    
    # 🛠️ UPDATE 2: Convert all columns to strings (text) initially
    # Why? Streamlit's PyArrow engine crashes if a column has both numbers (530.00) and blanks. 
    # Converting everything to text strings makes PyArrow happy.
    df_sales = df_sales.astype(str)
    df_expenses = df_expenses.astype(str)
    
    return df_sales, df_expenses

# --- 2. DASHBOARD UI ---
try:
    df_sales, df_expenses = load_business_data()
    st.success("✅ Connected directly to the Master Ledger.")
    
    # Clean the Sales Data (Remove empty rows if any exist at the bottom of the sheet)
    # This filters out rows where 'ORDER ID' is blank
    df_sales = df_sales[df_sales['ORDER ID'] != ''] 

    # --- Quick KPI Metrics ---
    col1, col2, col3 = st.columns(3)
    
    # 🛠️ UPDATE 3: Safely calculate total revenue
    # Why? Because we turned everything to strings in Update 2, we must use pd.to_numeric here.
    # errors='coerce' forces any weird blank cells to become 'NaN' (Not a Number) so they don't break the sum.
    total_revenue = pd.to_numeric(df_sales['TOTAL AMOUNT'], errors='coerce').sum()
    
    # Count Pending Orders
    pending_orders = df_sales[df_sales['STATUS'] == 'PENDING']
    pending_count = len(pending_orders)
    
    col1.metric("Total Sales Logged", len(df_sales))
    col2.metric("Total Revenue Logged", f"Rs. {total_revenue:,.0f}")
    col3.metric("Pending Payments (Action Req.)", pending_count)

    # --- Data Views ---
    # --- Data Views ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Sales", "💸 Expenses", "🚨 Pending", "🏆 Loyalty", "🖨️ Receipt Generator"])
    with tab1:
        st.subheader("Recent Sales Transactions")
        st.dataframe(df_sales)
        
    with tab2:
        st.subheader("Recorded Expenses & COGS")
        st.dataframe(df_expenses)
        
    with tab3:
        st.subheader("Students with Pending Payments")
        if pending_count > 0:
            st.warning(f"You have {pending_count} unpaid orders. Time to send reminders!")
            # Show only the relevant columns for debt collection
            st.dataframe(pending_orders[['ORDER ID', 'STUDENT NAME/Description', 'Program', 'TOTAL AMOUNT', 'DUE DATE', 'Sold By']])
        else:
            st.success("All clear! No pending payments.")
    with tab4:
        st.subheader("Customer Loyalty & VIP Tracker")
        
        # 🛠️ THE FIX: Group by all three columns to make sure every customer is unique
        customer_counts = df_sales.groupby(
            ['STUDENT NAME/Description', 'Program', 'Student Status']
        ).size().reset_index(name='Total Orders')
        
        # 🛠️ THE LOGIC: Define the tiers
        def get_tier(orders):
            if orders >= 10:
                return "👑 VIP"
            elif orders >= 3:
                return "⭐ Regular"
            else:
                return "🆕 First Timer"
                
        # Apply the tier logic to create a new column
        customer_counts['Loyalty Tier'] = customer_counts['Total Orders'].apply(get_tier)
        
        # Sort the data so your best customers (VIPs) are at the very top
        customer_counts = customer_counts.sort_values(by='Total Orders', ascending=False).reset_index(drop=True)
        
        # --- UI Display for Loyalty ---
        col_a, col_b, col_c = st.columns(3)
        
        vip_count = len(customer_counts[customer_counts['Loyalty Tier'] == '👑 VIP'])
        regular_count = len(customer_counts[customer_counts['Loyalty Tier'] == '⭐ Regular'])
        first_timer_count = len(customer_counts[customer_counts['Loyalty Tier'] == '🆕 First Timer'])
        
        col_a.metric("👑 VIPs (10+ Orders)", vip_count)
        col_b.metric("⭐ Regulars (3-9 Orders)", regular_count)
        col_c.metric("🆕 First Timers (1-2 Orders)", first_timer_count)
        
        # Add a search box so A1, J2, or M3 can quickly check a student's status
        search_query = st.text_input("🔍 Search for a specific student:")
        
        if search_query:
            # Filter the dataframe based on the search
            filtered_df = customer_counts[
                customer_counts['STUDENT NAME/Description'].str.contains(search_query, case=False, na=False)
            ]
            st.dataframe(filtered_df, use_container_width=True)
        else:
            # Show the whole leaderboard
            st.dataframe(customer_counts, use_container_width=True)

        with tab5:
            st.subheader("🖨️ Generate Image Receipts")
        st.write("Select a 'PAID' order to instantly generate a shareable PNG receipt.")
        
        # Filter for only PAID orders
        paid_orders = df_sales[df_sales['STATUS'].str.upper() == 'PAID']
        
        if not paid_orders.empty:
            # Create a dropdown for the user to select an order
            # We format it to show: "Order ID - Student Name (Rs. Amount)"
            order_options = paid_orders.apply(
                lambda row: f"Order #{row['ORDER ID']} - {row['STUDENT NAME/Description']} (Rs. {row['TOTAL AMOUNT']})", 
                axis=1
            ).tolist()
            
            selected_order_str = st.selectbox("Select an Order:", order_options)
            
            if st.button("Generate Digital Receipt"):
                # Extract the selected Order ID from the string (e.g., gets "66" from "Order #66 - Ahsan...")
                selected_id = selected_order_str.split(" - ")[0].replace("Order #", "")
                
                # Find the exact row in the dataframe
                order_row = paid_orders[paid_orders['ORDER ID'].astype(str) == selected_id].iloc[0]
                
                # Generate the image!
                file_path = generate_receipt_image(
                    order_id=order_row['ORDER ID'],
                    student_name=order_row['STUDENT NAME/Description'],
                    program=order_row['Program'],
                    amount=order_row['TOTAL AMOUNT'],
                    date_str=order_row['Date'],
                    partner_id=order_row['Sold By']
                )
                
                st.success(f"Receipt generated successfully!")
                
                # Show the image directly in the dashboard
                st.image(file_path, caption=f"Receipt for {order_row['STUDENT NAME/Description']}")
                
                # Add a download button so you can save it and send via WhatsApp
                with open(file_path, "rb") as file:
                    st.download_button(
                        label="Download PNG for WhatsApp",
                        data=file,
                        file_name=file_path.split("/")[-1],
                        mime="image/png"
                    )
        else:
            st.info("No paid orders available to generate receipts for.")
except Exception as e:
    st.error("❌ Connection Failed! Check your terminal.")
    print("\n--- ERROR LOG ---")
    print(traceback.format_exc())
    print("-----------------\n")