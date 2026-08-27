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
    speed: 1000,
    speedMode: 1, // 1, 2, 5, 0(Instant)
    chart: null,
    labels: [],
    balanceHistory: [],
    // Keno specific
    selectedNumbers: new Set(),
    drawnNumbers: [],
    maxMatch: 0,
    totalMatches: 0,
    totalBetAmount: 0,
};

// Payout Table (Catch count vs selection size)
const PAYOUTS = {
    1: { 1: 3 },
    2: { 1: 1, 2: 9 },
    3: { 2: 2, 3: 16 },
    4: { 2: 1, 3: 10, 4: 50 },
    5: { 3: 3, 4: 15, 5: 350 },
    6: { 3: 1, 4: 10, 5: 50, 6: 1200 },
    7: { 4: 2, 5: 15, 6: 150, 7: 3000 },
    8: { 5: 10, 6: 50, 7: 400, 8: 10000 },
    9: { 5: 5, 6: 25, 7: 150, 8: 1500, 9: 25000 },
    10: { 5: 2, 6: 15, 7: 40, 8: 150, 9: 1000, 10: 50000 }
};

// Theoretical Edge (Approximate based on selection count)
const HOUSE_EDGE = {
    1: 25.0, 2: 25.5, 3: 26.2, 4: 25.8, 5: 27.1,
    6: 28.5, 7: 29.3, 8: 30.1, 9: 30.5, 10: 31.2
};

function initGrid() {
    const grid = document.getElementById('keno-grid');
    grid.innerHTML = '';
    for (let i = 1; i <= 80; i++) {
        const cell = document.createElement('div');
        cell.className = 'keno-cell';
        cell.textContent = i;
        cell.dataset.num = i;

        // Drag select support
        cell.addEventListener('mousedown', () => toggleNumber(i));
        cell.addEventListener('mouseover', (e) => {
            if (e.buttons === 1) toggleNumber(i, true);
        });

        // Touch select support
        cell.addEventListener('touchstart', (e) => {
            e.preventDefault();
            toggleNumber(i);
        }, { passive: false });

        grid.appendChild(cell);
    }
}

function toggleNumber(num, isDrag = false) {
    if (state.isPlaying) return;
    if (state.selectedNumbers.has(num)) {
        if (!isDrag) {
            state.selectedNumbers.delete(num);
            vibrate(10);
        }
    } else {
        if (state.selectedNumbers.size < 10) {
            state.selectedNumbers.add(num);
            vibrate(10);
        }
    }
    updateBoardUI();
}

function updateBoardUI() {
    const cells = document.querySelectorAll('.keno-cell');
    cells.forEach(cell => {
        const n = parseInt(cell.dataset.num);
        cell.classList.toggle('selected', state.selectedNumbers.has(n));
        cell.classList.remove('draw', 'hit');
    });

    document.getElementById('sel-count').textContent = state.selectedNumbers.size;
    renderPayoutTable();
    updateAnalysis();
}

function renderPayoutTable() {
    const container = document.getElementById('payout-table');
    container.innerHTML = '';
    const selCount = state.selectedNumbers.size;
    if (selCount === 0) return;

    const table = PAYOUTS[selCount];
    Object.keys(table).forEach(match => {
        const item = document.createElement('div');
        item.className = 'payout-item';
        item.innerHTML = `<span class="payout-match">${match} Hits</span><span class="payout-odd">${table[match]}x</span>`;
        container.appendChild(item);
    });
}

function quickPick() {
    if (state.isPlaying) return;
    state.selectedNumbers.clear();
    while (state.selectedNumbers.size < 10) {
        state.selectedNumbers.add(Math.floor(Math.random() * 80) + 1);
    }
    updateBoardUI();
}

function clearSelection() {
    if (state.isPlaying) return;
    state.selectedNumbers.clear();
    updateBoardUI();
}

