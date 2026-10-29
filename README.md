# 🚢 EduNav – Gra Edukacyjna ze Statkami i AI

Interaktywna gra edukacyjno-zręcznościowa 3D stworzona w celach portfolio, łącząca naukę dowolnych tematów z mechaniką sterowania statkiem po morzu, omijaniem piratów i wykorzystaniem sztucznej inteligencji.

## 🚀 Technologie
* **Frontend:** HTML5, CSS3, JavaScript, Three.js (grafika 3D)
* **Backend:** Python, Flask, Flask-CORS, Google GenAI SDK (Gemini API)
* **Baza danych:** Microsoft SQL Server (uruchamiany w kontenerze Docker)
* **Konteneryzacja:** Docker & Docker Compose

## 🧠 Kluczowe Funkcje
* **Dynamiczna generacja pytań przez AI:** Jeśli temat nie istnieje w bazie, aplikacja automatycznie generuje pakiet pytań przy użyciu modelu Gemini.
* **Trwałość danych i Docker:** Pełna baza MS SQL Server uruchamiana w kontenerze, co eliminuje potrzebę skomplikowanej instalacji oprogramowania.
* **Śledzenie postępów:** Indywidualne statystyki gracza (celność, opanowane pytania, historia odpowiedzi) powiązane z bazą danych.

(main.py to legacy/CLI wersja gry)

## ⚙️ Jak uruchomić projekt lokalnie?

1. Sklonuj repozytorium na swój komputer:
   ```bash
   git clone https://github.com/Jaimardio/EduNav.git
   cd EduNav
2. Uruchom serwer bazy danych MS SQL w Dockerze:
    docker compose up -d
3. Zainstaluj wymagane zależności Pythona:
    pip install -r requirements.txt
4. Zainicjalizuj strukturę bazy danych za pomocą pliku schema.sql (np. przez rozszerzenie SQL Server w VS Code).
5. Skonfiguruj plik .env w głównym folderze i dodaj swój klucz API:
    GEMINI_API_KEY=twój_klucz_api_tutaj
6. Uruchom serwer backendu (Flask):
    python app.py
7. Otwórz plik index.html w przeglądarce lub uruchom grę lokalnie!