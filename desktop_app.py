"""
WisperMod — Desktop Application
Interface CustomTkinter para processamento local de áudio.
"""

import os
import sys
import threading
import queue
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

# ─── tema ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

ACCENT      = "#00ff88"
BG_DARK     = "#0a0a0a"
BG_PANEL    = "#111111"
BG_CARD     = "#1a1a1a"
TEXT_DIM    = "#666666"
TEXT_BRIGHT = "#e0e0e0"

CATEGORIAS = ["FUGA", "DROGA", "ORDEM", "VIOLENCIA", "LOGISTICA", "COMUNICACAO"]
CAT_COLORS = {
    "FUGA":        "#ff3333",
    "DROGA":       "#ff6600",
    "ORDEM":       "#ffcc00",
    "VIOLENCIA":   "#ff0066",
    "LOGISTICA":   "#3399ff",
    "COMUNICACAO": "#33cc99",
}


# ─── janela principal ─────────────────────────────────────────────────────────

class WisperModApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WisperMod — Análise de Áudio")
        self.geometry("980x720")
        self.minsize(820, 600)
        self.configure(fg_color=BG_DARK)

        self._arquivo: str | None = None
        self._pasta_resultados: str | None = None
        self._processando = False
        self._queue: queue.Queue = queue.Queue()

        self._build_ui()
        self._poll_queue()

    # ─── construção da interface ─────────────────────────────────────────────

    def _build_ui(self):
        # ── cabeçalho ────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="● WISPERMOD",
            font=ctk.CTkFont(family="Courier", size=20, weight="bold"),
            text_color=ACCENT,
        ).pack(side="left", padx=20)

        ctk.CTkLabel(
            header,
            text="Inteligência de Áudio  v1.0",
            font=ctk.CTkFont(family="Courier", size=11),
            text_color=TEXT_DIM,
        ).pack(side="left")

        # ── corpo ─────────────────────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        self._build_left(body)
        self._build_right(body)

    def _build_left(self, parent):
        left = ctk.CTkFrame(parent, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(2, weight=1)
        left.columnconfigure(0, weight=1)

        # ── zona de drop / seleção ────────────────────────────────────────────
        self._drop_frame = ctk.CTkFrame(
            left, fg_color=BG_CARD, corner_radius=10,
            border_width=2, border_color="#2a2a2a",
            cursor="hand2",
        )
        self._drop_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._drop_frame.bind("<Button-1>", lambda _e: self._selecionar_arquivo())

        for widget_cls, kwargs, pack_kw in [
            (ctk.CTkLabel, dict(
                text="⬆",
                font=ctk.CTkFont(size=38),
                text_color=TEXT_DIM,
            ), dict(pady=(18, 4))),
            (ctk.CTkLabel, dict(
                text="Clique para selecionar arquivo de áudio",
                font=ctk.CTkFont(family="Courier", size=13),
                text_color=TEXT_DIM,
            ), dict(pady=(0, 4))),
        ]:
            w = widget_cls(self._drop_frame, **kwargs)
            w.pack(**pack_kw)
            w.bind("<Button-1>", lambda _e: self._selecionar_arquivo())

        self._drop_icon  = self._drop_frame.winfo_children()[0]   # ⬆ label
        self._drop_hint  = self._drop_frame.winfo_children()[1]   # texto label

        self._file_label = ctk.CTkLabel(
            self._drop_frame,
            text="MP3 · WAV · M4A · AAC · FLAC · OGG",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color="#444444",
        )
        self._file_label.pack(pady=(0, 16))
        self._file_label.bind("<Button-1>", lambda _e: self._selecionar_arquivo())

        # ── botões ────────────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(left, fg_color="transparent")
        btn_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        self._btn_processar = ctk.CTkButton(
            btn_row,
            text="▶  PROCESSAR",
            font=ctk.CTkFont(family="Courier", size=12, weight="bold"),
            fg_color=ACCENT, text_color="#000000",
            hover_color="#00cc66", corner_radius=6,
            state="disabled",
            command=self._iniciar_processamento,
        )
        self._btn_processar.pack(side="left", padx=(0, 8))

        self._btn_abrir = ctk.CTkButton(
            btn_row,
            text="📂  ABRIR PASTA",
            font=ctk.CTkFont(family="Courier", size=12),
            fg_color="#222222", text_color=TEXT_DIM,
            hover_color="#333333", corner_radius=6,
            state="disabled",
            command=self._abrir_pasta_resultados,
        )
        self._btn_abrir.pack(side="left")

        # ── progresso + log ───────────────────────────────────────────────────
        prog = ctk.CTkFrame(left, fg_color=BG_CARD, corner_radius=10)
        prog.grid(row=2, column=0, sticky="nsew")
        prog.rowconfigure(3, weight=1)
        prog.columnconfigure(0, weight=1)

        self._status_label = ctk.CTkLabel(
            prog,
            text="Aguardando arquivo...",
            font=ctk.CTkFont(family="Courier", size=11),
            text_color=TEXT_DIM, anchor="w",
        )
        self._status_label.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))

        self._progress = ctk.CTkProgressBar(prog, height=10, corner_radius=5)
        self._progress.set(0)
        self._progress.configure(progress_color=ACCENT, fg_color="#222222")
        self._progress.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        ctk.CTkLabel(
            prog,
            text="LOG",
            font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
            text_color=TEXT_DIM, anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=14)

        self._log_box = ctk.CTkTextbox(
            prog,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color="#0d0d0d", text_color="#888888",
            corner_radius=6, wrap="word",
            state="disabled",
        )
        self._log_box.grid(row=3, column=0, sticky="nsew", padx=14, pady=(4, 14))

    def _build_right(self, parent):
        right = ctk.CTkFrame(parent, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=0)
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            right,
            text="CATEGORIAS DETECTADAS",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=TEXT_DIM, anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 6))

        # grade de categorias (2 colunas × 3 linhas)
        grid = ctk.CTkFrame(right, fg_color="transparent")
        grid.grid(row=1, column=0, sticky="ew")
        grid.columnconfigure((0, 1), weight=1)

        self._cat_counts: dict[str, ctk.CTkLabel] = {}

        for idx, cat in enumerate(CATEGORIAS):
            row_i, col_i = divmod(idx, 2)
            color = CAT_COLORS[cat]

            card = ctk.CTkFrame(grid, fg_color=BG_CARD, corner_radius=8, height=82)
            card.grid(row=row_i, column=col_i, padx=4, pady=4, sticky="nsew")
            card.pack_propagate(False)

            ctk.CTkLabel(
                card,
                text=cat,
                font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                text_color=color,
            ).pack(pady=(12, 2))

            cnt = ctk.CTkLabel(
                card,
                text="0",
                font=ctk.CTkFont(family="Courier", size=26, weight="bold"),
                text_color=TEXT_DIM,
            )
            cnt.pack()
            self._cat_counts[cat] = cnt

        # caixa de síntese
        self._resumo_box = ctk.CTkTextbox(
            right,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=BG_CARD, text_color="#aaaaaa",
            corner_radius=8, wrap="word",
            state="disabled",
        )
        self._resumo_box.grid(row=2, column=0, sticky="nsew", pady=(12, 0))
        self._resumo_set("Síntese aparecerá aqui após o processamento.")

    # ─── lógica ───────────────────────────────────────────────────────────────

    def _selecionar_arquivo(self):
        if self._processando:
            return
        path = filedialog.askopenfilename(
            title="Selecionar arquivo de áudio",
            filetypes=[
                ("Arquivos de Áudio", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.wma *.opus"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if path:
            self._arquivo = path
            self._drop_icon.configure(text="✔", text_color=ACCENT)
            self._drop_hint.configure(text="Arquivo selecionado:")
            self._file_label.configure(text=Path(path).name, text_color=ACCENT)
            self._drop_frame.configure(border_color=ACCENT)
            self._btn_processar.configure(state="normal")
            self._log(f"Arquivo: {path}")

    def _iniciar_processamento(self):
        if not self._arquivo or self._processando:
            return
        self._processando = True
        self._pasta_resultados = None
        self._btn_processar.configure(state="disabled", text="PROCESSANDO...")
        self._btn_abrir.configure(state="disabled")
        self._progress.set(0)
        self._status_label.configure(text="Iniciando...", text_color=ACCENT)

        for cat in CATEGORIAS:
            self._cat_counts[cat].configure(text="0", text_color=TEXT_DIM)
        self._resumo_set("Processando...")

        threading.Thread(
            target=self._pipeline_thread,
            args=(self._arquivo,),
            daemon=True,
        ).start()

    def _pipeline_thread(self, arquivo: str):
        from core.processador import processar_audio

        def on_progress(pct: int, msg: str):
            self._queue.put(("progress", pct, msg))

        try:
            resultado = processar_audio(arquivo, progress_callback=on_progress)
            self._queue.put(("done", resultado))
        except Exception as exc:
            self._queue.put(("error", str(exc)))

    def _poll_queue(self):
        try:
            while True:
                item = self._queue.get_nowait()
                kind = item[0]
                if kind == "progress":
                    _, pct, msg = item
                    self._progress.set(pct / 100)
                    self._status_label.configure(text=msg, text_color=ACCENT)
                    self._log(f"[{pct:3d}%] {msg}")
                elif kind == "done":
                    self._on_done(item[1])
                elif kind == "error":
                    self._on_error(item[1])
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)

    def _on_done(self, resultado: dict):
        self._processando = False
        self._pasta_resultados = resultado["pasta_saida"]
        self._progress.set(1.0)
        self._status_label.configure(text="Concluído!", text_color=ACCENT)
        self._btn_processar.configure(state="normal", text="▶  PROCESSAR")
        self._btn_abrir.configure(
            state="normal",
            fg_color="#1a3322",
            text_color=ACCENT,
        )

        for cat, cnt in resultado["contagem_por_cat"].items():
            if cat in self._cat_counts:
                cor = CAT_COLORS.get(cat, TEXT_DIM) if cnt > 0 else TEXT_DIM
                self._cat_counts[cat].configure(text=str(cnt), text_color=cor)

        linhas = [
            f"Segmentos    : {len(resultado['segmentos'])}",
            f"Eventos      : {resultado['total_eventos']}",
            f"Destaques    : {resultado['total_destaques']}",
            "",
            f"Pasta: {resultado['pasta_saida']}",
        ]
        self._resumo_set("\n".join(linhas))
        self._log(f"Resultados em: {resultado['pasta_saida']}")

    def _on_error(self, msg: str):
        self._processando = False
        self._progress.set(0)
        self._status_label.configure(text="Erro no processamento", text_color="#ff4444")
        self._btn_processar.configure(state="normal", text="▶  PROCESSAR")
        self._log(f"ERRO: {msg}")
        messagebox.showerror("WisperMod — Erro", msg)

    def _abrir_pasta_resultados(self):
        if self._pasta_resultados and os.path.isdir(self._pasta_resultados):
            if sys.platform == "win32":
                os.startfile(self._pasta_resultados)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.run(["open", self._pasta_resultados])
            else:
                import subprocess
                subprocess.run(["xdg-open", self._pasta_resultados])

    def _log(self, msg: str):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", f"> {msg}\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _resumo_set(self, text: str):
        self._resumo_box.configure(state="normal")
        self._resumo_box.delete("1.0", "end")
        self._resumo_box.insert("1.0", text)
        self._resumo_box.configure(state="disabled")


# ─── entry point ──────────────────────────────────────────────────────────────

def main():
    app = WisperModApp()
    app.mainloop()


if __name__ == "__main__":
    main()
