const savedState = CasinoStorage.getCombinedState();
const state = {
    money: savedState.money,
    initialMoney: savedState.initialMoney,
    currentBet: 10000,
    isPlaying: false,
    totalRounds: savedState.totalRounds,
    houseProfit: savedState.houseProfit,
    peakBalance: savedState.peakBalance,
    isAutoMode: false,
    speed: 500,
    chart: null,
    labels: [],
    balanceHistory: [],
    // Analysis Stats
    totalBetAmount: 0,
    totalPayout: 0,
    currentLossStreak: 0,
    maxLossStreak: 0
};

const SYMBOLS = [
    { name: 'CHERRY', icon: '🍒', payout: 10 },
    { name: 'BAR', icon: 'BAR', payout: 25 },
    { name: 'SEVEN', icon: '7', payout: 100 },
    { name: 'JACKPOT', icon: '💎', payout: 500 }
];

const REEL_SYMBOL_COUNT = 50; // Total symbols in a reel strip

function initChart() {
    const ctx = document.getElementById('assetChart').getContext('2d');
    state.chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: state.labels,
            datasets: [{
                label: '보유 자산',
                data: state.balanceHistory,
                borderColor: '#ffd700',
                borderWidth: 2,
                fill: false,
                tension: 0.1,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { display: false },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#aaa', font: { size: 10 } }
                }
            },
            plugins: { legend: { display: false } }
        }
    });
}

function updateUI() {
    document.getElementById('money').textContent = Math.floor(state.money).toLocaleString();
    document.getElementById('current-bet-display').textContent = state.currentBet.toLocaleString();
    document.getElementById('total-rounds').textContent = state.totalRounds;
    document.getElementById('house-profit').textContent = Math.floor(state.houseProfit).toLocaleString();
    document.getElementById('peak-balance').textContent = Math.floor(state.peakBalance).toLocaleString();

    const autoBtn = document.getElementById('auto-btn');
    if (state.isAutoMode) {
        autoBtn.textContent = "시뮬레이션 중지";
        autoBtn.classList.add('active');
    } else {
        autoBtn.textContent = '자동 시뮬레이션 시작';
        autoBtn.classList.remove('active');
    }

    const playOnceBtn = document.getElementById('play-once-btn');
    if (playOnceBtn) {
        playOnceBtn.disabled = state.isPlaying || state.isAutoMode;
    }
}

function adjustBet(amount) {
    if (state.isPlaying) return;
    const nextBet = state.currentBet + amount;
    if (nextBet >= 10000 && nextBet <= state.money) {
        state.currentBet = nextBet;
        updateUI();
    }
}

function updateSpeed(val) {
    const sliderVal = parseInt(val);
    state.speed = Math.floor(1000 / sliderVal);
    document.getElementById('speed-val').textContent = sliderVal + 'x';
}

function initReels() {
    for (let i = 1; i <= 3; i++) {
        const strip = document.getElementById(`strip-${i}`);
        strip.innerHTML = '';
        for (let j = 0; j < REEL_SYMBOL_COUNT; j++) {
            const sym = SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)];
            const div = document.createElement('div');
            div.className = `symbol ${sym.name === 'JACKPOT' ? 'jackpot' : ''}`;
            div.innerHTML = sym.name === 'JACKPOT' ? '광진<br>랜드' : sym.icon;
            strip.appendChild(div);
        }
    }
}

