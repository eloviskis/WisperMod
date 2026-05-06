#!/bin/bash
# deploy.sh — Instala/atualiza WisperMod no servidor
# Uso: bash deploy.sh
set -e

APP_DIR="/opt/wispermod"
WWW_DIR="/var/www/wispermod"
REPO="https://github.com/eloviskis/WisperMod.git"

echo "=== [1/7] Instalando dependências do sistema ==="
apt-get update -qq
apt-get install -y -qq ffmpeg git nodejs npm

echo "=== [2/7] Clonando/atualizando repositório ==="
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull
else
    git clone "$REPO" "$APP_DIR"
fi

echo "=== [3/7] Configurando Python venv ==="
cd "$APP_DIR"
python3 -m venv venv
venv/bin/pip install --upgrade pip -q
venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu -q
venv/bin/pip install -r requirements_web.txt -q

echo "=== [4/7] Construindo frontend ==="
cd "$APP_DIR"
npm install --silent

VITE_API_URL=http://77.37.41.105/wispermod/api \
VITE_WS_URL=ws://77.37.41.105/wispermod/ws \
npx vite build --base=/wispermod/ --outDir=dist

echo "=== [5/7] Deployando frontend estático ==="
mkdir -p "$WWW_DIR"
cp -r "$APP_DIR"/dist/* "$WWW_DIR/"
echo "   Frontend copiado para $WWW_DIR"

echo "=== [6/7] Configurando nginx ==="
cp "$APP_DIR/nginx-wispermod.conf" /etc/nginx/sites-available/wispermod
if [ ! -L /etc/nginx/sites-enabled/wispermod ]; then
    ln -s /etc/nginx/sites-available/wispermod /etc/nginx/sites-enabled/wispermod
fi
nginx -t
nginx -s reload
echo "   Nginx recarregado"

echo "=== [7/7] Configurando serviço systemd ==="
cp "$APP_DIR/wispermod.service" /etc/systemd/system/wispermod.service
systemctl daemon-reload
systemctl enable wispermod
systemctl restart wispermod
sleep 2
systemctl status wispermod --no-pager

echo ""
echo "=== DEPLOY CONCLUÍDO ==="
echo "   Acesse: http://77.37.41.105/wispermod/"
