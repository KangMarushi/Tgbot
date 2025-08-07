#!/bin/bash

# 🚀 SextBot Raspberry Pi 5 Deployment Script
# This script automates the deployment process

set -e  # Exit on any error

echo "🚀 Starting SextBot deployment on Raspberry Pi 5..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root. Please run as 'pi' user."
   exit 1
fi

# Check if we're on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    print_warning "This script is designed for Raspberry Pi. Continue anyway? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

print_status "Step 1: Updating system packages..."
sudo apt update && sudo apt upgrade -y

print_status "Step 2: Installing required packages..."
sudo apt install -y python3-pip python3-venv git sqlite3 tesseract-ocr libtesseract-dev htop iotop ufw

print_status "Step 3: Creating project directory..."
cd ~
if [ -d "tybot" ]; then
    print_warning "tybot directory already exists. Backup and replace? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        mv tybot tybot_backup_$(date +%Y%m%d_%H%M%S)
    else
        print_error "Please remove or rename existing tybot directory"
        exit 1
    fi
fi

mkdir -p tybot
cd tybot

print_status "Step 4: Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

print_status "Step 5: Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    print_error "requirements.txt not found. Please ensure all project files are copied."
    exit 1
fi

print_status "Step 6: Creating environment file..."
if [ ! -f ".env" ]; then
    cat > .env << EOF
# Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# UPI Payment Configuration
EXPECTED_UPI_ID=your_upi_id
EXPECTED_AMOUNT=10
QR_IMAGE_PATH=qr_png.png

# Database Configuration
DATABASE_PATH=./bot_data.db

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=./bot.log
EOF
    print_warning "Created .env file. Please edit it with your actual API keys!"
    chmod 600 .env
fi

print_status "Step 7: Creating data directory..."
mkdir -p data
chmod 755 data

print_status "Step 8: Initializing database..."
python3 -c "
from characters import character_manager
from memory import init_database
import sqlite3

# Initialize all databases
init_database()
character_manager.init_database()
print('✅ Database initialized successfully')
"

print_status "Step 9: Testing bot components..."
python3 -c "import bot; print('✅ Bot imports successfully')"
python3 -c "
from characters import character_manager
chars = character_manager.characters
print(f'✅ Loaded {len(chars)} characters')
"
python3 -c "
from ai_models import ai_model_manager
model = ai_model_manager.get_model_for_character(80)
print(f'✅ AI model: {model[\"name\"]}')
"

print_status "Step 10: Creating systemd service..."
sudo tee /etc/systemd/system/sextbot.service > /dev/null << EOF
[Unit]
Description=SextBot Telegram Bot
After=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/tybot
Environment=PATH=/home/pi/tybot/.venv/bin
ExecStart=/home/pi/tybot/.venv/bin/python /home/pi/tybot/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

print_status "Step 11: Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable sextbot

print_status "Step 12: Setting up firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 22
sudo ufw --force enable

print_status "Step 13: Creating management scripts..."

# Update script
cat > ~/update_bot.sh << 'EOF'
#!/bin/bash
echo "🔄 Updating SextBot..."
cd /home/pi/tybot
sudo systemctl stop sextbot
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl start sextbot
echo "✅ SextBot updated successfully!"
EOF

# Backup script
cat > ~/backup_bot.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/pi/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
sudo systemctl stop sextbot
tar -czf $BACKUP_DIR/sextbot_backup_$DATE.tar.gz \
    /home/pi/tybot/bot_data.db \
    /home/pi/tybot/.env \
    /home/pi/tybot/characters.json
sudo systemctl start sextbot
find $BACKUP_DIR -name "sextbot_backup_*.tar.gz" -mtime +7 -delete
echo "✅ Backup created: sextbot_backup_$DATE.tar.gz"
EOF

chmod +x ~/update_bot.sh
chmod +x ~/backup_bot.sh

print_status "Step 14: Setting up automated backups..."
(crontab -l 2>/dev/null; echo "0 2 * * * /home/pi/backup_bot.sh") | crontab -

print_status "Step 15: Optimizing SQLite database..."
sqlite3 bot_data.db "PRAGMA journal_mode=WAL;"
sqlite3 bot_data.db "PRAGMA synchronous=NORMAL;"
sqlite3 sqlite3 bot_data.db "PRAGMA cache_size=10000;"

print_success "🎉 Deployment completed successfully!"

echo ""
echo "📋 Next Steps:"
echo "1. Edit .env file with your actual API keys:"
echo "   nano /home/pi/tybot/.env"
echo ""
echo "2. Start the bot:"
echo "   sudo systemctl start sextbot"
echo ""
echo "3. Check status:"
echo "   sudo systemctl status sextbot"
echo ""
echo "4. View logs:"
echo "   sudo journalctl -u sextbot -f"
echo ""
echo "5. Test your bot by sending /start on Telegram"
echo ""
echo "🔧 Management Commands:"
echo "   Update bot: ~/update_bot.sh"
echo "   Create backup: ~/backup_bot.sh"
echo "   Monitor system: htop"
echo "   View logs: sudo journalctl -u sextbot -f"
echo ""

print_warning "⚠️  IMPORTANT: Don't forget to edit the .env file with your actual API keys before starting the bot!"

print_success "🚀 Your SextBot is ready for deployment on Raspberry Pi 5!"
