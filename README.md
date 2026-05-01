# RAG com LangChain + PostgreSQL + pgVector

Sistema Python que ingere um arquivo PDF, divide seu conteúdo em chunks, gera embeddings e os persiste no PostgreSQL com a extensão pgVector. Uma CLI interativa permite fazer perguntas em linguagem natural; o sistema busca os trechos mais relevantes por similaridade vetorial e utiliza um LLM (OpenAI ou Gemini) para gerar respostas baseadas exclusivamente no conteúdo do documento. Se a informação não estiver no PDF, o sistema responde com uma frase de fallback determinística, sem alucinações.

Para detalhes de requisitos e decisões de arquitetura, consulte [`docs/SPEC.md`](SPEC.md) e [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Stack

- Python 3.11+
- LangChain (`langchain`, `langchain-openai`, `langchain-google-genai`, `langchain-community`, `langchain-postgres`, `langchain-text-splitters`)
- PostgreSQL 16 + pgVector (`pgvector/pgvector:pg16`)
- Docker e Docker Compose
- Provedores de LLM/Embeddings: OpenAI (`text-embedding-3-small` / `gpt-5-nano`) ou Google Gemini (`models/embedding-001` / `gemini-2.5-flash-lite`)

---

## Pre-requisitos

- Python 3.11 ou superior
- Docker Desktop em execucao (ou Docker Engine + Docker Compose plugin)
- Chave de API valida da OpenAI **ou** do Google Gemini (ao menos uma)
- Git

---

## Instalacao

### 1. Clonar o repositorio

```bash
git clone <URL-DO-REPOSITORIO>
cd <NOME-DA-PASTA>
```

### 2. Criar e ativar o ambiente virtual

**Linux / macOS**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell)**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

> Se o PowerShell bloquear a execucao de scripts, execute primeiro:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 3. Instalar as dependencias

```bash
pip install -r requirements.txt
```

---

## Configuracao

### 1. Criar o arquivo `.env`

**Linux / macOS**
```bash
cp .env.example .env
```

**Windows (PowerShell)**
```powershell
Copy-Item .env.example .env
```

### 2. Editar o `.env`

Abra o arquivo `.env` em qualquer editor de texto e preencha os valores:

```dotenv
# Escolha o provider: openai | gemini
LLM_PROVIDER=openai

# Preencha somente as variaveis do provider escolhido
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
```

As demais variaveis ja possuem valores padrao adequados para uso local e nao precisam ser alteradas, a menos que voce queira customizar modelos ou o nome da collection.

### 3. Colocar o PDF na raiz do projeto

Copie o arquivo que deseja consultar para a raiz do projeto com o nome `document.pdf`:

```
<raiz-do-projeto>/document.pdf
```

Caso queira usar outro caminho, ajuste a variavel `PDF_PATH` no `.env`.

> O PDF deve conter texto extraivel (nao pode ser um documento escaneado sem OCR).

---

## Execucao

Execute os passos na ordem abaixo.

### Passo 1 — Subir o banco de dados

```bash
docker compose up -d
```

Aguarde o container `rag_postgres` ficar saudavel. Voce pode verificar com:

```bash
docker compose ps
```

### Passo 2 — Ingerir o PDF

```bash
python src/ingest.py
```

Saida esperada (exemplo):

```
[ingest] Carregando PDF: /caminho/para/document.pdf
[ingest] Paginas carregadas: 5
[ingest] Chunks gerados: 42 (size=1000, overlap=150)
[ingest] Conectando ao Postgres e (re)criando collection 'documents'...
[ingest] Gerando embeddings e persistindo 42 chunks...
[ingest] OK. 42 chunks ingeridos na collection 'documents'.
```

> Re-executar `ingest.py` e seguro: a collection e recriada do zero a cada execucao.

### Passo 3 — Iniciar o chat

```bash
python src/chat.py
```

---

## Como usar

Apos iniciar `chat.py`, o prompt `PERGUNTA:` aparece no terminal. Digite sua pergunta e pressione Enter.

**Pergunta dentro do conteudo do PDF:**
```
Faca sua pergunta (digite 'sair' ou Ctrl+C para encerrar).
PERGUNTA: Qual o faturamento da Empresa SuperTechIABrazil?
RESPOSTA: O faturamento foi de 10 milhoes de reais.
```

**Pergunta fora do conteudo do PDF:**
```
PERGUNTA: Qual e a capital da Franca?
RESPOSTA: Nao tenho informacoes necessarias para responder sua pergunta.
```

**Encerrar a sessao:**
```
PERGUNTA: sair
Encerrando.
```

Voce tambem pode usar `exit`, `quit` ou pressionar `Ctrl+C`.

---

## Estrutura do projeto

