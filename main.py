import json
import os
import random
import time
from dotenv import load_dotenv
from google import genai
import pyodbc

# 1. Konfiguracja Gemini i ładowanie .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("BŁĄD: Brak klucza GEMINI_API_KEY w pliku .env!")
    exit()

client = genai.Client(api_key=api_key)

# 2. Połączenie z bazą danych SQL Server
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost,1433;"
    "DATABASE=GraEdukacyjna;"
    "UID=sa;"
    "PWD=StrongPassword123!;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    print("✓ Połączono z bazą danych GraEdukacyjna")
except Exception as e:
    print(f"Błąd połączenia z bazą: {e}")
    exit()

def pobierz_lub_utworz_definicje_tematu(temat: str) -> int:
    """Sprawdza rozmiar tematu w bazie. Jeśli temat jest nowy, Gemini go szacuje."""
    cursor.execute(
        "SELECT CalkowitaLiczbaSlowek FROM DefinicjeTematow WHERE Temat = ?",
        (temat,),
    )
    row = cursor.fetchone()

    if row:
        return row[0]

    print(f"[Dżin] Nowy temat '{temat}'! Oceniam wielkość zakresu materiału...")

    prompt_rozmiar = f"""
    Oceń, ile w przybliżeniu unikalnych pojęć, słówek lub kluczowych pytań trzeba opanować, 
    aby dobrze opanować temat: '{temat}'.
    Zwróć TYLKO I WYŁĄCZNIE jedną liczbę całkowitą (np. 150), bez żadnego innego tekstu ani słów.
    """

    try:
        resp = client.models.generate_content(
            model="gemini-3.8-flash", contents=prompt_rozmiar
        )
        calkowita_liczba = int(resp.text.strip())
        print(f"[Dżin] Otrzymano odpowiedź! Oszacowano na: {calkowita_liczba} pojęć.")
    except Exception as e:
        print(f"\n[BŁĄD SIECI/API] Nie udało się połączyć z Gemini: {e}")
        calkowita_liczba = 100

    cursor.execute(
        "INSERT INTO DefinicjeTematow (Temat, CalkowitaLiczbaSlowek) VALUES (?, ?)",
        (temat, calkowita_liczba),
    )
    conn.commit()
    return calkowita_liczba

def pobierz_pytanie_od_dzina(email: str, temat: str):
    pobierz_lub_utworz_definicje_tematu(temat)

    cursor.execute(
        "SELECT Pytanie FROM HistoriaOdpowiedziGracza WHERE Email = ? AND Temat = ? AND CzyPoprawnie = 1",
        (email, temat),
    )
    opanowane = [r[0] for r in cursor.fetchall()]

    prompt_pytanie = f"""
    Jesteś Dżinem – strażnikiem wiedzy w grze o statkach i portach.
    Użytkownik {email} realizuje temat: '{temat}'.
    
    Lista pytań, które ten gracz MA JUŻ OPANOWANE (NIE MOŻESZ ich powtórzyć):
    {opanowane}

    Wygeneruj 1 nowe pytanie z tego tematu i 3 warianty odpowiedzi.
    Odpowiedź zwróć DOKŁADNIE w formacie JSON (bez dodatkowego markdownu/znaczników ```json):
    {{
      "pytanie": "Treść nowego pytania?",
      "odpowiedzi": [
        {{"tekst": "Odpowiedź 1", "poprawna": false}},
        {{"tekst": "Odpowiedź 2", "poprawna": true}},
        {{"tekst": "Odpowiedź 3", "poprawna": false}}
      ]
    }}
    """

    max_prob = 3
    for proba in range(1, max_prob + 1):
        try:
            print(f"[Dżin] Generuję pytanie (próba {proba}/{max_prob})...")
            response = client.models.generate_content(
                model="gemini-3.8-flash", contents=prompt_pytanie
            )
            czysty_json = response.text.replace("```json", "").replace("```", "").strip()
            dane_pytania = json.loads(czysty_json)
            random.shuffle(dane_pytania["odpowiedzi"])
            return dane_pytania
        except Exception as e:
            print(f"[Dżin] Serwer Gemini jest chwilowo przeciążony. Czekam 3 sekundy przed ponownieniem... (Błąd: {e})")
            time.sleep(3)
    
    print("[BŁĄD] Nie udało się połączyć z Gemini po kilku próbach.")
    exit()

# --- GŁÓWNA PETLA GRY W TERMINALU ---
if __name__ == "__main__":
    email_gracza = input("Podaj e-mail: ").strip().lower()
    wybrany_temat = input("Podaj temat do nauki: ").strip().lower()

    zadanie = pobierz_pytanie_od_dzina(email_gracza, wybrany_temat)

    print("\n================ DŻIN PRZYGOTOWAŁ ZADANIE ================")
    print(f"PYTANIE: {zadanie['pytanie']}")
    print("PORTY (ODPOWIEDZI):")
    for idx, odp in enumerate(zadanie["odpowiedzi"], start=1):
        # UWAGA: Ukrywamy pole 'poprawna' przed graczem, żeby nie było widoczne w konsoli!
        print(f" Port {idx}: {odp['tekst']}")
    print("==========================================================")

    # Pozwól graczu wybrać port
    wybor = input("\nWybierz numer portu (1, 2 lub 3), do którego chcesz wpłynąć: ").strip()
    
    try:
        wybrany_idx = int(wybor) - 1
        wybrana_odp = zadanie["odpowiedzi"][wybrany_idx]
        czy_poprawnie = 1 if wybrana_odp["poprawna"] else 0

        # Zapisz wynik gracza w bazie danych SQL Server
        cursor.execute(
            "INSERT INTO HistoriaOdpowiedziGracza (Email, Temat, Pytanie, CzyPoprawnie) VALUES (?, ?, ?, ?)",
            (email_gracza, wybrany_temat, zadanie["pytanie"], czy_poprawnie)
        )
        conn.commit()

        if czy_poprawnie:
            print("\n🎉 Brawo! Statek szczęśliwie wpłynął do właściwego portu! Odpowiedź POPRAWNA.")
        else:
            print("\n💥 O nie! Twój statek wszedł na mieliznę! Odpowiedź BŁĘDNA.")

    except (ValueError, IndexError):
        print("\n❌ Nieprawidłowy wybór portu! Wpisz cyfrę 1, 2 lub 3.")

    cursor.close()
    conn.close()