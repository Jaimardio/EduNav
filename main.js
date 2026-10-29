let playerEmail = "";
let playerTemat = "";
let currentQuestion = null;
let isProcessingAnswer = false;

// --- Scena, kamera, renderer ---
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xFFCC66);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.set(0, 8, 20);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.getElementById("canvas-container").appendChild(renderer.domElement);

// --- Morze z siatką segmentów (fale) ---
const seaGeo = new THREE.PlaneGeometry(200, 200, 60, 60);
const seaMat = new THREE.MeshPhongMaterial({ color: 0x1e90ff, flatShading: true });
const sea = new THREE.Mesh(seaGeo, seaMat);
sea.rotation.x = -Math.PI / 2;
scene.add(sea);

// --- Światło ---
const light = new THREE.DirectionalLight(0xffffff, 1);
light.position.set(20, 50, 20);
scene.add(light);
scene.add(new THREE.AmbientLight(0x404040));

// --- Statek gracza ---
const ship = new THREE.Mesh(
    new THREE.BoxGeometry(2, 1, 4),
    new THREE.MeshPhongMaterial({ color: 0xff0000 })
);
ship.position.set(0, 0.5, 0);
scene.add(ship);

const glow = new THREE.Mesh(
    new THREE.SphereGeometry(3, 32, 32),
    new THREE.MeshBasicMaterial({ color: 0x00ff00, transparent: true, opacity: 0.3 })
);
glow.visible = false;
scene.add(glow);

// --- 3 Porty w 3D ---
const portsData = [
    { label: "A", x: -25, z: -50 },
    { label: "B", x: 0,   z: -50 },
    { label: "C", x: 25,  z: -50 }
];

portsData.forEach(p => {
    const group = new THREE.Group();
    const dock = new THREE.Mesh(new THREE.BoxGeometry(14, 0.5, 8), new THREE.MeshPhongMaterial({ color: 0x8B4513 }));
    dock.position.set(0, 0.25, 0);
    group.add(dock);

    for (let i = -1; i <= 1; i++) {
        const bld = new THREE.Mesh(new THREE.BoxGeometry(3, 4, 3), new THREE.MeshPhongMaterial({ color: 0x777777 }));
        bld.position.set(i * 4, 2, -2);
        group.add(bld);
    }
    group.position.set(p.x, 0, p.z);
    scene.add(group);
});

// --- Piraci (goniące statki) ---
const pirates = [];
const pirateCount = 3;
for (let i = 0; i < pirateCount; i++) {
    const pirate = new THREE.Mesh(
        new THREE.BoxGeometry(1.5, 0.6, 3),
        new THREE.MeshPhongMaterial({ color: 0x111111 })
    );
    pirate.position.set(Math.random() * 40 - 20, 0.3, -30 - i * 20);
    scene.add(pirate);
    pirates.push(pirate);
}

// --- Sterowanie ---
const keys = {};
document.addEventListener("keydown", e => keys[e.key] = true);
document.addEventListener("keyup", e => keys[e.key] = false);

// --- Inicjalizacja: Pobranie listy tematów z bazy SQL ---
async function wczytajListematow() {
    try {
        const res = await fetch("http://127.0.0.1:5000/api/pobierz-tematy");
        const data = await res.json();
        const select = document.getElementById("select-temat");
        select.innerHTML = '<option value="">-- Wybierz istniejący temat --</option>';
        if (data.tematy) {
            data.tematy.forEach(t => {
                select.innerHTML += `<option value="${t}">${t.toUpperCase()}</option>`;
            });
        }
    } catch (e) {
        console.error("Błąd wczytywania tematów:", e);
    }
}
wczytajListematow();

// --- PRZYCISK: Start Gry (z paczką 50 pytań startowych) ---
document.getElementById("btn-start").addEventListener("click", async () => {
    playerEmail = document.getElementById("input-email").value.trim();
    const wybranyZListy = document.getElementById("select-temat").value;
    const wpisanyNowy = document.getElementById("input-nowy-temat").value.trim();

    playerTemat = wpisanyNowy || wybranyZListy;

    if (!playerEmail || !playerTemat) {
        alert("Podaj swój e-mail oraz wybierz lub wpisz temat!");
        return;
    }

    document.getElementById("btn-start").innerText = "Generowanie 50 pytań przez AI...";

    try {
        const initRes = await fetch("http://127.0.0.1:5000/api/inicjalizuj-temat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                temat: playerTemat,
                ilosc: 50
            })
        });
        const initData = await initRes.json();

        if (initData.blad) {
            alert("Błąd: " + initData.blad);
            document.getElementById("btn-start").innerText = "Rozpocznij Rejs";
            return;
        }

        document.getElementById("login-modal").style.display = "none";
        document.getElementById("hud").style.display = "block";
        document.getElementById("game-controls").style.display = "flex";

        pobierzNowePytanie();

    } catch (err) {
        alert("Błąd połączenia z serwerem API!");
        document.getElementById("btn-start").innerText = "Rozpocznij Rejs";
    }
});

