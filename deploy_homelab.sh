#!/bin/bash

# 🏠 SextBot Homelab Deployment Script
# Specifically for ~/homelab/apps/Tgbot directory

set -e  # Exit on any error

echo "🏠 Starting SextBot deployment in homelab..."

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

# Get current username
CURRENT_USER=$(whoami)
WORKING_DIR="/home/$CURRENT_USER/homelab/apps/Tgbot"

print_status "Step 1: Navigating to working directory..."
cd $WORKING_DIR
print_success "Working directory: $WORKING_DIR"

print_status "Step 2: Updating system packages..."
sudo apt update && sudo apt upgrade -y

print_status "Step 3: Installing required packages..."
sudo apt install -y python3-pip python3-venv git sqlite3 tesseract-ocr libtesseract-dev htop iotop ufw nginx

print_status "Step 4: Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

print_status "Step 5: Installing Python dependencies..."
pip install -r requirements.txt

print_status "Step 6: Creating images directory..."
mkdir -p images
chmod 755 images

print_status "Step 7: Setting up environment file..."
if [ ! -f ".env" ]; then
    cat > .env << EOF
# Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Database Configuration
DATABASE_PATH=./bot_data.db

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=./bot.log
EOF
    print_warning "Created .env file. Please edit it with your actual API keys!"
    chmod 600 .env
fi

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

print_status "Step 10: Setting up Nginx for image serving..."
sudo tee /etc/nginx/sites-available/sextbot > /dev/null << EOF
server {
    listen 80;
    server_name _;  # Will match any domain/IP

    # Serve character images
    location /images/ {
        alias $WORKING_DIR/images/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint
    location /health {
        return 200 "OK";
        add_header Content-Type text/plain;
    }
}
EOF

# Enable Nginx site
sudo ln -sf /etc/nginx/sites-available/sextbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

print_status "Step 11: Creating systemd service..."
sudo tee /etc/systemd/system/sextbot.service > /dev/null << EOF
[Unit]
Description=SextBot Telegram Bot
After=network.target nginx.service

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$WORKING_DIR
Environment=PATH=$WORKING_DIR/.venv/bin
ExecStart=$WORKING_DIR/.venv/bin/python $WORKING_DIR/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

print_status "Step 12: Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable sextbot

print_status "Step 13: Setting up firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw --force enable

print_status "Step 14: Setting secure permissions..."
chmod 600 .env
chmod 755 images
chmod 644 images/* 2>/dev/null || true
chmod 600 bot_data.db 2>/dev/null || true

print_status "Step 15: Creating management scripts..."

# Update script
cat > ~/update_sextbot.sh << 'EOF'
#!/bin/bash
echo "🔄 Updating SextBot..."
cd /home/your-username/homelab/apps/Tgbot
sudo systemctl stop sextbot
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl start sextbot
echo "✅ SextBot updated successfully!"
EOF

# Backup script
cat > ~/backup_sextbot.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/your-username/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
sudo systemctl stop sextbot
tar -czf $BACKUP_DIR/sextbot_backup_$DATE.tar.gz \
    /home/your-username/homelab/apps/Tgbot/bot_data.db \
    /home/your-username/homelab/apps/Tgbot/.env \
    /home/your-username/homelab/apps/Tgbot/characters.json \
    /home/your-username/homelab/apps/Tgbot/images/
sudo systemctl start sextbot
find $BACKUP_DIR -name "sextbot_backup_*.tar.gz" -mtime +7 -delete
echo "✅ Backup created: sextbot_backup_$DATE.tar.gz"
EOF

# Replace username in scripts
sed -i "s/your-username/$CURRENT_USER/g" ~/update_sextbot.sh
sed -i "s/your-username/$CURRENT_USER/g" ~/backup_sextbot.sh

chmod +x ~/update_sextbot.sh
chmod +x ~/backup_sextbot.sh

print_status "Step 16: Setting up automated backups..."
(crontab -l 2>/dev/null; echo "0 2 * * * /home/$CURRENT_USER/backup_sextbot.sh") | crontab -

print_status "Step 17: Optimizing SQLite database..."
sqlite3 bot_data.db "PRAGMA journal_mode=WAL;" 2>/dev/null || true
sqlite3 bot_data.db "PRAGMA synchronous=NORMAL;" 2>/dev/null || true
sqlite3 bot_data.db "PRAGMA cache_size=10000;" 2>/dev/null || true

print_success "🎉 Homelab deployment completed successfully!"

echo ""
echo "📋 Next Steps:"
echo "1. Add your character images to the images folder:"
echo "   cd $WORKING_DIR/images"
echo "   # Add: priya.jpeg, meera.jpeg, anaya.jpeg, rhea.jpeg, aisha.jpeg"
echo "   # Add: shruti.png, isha.png, tanya.png, sana.png, nikita.png"
echo ""
echo "2. Edit .env file with your API keys:"
echo "   nano $WORKING_DIR/.env"
echo ""
echo "3. Start the bot:"
echo "   sudo systemctl start sextbot"
echo ""
echo "4. Check status:"
echo "   sudo systemctl status sextbot"
echo ""
echo "5. Test image serving:"
echo "   curl -I http://your-server-ip/images/priya.jpeg"
echo ""
echo "6. Test your bot by sending /start on Telegram"
echo ""
echo "🔧 Management Commands:"
echo "   Update bot: ~/update_sextbot.sh"
echo "   Create backup: ~/backup_sextbot.sh"
echo "   Monitor system: htop"
echo "   View logs: sudo journalctl -u sextbot -f"
echo "   Check Nginx: sudo systemctl status nginx"
echo ""

print_warning "⚠️  IMPORTANT: Don't forget to edit the .env file with your actual API keys before starting the bot!"

print_success "🚀 Your SextBot is ready for deployment in your homelab!"
print_success "📍 Working Directory: $WORKING_DIR"
print_success "👤 User: $CURRENT_USER"
