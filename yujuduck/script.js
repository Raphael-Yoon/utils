// HTML 이스케이프 유틸리티 함수 (XSS 방지)
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM fully loaded and parsed");
    const e = document.getElementById("game-canvas"),
        t = e.getContext("2d"),
        n = document.getElementById("coin-display"),
        o = document.getElementById("result-display"),
        a = document.getElementById("collection-container"),
        l = document.getElementById("beg-confirmation-buttons"),
        i = document.getElementById("left-button"),
        d = document.getElementById("right-button"),
        r = document.getElementById("drop-button"),
        s = document.getElementById("game-over-modal"),
        c = document.getElementById("collected-count"),
        g = document.getElementById("restart-game-btn"),
        m = document.getElementById("player-name-input"),
        h = document.getElementById("save-score-btn"),
        u = -80,
        y = ["바보! 인형이 도망갔잖아!", "에휴, 그것도 못 잡니?", "다음 생에 잡으렴!", "돈만 날렸네!", "엄마한테 일러바칠 거야!", "넌 인형 뽑기 소질 없어!", "다음에 또 도전해봐! (과연 잡을 수 있을까?)", "실력이 부족하네!", "야 이 똥멍청이야!!"],
        p = ["와! ${dollName} 획득!", "대단해요! ${dollName}을(를) 잡았어요!", "컬렉션에 ${dollName} 추가!", "나이스 캐치! ${dollName}!"],
        b = [
            { id: 1, name: "인형 1호", rarity: "Common", src: "images/doll_01.png", type: "normal" },
            { id: 2, name: "인형 2호", rarity: "Common", src: "images/doll_02.png", type: "normal" },
            { id: 3, name: "인형 3호", rarity: "Common", src: "images/doll_03.png", type: "normal" },
            { id: 4, name: "인형 4호", rarity: "Common", src: "images/doll_04.png", type: "normal" },
            { id: 5, name: "인형 5호", rarity: "Common", src: "images/doll_05.png", type: "normal" },
            { id: 6, name: "인형 6호", rarity: "Common", src: "images/doll_06.png", type: "normal" },
            { id: 7, name: "인형 7호", rarity: "Common", src: "images/doll_07.png", type: "normal" },
            { id: 8, name: "인형 8호", rarity: "Common", src: "images/doll_08.png", type: "normal" },
            { id: 9, name: "인형 9호", rarity: "Common", src: "images/doll_09.png", type: "normal" },
            { id: 10, name: "인형 10호", rarity: "Common", src: "images/doll_10.png", type: "normal" },
            { id: 11, name: "인형 11호", rarity: "Rare", src: "images/doll_11.png", type: "normal" },
            { id: 12, name: "인형 12호", rarity: "Rare", src: "images/doll_12.png", type: "normal" },
            { id: 13, name: "인형 13호", rarity: "Rare", src: "images/doll_13.png", type: "normal" },
            { id: 14, name: "인형 14호", rarity: "Rare", src: "images/doll_14.png", type: "normal" },
            { id: 15, name: "인형 15호", rarity: "Rare", src: "images/doll_15.png", type: "normal" },
            { id: 16, name: "인형 16호", rarity: "Rare", src: "images/doll_16.png", type: "normal" },
            { id: 17, name: "인형 17호", rarity: "Super Rare", src: "images/doll_17.png", type: "normal" },
            { id: 18, name: "인형 18호", rarity: "Super Rare", src: "images/doll_18.png", type: "normal" },
            { id: 19, name: "폭탄 인형", rarity: "Super Rare", src: "images/doll_19.png", type: "bomb" },
            { id: 20, name: "돈 인형", rarity: "Super Rare", src: "images/doll_20.png", type: "coin" }
        ];
    let f = 1e3;
    const E = new Set;
    let D, x, C, I, w = [], R = {}, v = "LOADING", M = !1;
    const A = { x: e.width / 2, y: 50, width: 60, height: 60, speed: 3, isClosed: !1, grabbedDoll: null, isShaking: !1 };
    let k = !1;

    function B() { "READY" === v && (A.x = Math.max(0, A.x - 20)) }
    function G() { "READY" === v && (A.x = Math.min(e.width - A.width, A.x + 20)) }
    function N(e) {
        if ("READY" !== v) return;
        e.touches && e.preventDefault();
        const t = _(e);
        t.x >= A.x && t.x <= A.x + A.width && t.y >= A.y && t.y <= A.y + A.height && (k = !0)
    }
    function L(t) {
        if (!k || "READY" !== v) return;
        t.touches && t.preventDefault();
        const n = _(t);
        A.x = Math.max(0, Math.min(e.width - A.width, n.x - A.width / 2))
    }
    function S(e) { k = !1 }
    function _(t) {
        const n = e.getBoundingClientRect();
        return t.touches && t.touches.length > 0 ? { x: t.touches[0].clientX - n.left, y: t.touches[0].clientY - n.top } : { x: t.clientX - n.left, y: t.clientY - n.top }
    }
    function O() {
        w = [];
        const t = { x: u, y: e.height - 200, width: 300, height: 200 };
        for (let n = 0; n < 15; n++) {
            const n = b[Math.floor(Math.random() * b.length)];
            let o;
            do {
                o = { x: Math.random() * (e.width - 150) + 100, y: e.height - (100 * Math.random() + 40), width: 60, height: 60, isGrabbed: !1, isFalling: !1, ...n }
            } while (P(o, t));
            w.push(o)
        }
    }
    function $(t) {
        console.log("handleKeyDown - gameState:", v, "key:", t.key),
            "READY" === v && ("ArrowLeft" === t.key ? A.x = Math.max(0, A.x - A.speed) : "ArrowRight" === t.key ? A.x = Math.min(e.width - A.width, A.x + A.speed) : " " === t.key && "READY" === v && (t.preventDefault(), T()))
    }
    function T() {
        "READY" === v && (f < 100 ? M ? j() : (v = "AWAITING_BEG_CONFIRMATION", o.textContent = "돈이 부족합니다! 💰") : (f -= 100, n.textContent = `${f}원`, f < 100 && !M && (r.textContent = "찬스!!!"), o.textContent = "", v = "DROPPING", A.isClosed = !1, A.grabbedDoll = null))
    }
    function U() {
        if ("AWAITING_BEG_CONFIRMATION" !== v) return;
        M = !0, v = "COUNTDOWN", l.style.display = "none";
        let e = 3;
        o.textContent = e;
        const t = setInterval(() => {
            if (e--, e > 0) o.textContent = e;
            else {
                if (clearInterval(t), Math.random() < .6) {
                    const e = 100 * (Math.floor(10 * Math.random()) + 1);
                    f += e, n.textContent = `${f}원`, o.textContent = `엄마가 돈을 주셨어요! +${e}원!`
                } else o.textContent = "엄마가 돈을 안 주셨어요...";
                setTimeout(() => { v = "READY", r.textContent = "내려가기" }, 1e3)
            }
        }, 1e3)
    }
    function Y() {
        "AWAITING_BEG_CONFIRMATION" === v && (M = !0, o.textContent = "돈이 부족합니다!", v = "READY", l.style.display = "none", r.textContent = "게임 끝")
    }
    function F() {
        !function () {
            if (console.log("UPDATE - Current gameState:", v), function () {
                l.style.display = "AWAITING_BEG_CONFIRMATION" === v ? "block" : "none";
                const e = "READY" === v;
                i.disabled = !e, d.disabled = !e, r.disabled = !e
            }(), w.forEach(t => {
                t.isFalling && (t.y += 1.5 * A.speed, t.y >= e.height - t.height && (t.y = e.height - t.height, t.isFalling = !1))
            }), "DROPPING" === v) {
                console.log("DEBUG: Entering DROPPING state. claw.y:", A.y), A.y += A.speed;
                let t = null;
                for (const e of w) if (!e.isGrabbed && P(A, e)) { t = e, console.log("DEBUG: Collision detected with doll:", e.name); break }
                console.log("DEBUG: hitDoll is:", t ? t.name : "null", "claw.y:", A.y, "bottom threshold:", e.height - A.height), t ? (Math.random() < .7 ? (A.grabbedDoll = t, t.isGrabbed = !0, console.log("DEBUG: Doll grabbed successfully.")) : (console.log("DEBUG: Failed to grab doll (50% chance). Displaying taunt."), o.textContent = y[Math.floor(Math.random() * y.length)]), A.isClosed = !0, v = "RAISING", A.grabbedDoll && Math.random() < .25 && (A.isShaking = !0, o.textContent = "집게가 심하게 흔들립니다!", console.log("DEBUG: Claw shaking activated."))) : A.y >= e.height - A.height && (console.log("DEBUG: Claw hit bottom empty-handed. Displaying taunt."), A.isClosed = !0, v = "RAISING", o.textContent = y[Math.floor(Math.random() * y.length)])
            } else if ("RAISING" === v) {
                if (console.log("DEBUG: Entering RAISING state."), A.y -= A.speed, A.grabbedDoll) {
                    const e = A.isShaking ? .025 : .007;
                    Math.random() < e ? (console.log("DEBUG: Doll dropped while raising. Displaying taunt."), o.textContent = y[Math.floor(Math.random() * y.length)], A.grabbedDoll.isGrabbed = !1, A.grabbedDoll.isFalling = !0, A.grabbedDoll = null, A.isShaking = !1) : (A.grabbedDoll.x = A.x, A.grabbedDoll.y = A.y + A.height - 20)
                }
                A.y <= 50 && (A.isShaking = !1, v = "RETURNING")
            } else if ("RETURNING" === v) {
                console.log("DEBUG: Entering RETURNING state.");
                const e = 50;
                A.x > e ? A.x = Math.max(e, A.x - A.speed) : A.x < e ? A.x = Math.min(e, A.x + A.speed) : (v = "RELEASING_DOLL", A.isClosed = !1), A.grabbedDoll && (A.grabbedDoll.x = A.x)
            } else if ("RELEASING_DOLL" === v) if (console.log("DEBUG: Entering RELEASING_DOLL state."), A.grabbedDoll) {
                if (A.grabbedDoll.y += 2 * A.speed, A.grabbedDoll.y > e.height) {
                    switch (A.grabbedDoll.type) {
                        case "bomb": o.textContent = "펑! 폭탄이었습니다..."; break;
                        case "coin": f += 500, n.textContent = `${f}원`, o.textContent = "돈 인형! +500원!", E.has(A.grabbedDoll.id) || (E.add(A.grabbedDoll.id), Q()); break;
                        default: const e = p[Math.floor(Math.random() * p.length)]; o.textContent = e.replace("${dollName}", A.grabbedDoll.name), E.has(A.grabbedDoll.id) || (E.add(A.grabbedDoll.id), Q())
                    }
                    if (w = w.filter(e => e !== A.grabbedDoll), A.grabbedDoll = null, f < 100 && M) return void j();
                    z()
                }
            } else z()
        }(), function () {
            t.clearRect(0, 0, e.width, e.height), D && D.complete && t.drawImage(D, 0, 0, e.width, e.height);
            w.forEach(e => {
                const n = R[e.src];
                n ? t.drawImage(n, e.x, e.y, e.width, e.height) : (t.fillStyle = "#ff00ff", t.fillRect(e.x, e.y, e.width, e.height))
            }), I && I.complete ? t.drawImage(I, u, e.height - 200, 300, 200) : (t.fillStyle = "#a0a0a0", t.fillRect(u, e.height - 50, 80, 50), t.fillStyle = "#c0c0c0", t.fillRect(u, e.height - 50, 80, 10));
            !function () {
                let e = A.x;
                A.isShaking && (e += 10 * (Math.random() - .5));
                t.beginPath(), t.moveTo(e + A.width / 2, 0), t.lineTo(e + A.width / 2, A.y), t.strokeStyle = "#777", t.lineWidth = 2, t.stroke();
                const n = A.isClosed ? C : x;
                n && n.complete ? t.drawImage(n, e, A.y, A.width, A.height) : (t.fillStyle = "#999", t.fillRect(e, A.y, A.width, A.height))
            }()
        }(), requestAnimationFrame(F)
    }
    function z() {
        A.x = e.width / 2, A.y = 50, A.isClosed = !1, A.grabbedDoll = null, A.isShaking = !1, v = "READY"
    }
    function P(e, t) {
        return e.x < t.x + t.width && e.x + e.width > t.x && e.y < t.y + t.height && e.y + e.height > t.y
    }
    function j() {
        v = "GAME_OVER", c.textContent = E.size, m.value = "", s.style.display = "block", r.disabled = !0, r.textContent = "게임 끝", m.focus()
    }
    function W() {
        const e = m.value.trim();
        if ("" === e) return alert("이름을 입력해주세요!"), void m.focus();
        !function (e, t) {
            const n = new Date, o = n.getDay(), a = 0 === o ? 6 : o - 1, l = new Date(n);
            l.setDate(n.getDate() - a), l.setHours(0, 0, 0, 0);
            const i = l.getFullYear(), d = (l.getMonth() + 1).toString().padStart(2, "0"), r = l.getDate().toString().padStart(2, "0"), s = `${i}-${d}-${r}`, c = X.ref(`ranking/${s}/${e}`);
            c.once("value", e => {
                e.exists() && e.val().score >= t ? alert("기존 점수보다 낮은 점수입니다. 갱신되지 않았습니다.") : c.set({ score: t }, e => {
                    e ? alert("점수 저장에 실패했습니다.") : alert("점수가 저장되었습니다!")
                })
            })
        }(e, E.size), h.disabled = !0, h.textContent = "저장됨"
    }
    function H() {
        f = 1e3, M = !1, E.clear(), n.textContent = `${f}원`, o.textContent = "", s.style.display = "none", h.disabled = !1, h.textContent = "점수 저장", O(), Q(), z(), r.disabled = !1, r.textContent = "내려가기"
    }
    function Q() {
        a.innerHTML = "", b.forEach(e => {
            const t = document.createElement("div");
            t.classList.add("collection-item");
            const n = document.createElement("img"), o = document.createElement("p");
            if (E.has(e.id)) {
                const a = R[e.src];
                a && (n.src = a.src), o.textContent = e.name, t.style.backgroundColor = "#e0ffe0"
            } else {
                n.style.opacity = "0.2";
                const t = R[e.src];
                t && (n.src = t.src), o.textContent = "???"
            }
            t.appendChild(n), t.appendChild(o), a.appendChild(t)
        })
    }
    !function (e) {
        let t = 0;
        const n = b.length + 4;
        D = new Image, D.src = "images/background.jpg", D.onload = () => { t++, t === n && e() }, D.onerror = () => { t++, console.error("Could not load image: images/background.jpg"), t === n && e() },
            b.forEach(o => {
                const a = new Image;
                a.src = o.src, a.onload = () => { t++, R[o.src] = a, t === n && e() }, a.onerror = () => { t++, console.error(`Could not load image: ${o.src}`), t === n && e() }
            }),
            x = new Image, x.src = "images/catch_o.png", x.onload = () => { t++, t === n && e() }, x.onerror = () => { t++, console.error("Could not load image: images/catch_o.png"), t === n && e() },
            C = new Image, C.src = "images/catch_c.png", C.onload = () => { t++, t === n && e() }, C.onerror = () => { t++, console.error("Could not load image: images/catch_c.png"), t === n && e() },
            I = new Image, I.src = "images/prize.png", I.onload = () => { t++, t === n && e() }, I.onerror = () => { t++, console.error("Could not load image: images/prize.png"), t === n && e() }
    }(function () {
        void 0 !== window.orientation || -1 !== navigator.userAgent.indexOf("Mobi") ? A.speed = 3.5 : A.speed = 3;
        O(), Q(),
            document.addEventListener("keydown", $),
            document.getElementById("drop-button").addEventListener("click", T),
            document.getElementById("left-button").addEventListener("click", B),
            document.getElementById("right-button").addEventListener("click", G),
            document.getElementById("left-button").addEventListener("touchstart", function (e) { e.preventDefault(), B() }),
            document.getElementById("right-button").addEventListener("touchstart", function (e) { e.preventDefault(), G() }),
            document.getElementById("confirm-beg-button").addEventListener("click", U),
            document.getElementById("decline-beg-button").addEventListener("click", Y),
            g.addEventListener("click", H),
            h.addEventListener("click", W),
            e.addEventListener("mousedown", N),
            e.addEventListener("mousemove", L),
            e.addEventListener("mouseup", S),
            e.addEventListener("mouseleave", S),
            e.addEventListener("touchstart", N),
            e.addEventListener("touchmove", L),
            e.addEventListener("touchend", S),
            n.textContent = `${f}원`,
            v = "READY",
            function () {
                K.textContent = "주간 랭킹";
                const e = new Date, t = e.getDay(), n = 0 === t ? 6 : t - 1, o = new Date(e);
                o.setDate(e.getDate() - n), o.setHours(0, 0, 0, 0);
                const a = o.getFullYear(), l = (o.getMonth() + 1).toString().padStart(2, "0"), i = o.getDate().toString().padStart(2, "0"), d = `${a}-${l}-${i}`;
                X.ref("ranking/" + d).orderByChild("score").limitToLast(10).on("value", e => {
                    const t = [];
                    e.forEach(e => { t.push({ name: e.key, score: e.val().score }) }), t.reverse(), q.innerHTML = "",
                        t.forEach((e, t) => {
                            const n = document.createElement("tr");
                            const tdRank = document.createElement("td");
                            tdRank.textContent = t + 1;
                            const tdName = document.createElement("td");
                            tdName.textContent = e.name; // textContent로 안전하게 렌더링 (XSS 방어)
                            const tdScore = document.createElement("td");
                            tdScore.textContent = e.score;
                            n.appendChild(tdRank);
                            n.appendChild(tdName);
                            n.appendChild(tdScore);
                            q.appendChild(n);
                        })
                })
            }(),
            F()
    });

    // Firebase 초기화 (databaseURL 기반)
    firebase.initializeApp({
        apiKey: "AIzaSyAwO92zAoXW3ujNoNfy4tOMzN8wZwwYQgg",
        authDomain: "yujuduck.firebaseapp.com",
        databaseURL: "https://yujuduck-default-rtdb.asia-southeast1.firebasedatabase.app/",
        projectId: "yujuduck",
        storageBucket: "yujuduck.firebasestorage.app",
        messagingSenderId: "749402785241",
        appId: "1:749402785241:web:dbf5ce7b4dd4d808e185c8",
        measurementId: "G-HQMEJQM1ML"
    });
    const X = firebase.database(),
        q = document.querySelector("#ranking-table tbody"),
        K = document.getElementById("ranking-title")
});