// --- Pobieranie pytania ze zgromadzonej bazy SQL ---
async function pobierzNowePytanie() {
    isProcessingAnswer = true;
    document.getElementById("question-text").innerText = "Ładowanie pytania z bazy...";
    document.getElementById("ans-a").innerText = "...";
    document.getElementById("ans-b").innerText = "...";
    document.getElementById("ans-c").innerText = "...";

    const loadingOverlay = document.getElementById('loading-overlay');

    try {
        if (loadingOverlay) loadingOverlay.style.display = 'flex';

        const url = `http://127.0.0.1:5000/api/pobierz-pytanie?email=${encodeURIComponent(playerEmail)}&temat=${encodeURIComponent(playerTemat)}`;
        const res = await fetch(url);
        const data = await res.json();

        if (data.blad) {
            document.getElementById("question-text").innerText = data.blad;
            isProcessingAnswer = false; // <--- DODANE: Odblokowuje sterowanie przy błędzie
            return;
        }

        currentQuestion = data;
        document.getElementById("question-text").innerText = data.pytanie;
        document.getElementById("ans-a").innerText = data.odpowiedzi[0].tresc;
        document.getElementById("ans-b").innerText = data.odpowiedzi[1].tresc;
        document.getElementById("ans-c").innerText = data.odpowiedzi[2].tresc;

        pirates.forEach((p, idx) => {
            p.position.set(Math.random() * 40 - 20, 0.3, ship.position.z - 40 - idx * 15);
        });

        isProcessingAnswer = false;

    } catch (err) {
        document.getElementById("question-text").innerText = "Błąd pobierania pytania!";
        isProcessingAnswer = false; // <--- DODANE: Odblokowuje sterowanie przy wyjątku
    } finally {
        if (loadingOverlay) loadingOverlay.style.display = 'none';
    }
}

// --- Obsługa Wpływu do Portu (Odpowiedź) ---
async function obsluzWplyniecieDoPortu(wybranyIndex) {
    if (isProcessingAnswer || !currentQuestion) return;
    isProcessingAnswer = true;

    const wybranaOdpowiedz = currentQuestion.odpowiedzi[wybranyIndex];
    const czyPoprawna = wybranaOdpowiedz.czy_poprawna ? 1 : 0;

    glow.material.color.set(czyPoprawna ? 0x00ff00 : 0xff0000);
    glow.visible = true;

    try {
        await fetch('http://127.0.0.1:5000/api/zapisz-odpowiedz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: playerEmail,
                pytanie_id: currentQuestion.id,
                czy_poprawna: czyPoprawna
            })
        });

        setTimeout(() => {
            glow.visible = false;
            ship.position.set(0, 0.5, 0);
            ship.rotation.set(0, 0, 0);
            pobierzNowePytanie();
        }, 1200);

    } catch (err) {
        console.error("Błąd zapisu odpowiedzi:", err);
        isProcessingAnswer = false;
    }
}

// --- Obsługa Złapania przez Piratów (Błąd) ---
async function obsluzAtakPiratow() {
    if (isProcessingAnswer || !currentQuestion) return;
    isProcessingAnswer = true;

    glow.material.color.set(0xff0000);
    glow.visible = true;
    document.getElementById("question-text").innerText = "Złapany przez piratów! Zapisano błąd.";

    try {
        await fetch('http://127.0.0.1:5000/api/zapisz-odpowiedz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: playerEmail,
                pytanie_id: currentQuestion.id,
                czy_poprawna: 0
            })
        });

        setTimeout(() => {
            glow.visible = false;
            ship.position.set(0, 0.5, 0);
            ship.rotation.set(0, 0, 0);
            pobierzNowePytanie();
        }, 1500);

    } catch (err) {
        console.error("Błąd zapisu ataku piratów:", err);
        isProcessingAnswer = false;
    }
}

