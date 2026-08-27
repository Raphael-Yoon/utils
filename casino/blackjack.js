const savedState = CasinoStorage.getCombinedState();
const state = {
    money: savedState.money,
    initialMoney: savedState.initialMoney,
    totalRounds: savedState.totalRounds,
    wins: 0,
    losses: 0,
    pushes: 0,
    playerBusts: 0,
    dealerBusts: 0,
    betAmount: 10000,
    houseProfit: savedState.houseProfit,
    peakBalance: savedState.peakBalance,
    isAutoMode: false,
    speed: 500, // ms
    deck: [],
    playerHand: [],
    dealerHand: [],
    isPlaying: false,
    chart: null,
    labels: [],
    balanceHistory: [],
    // Analysis Stats
    pWins: 0,
    dWins: 0,
    ties: 0,
    currentStreak: 0,
    maxWins: 0,
    maxLosses: 0,
    totalBetAmount: 0
};

const SUITS = ['♠', '♥', '♦', '♣'];
const VALUES = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];

function initDeck() {
    state.deck = [];
    for (let i = 0; i < 6; i++) { // 6-deck
        for (let suit of SUITS) {
            for (let value of VALUES) {
                state.deck.push({ suit, value });
            }
        }
    }
    shuffle(state.deck);
}

function shuffle(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}

function calculateScore(hand) {
    let score = 0;
    let aces = 0;
    for (let card of hand) {
        if (card.value === 'A') {
            aces += 1;
            score += 11;
        } else if (['J', 'Q', 'K'].includes(card.value)) {
            score += 10;
        } else {
            score += parseInt(card.value);
        }
    }
    while (score > 21 && aces > 0) {
        score -= 10;
        aces -= 1;
    }
    return score;
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
    document.getElementById('total-rounds').textContent = state.totalRounds;
    document.getElementById('house-profit').textContent = Math.floor(state.houseProfit).toLocaleString();
    document.getElementById('peak-balance').textContent = Math.floor(state.peakBalance).toLocaleString();
    document.getElementById('p-bust-count').textContent = state.playerBusts;
    document.getElementById('current-bet-display').textContent = state.betAmount.toLocaleString();

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

function addLog(msg, color = '#eee') {
    CasinoLogger.add(msg, color);
}

function adjustBet(amount) {
    if (state.isAutoMode) return;
    const nextBet = state.betAmount + amount;
    if (nextBet >= 10000 && nextBet <= state.money) {
        state.betAmount = nextBet;
        updateUI();
    }
}

function updateSpeed(val) {
    const sliderVal = parseInt(val);
    state.speed = Math.floor(1000 / sliderVal);
    document.getElementById('speed-val').textContent = sliderVal + 'x';
}

function renderHand(hand, containerId, scoreId, hideFirst = false) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    hand.forEach((card, index) => {
        const cardEl = document.createElement('div');
        const isRed = ['♥', '♦'].includes(card.suit);
        cardEl.className = `card ${isRed ? 'red' : ''}`;

        if (hideFirst && index === 0) {
            cardEl.style.background = 'linear-gradient(135deg, #1a2a3a, #000)';
            cardEl.style.border = '2px solid var(--gold)';
            cardEl.innerHTML = '<div style="height:100%; display:flex; align-items:center; justify-content:center; color:var(--gold)">?</div>';
        } else {
            cardEl.innerHTML = `<div>${card.value}</div><div style="font-size:2rem; text-align:center">${card.suit}</div><div style="transform:rotate(180deg)">${card.value}</div>`;
        }
        container.appendChild(cardEl);
    });

    const scoreVal = hideFirst ? '?' : calculateScore(hand);
    document.getElementById(scoreId).textContent = scoreVal;
}

