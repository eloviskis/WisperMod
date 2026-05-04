# 🌐 Audio Intelligence Pipeline - Versão Web

## 🎯 Visão Geral

Sistema web full-stack para processamento de áudio com:
- **Frontend**: React com interface industrial/terminal
- **Backend**: FastAPI com processamento assíncrono
- **Realtime**: WebSocket para atualizações ao vivo
- **Download**: Exportação automática de resultados

---

## 🚀 Setup Rápido (Windows)

### 1️⃣ Pré-requisitos

```bash
# Python 3.8+
python --version

# FFmpeg
ffmpeg -version

# Node.js (para frontend)
node --version
npm --version
```

### 2️⃣ Instalar Backend

```bash
# Clonar/copiar arquivos
cd seu_projeto

# Criar venv (opcional mas recomendado)
python -m venv venv
.\venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r backend_requirements.txt
```

### 3️⃣ Instalar Frontend

```bash
# Criar app React
npx create-react-app frontend

# Entrar no diretório
cd frontend

# Copiar arquivo do componente
# Substituir src/App.jsx pelo arquivo frontend.jsx

# Instalar lucide-react (ícones)
npm install lucide-react
```

### 4️⃣ Executar

**Terminal 1 - Backend:**
```bash
python backend.py
# Rodando em http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
# Rodando em http://localhost:3000
```

---

## 📁 Estrutura do Projeto

```
seu_projeto/
├── backend.py                    # API FastAPI
├── backend_requirements.txt       # Deps backend
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Componente principal (frontend.jsx)
│   │   └── index.js
│   ├── public/
│   └── package.json
├── uploads/                      # Áudios enviados
├── results/                      # Resultados processados
└── README.md                     # Este arquivo
```

---

## 🔄 Fluxo da Aplicação

```
1. Usuário acessa http://localhost:3000
2. Upload do áudio (drag & drop)
3. Backend inicia processamento (background)
4. WebSocket envia atualizações em tempo real
5. Frontend mostra progresso
6. Ao terminar, opção de download
```

---

## 🛠️ Endpoints da API

### Upload e Processamento

**POST** `/upload`
```bash
curl -X POST -F "file=@audio.mp3" http://localhost:8000/upload
# Resposta:
# {
#   "job_id": "uuid-aqui",
#   "status": "processando"
# }
```

### Status

**GET** `/status/{job_id}`
```bash
curl http://localhost:8000/status/uuid-aqui
# Resposta:
# {
#   "status": "processando",
#   "progresso": 45,
#   "mensagem": "Segmento 2/5: Transcrição...",
#   "resultados": null
# }
```

### Download

**GET** `/download/{job_id}`
```bash
curl http://localhost:8000/download/uuid-aqui -o resultados.zip
```

### WebSocket

**WS** `/ws/{job_id}`
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/${jobId}`);
ws.onmessage = (event) => {
  const status = JSON.parse(event.data);
  console.log(status);
};
```

---

## 🎨 Interface

### Upload Page
- Drag & drop de áudio
- Seleção via clique
- Informações do arquivo
- Status do processamento

### Processing Page
- Progresso em tempo real
- Barra de andamento
- Status de cada etapa
- Resultados (ao terminar)
- Download automático

---

## ⚙️ Configuração Avançada

### Ajustar Duração dos Segmentos

**backend.py**, linha ~130:
```python
"-segment_time", "1800",  # 30 min em segundos
```

Mudar para:
```python
"-segment_time", "3600",  # 60 min
```

### Adicionar Categorias Críticas

**backend.py**, função `extrair_timeline()`:
```python
categorias_dict = {
    "FUGA": ["fuga", "escapar"],
    "NOVA": ["palavra1", "palavra2"],  # ← Adicionar
    # ...
}
```

### Ajustar Redução de Ruído

**backend.py**, linha ~180:
```python
"-af", "afftdn=nf=-25",  # -25 = moderado
```

Valores:
- `-20`: Leve
- `-25`: Moderado (padrão)
- `-30`: Agressivo

### Customizar Frontend

**frontend.jsx** - Cores (CSS):
```javascript
.terminal-text { color: rgb(34, 197, 94); }  // Verde
// Mudar para outras cores:
// rgb(59, 130, 246)     - Azul
// rgb(249, 115, 22)     - Laranja
// rgb(239, 68, 68)      - Vermelho
```

---

## 🐛 Troubleshooting

### "Connection refused" ao acessar frontend

- Verificar se backend está rodando: `python backend.py`
- Verificar se porta 8000 está livre
- Testar: `http://localhost:8000/` deve retornar `{"status":"ok"}`

### "Whisper not found"

```bash
pip install openai-whisper
# Se falhar, tente:
pip install --upgrade openai-whisper
```

### "FFmpeg not found"

Windows:
- Instalar de: https://www.gyan.dev/ffmpeg/builds/
- Adicionar `C:\ffmpeg\bin` ao PATH

### Upload não funciona

- Verificar tamanho do arquivo (muito grande = timeout)
- Aumentar timeout no frontend se necessário
- Testar com arquivo menor primeiro

### WebSocket não conecta

- Verificar console do navegador (F12)
- Testar se backend está em http://localhost:8000
- Confirmar que não há firewall bloqueando porta 8000

---

## 📊 Exemplo de Resultado

```
uploads/
└── audio_XXX/
    ├── DIA01-00a30_RELATORIO.txt
    ├── DIA01-30a60_RELATORIO.txt
    └── ...

Cada relatório contém:
- Transcrição completa com timestamps
- Síntese automática
- Destaques críticos
- Estatísticas
```

---

## 🚀 Deploy para Produção

### Servidor (recomendado: DigitalOcean, Heroku, AWS)

```bash
# Backend com Gunicorn
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend:app --bind 0.0.0.0:8000

# Frontend com Nginx
npm run build
# Servir arquivos em /build
```

### Variáveis de Ambiente

**backend.py** - Adicionar:
```python
import os
API_URL = os.getenv("API_URL", "http://localhost:8000")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
```

---

## 💡 Dicas

✅ **Testar com áudio pequeno** - Para verificar setup antes de processar muitas horas  
✅ **Monitorar uso de disco** - Arquivo grande = espaço em disco necessário  
✅ **GPU acelera Whisper** - Se tiver NVIDIA/AMD, Whisper fica muito mais rápido  
✅ **Acompanhar WebSocket** - Abre a janela de desenvolvedor para ver logs  

---

## 📞 Suporte

1. Verificar seção "Troubleshooting"
2. Verificar logs do terminal (backend)
3. Verificar console do navegador (frontend)
4. Testar endpoints via curl/Postman

---

**Versão:** 1.0 Web  
**Stack:** FastAPI + React + WebSocket  
**Compatibilidade:** Windows 10+, macOS 10.14+, Linux  
**Python:** 3.8+  
**Node:** 14+
