const CONFIG = [
    { label: 1, payout: 1, count: 24, color: '#333' },
    { label: 2, payout: 2, count: 15, color: '#2196f3' },
    { label: 5, payout: 5, count: 7, color: '#4caf50' },
    { label: 10, payout: 10, count: 4, color: '#ff9800' },
    { label: 20, payout: 20, count: 2, color: '#ff5722' },
    { label: 40, payout: 40, count: 2, color: '#ffc107' } // We will adjust the total segments to make this hit high edge
];

// Re-adjusting to 54 standard pockets
// 1: 24 seg (11.1% Edge)
// 2: 15 seg (16.7% Edge)
// 5: 7 seg (22.2% Edge)
// 10: 4 seg (18.5% Edge)
// 20: 2 seg (22.2% Edge)
// 40: 1 seg (24.1% Edge) - Let's use 1 Joker and 1 Logo, each paying 40:1
const SEGMENT_DATA = [
    { label: 1, payout: 1, count: 24, color: '#333' },
    { label: 2, payout: 2, count: 15, color: '#2196f3' },
    { label: 5, payout: 5, count: 7, color: '#4caf50' },
    { label: 10, payout: 10, count: 4, color: '#ff9800' },
    { label: 20, payout: 20, count: 2, color: '#ff5722' },
    { label: 40, payout: 40, count: 1, color: '#ffc107' }, // Joker
    { label: 40, payout: 40, count: 1, color: '#ffc107' }  // Logo (Both count as 40 for the bet)
];

let SEGMENTS = [];
SEGMENT_DATA.forEach(c => {
    for (let i = 0; i < c.count; i++) SEGMENTS.push(c);
});
// Shuffle
SEGMENTS.sort(() => Math.random() - 0.5);

const savedState = CasinoStorage.getCombinedState();
const state = {
    money: savedState.money,
    initialMoney: savedState.initialMoney,
    currentBet: 10000,
    betSide: 1,
    isPlaying: false,
    totalRounds: savedState.totalRounds,
    houseProfit: savedState.houseProfit,
    peakBalance: savedState.peakBalance,
    isAutoMode: false,
    speed: 500,
    chart: null,
    labels: [],
    balanceHistory: [],
    rotation: 0,
    stats: { 1: 0, 2: 0, 5: 0, 10: 0, 20: 0, 40: 0 },
    totalBetAmount: 0
};

function initWheel() {
    const wheel = document.getElementById('big-wheel');
    wheel.innerHTML = '';
    const step = 360 / SEGMENTS.length;
    SEGMENTS.forEach((seg, i) => {
        const div = document.createElement('div');
        div.className = 'segment';
        div.style.transform = `rotate(${i * step}deg) skewY(${90 - step}deg)`;
        div.style.backgroundColor = seg.color;

        const span = document.createElement('span');
        span.textContent = seg.label;
        span.style.transform = `skewY(-${90 - step}deg) rotate(${step / 2}deg)`;
        span.style.position = 'absolute';
        span.style.top = '15px';
        div.appendChild(span);

        wheel.appendChild(div);
    });
}

function initChart() {
    const ctx = document.getElementById('assetChart').getContext('2d');
    state.chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: state.labels,
            datasets: [{
                label: '보유 자산',
                data: state.balanceHistory,
                borderColor: '#e91e63',
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
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#888', font: { size: 10 } } }
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

    document.querySelectorAll('.bet-item').forEach(btn => {
        const val = parseInt(btn.textContent.split(' ')[0]);
        btn.classList.toggle('active', val === state.betSide);
    });

    const autoBtn = document.getElementById('auto-btn');
    autoBtn.textContent = state.isAutoMode ? '시뮬레이션 중지' : '자동 시뮬레이션 시작';
    autoBtn.classList.toggle('active', state.isAutoMode);

    const playOnceBtn = document.getElementById('play-once-btn');
    if (playOnceBtn) {
        playOnceBtn.disabled = state.isPlaying || state.isAutoMode;
    }
}

function selectBet(val) {
    if (state.isPlaying) return;
    state.betSide = val;
    updateUI();
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
    const wheel = document.getElementById('big-wheel');

    const luckyIndex = Math.floor(Math.random() * SEGMENTS.length);
    const step = 360 / SEGMENTS.length;

    // Calculate rotation to land with current luckyIndex at the TOP (pin is at -90deg or 0deg depending on CSS)
    // CSS Pin is at top (0deg). Wheel rotation 0 means index 0 is at 12 o'clock if not skewed.
    // Actually, skew makes it tricky. Let's just use absolute index.
    const extraRot = 360 * 5;
    const targetRot = (SEGMENTS.length - luckyIndex) * step;
    state.rotation += extraRot + targetRot - (state.rotation % 360);

    if (!isFast) {
        wheel.style.transition = `transform ${state.speed * 6}ms cubic-bezier(0.15, 0, 0.15, 1)`;
        wheel.style.transform = `rotate(${state.rotation}deg)`;
        document.getElementById('game-message').textContent = "행운의 휠이 돌아갑니다...";
        await sleep(state.speed * 6);
    } else {
        wheel.style.transition = 'none';
        wheel.style.transform = `rotate(${state.rotation}deg)`;
    }

    const res = SEGMENTS[luckyIndex];
    state.stats[res.label]++;
    const won = (state.betSide === res.label);

    if (won) {
        const payout = state.currentBet * (res.payout + 1);
        state.money += payout;
        const msg = `결과: ${res.label}번! 🎉 +${payout.toLocaleString()}원 당첨!`;
        document.getElementById('game-message').textContent = msg;
        CasinoLogger.add(msg, 'var(--gold)');
    } else {
        state.houseProfit += state.currentBet;
        const msg = `결과: ${res.label}번 - 아쉽네요. 다음 기회에!`;
        document.getElementById('game-message').textContent = msg;
        CasinoLogger.add(msg, '#666');
    }

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
    updateUI();

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
    const list = document.getElementById('freq-list');
    list.innerHTML = '';
    [1, 2, 5, 10, 20, 40].forEach(label => {
        const div = document.createElement('div');
        div.className = 'freq-item';
        div.innerHTML = `<span>${label}번</span><span>${state.stats[label]}회</span>`;
        list.appendChild(div);
    });

    const netProfit = state.money - state.initialMoney;
    const roi = state.totalBetAmount > 0 ? (netProfit / state.totalBetAmount * 100).toFixed(1) : "0.0";

    const target = SEGMENT_DATA.find(c => c.label === state.betSide);
    const totalCount = SEGMENTS.length;
    const theoreticalProb = (target.count) / totalCount;
    const theoreticalEdge = (1 - (theoreticalProb * (target.payout + 1))) * 100;

    document.getElementById('edge-value').textContent = theoreticalEdge.toFixed(1) + '%';

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
    Object.keys(state.stats).forEach(k => state.stats[k] = 0);
    state.totalBetAmount = 0;
    state.chart.update();
    document.getElementById('bankruptcy-modal').classList.add('hidden');
    updateAnalysis();
    updateUI();
}

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

window.onload = () => {
    initWheel();
    initChart();
    updateUI();
};