function updateSpeed(mode) {
    state.speedMode = mode;
    document.querySelectorAll('.speed-btns button').forEach((btn, idx) => {
        const btnMode = [1, 2, 5, 0][idx];
        btn.classList.toggle('active', btnMode === mode);
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

    const autoBtn = document.getElementById('auto-btn');
    autoBtn.textContent = state.isAutoMode ? '시뮬레이션 중지' : '자동 시뮬레이션 시작';
    autoBtn.classList.toggle('active', state.isAutoMode);

    const playOnceBtn = document.getElementById('play-once-btn');
    if (playOnceBtn) {
        playOnceBtn.disabled = state.isPlaying || state.isAutoMode || state.selectedNumbers.size === 0;
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

async function playRound() {
    if (state.isPlaying || state.selectedNumbers.size === 0) return;
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

    // Reset board visuals for new draw
    const cells = Array.from(document.querySelectorAll('.keno-cell'));
    cells.forEach(c => c.classList.remove('draw', 'hit'));

    // Draw 20 numbers
    const pool = Array.from({ length: 80 }, (_, i) => i + 1);
    state.drawnNumbers = [];
    for (let i = 0; i < 20; i++) {
        const idx = Math.floor(Math.random() * pool.length);
        state.drawnNumbers.push(pool.splice(idx, 1)[0]);
    }

    let matches = 0;
    if (state.speedMode === 0) { // Instant
        state.drawnNumbers.forEach(num => {
            const cell = cells[num - 1];
            cell.classList.add('draw');
            if (state.selectedNumbers.has(num)) {
                cell.classList.add('hit');
                matches++;
            }
        });
    } else {
        const drawDelay = 1000 / (state.speedMode * 4); // Delay per ball
        for (const num of state.drawnNumbers) {
            const cell = cells[num - 1];
            cell.classList.add('draw');
            if (state.selectedNumbers.has(num)) {
                cell.classList.add('hit');
                matches++;
                vibrate(20);
            }
            await sleep(drawDelay);
        }
    }

    // Process Result
    const selCount = state.selectedNumbers.size;
    const table = PAYOUTS[selCount];
    const odd = table[matches] || 0;
    const payout = state.currentBet * odd;

    if (payout > 0) {
        state.money += payout;
        const msg = `${matches}개 적중! ${payout.toLocaleString()}원 획득 (${odd}배)`;
        document.getElementById('game-message').textContent = msg;
        CasinoLogger.add(msg, '#4caf50');
    } else {
        state.houseProfit += state.currentBet;
        document.getElementById('game-message').textContent = `${matches}개 적중. 꽝입니다.`;
        CasinoLogger.add(`${matches}개 적중. 꽝.`, '#666');
    }

    // Stats
    if (matches > state.maxMatch) state.maxMatch = matches;
    state.totalMatches += matches;

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
        const delay = state.speedMode === 0 ? 100 : 800;
        setTimeout(autoTick, delay);
    }
}

function autoTick() {
    if (!state.isAutoMode || state.money < state.currentBet) return;
    if (state.selectedNumbers.size === 0) quickPick();
    if (!state.isPlaying) playRound();
}

function updateAnalysis() {
    const selCount = state.selectedNumbers.size;
    const edge = selCount > 0 ? HOUSE_EDGE[selCount] : 0;
    const evEl = document.getElementById('theoretical-ev');
    evEl.textContent = `-${edge}%`;

    document.getElementById('max-match').textContent = state.maxMatch;
    const avg = state.totalRounds > 0 ? (state.totalMatches / state.totalRounds).toFixed(1) : "0.0";
    document.getElementById('avg-match').textContent = avg;

    const netProfit = state.money - state.initialMoney;
    const roi = state.totalBetAmount > 0 ? (netProfit / state.totalBetAmount * 100).toFixed(1) : "0.0";
    const roiEl = document.getElementById('roi-display');
    roiEl.textContent = (roi > 0 ? "+" : "") + roi + "%";
    roiEl.style.color = roi >= 0 ? "#4caf50" : "var(--neon-red)";
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
    state.maxMatch = 0;
    state.totalMatches = 0;
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
    updateBoardUI();
}

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
function vibrate(pattern) {
    if (window.navigator && window.navigator.vibrate) {
        window.navigator.vibrate(pattern);
    }
}

window.onload = () => {
    initGrid();
    initChart();
    updateUI();
    updateSpeed(1);
};
