import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pywhatkit as kit
import time
from datetime import datetime

# --- 1. CONFIGURATION ---
# ⚠️ Replace these with the ACTUAL phone numbers of you and your partners.
# Must include the country code (e.g., +92 for Pakistan) and NO spaces.
PARTNER_PHONES = {
    "A1": "+923241099849", # Example: Ali Murad's number
    "J2": "+923468196151", # Example: Jalal's number
    "M3": "+923105686618"  # Example: Muazzam's number
}

# Add your Google Form EasyPaisa number here
EASYPAISA_NUMBER = "0324-1099849" 

# --- 2. DATA CONNECTION ---
def load_pending_orders():
    print("⏳ Connecting to Master Ledger...")
    # ⚠️ Use your actual JSON filename
    KEY_FILE = 'involuted-shine-494407-e6-67c4a3a4d454.json' 
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(KEY_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    
    # ⚠️ Use your actual URL
    URL = "https://docs.google.com/spreadsheets/d/1Ou6ix0k6cmX9gnpZjRHbnx9eAuHH_zO9Av_CaEnGMB4/edit?resourcekey=&gid=1522633768#gid=1522633768" 
    sheet = client.open_by_url(URL).worksheet("Sales Ledger")
    
    df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip() # Clean headers
    
    # Filter for only pending orders
    pending_df = df[df['STATUS'] == 'PENDING'].copy()
    return pending_df

# --- 3. MESSAGE FORMATTER ---
def format_partner_message(partner_id, orders_df):
    """Creates a clean summary message for a specific partner."""
    
    total_owed = pd.to_numeric(orders_df['TOTAL AMOUNT'], errors='coerce').sum()
    order_count = len(orders_df)
    
    msg = f"🚨 *HassleFree Pulse: Pending Payment Alert* 🚨\n"
    msg += f"Partner: {partner_id}\n"
    msg += f"Pending Orders: {order_count} | Total Trapped Cash: Rs. {total_owed:,.0f}\n"
    msg += f"-----------------------------------\n\n"
    msg += f"Please *forward* these individual messages to your customers:\n\n"
    
    for index, row in orders_df.iterrows():
        student = row['STUDENT NAME/Description']
        program = row['Program']
        amount = row['TOTAL AMOUNT']
        order_id = row['ORDER ID']
        
        # This is the part the partner will copy/forward
        msg += f"📌 *To: {student} ({program})*\n"
        msg += f"Hi! Just a friendly reminder from Hassle Free Printing. 🖨️\n"
        msg += f"Your print order #{order_id} is pending payment of *Rs. {amount}*.\n"
        msg += f"Please clear this via EasyPaisa to: {EASYPAISA_NUMBER}\n"
        msg += f"Thanks!\n\n"
        
    return msg

# --- 4. SENDING LOGIC ---
def send_reminders():
    df = load_pending_orders()
    
    if df.empty:
        print("✅ No pending orders! Everyone has paid.")
        return

    # Group the pending orders by the 'Sold By' column (A1, J2, M3)
    grouped_orders = df.groupby('Sold By')
    
    for partner_id, partner_orders in grouped_orders:
        if partner_id not in PARTNER_PHONES:
            print(f"⚠️ Warning: Found pending orders for '{partner_id}', but no phone number is configured. Skipping.")
            continue
            
        phone_number = PARTNER_PHONES[partner_id]
        message = format_partner_message(partner_id, partner_orders)
        
        print(f"\n📨 Preparing to send message to Partner {partner_id}...")
        
        # IMPORTANT: pywhatkit uses time based on your computer clock.
        # We tell it to send the message 2 minutes from "now" so WhatsApp Web has time to load.
        current_time = datetime.now()
        send_hour = current_time.hour
        send_minute = current_time.minute + 2 
        
        # Handle minute overflow (e.g., if it's 2:59, we need it to be 3:01)
        if send_minute >= 60:
            send_minute -= 60
            send_hour = (send_hour + 1) % 24
            
        try:
            print(f"Opening WhatsApp Web... Do not touch your mouse/keyboard.")
            # time_hour (24hr format), time_min, wait_time (seconds to load web), tab_close (close browser after)
            kit.sendwhatmsg(phone_number, message, send_hour, send_minute, wait_time=15, tab_close=True)
            print(f"✅ Message scheduled for {partner_id}.")
            
            # Add a delay between partners so WhatsApp doesn't block you
            time.sleep(30) 
            
        except Exception as e:
            print(f"❌ Failed to send to {partner_id}. Error: {e}")

# --- RUN SCRIPT ---
if __name__ == "__main__":

    
    print("🚀 Starting Debt Collector Bot...")
    send_reminders()
    print("\n🏁 Finished running reminders.")