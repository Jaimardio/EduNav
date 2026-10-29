import json
import os
import random
import traceback
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from google import genai
import pyodbc

load_dotenv()

app = Flask(__name__)
CORS(app)

# Konfiguracja SQL Server (dostosowana pod Dockera lub lokalną instancję)
DB_CONFIG = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost,1433;"
    "DATABASE=GraEdukacyjna;"
    "UID=sa;"
    "PWD=StrongPassword123!;"
)

def get_db():
    return pyodbc.connect(DB_CONFIG)

# Konfiguracja Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("[OSTRZEŻENIE] Brak klucza GEMINI_API_KEY w pliku .env!")

client = genai.Client(api_key=api_key) if api_key else None


# 1. Pobieranie listy dostępnych tematów z bazy
@app.route("/api/pobierz-tematy", methods=["GET"])
def pobierz_tematy():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT Temat FROM PytaniaGlobalne ORDER BY Temat")
        tematy = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify({"tematy": tematy})
    except Exception as e:
        print(f"[BŁĄD DB] Nie udało się pobrać tematów: {e}")
        return jsonify({"tematy": [], "blad": str(e)})


# 2. Inicjalizacja tematu i pobieranie pytań (domyślnie 10 na start)
@app.route("/api/inicjalizuj-temat", methods=["POST"])
def inicjalizuj_temat():
    dane = request.json
    temat = dane.get("temat", "").strip().lower()
    ilosc_pytan = int(dane.get("ilosc", 10))

    if not temat:
        return jsonify({"blad": "Brak tematu"}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM PytaniaGlobalne WHERE LOWER(Temat) = ?",
            (temat,),
        )
        count = cursor.fetchone()[0]

        # Jeśli temat nie ma pytań w bazie, generujemy je przez Gemini
        if count == 0:
            if not client:
                conn.close()
                return jsonify({"blad": "Brak klucza API Gemini – nie można wygenerować nowych pytań."}), 500

            prompt = f"""Wygeneruj pakiet dokładnie {ilosc_pytan} unikalnych pytań testowych na temat: '{temat}'.
Zwróć WYŁĄCZNIE czysty JSON w postaci tablicy obiektów o strukturze:
[
  {{
    "pytanie": "Treść pytania...",
    "poprawna": "Poprawna odpowiedź",
    "bledna1": "Błędna odpowiedź 1",
    "bledna2": "Błędna odpowiedź 2"
  }}
]"""

            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash", contents=prompt
                )
                
                # Bezpieczniejsze czyszczenie odpowiedzi z markdownu
                tekst_odpowiedzi = response.text.strip()
                if "```json" in tekst_odpowiedzi:
                    tekst_odpowiedzi = tekst_odpowiedzi.split("```json")[1].split("```")[0].strip()
                elif "```" in tekst_odpowiedzi:
                    tekst_odpowiedzi = tekst_odpowiedzi.split("```")[1].split("```")[0].strip()

                pytania_pack = json.loads(tekst_odpowiedzi)

                for p in pytania_pack:
                    cursor.execute(
                        """
                        INSERT INTO PytaniaGlobalne (Temat, Pytanie, Poprawna, Bledna1, Bledna2)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            temat,
                            p["pytanie"],
                            p["poprawna"],
                            p["bledna1"],
                            p["bledna2"],
                        ),
                    )
                conn.commit()

            except Exception as ai_err:
                print(f"\n[BŁĄD AI / JSON] Nie udało się wygenerować lub zapisać pytań:")
                traceback.print_exc()
                conn.close()
                return jsonify({"blad": f"Błąd generowania pytań przez AI: {str(ai_err)}"}), 500

        conn.close()
        return jsonify(
            {"status": "ok", "message": "Temat gotowy do rozgrywki", "wygenerowano": ilosc_pytan}
        )

    except Exception as e:
        print(f"\n[BŁĄD SERWERA]: {e}")
        traceback.print_exc()
        return jsonify({"blad": f"Błąd inicjalizacji: {str(e)}"}), 500


# 3. Pobieranie kolejnego pytania z bazy SQL (z opcją rozszerzania bazy)
@app.route("/api/pobierz-pytanie", methods=["GET"])
def pobierz_pytanie():
    email = request.args.get("email")
    temat = request.args.get("temat", "").strip().lower()

    try:
        conn = get_db()
        cursor = conn.cursor()

        query = """
            SELECT TOP 1 Id, Pytanie, Poprawna, Bledna1, Bledna2 
            FROM PytaniaGlobalne 
            WHERE LOWER(Temat) = ? AND Id NOT IN (
                SELECT PytanieId FROM GraczPostep WHERE Email = ? AND CzyPoprawna = 1
            )
            ORDER BY NEWID()
        """
        cursor.execute(query, (temat, email))
        row = cursor.fetchone()

        # Jeśli gracz odpowiedział już na wszystko, dociągamy nowe pytania przez AI
        if not row and client:
            prompt = f"""Wygeneruj kolejny pakiet 10 unikalnych pytań testowych na temat: '{temat}'.
Zwróć WYŁĄCZNIE czysty JSON w postaci tablicy obiektów o strukturze:
[
  {{
    "pytanie": "Treść pytania...",
    "poprawna": "Poprawna odpowiedź",
    "bledna1": "Błędna odpowiedź 1",
    "bledna2": "Błędna odpowiedź 2"
  }}
]"""
            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash", contents=prompt
                )
                tekst_odpowiedzi = response.text.strip()
                if "```json" in tekst_odpowiedzi:
                    tekst_odpowiedzi = tekst_odpowiedzi.split("```json")[1].split("```")[0].strip()
                elif "```" in tekst_odpowiedzi:
                    tekst_odpowiedzi = tekst_odpowiedzi.split("```")[1].split("```")[0].strip()

                nowy_pack = json.loads(tekst_odpowiedzi)

                for p in nowy_pack:
                    cursor.execute("""
                        INSERT INTO PytaniaGlobalne (Temat, Pytanie, Poprawna, Bledna1, Bledna2)
                        VALUES (?, ?, ?, ?, ?)
                    """, (temat, p["pytanie"], p["poprawna"], p["bledna1"], p["bledna2"]))
                conn.commit()

                cursor.execute(query, (temat, email))
                row = cursor.fetchone()
            except Exception as ai_err:
                print(f"[AI Expansion Error]: {ai_err}")
                traceback.print_exc()

        if not row:
            cursor.execute("""
                SELECT TOP 1 Id, Pytanie, Poprawna, Bledna1, Bledna2 
                FROM PytaniaGlobalne WHERE LOWER(Temat) = ? ORDER BY NEWID()
            """, (temat,))
            row = cursor.fetchone()

        conn.close()

        if not row:
            return jsonify({"blad": "Brak pytań w bazie dla tego tematu."}), 404

        pytanie_id, q_text, poprawna, b1, b2 = row

        odpowiedzi = [
            {"tresc": poprawna, "czy_poprawna": True},
            {"tresc": b1, "czy_poprawna": False},
            {"tresc": b2, "czy_poprawna": False}
        ]
        random.shuffle(odpowiedzi)

        return jsonify({
            "id": pytanie_id,
            "pytanie": q_text,
            "odpowiedzi": odpowiedzi
        })

    except Exception as e:
        print(f"[BŁĄD POBIERANIA PYTANIA]: {e}")
        traceback.print_exc()
        return jsonify({"blad": str(e)}), 500


# 4. Zapis odpowiedzi gracza
@app.route("/api/zapisz-odpowiedz", methods=["POST"])
def zapisz_odpowiedz():
    dane = request.json
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO GraczPostep (Email, PytanieId, CzyPoprawna, Data)
            VALUES (?, ?, ?, GETDATE())
        """,
            (dane["email"], dane["pytanie_id"], dane["czy_poprawna"]),
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "zapisano"})
    except Exception as e:
        return jsonify({"blad": str(e)}), 500