async function spin() {
    if (state.isPlaying) return;
    if (state.money < state.currentBet) {
        state.isAutoMode = false;
        showBankruptcy();
        updateUI();
        return;
    }

    state.isPlaying = true;
    state.money -= state.currentBet;
    state.totalBetAmount += state.currentBet;
    state.totalRounds++;
    updateUI();

    const isFast = state.speed <= 250;

    // 1. Determine Result Logic (RTP 94%)
    const roll = Math.random();
    let winSym = null;
    let resultSymbols = [];

    // Winning probabilities to achieve 94% RTP
    if (roll < 0.0005) winSym = SYMBOLS.find(s => s.name === 'JACKPOT'); // 500x
    else if (roll < 0.0025) winSym = SYMBOLS.find(s => s.name === 'SEVEN'); // 100x
    else if (roll < 0.0125) winSym = SYMBOLS.find(s => s.name === 'BAR');   // 25x
    else if (roll < 0.0365) winSym = SYMBOLS.find(s => s.name === 'CHERRY'); // 10x

    if (winSym) {
        resultSymbols = [winSym, winSym, winSym];
        state.currentLossStreak = 0;
        document.getElementById('game-message').textContent = "스핀 중...";
    } else {
        // Loss. 40% chance of "Near Miss"
        const nearMissRoll = Math.random();
        if (nearMissRoll < 0.4) {
            const pool = SYMBOLS.map(s => s);
            const lucky = pool[Math.floor(Math.random() * pool.length)];
            const fail = pool.filter(s => s.name !== lucky.name)[Math.floor(Math.random() * (pool.length - 1))];
            resultSymbols = [lucky, lucky, fail];
            // Message will be set after animation
        } else {
            resultSymbols = [
                SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)],
                SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)],
                SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)]
            ];
            // Safety: check if it accidentally won
            if (resultSymbols[0].name === resultSymbols[1].name && resultSymbols[1].name === resultSymbols[2].name) {
                const fail = SYMBOLS.filter(s => s.name !== resultSymbols[0].name)[0];
                resultSymbols[2] = fail;
            }
        }
        state.currentLossStreak++;
        if (state.currentLossStreak > state.maxLossStreak) state.maxLossStreak = state.currentLossStreak;
        document.getElementById('game-message').textContent = "스핀 중...";
    }

    // 2. Animation Logic
    if (!isFast) {
        const promises = [];
        for (let i = 1; i <= 3; i++) {
            const strip = document.getElementById(`strip-${i}`);
            // Place result symbol at index 1 (to be center of 3x3)
            // But to animate properly, we scroll TO it.
            // Let's redo the strip content to show result at a specific stop.
            const targetSymbol = resultSymbols[i - 1];

            // Randomly fill the end of the strip
            const children = strip.children;
            const targetIndex = REEL_SYMBOL_COUNT - 3; // Stop near the end
            const targetDiv = children[targetIndex + 1]; // Offset 1 for center
            targetDiv.className = `symbol ${targetSymbol.name === 'JACKPOT' ? 'jackpot' : ''}`;
            targetDiv.innerHTML = targetSymbol.name === 'JACKPOT' ? '광진<br>랜드' : targetSymbol.icon;

            strip.style.transition = 'none';
            strip.style.transform = 'translateY(0)';
            strip.offsetHeight;

            strip.style.transition = `transform ${0.8 + i * 0.4}s cubic-bezier(0.45, 0.05, 0.55, 1.05)`;
            strip.style.transform = `translateY(-${targetIndex * 100}px)`;

            promises.push(new Promise(resolve => setTimeout(resolve, (0.8 + i * 0.4) * 1000)));
        }
        await Promise.all(promises);
    } else {
        // Instant
        for (let i = 1; i <= 3; i++) {
            const strip = document.getElementById(`strip-${i}`);
            strip.style.transition = 'none';
            strip.style.transform = `translateY(-${(REEL_SYMBOL_COUNT - 3) * 100}px)`;
            const targetDiv = strip.children[REEL_SYMBOL_COUNT - 2];
            targetDiv.className = `symbol ${resultSymbols[i - 1].name === 'JACKPOT' ? 'jackpot' : ''}`;
            targetDiv.innerHTML = resultSymbols[i - 1].name === 'JACKPOT' ? '광진<br>랜드' : resultSymbols[i - 1].icon;
        }
    }

    // 3. Payout and Final Message
    if (winSym) {
        const payout = state.currentBet * winSym.payout;
        state.money += payout;
        state.totalPayout += payout;
        const msg = `${winSym.name} 잭팟! +${payout.toLocaleString()}원`;
        document.getElementById('game-message').textContent = msg;
        CasinoLogger.add(msg, 'var(--gold)');
    } else {
        state.houseProfit += state.currentBet;
        if (resultSymbols[0].name === resultSymbols[1].name) {
            const msg = "아... 아깝습니다! (Near Miss)";
            document.getElementById('game-message').textContent = msg;
            CasinoLogger.add(msg, '#aaa');
        } else {
            const msg = "다음 기회에...";
            document.getElementById('game-message').textContent = msg;
            CasinoLogger.add(msg, '#666');
        }
    }

    // 4. State Update
    if (state.money > state.peakBalance) state.peakBalance = state.money;
    state.labels.push(state.totalRounds);
    state.balanceHistory.push(state.money);
    if (state.labels.length > 50) {
        state.labels.shift();
        state.balanceHistory.shift();
    }
    state.chart.update('none');
    updateAnalysis();
    updateUI();

    state.isPlaying = false;
    CasinoStorage.saveState({
        money: state.money,
        totalRounds: state.totalRounds,
        houseProfit: state.houseProfit,
        peakBalance: state.peakBalance
    });

    if (state.money <= 0) {
        state.isAutoMode = false;
        showBankruptcy();
    } else if (state.isAutoMode) {
        const isBatterySaving = localStorage.getItem('battery_saving') === 'true';
        const delay = isBatterySaving ? (isFast ? 150 : state.speed * 1.5) : (isFast ? 50 : state.speed);
        setTimeout(spin, delay);
    }
}

