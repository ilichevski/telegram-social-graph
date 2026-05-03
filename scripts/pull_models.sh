#!/usr/bin/env bash
set -euo pipefail

MODEL="${OLLAMA_MODEL:-qwen3:8b}"
EMBED_MODEL="${OLLAMA_EMBED_MODEL:-embeddinggemma}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "error: ollama is not installed."
  echo "Install it first from https://ollama.com/ or with Homebrew:"
  echo "  brew install --cask ollama"
  exit 1
fi

echo "Pulling local models..."
ollama pull "$MODEL"
ollama pull "$EMBED_MODEL"

echo
echo "Models are ready:"
echo "  LLM:        $MODEL"
echo "  embeddings: $EMBED_MODEL"
