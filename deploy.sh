#!/bin/bash
# Piarte Kurs Yönetim Sistemi - Otomatik Deployment Script
# Kullanım: ./deploy.sh

set -e  # Hata durumunda dur

echo "🚀 Piarte Deployment Başlatılıyor..."
echo ""

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Proje dizini
PROJECT_DIR=$(pwd)

# Virtual environment kontrolü
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Virtual environment oluşturuluyor...${NC}"
    python3 -m venv venv
fi

# Virtual environment'ı aktif et
echo -e "${GREEN}✅ Virtual environment aktif ediliyor...${NC}"
source venv/bin/activate

# Pip'i güncelle
echo -e "${YELLOW}📦 pip güncelleniyor...${NC}"
pip install --upgrade pip

# Bağımlılıkları yükle
echo -e "${YELLOW}📦 Bağımlılıklar yükleniyor...${NC}"
pip install -r requirements.txt

# .env dosyası kontrolü
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env dosyası bulunamadı!${NC}"
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}📝 .env.example'dan .env oluşturuluyor...${NC}"
        cp .env.example .env
        echo -e "${RED}❌ LÜTFEN .env DOSYASINI DÜZENLEYİN VE DATABASE_URL VE SECRET_KEY DEĞERLERİNİ AYARLAYIN!${NC}"
        exit 1
    else
        echo -e "${RED}❌ .env dosyası bulunamadı ve .env.example da yok!${NC}"
        exit 1
    fi
fi

# Veritabanı bağlantısını kontrol et
echo -e "${YELLOW}🔍 Veritabanı bağlantısı kontrol ediliyor...${NC}"
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
db_url = os.getenv('DATABASE_URL', '')
if not db_url:
    print('❌ DATABASE_URL bulunamadı!')
    exit(1)
print(f'✅ DATABASE_URL: {db_url.split(\"@\")[1] if \"@\" in db_url else db_url}')
"

# Veritabanı tablolarını oluştur
echo -e "${YELLOW}📦 Veritabanı tabloları oluşturuluyor...${NC}"
python3 setup_database.py

echo ""
echo -e "${GREEN}✅ Deployment tamamlandı!${NC}"
echo ""
echo "📝 Sonraki adımlar:"
echo "1. Uygulamayı başlatın:"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "2. Veya systemd service kullanın:"
echo "   sudo systemctl start piarte"
echo ""
echo "3. Tarayıcıda açın: http://sunucu-ip:8000"
echo "4. /setup-database endpoint'ine giderek veritabanını başlatın"
echo "5. Admin ile giriş yapın (admin/admin123) ve şifreyi değiştirin!"













