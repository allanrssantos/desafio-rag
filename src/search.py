from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Tuple

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import PromptTemplate
from langchain_postgres import PGVector

load_dotenv()


PROMPT_TEMPLATE = """CONTEXTO:
{contexto}

REGRAS:
- Responda somente com base no CONTEXTO.
- Se a informação não estiver explicitamente no CONTEXTO, responda:
  "Não tenho informações necessárias para responder sua pergunta."
- Nunca invente ou use conhecimento externo.
- Nunca produza opiniões ou interpretações além do que está escrito.

EXEMPLOS DE PERGUNTAS FORA DO CONTEXTO:
Pergunta: "Qual é a capital da França?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."
Pergunta: "Quantos clientes temos em 2024?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."
Pergunta: "Você acha isso bom ou ruim?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

PERGUNTA DO USUÁRIO:
{pergunta}

RESPONDA A "PERGUNTA DO USUÁRIO\""""


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Variavel de ambiente obrigatoria ausente: {name}. "
            f"Configure-a no arquivo .env."
        )
    return value


def _provider() -> str:
    provider = (os.getenv("LLM_PROVIDER") or "openai").strip().lower()
    if provider not in {"openai", "gemini"}:
        raise ValueError(
            "LLM_PROVIDER invalido. Use 'openai' ou 'gemini'."
        )
    return provider


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    provider = _provider()
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        _require_env("OPENAI_API_KEY")
        model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        return OpenAIEmbeddings(model=model)

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    _require_env("GOOGLE_API_KEY")
    model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/embedding-001")
    return GoogleGenerativeAIEmbeddings(model=model)


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    provider = _provider()
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        _require_env("OPENAI_API_KEY")
        model = os.getenv("OPENAI_LLM_MODEL", "gpt-5-nano")
        return ChatOpenAI(model=model, temperature=0)

    from langchain_google_genai import ChatGoogleGenerativeAI

    _require_env("GOOGLE_API_KEY")
    model = os.getenv("GEMINI_LLM_MODEL", "gemini-2.5-flash-lite")
    return ChatGoogleGenerativeAI(model=model, temperature=0)


@lru_cache(maxsize=1)
def get_vector_store() -> PGVector:
    connection = _require_env("DATABASE_URL")
    collection = os.getenv("PG_VECTOR_COLLECTION_NAME", "documents")
    try:
        return PGVector(
            embeddings=get_embeddings(),
            collection_name=collection,
            connection=connection,
            use_jsonb=True,
        )
    except Exception as exc:
        raise RuntimeError(
            "Falha ao conectar ao Postgres/pgVector. "
            "Verifique DATABASE_URL e se o container esta ativo "
            "(docker compose up -d). Detalhe: "
            f"{exc}"
        ) from exc


def search_context(
    question: str, k: int = 10
) -> List[Tuple[Document, float]]:
    store = get_vector_store()
    return store.similarity_search_with_score(question, k=k)


def build_prompt(
    context: str | List[Tuple[Document, float]], question: str
) -> str:
    if isinstance(context, str):
        contexto = context
    else:
        contexto = "\n\n".join(doc.page_content for doc, _ in context)

    template = PromptTemplate.from_template(PROMPT_TEMPLATE)
    return template.format(contexto=contexto, pergunta=question)


def ask(question: str) -> str:
    if not question or not question.strip():
        return "Não tenho informações necessárias para responder sua pergunta."

    results = search_context(question, k=10)
    prompt = build_prompt(results, question)
    response = get_llm().invoke(prompt)
    content = getattr(response, "content", response)
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content).strip()
