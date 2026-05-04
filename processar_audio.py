#!/usr/bin/env python3
"""
Pipeline de Processamento de Áudio
Transcrição + Diarização + Análise de Conteúdo Crítico
"""

import os
import subprocess
import sys
import re
import json
from pathlib import Path
from datetime import timedelta

# =============================
# FUNÇÕES AUXILIARES
# =============================

def ajustar_timestamp(texto, offset_minutos):
    """Ajusta timestamps considerando offset de segmentos anteriores"""
    linhas = texto.split("\n")
    novo = []

    for linha in linhas:
        match = re.match(r"\[(\d+):(\d+):(\d+)\]", linha)
        if match:
            h, m, s = map(int, match.groups())
            total = h*3600 + m*60 + s + offset_minutos*60

            nh = total // 3600
            nm = (total % 3600) // 60
            ns = total % 60

            linha = re.sub(
                r"\[\d+:\d+:\d+\]",
                f"[{nh:02d}:{nm:02d}:{ns:02d}]",
                linha
            )

        novo.append(linha)

    return "\n".join(novo)


def classificar_assunto(linha):
    """Classifica linha por categorias de conteúdo crítico"""
    categorias = {
        "FUGA": ["fuga", "escapar", "fugir", "sair"],
        "DROGA": ["droga", "pó", "cocaína", "maconha", "heroína"],
        "ORDEM": ["mandar", "ordem", "comando", "chefe"],
        "VIOLENCIA": ["matar", "cobrar", "bater", "quebrar", "morte"],
        "LOGISTICA": ["entregar", "esconder", "trazer", "levar", "armazenar"],
        "COMUNICACAO": ["recado", "salve", "aviso", "mensagem", "passar"]
    }

    encontrados = []
    linha_lower = linha.lower()
    
    for cat, palavras in categorias.items():
        for p in palavras:
            if p in linha_lower:
                encontrados.append(cat)
                break
    
    return encontrados


def extrair_timeline(texto):
    """Extrai eventos com timestamps e classificação"""
    eventos = []
    
    for linha in texto.split("\n"):
        match = re.match(r"\[(\d+):(\d+):(\d+)\]", linha)
        if match:
            cats = classificar_assunto(linha)
            if cats:
                eventos.append({
                    "tempo": match.group(1),
                    "categorias": cats,
                    "texto": linha.strip()
                })
    
    return eventos


def gerar_sintese(eventos):
    """Gera síntese automática baseada em categorias"""
    resumo = []
    categorias = {
        c: [] for c in ["FUGA", "VIOLENCIA", "DROGA", "ORDEM", "LOGISTICA", "COMUNICACAO"]
    }

    for ev in eventos:
        for c in ev["categorias"]:
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


def extrair_destaques(eventos):
    """Extrai eventos prioritários"""
    prioridade = ["FUGA", "VIOLENCIA", "DROGA", "ORDEM"]
    destaques = []

    for p in prioridade:
        for ev in eventos:
            if p in ev["categorias"]:
                destaques.append(ev)

    return destaques[:10]


