from PIL import Image, ImageDraw, ImageFont
import datetime
import os

def generate_receipt_image(order_id, student_name, program, amount, date_str, partner_id):
    # 1. Create a blank white canvas (width: 400px, height: 500px)
    img = Image.new('RGB', (400, 500), color='white')
    draw = ImageDraw.Draw(img)
    
    # 2. Load the default font
    # (In a production environment, you can download a custom .ttf file like Roboto)
    font = ImageFont.load_default()
    
    # 3. Define some colors and layouts
    text_color = (0, 0, 0) # Black
    accent_color = (41, 128, 185) # Blue
    
    # Draw a colored header box
    draw.rectangle([(0, 0), (400, 60)], fill=accent_color)
    
    # --- HEADER ---
    draw.text((100, 20), "HASSLE FREE PRINTING", fill="white", font=font)
    draw.text((140, 40), "Official Receipt", fill="white", font=font)
    
    # --- ORDER DETAILS ---
    y_offset = 100
    draw.text((20, y_offset), f"Invoice No: INV-2026-{order_id}", fill=text_color, font=font)
    draw.text((20, y_offset + 30), f"Date: {date_str}", fill=text_color, font=font)
    
    draw.line([(20, y_offset + 60), (380, y_offset + 60)], fill="gray", width=1) # Separator Line
    
    # --- CUSTOMER DETAILS ---
    y_offset = 190
    draw.text((20, y_offset), f"Billed To: {student_name}", fill=text_color, font=font)
    draw.text((20, y_offset + 30), f"Program: {program}", fill=text_color, font=font)
    draw.text((20, y_offset + 60), f"Served By: Partner {partner_id}", fill=text_color, font=font)
    
    draw.line([(20, y_offset + 100), (380, y_offset + 100)], fill="gray", width=1)
    
    # --- FINANCIALS ---
    y_offset = 320
    draw.text((20, y_offset), "Payment Status:", fill=text_color, font=font)
    draw.text((300, y_offset), "PAID", fill=(39, 174, 96), font=font) # Green text
    
    draw.text((20, y_offset + 40), "TOTAL AMOUNT:", fill=text_color, font=font)
    draw.text((280, y_offset + 40), f"Rs. {amount}", fill=text_color, font=font)
    
    # --- FOOTER ---
    draw.text((80, 450), "Thank you for trusting HassleFree!", fill="gray", font=font)
    
    # 4. Create an 'Invoices' folder if it doesn't exist
    if not os.path.exists("Invoices"):
        os.makedirs("Invoices")
        
    # 5. Save the image
    filename = f"Invoices/INV-{order_id}_{student_name.replace(' ', '')}.png"
    img.save(filename)
    
    return filename

# --- QUICK TEST ---
if __name__ == "__main__":
    # If you run this script directly, it will generate a test receipt!
    test_file = generate_receipt_image(
        order_id="66", 
        student_name="Ahsan", 
        program="BE CE", 
        amount="190.00", 
        date_str="4/27/2026", 
        partner_id="M3"
    )
    print(f"✅ Success! Open the 'Invoices' folder to see: {test_file}")