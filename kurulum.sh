#!/bin/bash
# Piarte Hızlı Kurulum Scripti
# www.baycode.com.tr/piarte için

set -e  # Hata durumunda dur

echo "🚀 Piarte Kurulum Başlıyor..."
echo ""

# Renkler
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Ayarlar
PROJECT_DIR="/var/www/piarte"
SERVICE_USER="www-data"

# 1. Dizin kontrolü
echo -e "${YELLOW}[1/8] Dizin kontrolü...${NC}"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ $PROJECT_DIR dizini bulunamadı!"
    echo "Dosyaları önce yükleyin: app/, templates/, index.html, requirements.txt"
    exit 1
fi

cd $PROJECT_DIR

# 2. Python kontrolü
echo -e "${YELLOW}[2/8] Python kontrolü...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 bulunamadı! Yükleniyor...${NC}"
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

# 3. Virtual environment
echo -e "${YELLOW}[3/8] Virtual environment oluşturuluyor...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# 4. Bağımlılıklar
echo -e "${YELLOW}[4/8] Bağımlılıklar yükleniyor...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# 5. Dosya izinleri
echo -e "${YELLOW}[5/8] Dosya izinleri ayarlanıyor...${NC}"
sudo chown -R $SERVICE_USER:$SERVICE_USER $PROJECT_DIR
sudo chmod -R 755 $PROJECT_DIR

# 6. Systemd service
echo -e "${YELLOW}[6/8] Systemd service oluşturuluyor...${NC}"
sudo tee /etc/systemd/system/piarte.service > /dev/null <<EOF
[Unit]
Description=Piarte Kurs Yönetimi
After=network.target

[Service]
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
Environment="ROOT_PATH=/piarte"
ExecStart=$PROJECT_DIR/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --root-path /piarte
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 7. Service başlat
echo -e "${YELLOW}[7/8] Service başlatılıyor...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable piarte
sudo systemctl start piarte

# 8. Durum kontrolü
echo -e "${YELLOW}[8/8] Durum kontrolü...${NC}"
sleep 2
if sudo systemctl is-active --quiet piarte; then
    echo -e "${GREEN}✅ Service çalışıyor!${NC}"
else
    echo -e "${RED}❌ Service başlatılamadı!${NC}"
    echo "Logları kontrol edin: sudo journalctl -u piarte -n 50"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Kurulum tamamlandı!${NC}"
echo ""
echo "📋 Sonraki adımlar:"
echo "1. Nginx yapılandırmasını yapın (nginx_piarte.conf dosyasına bakın)"
echo "2. Test edin: http://www.baycode.com.tr/piarte/"
echo ""
echo "🔍 Service durumu:"
sudo systemctl status piarte --no-pager -l
echo ""
echo "📝 Logları görmek için:"
echo "sudo journalctl -u piarte -f"