async function playRound() {
    if (state.isPlaying) return;
    if (state.money < state.betAmount) {
        state.isAutoMode = false;
        showBankruptcy();
        updateUI();
        return;
    }

    const isFast = state.speed <= 250;
    try {
        state.isPlaying = true;
        state.money -= state.betAmount;
        state.totalRounds++;
        state.totalBetAmount += state.betAmount;

        // Clear previous cards
        document.getElementById('player-cards').innerHTML = '';
        document.getElementById('dealer-cards').innerHTML = '';

        if (state.deck.length < 20) initDeck();

        state.playerHand = [state.deck.pop(), state.deck.pop()];
        state.dealerHand = [state.deck.pop(), state.deck.pop()];

        renderHand(state.playerHand, 'player-cards', 'player-score');
        renderHand(state.dealerHand, 'dealer-cards', 'dealer-score', true);

        if (!isFast) await sleep(state.speed / 2);

        let pScore = calculateScore(state.playerHand);
        let dScore = calculateScore(state.dealerHand);
        let res = '';

        // Player Turn
        while (pScore < 17) {
            const card = state.deck.pop();
            state.playerHand.push(card);
            renderHand(state.playerHand, 'player-cards', 'player-score');
            pScore = calculateScore(state.playerHand);
            if (!isFast) await sleep(state.speed / 2);
            if (pScore > 21) break;
        }

        if (pScore > 21) {
            state.playerBusts++;
            state.losses++;
            state.houseProfit += state.betAmount;
            res = 'DEAL WIN';
        } else {
            // Dealer Turn
            renderHand(state.dealerHand, 'dealer-cards', 'dealer-score', false);
            if (!isFast) await sleep(state.speed / 2);
            dScore = calculateScore(state.dealerHand);

            while (dScore < 17) {
                const card = state.deck.pop();
                state.dealerHand.push(card);
                renderHand(state.dealerHand, 'dealer-cards', 'dealer-score');
                dScore = calculateScore(state.dealerHand);
                if (!isFast) await sleep(state.speed / 2);
            }

            if (dScore > 21) {
                state.dealerBusts++;
                state.wins++;
                state.money += state.betAmount * 2;
                res = 'PLAY WIN';
            } else if (pScore > dScore) {
                state.wins++;
                state.money += state.betAmount * 2;
                res = 'PLAY WIN';
            } else if (dScore > pScore) {
                state.losses++;
                state.houseProfit += state.betAmount;
                res = 'DEAL WIN';
            } else {
                state.pushes++;
                state.money += state.betAmount;
                res = 'PUSH';
            }
        }

        // Stats tracking
        if (res === 'PLAY WIN') state.pWins++;
        else if (res === 'DEAL WIN') state.dWins++;
        else if (res === 'PUSH') state.ties++;

        if (res !== 'PUSH') {
            const isWin = (res === 'PLAY WIN');
            if (isWin) {
                if (state.currentStreak > 0) state.currentStreak++;
                else state.currentStreak = 1;
                if (state.currentStreak > state.maxWins) state.maxWins = state.currentStreak;
            } else {
                if (state.currentStreak < 0) state.currentStreak--;
                else state.currentStreak = -1;
                if (Math.abs(state.currentStreak) > state.maxLosses) state.maxLosses = Math.abs(state.currentStreak);
            }
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

    } catch (error) {
        console.error("Blackjack error:", error);
    } finally {
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
            setTimeout(playRound, delay);
        }
        updateUI();
    }
}

function getCardValue(card) {
    if (['J', 'Q', 'K'].includes(card.value)) return 10;
    if (card.value === 'A') return 11;
    return parseInt(card.value);
}

function toggleAuto() {
    if (state.money <= 0) return;
    state.isAutoMode = !state.isAutoMode;
    if (state.isAutoMode && !state.isPlaying) playRound();
    updateUI();
}

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

function showBankruptcy() {
    document.getElementById('bankruptcy-modal').classList.remove('hidden');
}

function updateAnalysis() {
    const totalValid = state.pWins + state.dWins;
    if (totalValid > 0) {
        const pRate = (state.pWins / totalValid * 100).toFixed(1);
        const dRate = (state.dWins / totalValid * 100).toFixed(1);
        document.getElementById('p-rate-bar').style.width = pRate + '%';
        document.getElementById('d-rate-bar').style.width = dRate + '%';
        document.getElementById('p-rate-text').textContent = `P: ${pRate}%`;
        document.getElementById('d-rate-text').textContent = `D: ${dRate}%`;
    }
    document.getElementById('max-wins').textContent = state.maxWins;
    document.getElementById('max-losses').textContent = state.maxLosses;

    const netProfit = state.money - state.initialMoney;
    const roi = state.totalBetAmount > 0 ? (netProfit / state.totalBetAmount * 100).toFixed(1) : "0.0";
    const roiEl = document.getElementById('roi-display');
    roiEl.textContent = (roi > 0 ? "+" : "") + roi + "%";
    roiEl.style.color = roi >= 0 ? "#4caf50" : "var(--neon-red)";
}

function refill() {
    state.money = state.initialMoney;
    state.totalRounds = 0;
    state.wins = 0;
    state.losses = 0;
    state.pushes = 0;
    state.playerBusts = 0;
    state.dealerBusts = 0;
    state.houseProfit = 0;
    state.peakBalance = state.initialMoney;
    state.labels = [];
    state.balanceHistory = [];
    state.pWins = 0;
    state.dWins = 0;
    state.ties = 0;
    state.currentStreak = 0;
    state.maxWins = 0;
    state.maxLosses = 0;
    state.totalBetAmount = 0;
    state.chart.update();
    document.getElementById('bankruptcy-modal').classList.add('hidden');
    updateAnalysis();
    updateUI();
}

window.onload = () => {
    initDeck();
    initChart();
    updateUI();
};
