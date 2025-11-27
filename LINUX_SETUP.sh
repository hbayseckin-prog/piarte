#!/bin/bash
# Piarte Linux Kurulum Scripti
# www.baycode.com.tr/piarte için

echo "🚀 Piarte Kurulum Başlıyor..."

# Renkler
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Proje dizini
PROJECT_DIR="/var/www/piarte"
SERVICE_USER="www-data"

echo -e "${YELLOW}Proje dizini: $PROJECT_DIR${NC}"

# 1. Dizin oluştur
echo -e "\n${GREEN}[1/6] Dizin oluşturuluyor...${NC}"
sudo mkdir -p $PROJECT_DIR
sudo chown -R $SERVICE_USER:$SERVICE_USER $PROJECT_DIR

# 2. Python ve pip kontrolü
echo -e "\n${GREEN}[2/6] Python kontrol ediliyor...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 bulunamadı! Yükleniyor...${NC}"
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

# 3. Virtual environment oluştur
echo -e "\n${GREEN}[3/6] Virtual environment oluşturuluyor...${NC}"
cd $PROJECT_DIR
sudo -u $SERVICE_USER python3 -m venv venv
sudo -u $SERVICE_USER venv/bin/pip install --upgrade pip

# 4. Bağımlılıkları yükle
echo -e "\n${GREEN}[4/6] Bağımlılıklar yükleniyor...${NC}"
sudo -u $SERVICE_USER venv/bin/pip install -r requirements.txt

# 5. Systemd service oluştur
echo -e "\n${GREEN}[5/6] Systemd service oluşturuluyor...${NC}"
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

# 6. Service'i başlat
echo -e "\n${GREEN}[6/6] Service başlatılıyor...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable piarte
sudo systemctl start piarte

# Durum kontrolü
echo -e "\n${GREEN}✅ Kurulum tamamlandı!${NC}"
echo -e "\n${YELLOW}Service durumu:${NC}"
sudo systemctl status piarte --no-pager

echo -e "\n${YELLOW}Logları görmek için:${NC}"
echo "sudo journalctl -u piarte -f"

echo -e "\n${YELLOW}Sonraki adım: Nginx yapılandırmasını yapın!${NC}"


