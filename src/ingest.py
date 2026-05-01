from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

from search import get_embeddings

load_dotenv()

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def _resolve_pdf_path() -> Path:
    raw = os.getenv("PDF_PATH", "document.pdf")
    pdf = Path(raw)
    if not pdf.is_absolute():
        project_root = Path(__file__).resolve().parent.parent
        pdf = (project_root / pdf).resolve()
    if not pdf.exists():
        raise FileNotFoundError(
            f"PDF nao encontrado: {pdf}. "
            f"Defina PDF_PATH no .env ou coloque document.pdf na raiz."
        )
    return pdf


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Variavel de ambiente obrigatoria ausente: {name}."
        )
    return value


def main() -> int:
    try:
        pdf_path = _resolve_pdf_path()
    except FileNotFoundError as exc:
        print(f"[ingest] ERRO: {exc}", file=sys.stderr)
        return 2

    connection = _require_env("DATABASE_URL")
    collection = os.getenv("PG_VECTOR_COLLECTION_NAME", "documents")

    print(f"[ingest] Carregando PDF: {pdf_path}")
    try:
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
    except Exception as exc:
        print(f"[ingest] ERRO ao ler PDF: {exc}", file=sys.stderr)
        return 3
    print(f"[ingest] Paginas carregadas: {len(pages)}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(pages)
    print(f"[ingest] Chunks gerados: {len(chunks)} "
          f"(size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")

    if not chunks:
        print(
            "[ingest] ERRO: nenhum chunk gerado. "
            "O PDF pode estar vazio ou ser apenas imagem (scanned).",
            file=sys.stderr,
        )
        return 4

    try:
        embeddings = get_embeddings()
    except Exception as exc:
        print(f"[ingest] ERRO ao inicializar embeddings: {exc}",
              file=sys.stderr)
        return 5

    print(f"[ingest] Conectando ao Postgres e (re)criando "
          f"collection '{collection}'...")
    try:
        store = PGVector(
            embeddings=embeddings,
            collection_name=collection,
            connection=connection,
            use_jsonb=True,
            pre_delete_collection=True,
        )
    except Exception as exc:
        print(
            "[ingest] ERRO ao conectar no Postgres. "
            "Verifique DATABASE_URL e se o container esta ativo "
            f"(docker compose up -d). Detalhe: {exc}",
            file=sys.stderr,
        )
        return 6

    print(f"[ingest] Gerando embeddings e persistindo {len(chunks)} chunks...")
    try:
        store.add_documents(chunks)
    except Exception as exc:
        print(f"[ingest] ERRO ao persistir embeddings: {exc}",
              file=sys.stderr)
        return 7

    print(f"[ingest] OK. {len(chunks)} chunks ingeridos na "
          f"collection '{collection}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
