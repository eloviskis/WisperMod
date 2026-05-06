import React, { useState, useEffect, useRef } from 'react';
import { Upload, AlertCircle, CheckCircle, Loader, Download, BarChart3, Zap } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const WS_BASE  = (import.meta.env.VITE_WS_URL ?? API_BASE)
  .replace(/^https/, 'wss').replace(/^http/, 'ws');

export default function AudioIntelligence() {
  const [file, setFile] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef(null);
  const wsRef = useRef(null);

  // Upload
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const audioFile = files[0];
      if (audioFile.type.startsWith('audio/')) {
        setFile(audioFile);
      } else {
        alert('Por favor, selecione um arquivo de áudio');
      }
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleFileSelect = (e) => {
    if (e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      setUploadProgress(50);
      
      const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      setJobId(data.job_id);
      setUploadProgress(100);
      setStatus(null);
      
      // Conectar WebSocket
      connectWebSocket(data.job_id);
    } catch (error) {
      console.error('Erro no upload:', error);
      setUploadProgress(0);
    }
  };

  const connectWebSocket = (id) => {
    const ws = new WebSocket(`${WS_BASE}/ws/${id}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;
  };

  const handleDownload = async () => {
    if (!jobId) return;

    try {
      const response = await fetch(`${API_BASE}/download/${jobId}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `resultados_${jobId.substring(0, 8)}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Erro no download:', error);
    }
  };

  const reset = () => {
    setFile(null);
    setJobId(null);
    setStatus(null);
    setUploadProgress(0);
    if (wsRef.current) {
      wsRef.current.close();
    }
  };

  // Interface
  if (!jobId) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4 font-mono">
        <style>{`
          @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&family=Space+Mono:wght@400;700&display=swap');
          
          body {
            background-color: rgb(3, 7, 18);
            color: rgb(226, 232, 240);
            font-family: 'Courier Prime', monospace;
          }
          
          .terminal-border {
            border: 2px solid rgb(100, 116, 139);
            position: relative;
          }
          
          .terminal-header {
            background: linear-gradient(90deg, rgb(30, 41, 59), rgb(51, 65, 85));
            border-bottom: 2px solid rgb(100, 116, 139);
            padding: 12px 16px;
            display: flex;
            gap: 8px;
            align-items: center;
          }
          
          .terminal-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
          }
          
          .dot-red { background-color: rgb(248, 113, 113); }
          .dot-yellow { background-color: rgb(251, 191, 36); }
          .dot-green { background-color: rgb(74, 222, 128); }
          
          .upload-area {
            padding: 48px 32px;
            border: 2px dashed rgb(100, 116, 139);
            border-radius: 0;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
          }
          
          .upload-area:hover {
            border-color: rgb(148, 163, 184);
            background-color: rgba(15, 23, 42, 0.5);
          }
          
          .upload-area.dragging {
            border-color: rgb(34, 197, 94);
            background-color: rgba(34, 197, 94, 0.1);
          }
          
          .btn-primary {
            background-color: rgb(34, 197, 94);
            color: rgb(3, 7, 18);
            border: none;
            padding: 12px 24px;
            font-family: 'Space Mono', monospace;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
            letter-spacing: 0.05em;
          }
          
          .btn-primary:hover {
            background-color: rgb(22, 163, 74);
            transform: translateY(-2px);
          }
          
          .btn-primary:disabled {
            background-color: rgb(100, 116, 139);
            cursor: not-allowed;
            transform: none;
          }
          
          .file-name {
            background-color: rgba(30, 41, 59, 0.8);
            padding: 12px 16px;
            border-left: 3px solid rgb(34, 197, 94);
            margin: 16px 0;
            font-size: 0.9em;
          }
          
          .code-block {
            background-color: rgba(3, 7, 18, 0.8);
            padding: 16px;
            border-left: 3px solid rgb(100, 116, 139);
            margin: 16px 0;
            font-size: 0.85em;
            line-height: 1.6;
          }
          
          .terminal-text {
            color: rgb(34, 197, 94);
            font-weight: 700;
          }
          
          .highlight {
            color: rgb(96, 165, 250);
          }
          
          input[type="file"] {
            display: none;
          }
        `}</style>

        <div className="w-full max-w-2xl">
          {/* Header */}
          <div className="terminal-border mb-6">
            <div className="terminal-header">
              <div className="terminal-dot dot-red"></div>
              <div className="terminal-dot dot-yellow"></div>
              <div className="terminal-dot dot-green"></div>
              <span className="ml-4 text-sm">audio-intelligence / processar</span>
            </div>
            
            <div className="p-8 bg-slate-950">
              <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
                <Zap size={32} className="text-green-500" />
                <span><span className="terminal-text">AUDIO</span> Intelligence</span>
              </h1>
              <p className="text-slate-400 text-sm">Pipeline de processamento com transcrição + análise</p>
            </div>
          </div>

          {/* Upload Area */}
          <div 
            className={`terminal-border ${isDragging ? 'dragging' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="upload-area">
              <Upload size={48} className="mx-auto mb-4 text-slate-400" />
              <p className="text-lg mb-2">
                {file ? '✓ Arquivo selecionado' : 'Arraste seu áudio aqui'}
              </p>
              <p className="text-slate-500 text-sm mb-4">
                ou <span className="terminal-text cursor-pointer">clique para selecionar</span>
              </p>
              <p className="text-xs text-slate-600">
                Formatos: MP3, WAV, M4A, AAC, FLAC
              </p>
            </div>

            {file && (
              <div className="file-name">
                📁 {file.name} • {(file.size / 1024 / 1024).toFixed(2)} MB
              </div>
            )}
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*"
            onChange={handleFileSelect}
          />

          {/* Info */}
          <div className="code-block mt-6">
            <div className="terminal-text mb-3">$ processador --info</div>
            <div className="space-y-2 text-xs text-slate-400">
              <div>▸ Fracionamento: 30 min / segmento</div>
              <div>▸ Limpeza: Redução de ruído FFmpeg</div>
              <div>▸ Transcrição: OpenAI Whisper + diarização</div>
              <div>▸ Análise: 6 categorias críticas</div>
              <div>▸ Saída: Relatórios estruturados + dados</div>
            </div>
          </div>

          {/* Button */}
          <div className="mt-8 flex gap-4">
            <button
              onClick={handleUpload}
              disabled={!file}
              className="btn-primary flex-1 flex items-center justify-center gap-2"
            >
              <Upload size={18} />
              Processar Áudio
            </button>
          </div>

          {/* Footer */}
          <div className="mt-8 pt-6 border-t border-slate-800 text-xs text-slate-600">
            <div className="flex justify-between">
              <span>v1.0</span>
              <span>Intel Pipeline System</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Processing
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4 font-mono">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&family=Space+Mono:wght@400;700&display=swap');
        
        .progress-bar {
          background-color: rgb(30, 41, 59);
          border: 1px solid rgb(100, 116, 139);
          height: 24px;
          overflow: hidden;
          position: relative;
        }
        
        .progress-fill {
          background: linear-gradient(90deg, rgb(34, 197, 94), rgb(74, 222, 128));
          height: 100%;
          transition: width 0.3s ease;
          display: flex;
          align-items: center;
          justify-content: flex-end;
          padding-right: 8px;
        }
        
        .status-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          background-color: rgba(30, 41, 59, 0.5);
          border-left: 3px solid rgb(100, 116, 139);
          margin: 8px 0;
        }
        
        .status-item.active {
          border-left-color: rgb(34, 197, 94);
          background-color: rgba(34, 197, 94, 0.1);
        }
        
        .status-item.complete {
          border-left-color: rgb(34, 197, 94);
        }
        
        .status-item.error {
          border-left-color: rgb(248, 113, 113);
        }
        
        .spinner {
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        .result-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
          gap: 12px;
          margin: 16px 0;
        }
        
        .result-card {
          background: rgba(30, 41, 59, 0.6);
          border: 1px solid rgb(100, 116, 139);
          padding: 16px;
          text-align: center;
        }
        
        .result-card-value {
          font-size: 1.5em;
          font-weight: 700;
          color: rgb(34, 197, 94);
          margin: 8px 0;
        }
        
        .result-card-label {
          font-size: 0.8em;
          color: rgb(148, 163, 184);
        }
        
        .btn-secondary {
          background-color: rgb(100, 116, 139);
          color: rgb(226, 232, 240);
          border: none;
          padding: 12px 24px;
          font-family: 'Space Mono', monospace;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .btn-secondary:hover {
          background-color: rgb(148, 163, 184);
          transform: translateY(-2px);
        }
      `}</style>

      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="terminal-border mb-6">
          <div className="terminal-header">
            <div className="terminal-dot dot-red"></div>
            <div className="terminal-dot dot-yellow"></div>
            <div className="terminal-dot dot-green"></div>
            <span className="ml-4 text-sm">audio-intelligence / processando...</span>
          </div>
          
          <div className="p-8 bg-slate-950 border-b border-slate-800">
            <div className="flex items-center gap-3 mb-4">
              {status?.status === 'concluido' ? (
                <CheckCircle size={32} className="text-green-500" />
              ) : status?.status === 'erro' ? (
                <AlertCircle size={32} className="text-red-500" />
              ) : (
                <Loader size={32} className="text-blue-400 spinner" />
              )}
              <div>
                <h2 className="text-xl font-bold">
                  {status?.status === 'concluido' ? '✓ Concluído' : 
                   status?.status === 'erro' ? '✗ Erro' : 
                   'Processando...'}
                </h2>
                <p className="text-slate-400 text-sm">{status?.mensagem}</p>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="mt-4">
              <div className="flex justify-between mb-2 text-xs text-slate-400">
                <span>Progresso</span>
                <span>{status?.progresso || 0}%</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill"
                  style={{ width: `${status?.progresso || 0}%` }}
                >
                  {status?.progresso > 20 && (
                    <span className="text-xs font-bold">{status?.progresso}%</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Status Items */}
        <div className="terminal-border mb-6">
          <div className="p-8 bg-slate-950">
            <div className={`status-item ${status?.status === 'iniciado' ? 'active' : 'complete'}`}>
              {status?.status !== 'iniciado' ? (
                <CheckCircle size={20} className="text-green-500" />
              ) : (
                <Loader size={20} className="text-blue-400 spinner" />
              )}
              <div className="flex-1">
                <div className="font-bold">Upload e inicialização</div>
                <div className="text-xs text-slate-500">{status?.arquivo}</div>
              </div>
            </div>

            <div className={`status-item ${status?.status === 'processando' ? 'active' : status?.status !== 'erro' ? 'complete' : ''}`}>
              {status?.status === 'processando' ? (
                <Loader size={20} className="text-blue-400 spinner" />
              ) : (
                <CheckCircle size={20} className="text-green-500" />
              )}
              <span className="flex-1">Fracionamento e processamento</span>
            </div>

            <div className={`status-item ${status?.status === 'concluido' ? 'complete' : status?.status === 'erro' ? 'error' : ''}`}>
              {status?.status === 'concluido' ? (
                <CheckCircle size={20} className="text-green-500" />
              ) : status?.status === 'erro' ? (
                <AlertCircle size={20} className="text-red-500" />
              ) : (
                <div className="w-5 h-5"></div>
              )}
              <span className="flex-1">Análise e geração de relatórios</span>
            </div>

            {/* Results */}
            {status?.status === 'concluido' && status?.resultados && (
              <div className="mt-6">
                <div className="text-sm font-bold text-green-500 mb-4">Resultados da Análise</div>
                <div className="result-grid">
                  <div className="result-card">
                    <BarChart3 size={24} className="mx-auto text-blue-400" />
                    <div className="result-card-value">{status.resultados.segmentos?.length || 0}</div>
                    <div className="result-card-label">Segmentos</div>
                  </div>
                  <div className="result-card">
                    <AlertCircle size={24} className="mx-auto text-red-400" />
                    <div className="result-card-value">{status.resultados.total_eventos || 0}</div>
                    <div className="result-card-label">Eventos</div>
                  </div>
                  <div className="result-card">
                    <Zap size={24} className="mx-auto text-yellow-400" />
                    <div className="result-card-value">{status.resultados.total_destaques || 0}</div>
                    <div className="result-card-label">Destaques</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-4">
          {status?.status === 'concluido' && (
            <button
              onClick={handleDownload}
              className="btn-primary flex-1 flex items-center justify-center gap-2"
            >
              <Download size={18} />
              Download dos Resultados
            </button>
          )}
          <button
            onClick={reset}
            className="btn-secondary flex-1 flex items-center justify-center gap-2"
          >
            {status?.status === 'concluido' ? '↻ Novo Processamento' : 'Cancelar'}
          </button>
        </div>
      </div>
    </div>
  );
}
