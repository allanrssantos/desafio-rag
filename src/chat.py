from __future__ import annotations

import sys

from dotenv import load_dotenv

from search import ask

load_dotenv()

EXIT_COMMANDS = {"sair", "exit", "quit"}


def main() -> int:
    print("Faça sua pergunta (digite 'sair' ou Ctrl+C para encerrar).")
    while True:
        try:
            try:
                question = input("PERGUNTA: ").strip()
            except EOFError:
                print()
                return 0

            if not question:
                continue
            if question.lower() in EXIT_COMMANDS:
                print("Encerrando.")
                return 0

            try:
                answer = ask(question)
            except Exception as exc:  # mantem o REPL vivo
                print(f"[chat] ERRO: {exc}", file=sys.stderr)
                continue

            print(f"RESPOSTA: {answer}\n")
        except KeyboardInterrupt:
            print("\nEncerrando.")
            return 0


if __name__ == "__main__":
    sys.exit(main())
