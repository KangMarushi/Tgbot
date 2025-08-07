import json
import os
from PIL import Image
import pytesseract
import difflib
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

# UPI Payment Configuration
EXPECTED_UPI_ID = os.getenv("EXPECTED_UPI_ID", "yourupi@upi")  # Replace with your actual UPI ID
EXPECTED_AMOUNT = int(os.getenv("EXPECTED_AMOUNT", "49"))  # Set the expected amount in INR
QR_IMAGE_PATH = os.getenv("QR_IMAGE_PATH", "test_qr.png")  # Path to your QR code image
USER_DB_FILE = "users.json"

def get_qr_image_bytes():
    """Get QR image as bytes for sending via Telegram"""
    try:
        from PIL import Image
        from io import BytesIO
        
        if os.path.exists(QR_IMAGE_PATH):
            img = Image.open(QR_IMAGE_PATH)
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            return buffer.getvalue()
        else:
            # Create a simple QR code if file doesn't exist
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(EXPECTED_UPI_ID)
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            return buffer.getvalue()
    except Exception as e:
        print(f"Error creating QR image: {e}")
        return None

# User Database for UPI payments
def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "r") as f:
            return json.load(f)
    return {"paid": [], "pending": []}

def save_users(data):
    with open(USER_DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

# OCR & Matching functions
def extract_text_from_image(image: Image.Image) -> str:
    return pytesseract.image_to_string(image)

def is_fuzzy_match(text, pattern, threshold=0.6):
    return difflib.SequenceMatcher(None, text.lower(), pattern.lower()).ratio() > threshold

def has_paid(text: str) -> bool:
    amount_match = any(is_fuzzy_match(word.strip("₹₹Rs."), str(EXPECTED_AMOUNT)) for word in text.split())
    upi_match = is_fuzzy_match(text, EXPECTED_UPI_ID)
    return amount_match and upi_match

def verify_payment_screenshot(image_bytes: bytes, user_id: int) -> bool:
    """Verify payment screenshot and mark user as paid if valid"""
    try:
        image = Image.open(BytesIO(image_bytes))
        text = extract_text_from_image(image)
        
        if has_paid(text):
            users = load_users()
            user_id_str = str(user_id)
            if user_id_str not in users["paid"]:
                users["paid"].append(user_id_str)
            if user_id_str in users["pending"]:
                users["pending"].remove(user_id_str)
            save_users(users)
            return True
        return False
    except Exception as e:
        print(f"Error verifying payment: {e}")
        return False

def create_payment_instructions(user_id: int) -> dict:
    """Create UPI payment instructions instead of Razorpay link"""
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users["pending"]:
        users["pending"].append(user_id_str)
        save_users(users)
    
    return {
        "upi_id": EXPECTED_UPI_ID,
        "amount": EXPECTED_AMOUNT,
        "qr_path": QR_IMAGE_PATH,
        "instructions": f"Pay ₹{EXPECTED_AMOUNT} to {EXPECTED_UPI_ID}"
    }

def is_user_paid_upi(user_id: int) -> bool:
    """Check if user has paid using UPI system"""
    users = load_users()
    return str(user_id) in users["paid"]