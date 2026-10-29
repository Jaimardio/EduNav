-- 1. Tworzenie dedykowanej bazy dla gry (jeśli jeszcze nie istnieje)
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'GraEdukacyjna')
BEGIN
    CREATE DATABASE GraEdukacyjna;
END
GO

-- Przełączamy się na bazę gry
USE GraEdukacyjna;
GO

-- 2. Tabela definicji tematów
IF OBJECT_ID('DefinicjeTematow', 'U') IS NOT NULL
    DROP TABLE DefinicjeTematow;
GO

CREATE TABLE DefinicjeTematow (
    Temat NVARCHAR(50) PRIMARY KEY,
    CalkowitaLiczbaSlowek INT NOT NULL -- Szacowana całkowita liczba pojęć w tym temacie
);
GO

-- 3. Tabela przechowująca globalne pytania (dla trybu webowego/API)
IF OBJECT_ID('PytaniaGlobalne', 'U') IS NULL
BEGIN
    CREATE TABLE PytaniaGlobalne (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        Temat VARCHAR(100) NOT NULL,
        Pytanie VARCHAR(MAX) NOT NULL,
        Poprawna VARCHAR(MAX) NOT NULL,
        Bledna1 VARCHAR(MAX) NOT NULL,
        Bledna2 VARCHAR(MAX) NOT NULL
    );
END
GO

-- 4. Tabela indywidualnego postępu graczy (powiązana z pytaniami globalnymi)
IF OBJECT_ID('GraczPostep', 'U') IS NULL
BEGIN
    CREATE TABLE GraczPostep (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        Email VARCHAR(150) NOT NULL,
        PytanieId INT NOT NULL,
        CzyPoprawna BIT NOT NULL,
        Data DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (PytanieId) REFERENCES PytaniaGlobalne(Id)
    );
END
GO

-- 5. Tabela przechowująca historię każdej odpowiedzi gracza (dla trybu terminalowego / Dżina)
IF OBJECT_ID('HistoriaOdpowiedziGracza', 'U') IS NOT NULL
    DROP TABLE HistoriaOdpowiedziGracza;
GO

CREATE TABLE HistoriaOdpowiedziGracza (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    Email NVARCHAR(100) NOT NULL,
    Temat NVARCHAR(50) NOT NULL,         
    Pytanie NVARCHAR(MAX) NOT NULL,      
    CzyPoprawnie BIT NOT NULL,           
    DataOdpowiedzi DATETIME DEFAULT GETDATE()
);
GO

-- 6. Widok wyliczający postęp gracza, błędy i procentowy stan całego kursu
IF OBJECT_ID('WidokPostepuGracza', 'V') IS NOT NULL
    DROP VIEW WidokPostepuGracza;
GO

CREATE VIEW WidokPostepuGracza AS
SELECT 
    h.Email,
    h.Temat,
    ISNULL(d.CalkowitaLiczbaSlowek, 100) AS CalkowityCelKursu,
    COUNT(DISTINCT CASE WHEN h.CzyPoprawnie = 1 THEN h.Pytanie END) AS LiczbaOpanowanychUnikalnych,
    COUNT(h.ID) AS LiczbaWszystkichProb,
    SUM(CASE WHEN h.CzyPoprawnie = 0 THEN 1 ELSE 0 END) AS LiczbaBledow,
    CAST(
        (CAST(COUNT(DISTINCT CASE WHEN h.CzyPoprawnie = 1 THEN h.Pytanie END) AS FLOAT) / 
        ISNULL(NULLIF(d.CalkowitaLiczbaSlowek, 0), 100)) * 100 
    AS DECIMAL(5,2)) AS ProcentOgólnyMateriału
FROM HistoriaOdpowiedziGracza h
LEFT JOIN DefinicjeTematow d ON h.Temat = d.Temat
GROUP BY h.Email, h.Temat, d.CalkowitaLiczbaSlowek;
GO

-- 7. Dane początkowe (Seed Data) dla tematu 'historia ziemi'
IF NOT EXISTS (SELECT * FROM PytaniaGlobalne WHERE LOWER(Temat) = 'historia ziemi')
BEGIN
    INSERT INTO PytaniaGlobalne (Temat, Pytanie, Poprawna, Bledna1, Bledna2) VALUES
    ('historia ziemi', 'Około ile lat temu uformowała się Ziemia?', 'Około 4.5 miliarda lat temu', 'Około 6000 lat temu', 'Około 100 milionów lat temu'),
    ('historia ziemi', 'W której granicy er doszło do wielkiego wymarcia kredowego, w wyniku którego wyginęły dinozaury?', 'Granica kredy i paleogenu (K-Pg)', 'Granica permu i triasu', 'Granica jury i kredy'),
    ('historia ziemi', 'Jak nazywa się superkontynent, który istniał pod koniec ery paleozoicznej i na początku mezozoicznej?', 'Pangea', 'Gondwana', 'Rodinia'),
    ('historia ziemi', 'Która era geologiczna jest potocznie nazywana „Erą Gadów”?', 'Mezozoik', 'Paleozoik', 'Kenozoik'),
    ('historia ziemi', 'Jak nazywa się najstarszy eon w dziejach Ziemi, trwający od jej narodzin do około 4 miliardów lat temu?', 'Hadeik', 'Archaik', 'Proterozoik'),
    ('historia ziemi', 'Kiedy miała miejsce tzw. eksplozja kambryjska, podczas której gwałtownie pojawiła się ogromna różnorodność form życia?', 'Około 541 milionów lat temu', 'Około 2 miliardy lat temu', 'Około 65 milionów lat temu'),
    ('historia ziemi', 'Który okres geologiczny słynął z ogromnych lasów paprociowych, z których szczątków powstały dzisiejsze pokłady węgla kamiennego?', 'Karbon', 'Sylur', 'Dewon'),
    ('historia ziemi', 'Jakie wydarzenie doprowadziło do tzw. katastrofy tlenowej w paleoproterozoiku?', 'Masowy rozwój sinic produkujących tlen', 'Uderzenie wielkiej asteroidy', 'Erupcja superwulkanu'),
    ('historia ziemi', 'Która era geologiczna trwa obecnie i jest nazywana „Erą Ssáków”?', 'Kenozoik', 'Mezozoik', 'Paleozoik'),
    ('historia ziemi', 'Jak nazywa się nauka zajmująca się badaniem warstw skalnych i historii Ziemi w oparciu o skamieniałości?', 'Stratygrafia i paleontologia', 'Geodezja', 'Meteorologia');
    
    PRINT 'Pomyślnie zseedowano bazę pytaniami dla tematu historia ziemi!';
END
GO