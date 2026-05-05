"""
Módulo core de processamento de áudio — WisperMod
Transcrição com Whisper + Análise de Conteúdo Crítico
"""

import os
import sys
import re
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Callable, Dict, List, Optional


# ─── caminhos (desenvolvimento vs bundle PyInstaller) ────────────────────────

def _base_path() -> Path:
    """Retorna pasta base do executável ou do projeto em modo dev."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


def get_ffmpeg() -> str:
    """Retorna caminho do ffmpeg (bundled no .exe ou sistema)."""
    if getattr(sys, "frozen", False):
        return str(_base_path() / "bin" / "ffmpeg.exe")
    return "ffmpeg"


def get_model_dir() -> Path:
    """Retorna pasta onde o modelo Whisper está armazenado."""
    return _base_path() / "models"


def _setup_env():
    """Adiciona o ffmpeg bundled ao PATH para que o Whisper o encontre."""
    if getattr(sys, "frozen", False):
        bin_dir = str(_base_path() / "bin")
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")


# ─── análise de conteúdo crítico ─────────────────────────────────────────────

CATEGORIAS: Dict[str, List[str]] = {
    "FUGA":        ["fuga", "escapar", "fugir", "sair"],
    "DROGA":       ["droga", "pó", "cocaína", "maconha", "heroína"],
    "ORDEM":       ["mandar", "ordem", "comando", "chefe"],
    "VIOLENCIA":   ["matar", "cobrar", "bater", "quebrar", "morte"],
    "LOGISTICA":   ["entregar", "esconder", "trazer", "levar", "armazenar"],
    "COMUNICACAO": ["recado", "salve", "aviso", "mensagem", "passar"],
}


def classificar_linha(linha: str) -> List[str]:
    """Retorna lista de categorias encontradas em uma linha de texto."""
    encontrados = []
    ll = linha.lower()
    for cat, palavras in CATEGORIAS.items():
        for p in palavras:
            if p in ll:
                encontrados.append(cat)
                break
    return encontrados


def extrair_timeline(segmentos_whisper: list, offset_s: float = 0.0) -> List[Dict]:
    """Extrai eventos críticos da lista de segmentos retornada pelo Whisper."""
    eventos = []
    for seg in segmentos_whisper:
        cats = classificar_linha(seg["text"])
        if cats:
            t = seg["start"] + offset_s
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = int(t % 60)
            eventos.append({
                "tempo": f"[{h:02d}:{m:02d}:{s:02d}]",
                "categorias": cats,
                "texto": seg["text"].strip(),
            })
    return eventos


def gerar_sintese(eventos: List[Dict]) -> str:
    """Gera síntese automática baseada nos eventos críticos identificados."""
    por_cat: Dict[str, list] = {c: [] for c in CATEGORIAS}
    for ev in eventos:
        for c in ev["categorias"]:
            por_cat[c].append(ev)

    linhas = []
    if por_cat["FUGA"]:        linhas.append("AVISO:  Há indícios de planejamento de evasão.")
    if por_cat["VIOLENCIA"]:   linhas.append("ALERTA: Identificadas referências a ações violentas.")
    if por_cat["DROGA"]:       linhas.append("ALERTA: Constam menções a substâncias ilícitas.")
    if por_cat["ORDEM"]:       linhas.append("INFO:   Observa-se dinâmica clara de comando.")
    if por_cat["LOGISTICA"]:   linhas.append("INFO:   Há articulação logística estruturada.")
    if por_cat["COMUNICACAO"]: linhas.append("INFO:   Há troca estruturada de informações.")

    return "\n".join(linhas) if linhas else "Nenhum evento crítico identificado."


def extrair_destaques(eventos: List[Dict]) -> List[Dict]:
    """Extrai os eventos de maior prioridade (máx. 10)."""
    prioridade = ["FUGA", "VIOLENCIA", "DROGA", "ORDEM"]
    vistos: set = set()
    destaques: List[Dict] = []
    for p in prioridade:
        for ev in eventos:
            chave = ev["tempo"] + ev["texto"][:30]
            if p in ev["categorias"] and chave not in vistos:
                destaques.append(ev)
                vistos.add(chave)
    return destaques[:10]


# ─── pipeline principal ───────────────────────────────────────────────────────

def processar_audio(
    arquivo: str,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict:
    """
    Pipeline completo: segmentação → limpeza de ruído → transcrição →
    análise de conteúdo → relatórios.

    Args:
        arquivo: Caminho absoluto do arquivo de áudio.
        progress_callback: função(percent: int, message: str)
                           chamada a cada etapa para atualizar a UI.

    Returns:
        dict com:
            pasta_saida       — pasta onde os resultados foram salvos
            relatorio_final   — caminho do RELATORIO_FINAL.txt
            contagem_por_cat  — {categoria: total_ocorrencias}
            total_eventos     — total de eventos críticos
            total_destaques   — total de destaques extraídos
            segmentos         — lista com detalhes de cada segmento
    """

    def _cb(p: int, msg: str):
        if progress_callback:
            progress_callback(p, msg)

    _setup_env()

    ffmpeg = get_ffmpeg()
    model_dir = get_model_dir()
    arquivo_path = Path(arquivo)
    base_nome = arquivo_path.stem
    pasta_saida = arquivo_path.parent / f"{base_nome}_PROCESSADO"
    pasta_saida.mkdir(exist_ok=True)
    temp_dir = pasta_saida / "temp"
    temp_dir.mkdir(exist_ok=True)

    # ── ETAPA 1: segmentar o áudio ────────────────────────────────────────────
    # Re-encode para MP3 16 kHz mono — compatível com qualquer codec de entrada
    # (OGG/Opus, AAC, WAV, etc.) e otimizado para o Whisper.
    _cb(5, "Segmentando áudio em partes de 30 minutos...")
    subprocess.run(
        [
            ffmpeg, "-i", str(arquivo_path),
            "-f", "segment",
            "-segment_time", "1800",
            "-acodec", "libmp3lame",
            "-ar", "16000",
            "-ac", "1",
            "-q:a", "4",
            "-y",
            str(temp_dir / "seg_%03d.mp3"),
        ],
        capture_output=True,
        check=True,
    )

    segmentos = sorted(temp_dir.glob("seg_*.mp3"))
    if not segmentos:
        raise RuntimeError("Nenhum segmento gerado pelo FFmpeg. Verifique se o arquivo é válido.")

    # ── ETAPA 2: carregar modelo Whisper ──────────────────────────────────────
    _cb(10, f"Carregando modelo Whisper ({len(segmentos)} segmento(s) a processar)...")
    import whisper  # import tardio para não atrasar o startup da UI
    model = whisper.load_model("small", download_root=str(model_dir))

    # ── ETAPA 3: processar cada segmento ─────────────────────────────────────
    todos_eventos: List[Dict] = []
    resultados_seg: List[Dict] = []
    n = len(segmentos)

    for i, seg_path in enumerate(segmentos):
        pct_base = 15 + int(70 * i / n)
        nome_seg = f"SEG{i + 1:02d}_{i * 30:02d}min_{(i + 1) * 30:02d}min"
        offset_s = float(i * 1800)

        _cb(pct_base, f"Segmento {i + 1}/{n}: limpando ruído...")
        seg_clean = temp_dir / f"seg_{i:03d}_clean.mp3"
        subprocess.run(
            [
                ffmpeg, "-i", str(seg_path),
                "-af", "afftdn=nf=-25",
                "-y", str(seg_clean),
            ],
            capture_output=True,
            check=True,
        )

        _cb(pct_base + int(35 / n), f"Segmento {i + 1}/{n}: transcrevendo...")
        result = model.transcribe(str(seg_clean), language="pt", verbose=None)

        eventos = extrair_timeline(result["segments"], offset_s)
        todos_eventos.extend(eventos)

        sintese = gerar_sintese(eventos)
        destaques = extrair_destaques(eventos)

        # Relatório do segmento
        rel_path = pasta_saida / f"{nome_seg}_RELATORIO.txt"
        with open(rel_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write(f"RELATÓRIO DE ANÁLISE — {nome_seg}\n")
            f.write("=" * 70 + "\n\n")
            f.write("TRANSCRIÇÃO\n")
            f.write("-" * 70 + "\n")
            for s in result["segments"]:
                t = s["start"] + offset_s
                h, mv, sc = int(t // 3600), int((t % 3600) // 60), int(t % 60)
                f.write(f"[{h:02d}:{mv:02d}:{sc:02d}] {s['text'].strip()}\n")
            f.write("\n\nSÍNTESE\n")
            f.write("-" * 70 + "\n")
            f.write(sintese + "\n")
            f.write("\nDESTAQUES CRÍTICOS\n")
            f.write("-" * 70 + "\n")
            if destaques:
                for d in destaques:
                    f.write(f"{d['tempo']} [{' | '.join(d['categorias'])}]\n")
                    f.write(f"   {d['texto']}\n\n")
            else:
                f.write("Nenhum destaque crítico identificado.\n")

        resultados_seg.append({
            "nome": nome_seg,
            "eventos": len(eventos),
            "destaques": len(destaques),
            "relatorio": str(rel_path),
        })

    # ── ETAPA 4: relatório consolidado ────────────────────────────────────────
    _cb(88, "Gerando relatório consolidado...")

    contagem_total: Dict[str, int] = {c: 0 for c in CATEGORIAS}
    for ev in todos_eventos:
        for c in ev["categorias"]:
            contagem_total[c] += 1

    todos_destaques = extrair_destaques(todos_eventos)
    sintese_geral = gerar_sintese(todos_eventos)

    relatorio_final = pasta_saida / "RELATORIO_FINAL.txt"
    with open(relatorio_final, "w", encoding="utf-8") as rf:
        rf.write("=" * 70 + "\n")
        rf.write(f"ANÁLISE CONSOLIDADA — {base_nome}\n")
        rf.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
        rf.write("=" * 70 + "\n\n")
        rf.write("RESUMO EXECUTIVO\n")
        rf.write("-" * 70 + "\n")
        rf.write(f"Segmentos processados  : {len(segmentos)}\n")
        rf.write(f"Duração estimada       : ~{len(segmentos) * 30} minutos\n")
        rf.write(f"Eventos críticos       : {len(todos_eventos)}\n")
        rf.write(f"Destaques prioritários : {len(todos_destaques)}\n\n")
        rf.write("CONTAGEM POR CATEGORIA\n")
        rf.write("-" * 70 + "\n")
        for cat, cnt in contagem_total.items():
            rf.write(f"  {cat:<15} {cnt}\n")
        rf.write("\nSÍNTESE GERAL\n")
        rf.write("-" * 70 + "\n")
        rf.write(sintese_geral + "\n")
        rf.write("\nTOP DESTAQUES\n")
        rf.write("-" * 70 + "\n")
        for d in todos_destaques:
            rf.write(f"{d['tempo']} [{' | '.join(d['categorias'])}]\n")
            rf.write(f"   {d['texto']}\n\n")
        rf.write("\nRELATÓRIOS POR SEGMENTO\n")
        rf.write("-" * 70 + "\n")
        for r in resultados_seg:
            rf.write(f"  {r['nome']}: {r['eventos']} eventos, {r['destaques']} destaques\n")

    # ── LIMPEZA ───────────────────────────────────────────────────────────────
    _cb(95, "Limpando arquivos temporários...")
    shutil.rmtree(temp_dir, ignore_errors=True)

    _cb(100, "Processamento concluído!")

    return {
        "pasta_saida": str(pasta_saida),
        "relatorio_final": str(relatorio_final),
        "contagem_por_cat": contagem_total,
        "total_eventos": len(todos_eventos),
        "total_destaques": len(todos_destaques),
        "segmentos": resultados_seg,
    }
