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
    isTurbo: false,
    speed: 600,
    chart: null,
    labels: [],
    balanceHistory: [],
    // Analysis Stats
    winCount: 0,
    lossCount: 0,
    drawCount: 0,
    totalBetAmount: 0,
    totalWarCount: 0,
    totalWarWins: 0,
    isTieSituation: false
};

const SUITS = ['♠', '♥', '♣', '♦'];
const VALUES = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'];
const VALUE_MAP = { '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14 };

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
    document.getElementById('pot-amount').textContent = state.currentBet.toLocaleString();

    const autoBtn = document.getElementById('auto-btn');
    autoBtn.textContent = state.isAutoMode ? '시뮬레이션 중지' : '자동 시뮬레이션 시작';
    autoBtn.classList.toggle('active', state.isAutoMode);

    const playOnceBtn = document.getElementById('play-once-btn');
    if (playOnceBtn) {
        playOnceBtn.disabled = state.isPlaying || state.isAutoMode || state.isTieSituation;
    }
}

function adjustBet(amount) {
    if (state.isPlaying || state.isTieSituation) return;
    const nextBet = state.currentBet + amount;
    if (nextBet >= 10000 && nextBet <= state.money) {
        state.currentBet = nextBet;
        updateUI();
    }
}

// Tap & Hold logic
let holdTimer = null;
function startHold(amount) {
    adjustBet(amount);
    holdTimer = setInterval(() => adjustBet(amount), 150);
}
function stopHold() {
    if (holdTimer) clearInterval(holdTimer);
}

function toggleTurbo(checked) {
    state.isTurbo = checked;
}

function getRandomCard() {
    const suit = SUITS[Math.floor(Math.random() * SUITS.length)];
    const value = VALUES[Math.floor(Math.random() * VALUES.length)];
    return { suit, value, score: VALUE_MAP[value], isRed: (suit === '♥' || suit === '♦') };
}

function createCardUI(card) {
    const div = document.createElement('div');
    div.className = `card ${card.isRed ? 'red' : ''}`;
    div.innerHTML = `
        <div class="card-top">${card.value}${card.suit}</div>
        <div class="card-mid">${card.suit}</div>
        <div class="card-bot">${card.value}${card.suit}</div>
    `;
    return div;
}

async function deal() {
    if (state.isPlaying || state.isTieSituation) return;
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

    const dArea = document.getElementById('dealer-cards');
    const pArea = document.getElementById('player-cards');
    dArea.innerHTML = '';
    pArea.innerHTML = '';
    document.getElementById('war-pot').classList.add('hidden');

    const dCard = getRandomCard();
    const pCard = getRandomCard();

    if (!state.isTurbo) {
        document.getElementById('game-message').textContent = "딜링 중...";
        await sleep(400);
        dArea.appendChild(createCardUI(dCard));
        await sleep(400);
        pArea.appendChild(createCardUI(pCard));
        await sleep(400);
    } else {
        dArea.appendChild(createCardUI(dCard));
        pArea.appendChild(createCardUI(pCard));
    }

    if (pCard.score > dCard.score) {
        handleWin();
    } else if (dCard.score > pCard.score) {
        handleLoss();
    } else {
        handleTie();
    }
}

function handleWin() {
    const payout = state.currentBet * 2;
    state.money += payout;
    state.winCount++;
    const msg = "플레이어 승리! + " + state.currentBet.toLocaleString() + "원";
    document.getElementById('game-message').textContent = msg;
    CasinoLogger.add(msg, '#4caf50');
    vibrate(20);
    finishRound();
}

function handleLoss() {
    state.lossCount++;
    state.houseProfit += state.currentBet;
    const msg = "딜러 승리. 베팅금을 잃었습니다.";
    document.getElementById('game-message').textContent = msg;
    CasinoLogger.add(msg, '#ff3131');
    finishRound();
}

function handleTie() {
    state.drawCount++;
    state.isTieSituation = true;
    document.getElementById('game-message').textContent = "무승부! 전쟁을 하시겠습니까?";
    document.getElementById('tie-overlay').classList.remove('hidden');

    if (state.isAutoMode) {
        // AI Auto Decision: Always War (Mathematically worse but makes for better simulation)
        setTimeout(() => go2War(), 800);
    }
}