// --- PRZYCISK: Mój Postęp ---
document.getElementById("btn-show-stats").addEventListener("click", async () => {
    isProcessingAnswer = true;

    try {
        const url = `http://127.0.0.1:5000/api/pobierz-statystyki?email=${encodeURIComponent(playerEmail)}&temat=${encodeURIComponent(playerTemat)}`;
        const res = await fetch(url);
        const data = await res.json();

        const html = `
            <b>Temat:</b> ${playerTemat.toUpperCase()}<br>
            <b>Opanowane pytania:</b> ${data.zaliczonych} / ${data.total_pytan}<br>
            <b>Wszystkie próby:</b> ${data.razem_proby}<br>
            <b>Poprawne próby:</b> ${data.dobre_proby}<br>
            <hr>
            <b style="font-size:18px; color:#00ffcc;">Skuteczność: ${data.skutecznosc_procent}%</b>
        `;
        document.getElementById("stats-content").innerHTML = html;
        document.getElementById("stats-modal").style.display = "flex";
    } catch (e) {
        alert("Błąd pobierania statystyk");
        isProcessingAnswer = false;
    }
});

document.getElementById("btn-close-stats").addEventListener("click", () => {
    document.getElementById("stats-modal").style.display = "none";
    isProcessingAnswer = false;
});

// --- PRZYCISK: Koniec Gry ---
document.getElementById("btn-exit").addEventListener("click", () => {
    document.getElementById("hud").style.display = "none";
    document.getElementById("game-controls").style.display = "none";
    document.getElementById("login-modal").style.display = "flex";
    document.getElementById("btn-start").innerText = "Rozpocznij Rejs";
    ship.position.set(0, 0.5, 0);
    wczytajListematow();
});

// --- Główna pętla gry (Animation Loop) z obsługą pauzy ---
function animate() {
    requestAnimationFrame(animate);

    const time = performance.now() / 300;

    sea.geometry.attributes.position.needsUpdate = true;
    const pos = sea.geometry.attributes.position.array;
    for (let i = 0; i < pos.length; i += 3) {
        pos[i + 2] = Math.sin(i / 5 + time) * 0.8 + Math.cos(i / 7 + time) * 0.4;
    }

    if (!isProcessingAnswer) {
        const speed = 0.2;
        const turnSpeed = 0.03;

        if (keys["ArrowLeft"]) ship.rotation.y += turnSpeed;
        if (keys["ArrowRight"]) ship.rotation.y -= turnSpeed;
        if (keys["ArrowUp"]) {
            ship.position.x -= Math.sin(ship.rotation.y) * speed;
            ship.position.z -= Math.cos(ship.rotation.y) * speed;
        }
        if (keys["ArrowDown"]) {
            ship.position.x += Math.sin(ship.rotation.y) * speed;
            ship.position.z += Math.cos(ship.rotation.y) * speed;
        }
    }

    ship.position.y = 0.5 + Math.sin(time + ship.position.z) * 0.15;
    glow.position.x = ship.position.x;
    glow.position.z = ship.position.z;
    glow.position.y = ship.position.y + 0.5;

    pirates.forEach(p => {
        p.position.y = 0.3 + Math.sin(time + p.position.z) * 0.15;

        if (!isProcessingAnswer) {
            const dirX = ship.position.x - p.position.x;
            const dirZ = ship.position.z - p.position.z;
            const distToShip = Math.sqrt(dirX * dirX + dirZ * dirZ);

            if (distToShip > 1.5) {
                p.position.x += dirX * 0.0035; 
                p.position.z += dirZ * 0.0035;
            }

            if (currentQuestion && distToShip < 2.0) {
                obsluzAtakPiratow();
            }
        }
    });

    if (!isProcessingAnswer && currentQuestion) {
        portsData.forEach((p, idx) => {
            const dx = ship.position.x - p.x;
            const dz = ship.position.z - p.z;
            if (Math.sqrt(dx * dx + dz * dz) < 8) {
                obsluzWplyniecieDoPortu(idx);
            }
        });
    }

    const targetPos = new THREE.Vector3(ship.position.x, 10, ship.position.z + 25);
    camera.position.lerp(targetPos, 0.08);
    camera.lookAt(ship.position);

    renderer.render(scene, camera);
}
animate();

window.addEventListener("resize", () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});