import json
import re

DATASET_PATH = "dataset.json"
OUTPUT_TXT   = "teksty_piosenek.txt"

# Tryb separacji utworów w pliku .txt:
#   "separator" -> utwory oddzielone linią "=== ... ===" (czytelne)
#   "blankline" -> utwory oddzielone jedną pustą linią
#   "oneline"   -> każdy utwór w jednej linii (znaki \n zamienione na spacje)
#   "jsonl"     -> każda linia to JSON: {"text": "..."} (dobre do trenowania)
TRYB = "separator"

SEPARATOR = "\n" + "=" * 60 + "\n"


def wyciagnij_tekst(el) -> str | None:
    """Zwraca oczyszczony tekst piosenki z elementu datasetu."""
    if isinstance(el, dict):
        tekst = el.get("text") or el.get("lyrics") or el.get("content")
    elif isinstance(el, str):
        tekst = el
    else:
        return None

    if not isinstance(tekst, str):
        return None

    # Normalizacja: ujednolicamy końce linii, usuwamy zbędne białe znaki
    tekst = tekst.replace("\r\n", "\n").replace("\r", "\n")
    tekst = "\n".join(linia.rstrip() for linia in tekst.split("\n"))
    tekst = re.sub(r"\n{3,}", "\n\n", tekst).strip()   # max 2 puste linie z rzędu
    return tekst or None


def main():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dane = json.load(f)

    if not isinstance(dane, dict) or "train" not in dane:
        raise SystemExit("Brak klucza 'train' w dataset.json")

    teksty = []
    for el in dane["train"]:
        t = wyciagnij_tekst(el)
        if t:
            teksty.append(t)

    print(f"[i] Wyciągnięto {teksty} tekstów z {len(dane['train'])} elementów." if False else
          f"[i] Wyciągnięto {len(teksty)} tekstów z {len(dane['train'])} elementów.")

    # Zapis w wybranym trybie
    if TRYB == "separator":
        with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
            f.write(SEPARATOR.join(teksty))
    elif TRYB == "blankline":
        with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
            f.write("\n\n".join(teksty))
    elif TRYB == "oneline":
        with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
            for t in teksty:
                f.write(re.sub(r"\s+", " ", t).strip() + "\n")
    elif TRYB == "jsonl":
        with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
            for t in teksty:
                f.write(json.dumps({"text": t}, ensure_ascii=False) + "\n")
    else:
        raise SystemExit(f"Nieznany TRYB: {TRYB}")

    print(f"[✓] Zapisano do: {OUTPUT_TXT}")


if __name__ == "__main__":
    main()