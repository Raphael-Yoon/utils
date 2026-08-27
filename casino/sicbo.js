const savedState = CasinoStorage.getCombinedState();
const state = {
    money: savedState.money,
    initialMoney: savedState.initialMoney,
    currentBet: 10000,
    betSide: 'SMALL',
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
    bigWins: 0,
    smallWins: 0,
    tripleCount: 0,
    totalBetAmount: 0
};

function initChart() {
    const ctx = document.getElementById('assetChart').getContext('2d');
    state.chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: state.labels,
            datasets: [{
                label: '보유 자산',
                data: state.balanceHistory,
                borderColor: '#2196f3',
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

    document.querySelectorAll('.bet-spot').forEach(s => s.classList.remove('active'));
    document.getElementById(`bet-${state.betSide.toLowerCase()}`).classList.add('active');

    const autoBtn = document.getElementById('auto-btn');
    if (state.isAutoMode) {
        autoBtn.textContent = '시뮬레이션 중지';
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

function selectBet(side) {
    if (state.isPlaying) return;
    state.betSide = side;
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

async function playRound() {
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

    const isFast = state.speed <= 150; // Adjusted threshold
    const cup = document.getElementById('dice-cup');
    const diceElements = [
        document.getElementById('dice-1'),
        document.getElementById('dice-2'),
        document.getElementById('dice-3')
    ];

    if (!isFast) {
        cup.classList.add('shaking');
        diceElements.forEach(el => el.classList.add('rolling'));
        document.getElementById('game-message').textContent = "주사위를 흔드는 중...";

        // Show random numbers while shaking
        const rollInterval = setInterval(() => {
            diceElements.forEach(el => {
                el.textContent = Math.floor(Math.random() * 6) + 1;
            });
        }, 100);

        await sleep(state.speed * 2);

        clearInterval(rollInterval);
        cup.classList.remove('shaking');
        diceElements.forEach(el => el.classList.remove('rolling'));
    }

    const d1 = Math.floor(Math.random() * 6) + 1;
    const d2 = Math.floor(Math.random() * 6) + 1;
    const d3 = Math.floor(Math.random() * 6) + 1;
    const sum = d1 + d2 + d3;
    const isTriple = (d1 === d2 && d2 === d3);

    // Set final values with pop animation
    diceElements[0].textContent = d1;
    diceElements[1].textContent = d2;
    diceElements[2].textContent = d3;

    if (!isFast) {
        diceElements.forEach(el => {
            el.classList.add('pop');
            setTimeout(() => el.classList.remove('pop'), 400);
        });
    }

    let result = '';
    if (isTriple) {
        result = 'TRIPLE';
        state.tripleCount++;
    } else if (sum >= 11) {
        result = 'BIG';
        state.bigWins++;
    } else {
        result = 'SMALL';
        state.smallWins++;
    }

    const win = (state.betSide === result);
    let msg = `결과: ${sum}점 (${result})`;
    if (isTriple) msg = `결과: 트리플 ${d1}! (하우스 승리)`;

    if (win) {
        state.money += state.currentBet * 2;
        document.getElementById('game-message').textContent = `${msg} - 승리!`;
        CasinoLogger.add(`${msg} - 승리!`, '#4caf50');
    } else {
        state.houseProfit += state.currentBet;
        document.getElementById('game-message').textContent = `${msg} - 패배`;
        CasinoLogger.add(`${msg} - 패배`, '#ff3131');
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
        peakBalance: state.peakBalance,
        totalBetAmount: state.totalBetAmount
    });

    if (state.money < state.currentBet) {
        state.isAutoMode = false;
        showBankruptcy();
        updateUI();
    } else if (state.isAutoMode) {
        const isBatterySaving = localStorage.getItem('battery_saving') === 'true';
        const delay = isBatterySaving ? (isFast ? 150 : state.speed * 1.5) : (isFast ? 50 : state.speed);
        setTimeout(autoTick, delay);
    }
}

function autoTick() {
    if (!state.isAutoMode || state.money < state.currentBet) return;
    if (!state.isPlaying) playRound();
}

function toggleAuto() {
    if (state.money < state.currentBet && !state.isAutoMode) {
        showBankruptcy();
        return;
    }
    state.isAutoMode = !state.isAutoMode;
    if (state.isAutoMode) autoTick();
    updateUI();
}

function updateAnalysis() {
    const totalValid = state.bigWins + state.smallWins;
    if (totalValid > 0) {
        const bigRate = (state.bigWins / totalValid * 100).toFixed(1);
        const smallRate = (state.smallWins / totalValid * 100).toFixed(1);
        document.getElementById('big-rate-bar').style.width = bigRate + '%';
        document.getElementById('small-rate-bar').style.width = smallRate + '%';
        document.getElementById('big-rate-text').textContent = `大: ${bigRate}%`;
        document.getElementById('small-rate-text').textContent = `小: ${smallRate}%`;
    }

    document.getElementById('triple-count').textContent = state.tripleCount;

    const netProfit = state.money - state.initialMoney;
    const roi = state.totalBetAmount > 0 ? (netProfit / state.totalBetAmount * 100).toFixed(1) : "0.0";
    const roiEl = document.getElementById('roi-display');
    roiEl.textContent = (roi > 0 ? "+" : "") + roi + "%";
    roiEl.style.color = roi >= 0 ? "#4caf50" : "var(--neon-red)";
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
    state.bigWins = 0;
    state.smallWins = 0;
    state.tripleCount = 0;
    state.totalBetAmount = 0;
    state.chart.update();
    document.getElementById('bankruptcy-modal').classList.add('hidden');

    // Persist the refill immediately
    CasinoStorage.saveState({
        money: state.money,
        totalRounds: 0,
        houseProfit: 0,
        totalBetAmount: 0
    });

    updateAnalysis();
    updateUI();
}

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

window.onload = () => {
    initChart();
    updateUI();
};