```
.
├── docker-compose.yml        # Servico PostgreSQL + pgVector
├── requirements.txt          # Dependencias Python com versoes pinadas
├── .env.example              # Modelo de variaveis de ambiente
├── document.pdf              # PDF a ser consultado (fornecido pelo usuario)
├── src/
│   ├── ingest.py             # Carrega, divide e persiste o PDF no PGVector
│   ├── search.py             # Factories, busca vetorial, prompt e funcao ask()
│   └── chat.py               # CLI interativa (REPL)
└── README.md                 # Instruções de execução
```

---

## Variaveis de ambiente

| Variavel                    | Descricao                                                      | Obrigatoria?                        |
|-----------------------------|----------------------------------------------------------------|-------------------------------------|
| `LLM_PROVIDER`              | Provider a usar: `openai` ou `gemini`. Padrao: `openai`        | Nao (usa `openai` por padrao)       |
| `OPENAI_API_KEY`            | Chave de API da OpenAI                                         | Sim, se `LLM_PROVIDER=openai`       |
| `OPENAI_EMBEDDING_MODEL`    | Modelo de embeddings OpenAI. Padrao: `text-embedding-3-small`  | Nao                                 |
| `OPENAI_LLM_MODEL`          | Modelo de chat OpenAI. Padrao: `gpt-5-nano`                    | Nao                                 |
| `GOOGLE_API_KEY`            | Chave de API do Google Gemini                                  | Sim, se `LLM_PROVIDER=gemini`       |
| `GEMINI_EMBEDDING_MODEL`    | Modelo de embeddings Gemini. Padrao: `models/embedding-001`    | Nao                                 |
| `GEMINI_LLM_MODEL`          | Modelo de chat Gemini. Padrao: `gemini-2.5-flash-lite`         | Nao                                 |
| `DATABASE_URL`              | String de conexao PostgreSQL. Padrao: `postgresql+psycopg://postgres:postgres@localhost:5432/rag` | Nao (usa padrao local) |
| `PG_VECTOR_COLLECTION_NAME` | Nome da collection no PGVector. Padrao: `documents`            | Nao                                 |
| `PDF_PATH`                  | Caminho para o arquivo PDF. Padrao: `document.pdf`             | Nao                                 |

---

## Troubleshooting

### Banco de dados nao sobe ou conexao recusada

**Sintoma:** `ingest.py` ou `chat.py` falhام com erro de conexao ao Postgres.

**Verificacoes:**
1. Confirme que o Docker Desktop esta em execucao.
2. Execute `docker compose ps` e verifique se o container `rag_postgres` aparece com status `healthy`.
3. Se o container nao subiu, execute `docker compose up -d` novamente e aguarde ~15 segundos.
4. Confirme que nenhum outro servico esta usando a porta 5432.

---

### API key invalida ou ausente

**Sintoma:** Erro como `Variavel de ambiente obrigatoria ausente: OPENAI_API_KEY` ou erro HTTP 401 do provider.

**Verificacoes:**
1. Abra o arquivo `.env` e confirme que a variavel correta esta preenchida:
   - `OPENAI_API_KEY` se `LLM_PROVIDER=openai`
   - `GOOGLE_API_KEY` se `LLM_PROVIDER=gemini`
2. Verifique se nao ha espacos em branco ou aspas extras ao redor do valor.
3. Confirme que a chave e valida e que sua conta tem credito ou quota disponivel.

---

### PDF nao encontrado

**Sintoma:** `[ingest] ERRO: PDF nao encontrado: /caminho/document.pdf`

**Verificacoes:**
1. Confirme que o arquivo `document.pdf` existe na raiz do projeto.
2. Se usar outro caminho, defina `PDF_PATH=/caminho/absoluto/para/arquivo.pdf` no `.env`.
3. Certifique-se de que o PDF contem texto extraivel (nao e um arquivo escaneado sem OCR). Se `ingest.py` reportar `0 chunks gerados`, o PDF provavelmente e somente imagem.

---

### Troca de provider exige re-ingestao

**Sintoma:** Erros de dimensao de vetor ou respostas inconsistentes apos alterar `LLM_PROVIDER`.

**Causa:** OpenAI gera vetores de 1536 dimensoes; Gemini gera 768. A dimensao e fixada na primeira escrita na collection e nao pode ser alterada sem recriar os dados.

**Solucao:** Sempre que alterar `LLM_PROVIDER`, re-execute a ingestao completa:

```bash
python src/ingest.py
```

O `ingest.py` ja recria a collection automaticamente (`pre_delete_collection=True`), descartando os embeddings do provider anterior.

---

### Chat responde "Nao tenho informacoes" para perguntas que deveriam ter resposta

**Sintoma:** Perguntas cujo tema esta no PDF retornam a frase de fallback.

**Verificacoes:**
1. Confirme que `ingest.py` foi executado com sucesso apos o ultimo `document.pdf` ser colocado na raiz.
2. Confirme que `LLM_PROVIDER` e o mesmo utilizado na ingestao.
3. Verifique nos logs do `ingest.py` se o numero de chunks gerados e maior que zero.

---

## Licenca

Consulte o arquivo `LICENSE` na raiz do projeto, se presente.
