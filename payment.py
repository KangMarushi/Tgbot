import razorpay
from config import RAZORPAY_KEY, RAZORPAY_SECRET

client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))

def create_payment_link(user_id):
    return client.payment_link.create({
        "amount": 4900,
        "currency": "INR",
        "description": "Unlock your AI girlfriend for 7 days ❤️",
        "callback_url": "https://yourdomain.com/payment_success",
        "callback_method": "get"
    })