async function surrender() {
    state.isTieSituation = false;
    document.getElementById('tie-overlay').classList.add('hidden');
    const loss = state.currentBet / 2;
    state.money += loss; // Return half
    state.houseProfit += loss;
    const msg = "항복! 베팅금의 절반을 잃었습니다.";
    document.getElementById('game-message').textContent = msg;
    CasinoLogger.add(msg, '#aaa');
    finishRound();
}

async function go2War() {
    document.getElementById('tie-overlay').classList.add('hidden');
    if (state.money < state.currentBet) {
        CasinoLogger.add("전쟁을 위한 추가 자산이 부족하여 강제 항복합니다.", '#ff9800');
        surrender();
        return;
    }

    state.totalWarCount++;
    state.money -= state.currentBet;
    state.totalBetAmount += state.currentBet;
    document.getElementById('war-amount').textContent = state.currentBet.toLocaleString();
    document.getElementById('war-pot').classList.remove('hidden');
    updateUI();

    const dArea = document.getElementById('dealer-cards');
    const pArea = document.getElementById('player-cards');

    if (!state.isTurbo) {
        document.getElementById('game-message').textContent = "전쟁 시작! 카드 3장을 버립니다...";
        await sleep(800);
    }

    const dFinal = getRandomCard();
    const pFinal = getRandomCard();

    if (!state.isTurbo) {
        dArea.appendChild(createCardUI(dFinal));
        pArea.appendChild(createCardUI(pFinal));
        await sleep(600);
    } else {
        dArea.appendChild(createCardUI(dFinal));
        pArea.appendChild(createCardUI(pFinal));
    }

    if (pFinal.score >= dFinal.score) { // Tie in war usually counts as player win in many casinos
        state.totalWarWins++;
        state.money += (state.currentBet * 3); // Return original(1) + raise(1) + payout on raise(1)
        const msg = "전쟁 승리! 추가 배팅금의 이익을 얻었습니다.";
        document.getElementById('game-message').textContent = msg;
        CasinoLogger.add(msg, '#ffd700');
        vibrate([50, 30, 50]);
    } else {
        state.houseProfit += (state.currentBet * 2);
        const msg = "전쟁 패배... 모든 배팅금을 잃었습니다.";
        document.getElementById('game-message').textContent = msg;
        CasinoLogger.add(msg, '#ff3131');
    }

    state.isTieSituation = false;
    finishRound();
}

function finishRound() {
    state.isPlaying = false;
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
        const delay = state.isTurbo ? 50 : state.speed;
        setTimeout(autoTick, delay);
    }
}

function autoTick() {
    if (!state.isAutoMode || state.money < state.currentBet) return;
    if (state.isTieSituation) {
        go2War();
    } else if (!state.isPlaying) {
        deal();
    }
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
    const totalWins = state.winCount + state.totalWarWins;
    const winRate = state.totalRounds > 0 ? (totalWins / state.totalRounds * 100).toFixed(1) : "0.0";
    document.getElementById('win-rate-bar').style.width = Math.min(winRate, 100) + '%';
    document.getElementById('win-rate-text').textContent = `Win: ${winRate}%`;
    document.getElementById('draw-count').textContent = `Tie: ${state.drawCount}회`;

    const warRatio = state.drawCount > 0 ? (state.totalWarCount / state.drawCount * 100).toFixed(0) : "0";
    document.getElementById('war-ratio').textContent = `${warRatio}%`;

    // War ROI (Profit from War / Total Amount bet in War)
    const warProfit = (state.totalWarWins * state.currentBet) - ((state.totalWarCount - state.totalWarWins) * state.currentBet * 2);
    const warInvest = state.totalWarCount * state.currentBet * 2;
    const warROI = warInvest > 0 ? (warProfit / warInvest * 100).toFixed(1) : "0.0";
    const warRoiEl = document.getElementById('war-roi');
    warRoiEl.textContent = `${warROI}%`;

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
    state.winCount = 0;
    state.lossCount = 0;
    state.drawCount = 0;
    state.totalBetAmount = 0;
    state.totalWarCount = 0;
    state.totalWarWins = 0;
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
function vibrate(pattern) {
    if (window.navigator && window.navigator.vibrate) {
        window.navigator.vibrate(pattern);
    }
}

window.onload = () => {
    initChart();
    updateUI();
};
