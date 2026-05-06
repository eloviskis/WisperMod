"""
Backend FastAPI para Pipeline de Processamento de Áudio
Processamento assíncrono com WebSocket para atualizações em tempo real
"""

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import subprocess
import json
import asyncio
from pathlib import Path
from datetime import datetime
import uuid
import re
from typing import List, Dict

# =============================
# CONFIG
# =============================

app = FastAPI(title="Audio Intelligence Pipeline")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diretórios
UPLOAD_DIR = Path("uploads")
RESULTS_DIR = Path("results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Limites e validação
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma", ".opus"}

# Store para status em tempo real
JOBS = {}


# =============================
# MODELOS
# =============================

class Event:
    def __init__(self, tempo, categorias, texto):
        self.tempo = tempo
        self.categorias = categorias
        self.texto = texto

    def to_dict(self):
        return {
            "tempo": self.tempo,
            "categorias": self.categorias,
            "texto": self.texto
        }


# =============================
# FUNÇÕES DE PROCESSAMENTO
# =============================

def atualizar_job(job_id: str, status: str, data: Dict = None):
    """Atualiza status de um job"""
    if job_id not in JOBS:
        JOBS[job_id] = {
            "status": "iniciado",
            "progresso": 0,
            "mensagem": "",
            "resultados": None
        }
    
    JOBS[job_id]["status"] = status
    if data:
        JOBS[job_id].update(data)


def extrair_timeline(texto: str) -> List[Event]:
    """Extrai eventos com timestamps e classificação"""
    categorias_dict = {
        "FUGA": ["fuga", "escapar", "fugir", "sair"],
        "DROGA": ["droga", "pó", "cocaína", "maconha", "heroína"],
        "ORDEM": ["mandar", "ordem", "comando", "chefe"],
        "VIOLENCIA": ["matar", "cobrar", "bater", "quebrar", "morte"],
        "LOGISTICA": ["entregar", "esconder", "trazer", "levar"],
        "COMUNICACAO": ["recado", "salve", "aviso", "mensagem"]
    }

    eventos = []
    
    for linha in texto.split("\n"):
        match = re.match(r"\[(\d+):(\d+):(\d+)\]", linha)
        if match:
            encontrados = []
            linha_lower = linha.lower()
            
            for cat, palavras in categorias_dict.items():
                for p in palavras:
                    if p in linha_lower:
                        encontrados.append(cat)
                        break
            
            if encontrados:
                eventos.append(Event(
                    tempo=match.group(1),
                    categorias=encontrados,
                    texto=linha.strip()
                ))
    
    return eventos


def gerar_sintese(eventos: List[Event]) -> str:
    """Gera síntese automática"""
    resumo = []
    categorias = {
        c: [] for c in ["FUGA", "VIOLENCIA", "DROGA", "ORDEM", "LOGISTICA", "COMUNICACAO"]
    }

    for ev in eventos:
        for c in ev.categorias:
            categorias[c].append(ev)

    if categorias["FUGA"]:
        resumo.append("⚠️ Há indícios de planejamento de evasão.")
    if categorias["VIOLENCIA"]:
        resumo.append("🔴 Identificadas referências a ações violentas.")
    if categorias["DROGA"]:
        resumo.append("🔴 Constam menções a substâncias ilícitas.")
    if categorias["ORDEM"]:
        resumo.append("👥 Observa-se dinâmica clara de comando.")
    if categorias["LOGISTICA"]:
        resumo.append("📦 Há articulação logística estruturada.")
    if categorias["COMUNICACAO"]:
        resumo.append("💬 Há troca estruturada de informações.")

    return "\n".join(resumo) if resumo else "Nenhum evento crítico identificado."


def extrair_destaques(eventos: List[Event]) -> List[Event]:
    """Extrai eventos prioritários"""
    prioridade = ["FUGA", "VIOLENCIA", "DROGA", "ORDEM"]
    destaques = []

    for p in prioridade:
        for ev in eventos:
            if p in ev.categorias:
                destaques.append(ev)

    return destaques[:10]


def processar_audio_sync(arquivo: str, job_id: str) -> Dict:
    """Processa áudio delegando ao core/processador.py"""
    from core.processador import processar_audio

    def _cb(progresso: int, mensagem: str):
        atualizar_job(job_id, "processando", {"progresso": progresso, "mensagem": mensagem})

    try:
        resultado = processar_audio(arquivo, progress_callback=_cb)

        atualizar_job(job_id, "concluido", {
            "progresso": 100,
            "mensagem": "Processamento concluído!",
            "resultados": {
                "pasta": resultado["pasta_saida"],
                "relatorio_final": resultado["relatorio_final"],
                "contagem_por_cat": resultado["contagem_por_cat"],
                "segmentos": resultado["segmentos"],
                "total_eventos": resultado["total_eventos"],
                "total_destaques": resultado["total_destaques"],
            }
        })

    except Exception as e:
        atualizar_job(job_id, "erro", {
            "mensagem": f"Erro: {str(e)}",
            "progresso": 0
        })

    return JOBS[job_id]


# =============================
# ROTAS
# =============================

@app.get("/")
async def root():
    return {"status": "ok", "versao": "1.0"}


@app.post("/upload")
async def upload_audio(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    """Upload e processamento de áudio"""

    # Validação de extensão
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Formato não suportado: '{ext}'. Use: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    job_id = str(uuid.uuid4())
    
    # Salvar arquivo com leitura em chunks para não estourar memória
    arquivo_path = UPLOAD_DIR / file.filename
    tamanho = 0
    with open(arquivo_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)  # 1 MB por vez
            if not chunk:
                break
            tamanho += len(chunk)
            if tamanho > MAX_FILE_SIZE:
                f.close()
                arquivo_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"Arquivo excede o limite de {MAX_FILE_SIZE // (1024*1024)} MB."
                )
            f.write(chunk)
    
    atualizar_job(job_id, "iniciado", {
        "progresso": 0,
        "mensagem": "Iniciando processamento...",
        "arquivo": file.filename,
        "tamanho": tamanho
    })
    
    # Processar em background
    background_tasks.add_task(processar_audio_sync, str(arquivo_path), job_id)
    
    return {
        "job_id": job_id,
        "status": "processando"
    }


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Obter status de um job"""
    return JOBS.get(job_id, {"status": "nao_encontrado"})


@app.get("/download/{job_id}")
async def download_results(job_id: str):
    """Download dos resultados"""
    
    if job_id not in JOBS:
        return {"erro": "Job não encontrado"}
    
    job = JOBS[job_id]
    
    if job["status"] != "concluido":
        return {"erro": "Job ainda está processando"}
    
    pasta = job["resultados"]["pasta"]
    
    # Criar ZIP com resultados
    import shutil
    zip_path = f"/tmp/{job_id}.zip"
    shutil.make_archive(zip_path.replace(".zip", ""), "zip", pasta)
    
    return FileResponse(zip_path, filename=f"resultados_{job_id[:8]}.zip")


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket para atualizações em tempo real"""
    await websocket.accept()
    
    ping_counter = 0
    try:
        while True:
            if job_id in JOBS:
                await websocket.send_json(JOBS[job_id])
            
            if job_id in JOBS and JOBS[job_id]["status"] in ["concluido", "erro"]:
                break
            
            await asyncio.sleep(1)

            # Ping a cada 5s para manter conexão viva
            ping_counter += 1
            if ping_counter >= 5:
                ping_counter = 0
                await websocket.send_json({"_ping": True})
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
