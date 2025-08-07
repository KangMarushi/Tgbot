# 🏠 Homelab Quick Setup - SextBot

## 📍 **Your Setup**
- **Working Directory**: `~/homelab/apps/Tgbot`
- **Images**: Local character images in `/images/` folder
- **Server**: Your homelab server

## ⚡ **Ultra-Fast Setup (3 minutes)**

### **Step 1: Navigate to Your Directory**
```bash
cd ~/homelab/apps/Tgbot
```

### **Step 2: Run Automated Deployment**
```bash
# Make script executable and run
chmod +x deploy_homelab.sh
./deploy_homelab.sh
```

### **Step 3: Add Character Images**
```bash
# Create images directory (if not exists)
mkdir -p images

# Add your character images:
# priya.jpeg, meera.jpeg, anaya.jpeg, rhea.jpeg, aisha.jpeg
# shruti.png, isha.png, tanya.png, sana.png, nikita.png

# Example: Copy your images to the folder
cp /path/to/your/images/* images/
```

### **Step 4: Configure API Keys**
```bash
# Edit environment file
nano .env

# Add your actual API keys:
TELEGRAM_BOT_TOKEN=your_actual_bot_token
OPENROUTER_API_KEY=your_actual_openrouter_key
```

### **Step 5: Start the Bot**
```bash
# Start the service
sudo systemctl start sextbot

# Check status
sudo systemctl status sextbot

# View logs
sudo journalctl -u sextbot -f
```

## 🎯 **That's It!**

Your SextBot is now running 24/7 in your homelab!

### **Test Your Bot**
1. Open Telegram
2. Find your bot
3. Send `/start`
4. Try `/characters` to see the character system with images

### **Test Image Serving**
```bash
# Test if images are being served
curl -I http://your-server-ip/images/priya.jpeg

# Should return HTTP 200 OK
```

## 🔧 **Management Commands**

### **Quick Status Check**
```bash
# Bot status
sudo systemctl status sextbot

# Nginx status (for images)
sudo systemctl status nginx

# View live logs
sudo journalctl -u sextbot -f

# Monitor system
htop
```

### **Update Bot**
```bash
~/update_sextbot.sh
```

### **Create Backup**
```bash
~/backup_sextbot.sh
```

### **Restart Services**
```bash
# Restart bot
sudo systemctl restart sextbot

# Restart Nginx (if needed)
sudo systemctl restart nginx
```

## 🖼️ **Image Management**

### **Current Image Setup**
Your characters are configured to use local images:
- **Priya**: `/images/priya.jpeg`
- **Meera**: `/images/meera.jpeg`
- **Anaya**: `/images/anaya.jpeg`
- **Rhea**: `/images/rhea.jpeg`
- **Aisha**: `/images/aisha.jpeg`
- **Shruti**: `/images/shruti.png`
- **Isha**: `/images/isha.png`
- **Tanya**: `/images/tanya.png`
- **Sana**: `/images/sana.png`
- **Nikita**: `/images/nikita.png`

### **Add/Update Images**
```bash
# Use the management script
python3 add_character_images.py

# Or manually replace images
cp new_priya.jpg images/priya.jpeg
```

## 🚨 **Troubleshooting**

### **Bot Won't Start**
```bash
# Check logs
sudo journalctl -u sextbot -n 50

# Check API keys
cat .env

# Test manually
cd ~/homelab/apps/Tgbot
source .venv/bin/activate
python3 bot.py
```

### **Images Not Loading**
```bash
# Check Nginx status
sudo systemctl status nginx

# Check image files exist
ls -la ~/homelab/apps/Tgbot/images/

# Test image URL
curl -I http://your-server-ip/images/priya.jpeg

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### **Database Issues**
```bash
# Check database
cd ~/homelab/apps/Tgbot
sqlite3 bot_data.db ".tables"

# Reinitialize if needed
source .venv/bin/activate
python3 -c "from characters import character_manager; character_manager.init_database()"
```

## 📊 **What's Included**

✅ **Automated Setup**: One script does everything  
✅ **Nginx Image Serving**: Local character images  
✅ **Systemd Service**: 24/7 operation with auto-restart  
✅ **Security**: Firewall and proper permissions  
✅ **Monitoring**: Logs and system monitoring  
✅ **Backup**: Automated daily backups  
✅ **Updates**: Easy update script  
✅ **AI Tiers**: Different models for different characters  
✅ **Stars Payments**: Telegram Stars integration  

## 🎉 **Ready for Production!**

Your SextBot now features:
- **10 AI Characters** with local profile images
- **3 AI Model Tiers** (Free, Premium, Ultra Premium)
- **Telegram Stars Payments** for premium characters
- **Unlimited Access** unlock system
- **24/7 Operation** in your homelab
- **Professional Image Serving** via Nginx

### **Revenue Streams**
- **Unlimited Access**: 50-150 Stars
- **Character Unlocks**: 70-150 Stars per character
- **Premium AI Models**: Better quality justifies pricing

**🚀 Deploy and start earning with your AI girlfriend bot from your homelab!**

### **Next Steps**
1. **Add Character Images**: Place your character photos in the `images/` folder
2. **Configure API Keys**: Update `.env` with your actual tokens
3. **Test Everything**: Verify bot and image serving work
4. **Monitor Performance**: Keep an eye on logs and system resources
5. **Scale Up**: Add more characters or features as needed