function updateAnalysis() {
    const actualRTP = state.totalBetAmount > 0 ? (state.totalPayout / state.totalBetAmount * 100).toFixed(1) : "0.0";
    document.getElementById('rtp-bar').style.width = Math.min(actualRTP, 100) + '%';
    document.getElementById('rtp-text').textContent = `RTP: ${actualRTP}%`;
    document.getElementById('max-losses').textContent = state.maxLossStreak;

    const netProfit = state.money - state.initialMoney;
    const roi = state.totalBetAmount > 0 ? (netProfit / state.totalBetAmount * 100).toFixed(1) : "0.0";
    const roiEl = document.getElementById('roi-display');
    roiEl.textContent = (roi > 0 ? "+" : "") + roi + "%";
    roiEl.style.color = roi >= 0 ? "#4caf50" : "var(--neon-red)";
}

function toggleAuto() {
    if (state.money <= 0) return;
    state.isAutoMode = !state.isAutoMode;
    if (state.isAutoMode && !state.isPlaying) spin();
    updateUI();
}

function showBankruptcy() {
    document.getElementById('bankruptcy-modal').classList.remove('hidden');
}

function refill() {
    state.money = state.initialMoney;
    state.totalRounds = 0;
    state.houseProfit = 0;
    state.peakBalance = state.initialMoney;
    state.labels = [];
    state.balanceHistory = [];
    state.totalBetAmount = 0;
    state.totalPayout = 0;
    state.currentLossStreak = 0;
    state.maxLossStreak = 0;
    state.chart.update();
    document.getElementById('bankruptcy-modal').classList.add('hidden');
    updateAnalysis();
    updateUI();
    initReels();
}

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

window.onload = () => {
    initChart();
    initReels();
    updateUI();
    initGestures();
};

function initGestures() {
    const container = document.querySelector('.slot-machine-container');
    let startY = 0;

    container.addEventListener('touchstart', (e) => {
        startY = e.touches[0].pageY;
    }, { passive: true });

    container.addEventListener('touchend', (e) => {
        const endY = e.changedTouches[0].pageY;
        const dist = endY - startY;

        if (dist > 50 && !state.isPlaying && !state.isAutoMode) {
            // Swipe Down detected
            spin();
            if (window.navigator && window.navigator.vibrate) {
                window.navigator.vibrate([20, 10, 20]);
            }
        }
    }, { passive: true });
}