def processar_segmento(caminho_audio, indice, nome_base, pasta_saida):
    """Processa um segmento de áudio individual"""
    
    offset_minutos = indice * 30
    nome_limpo = f"seg_{indice:03d}_clean.mp3"
    caminho_limpo = os.path.join(pasta_saida, nome_limpo)

    print(f"\n📍 Segmento {indice+1}: {nome_base}")
    print(f"   ├─ Limpeza de áudio...")
    
    # LIMPEZA (redução de ruído)
    try:
        subprocess.run([
            "ffmpeg", "-i", caminho_audio,
            "-af", "afftdn=nf=-25",
            "-y",  # sobrescrever sem perguntar
            caminho_limpo
        ], capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erro na limpeza: {e}")
        return None

    print(f"   ├─ Transcrição + diarização...")
    
    # TRANSCRIÇÃO COM DIARIZAÇÃO
    try:
        result = subprocess.run([
            "whisperx", caminho_limpo,
            "--language", "pt",
            "--diarize",
            "--output_format", "txt"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"   ⚠️  WhisperX retornou código {result.returncode}")
    except FileNotFoundError:
        print("   ❌ WhisperX não encontrado. Tentando Whisper simples...")
        try:
            subprocess.run([
                "whisper", caminho_limpo,
                "--language", "pt",
                "--output_format", "txt"
            ], capture_output=True, check=True)
        except FileNotFoundError:
            print("   ❌ Whisper também não encontrado. Instalado?")
            return None

    # LOCALIZAR ARQUIVO DE TRANSCRIÇÃO
    txt_file = caminho_limpo.replace(".mp3", ".txt")
    
    if not os.path.exists(txt_file):
        print(f"   ⚠️  Arquivo de transcrição não encontrado: {txt_file}")
        return None

    print(f"   ├─ Análise de conteúdo...")
    
    # PROCESSAR TRANSCRIÇÃO
    with open(txt_file, encoding="utf-8") as f:
        texto = f.read()

    # Ajustar timestamps para o documento completo
    texto = ajustar_timestamp(texto, offset_minutos)

    # Análise
    eventos = extrair_timeline(texto)
    sintese = gerar_sintese(eventos)
    destaques = extrair_destaques(eventos)

    # GERAR RELATÓRIO
    nome_relatorio = os.path.join(pasta_saida, f"{nome_base}_RELATORIO.txt")

    with open(nome_relatorio, "w", encoding="utf-8") as r:
        r.write("=" * 70 + "\n")
        r.write(f"RELATÓRIO DE ANÁLISE - {nome_base}\n")
        r.write("=" * 70 + "\n\n")

        r.write("📋 TRANSCRIÇÃO\n")
        r.write("-" * 70 + "\n")
        r.write(texto)

        r.write("\n\n" + "=" * 70 + "\n")
        r.write("🎯 SÍNTESE\n")
        r.write("-" * 70 + "\n")
        r.write(sintese)

        r.write("\n\n" + "=" * 70 + "\n")
        r.write("🔴 DESTAQUES CRÍTICOS\n")
        r.write("-" * 70 + "\n")
        
        if destaques:
            for d in destaques:
                cats_str = " | ".join(d["categorias"])
                r.write(f"{d['tempo']} [{cats_str}]\n")
                r.write(f"   {d['texto']}\n\n")
        else:
            r.write("Nenhum destaque crítico identificado.\n")

        r.write("\n" + "=" * 70 + "\n")
        r.write("📊 ESTATÍSTICAS\n")
        r.write("-" * 70 + "\n")
        r.write(f"Total de eventos críticos: {len(eventos)}\n")
        r.write(f"Destaques extraídos: {len(destaques)}\n")

    print(f"   ✅ Relatório gerado: {nome_relatorio}")
    
    return {
        "indice": indice,
        "eventos": eventos,
        "destaques": destaques,
        "arquivo_relatorio": nome_relatorio
    }


# =============================
# MAIN
# =============================

def main():
    if len(sys.argv) < 2:
        print("❌ Uso: python processar_audio.py <caminho_do_audio>")
        print("   Ou arraste o arquivo para processar_audio.bat")
        sys.exit(1)

    arquivo = sys.argv[1]

    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        sys.exit(1)

    # SETUP
    base_nome = os.path.splitext(os.path.basename(arquivo))[0]
    pasta_saida = os.path.join(os.path.dirname(arquivo), base_nome + "_PROCESSADO")
    
    os.makedirs(pasta_saida, exist_ok=True)

    print("\n" + "=" * 70)
    print("🎙️  PIPELINE DE PROCESSAMENTO DE ÁUDIO")
    print("=" * 70)
    print(f"📁 Arquivo: {arquivo}")
    print(f"📂 Saída: {pasta_saida}")
    print("=" * 70)

    # ETAPA 1: CORTE EM SEGMENTOS
    print("\n📁 Etapa 1: Fracionando áudio em segmentos de 30 min...")
    
    temp_dir = os.path.join(pasta_saida, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        subprocess.run([
            "ffmpeg", "-i", arquivo,
            "-f", "segment",
            "-segment_time", "1800",  # 30 min em segundos
            "-c", "copy",
            "-y",
            os.path.join(temp_dir, "seg_%03d.mp3")
        ], capture_output=True, check=True)
        
        print("✅ Áudio fracionado com sucesso")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao fraccionar: {e}")
        sys.exit(1)

    # ETAPA 2: PROCESSAR CADA SEGMENTO
    arquivos = sorted([f for f in os.listdir(temp_dir) if f.startswith("seg_")])
    
    if not arquivos:
        print("❌ Nenhum segmento gerado")
        sys.exit(1)

    print(f"\n🔄 Etapa 2: Processando {len(arquivos)} segmento(s)...\n")

    resultados = []
    
    for i, arq in enumerate(arquivos):
        caminho = os.path.join(temp_dir, arq)
        nome_base = f"DIA01-{i*30:02d}a{i*30+30:02d}"
        
        resultado = processar_segmento(caminho, i, nome_base, pasta_saida)
        
        if resultado:
            resultados.append(resultado)

    # ETAPA 3: CONSOLIDAR RELATÓRIO FINAL
    print("\n\n" + "=" * 70)
    print("📊 Etapa 3: Consolidando relatório final...")
    print("=" * 70)

    total_eventos = sum(len(r["eventos"]) for r in resultados)
    total_destaques = sum(len(r["destaques"]) for r in resultados)

    relatorio_final = os.path.join(pasta_saida, "RELATORIO_FINAL.txt")
    
    with open(relatorio_final, "w", encoding="utf-8") as rf:
        rf.write("=" * 70 + "\n")
        rf.write(f"ANÁLISE CONSOLIDADA - {base_nome}\n")
        rf.write("=" * 70 + "\n\n")

        rf.write("📊 RESUMO EXECUTIVO\n")
        rf.write("-" * 70 + "\n")
        rf.write(f"Total de segmentos processados: {len(resultados)}\n")
        rf.write(f"Duração total: ~{len(resultados)*30} minutos\n")
        rf.write(f"Eventos críticos identificados: {total_eventos}\n")
        rf.write(f"Destaques de alta prioridade: {total_destaques}\n")
        rf.write("\n")

        rf.write("📂 RELATÓRIOS GERADOS\n")
        rf.write("-" * 70 + "\n")
        for r in resultados:
            nome = os.path.basename(r["arquivo_relatorio"])
            rf.write(f"✅ {nome}\n")

        rf.write("\n" + "=" * 70 + "\n")
        rf.write("🎯 DESTAQUES CONSOLIDADOS\n")
        rf.write("-" * 70 + "\n")
        
        todos_destaques = []
        for r in resultados:
            todos_destaques.extend(r["destaques"])

        for d in todos_destaques[:20]:  # Top 20
            cats_str = " | ".join(d["categorias"])
            rf.write(f"{d['tempo']} [{cats_str}]\n")
            rf.write(f"   {d['texto']}\n\n")

    print(f"\n✅ Relatório final gerado: {relatorio_final}")
    
    # LIMPEZA
    print("\n🧹 Limpando arquivos temporários...")
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print("\n" + "=" * 70)
    print("✅ PROCESSAMENTO CONCLUÍDO")
    print("=" * 70)
    print(f"\n📁 Acesse os resultados em:")
    print(f"   {pasta_saida}\n")


if __name__ == "__main__":
    main()