# 5. Pobieranie statystyk postępu gracza
@app.route("/api/pobierz-statystyki", methods=["GET"])
def pobierz_statystyki():
    email = request.args.get("email")
    temat = request.args.get("temat", "").strip().lower()

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM PytaniaGlobalne WHERE LOWER(Temat) = ?",
            (temat,),
        )
        total_pytan = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(DISTINCT PytanieId) FROM GraczPostep gp
            JOIN PytaniaGlobalne pg ON gp.PytanieId = pg.Id
            WHERE gp.Email = ? AND LOWER(pg.Temat) = ? AND gp.CzyPoprawna = 1
        """,
            (email, temat),
        )
        zaliczonych = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*), SUM(CAST(CzyPoprawna AS INT)) FROM GraczPostep gp
            JOIN PytaniaGlobalne pg ON gp.PytanieId = pg.Id
            WHERE gp.Email = ? AND LOWER(pg.Temat) = ?
        """,
            (email, temat),
        )
        stats = cursor.fetchone()
        razem_proby = stats[0] or 0
        dobre_proby = stats[1] or 0

        procent = (
            round((dobre_proby / razem_proby) * 100, 1)
            if razem_proby > 0
            else 0.0
        )

        conn.close()
        return jsonify(
            {
                "total_pytan": total_pytan,
                "zaliczonych": zaliczonych,
                "razem_proby": razem_proby,
                "dobre_proby": dobre_proby,
                "skutecznosc_procent": procent,
            }
        )
    except Exception as e:
        return jsonify({"blad": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)