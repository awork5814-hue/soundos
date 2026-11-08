# SoundOS

A lightweight, local, offline voice-to-terminal desktop assistant built for Linux.

## Features
- **Speech-to-Text**: Offline speech recognition via `faster-whisper` (`tiny.en`).
- **Command Synthesis**: Natural language to bash command generation using `qwen2.5-coder:1.5b` running locally via Ollama.
- **Safety First**: Interactive GUI built with Tkinter allowing manual editing of transcriptions and generated bash commands before execution.
- **Rule Fallback**: Instant regex-based execution for standard filesystem operations.

## Prerequisites
1. **Ollama**:
   ```bash
   ollama pull qwen2.5-coder:1.5b
