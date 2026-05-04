"""
Backend FastAPI para Pipeline de Processamento de Áudio
Processamento assíncrono com WebSocket para atualizações em tempo real
"""

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, WebSocket
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
    """Processa áudio sincronamente"""
    
    try:
        atualizar_job(job_id, "processando", {"progresso": 10, "mensagem": "Fracionando áudio..."})
        
        base_nome = Path(arquivo).stem
        pasta_saida = RESULTS_DIR / f"{base_nome}_{job_id[:8]}"
        pasta_saida.mkdir(exist_ok=True)
        
        temp_dir = pasta_saida / "temp"
        temp_dir.mkdir(exist_ok=True)

        # FRACIONAMENTO
        subprocess.run([
            "ffmpeg", "-i", arquivo,
            "-f", "segment",
            "-segment_time", "1800",
            "-c", "copy",
            "-y",
            str(temp_dir / "seg_%03d.mp3")
        ], capture_output=True, check=True)

        arquivos = sorted([f for f in os.listdir(temp_dir) if f.startswith("seg_")])
        
        atualizar_job(job_id, "processando", {
            "progresso": 20,
            "mensagem": f"Processando {len(arquivos)} segmento(s)..."
        })

        resultados_segmentos = []
        
        for i, arq in enumerate(arquivos):
            caminho = temp_dir / arq
            nome_base_seg = f"DIA01-{i*30:02d}a{i*30+30:02d}"
            
            progresso = 20 + int(60 * (i / len(arquivos)))
            atualizar_job(job_id, "processando", {
                "progresso": progresso,
                "mensagem": f"Segmento {i+1}/{len(arquivos)}: Limpeza e transcrição..."
            })

            # LIMPEZA
            limpo = str(caminho).replace(".mp3", "_clean.mp3")
            subprocess.run([
                "ffmpeg", "-i", str(caminho),
                "-af", "afftdn=nf=-25",
                "-y",
                limpo
            ], capture_output=True, check=True)

            # TRANSCRIÇÃO
            try:
                subprocess.run([
                    "whisperx", limpo,
                    "--language", "pt",
                    "--output_format", "txt"
                ], capture_output=True, check=True)
            except:
                subprocess.run([
                    "whisper", limpo,
                    "--language", "pt",
                    "--output_format", "txt"
                ], capture_output=True, check=True)

            # ANÁLISE
            txt_file = limpo.replace(".mp3", ".txt")
            if os.path.exists(txt_file):
                with open(txt_file, encoding="utf-8") as f:
                    texto = f.read()

                eventos = extrair_timeline(texto)
                sintese = gerar_sintese(eventos)
                destaques = extrair_destaques(eventos)

                # SALVAR RELATÓRIO
                rel_file = pasta_saida / f"{nome_base_seg}_RELATORIO.txt"
                with open(rel_file, "w", encoding="utf-8") as r:
                    r.write("=" * 70 + "\n")
                    r.write(f"RELATÓRIO - {nome_base_seg}\n")
                    r.write("=" * 70 + "\n\n")
                    r.write("📋 TRANSCRIÇÃO\n")
                    r.write("-" * 70 + "\n")
                    r.write(texto)
                    r.write("\n\n" + "=" * 70 + "\n")
                    r.write("🎯 SÍNTESE\n")
                    r.write("-" * 70 + "\n")
                    r.write(sintese)
                    r.write("\n\n" + "=" * 70 + "\n")
                    r.write("🔴 DESTAQUES\n")
                    r.write("-" * 70 + "\n")
                    for d in destaques:
                        r.write(f"{d.tempo} [{','.join(d.categorias)}]\n")
                        r.write(f"   {d.texto}\n\n")

                resultados_segmentos.append({
                    "segmento": nome_base_seg,
                    "eventos": len(eventos),
                    "destaques": len(destaques)
                })

        atualizar_job(job_id, "concluido", {
            "progresso": 100,
            "mensagem": "Processamento concluído!",
            "resultados": {
                "pasta": str(pasta_saida),
                "segmentos": resultados_segmentos,
                "total_eventos": sum(r["eventos"] for r in resultados_segmentos),
                "total_destaques": sum(r["destaques"] for r in resultados_segmentos)
            }
        })

        return JOBS[job_id]

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
    
    job_id = str(uuid.uuid4())
    
    # Salvar arquivo
    arquivo_path = UPLOAD_DIR / file.filename
    with open(arquivo_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    atualizar_job(job_id, "iniciado", {
        "progresso": 0,
        "mensagem": "Iniciando processamento...",
        "arquivo": file.filename,
        "tamanho": len(content)
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
    
    try:
        while True:
            if job_id in JOBS:
                await websocket.send_json(JOBS[job_id])
            
            if job_id in JOBS and JOBS[job_id]["status"] in ["concluido", "erro"]:
                break
            
            await asyncio.sleep(1)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
