const savedState = CasinoStorage.getCombinedState();
const state = {
    money: savedState.money,
    initialMoney: savedState.initialMoney,
    currentBet: 10000,
    betSide: 'BANKER',
    deck: [],
    playerHand: [],
    bankerHand: [],
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
    pWins: 0,
    bWins: 0,
    ties: 0,
    currentStreak: 0,
    maxWins: 0,
    maxLosses: 0,
    totalBetAmount: 0,
    totalCommission: 0
};

const suits = ['♠', '♥', '♦', '♣'];
const values = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];

function initDeck() {
    state.deck = [];
    for (let i = 0; i < 8; i++) {
        for (let suit of suits) {
            for (let value of values) {
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
        autoBtn.textContent = "자동 시뮬레이션 시작";
        autoBtn.classList.remove('active');
    }

    document.querySelectorAll('.bet-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.id === `bet-${state.betSide.toLowerCase()}`) btn.classList.add('active');
    });

    const playOnceBtn = document.getElementById('play-once-btn');
    if (playOnceBtn) {
        playOnceBtn.disabled = state.isPlaying || state.isAutoMode;
    }
}

function addLog(msg, color = '#eee') {
    CasinoLogger.add(msg, color);
}

function adjustBet(amount) {
    if (state.isPlaying) return;
    const nextBet = state.currentBet + amount;
    if (nextBet >= 10000 && nextBet <= state.money) {
        state.currentBet = nextBet;
        updateUI();
    }
}

function selectBetSide(side) {
    if (state.isPlaying) return;
    state.betSide = side;
    updateUI();
}

function updateSpeed(val) {
    const sliderVal = parseInt(val);
    state.speed = Math.floor(1000 / sliderVal); // 1일 때 1000ms, 10일 때 100ms
    document.getElementById('speed-val').textContent = sliderVal + 'x';
}

function calculateScore(hand) {
    let total = 0;
    for (let card of hand) {
        let val = card.value;
        if (['10', 'J', 'Q', 'K'].includes(val)) total += 0;
        else if (val === 'A') total += 1;
        else total += parseInt(val);
    }
    return total % 10;
}

function renderCard(card, containerId) {
    const container = document.getElementById(containerId);
    const cardEl = document.createElement('div');
    const isRed = ['♥', '♦'].includes(card.suit);
    cardEl.className = `card ${isRed ? 'red' : ''}`;
    cardEl.innerHTML = `<div>${card.value}</div><div style="font-size:2rem; text-align:center">${card.suit}</div><div style="transform:rotate(180deg)">${card.value}</div>`;
    container.appendChild(cardEl);
}

async function startGame() {
    if (state.isPlaying) return;
    if (state.money < state.currentBet) {
        state.isAutoMode = false;
        showBankruptcyReport();
        updateUI();
        return;
    }

    const isFast = state.speed <= 250;

    try {
        state.isPlaying = true;
        state.money -= state.currentBet;
        state.playerHand = [];
        state.bankerHand = [];
        state.totalRounds++;
        state.totalBetAmount += state.currentBet;

        document.getElementById('game-message').textContent = '카드를 배분 중입니다...';
        document.getElementById('player-cards').innerHTML = '';
        document.getElementById('banker-cards').innerHTML = '';
        document.getElementById('player-score').textContent = '0';
        document.getElementById('banker-score').textContent = '0';

        if (state.deck.length < 12) initDeck();

        // Deal
        state.playerHand.push(state.deck.pop());
        state.bankerHand.push(state.deck.pop());
        state.playerHand.push(state.deck.pop());
        state.bankerHand.push(state.deck.pop());

        renderCard(state.playerHand[0], 'player-cards');
        renderCard(state.bankerHand[0], 'banker-cards');
        renderCard(state.playerHand[1], 'player-cards');
        renderCard(state.bankerHand[1], 'banker-cards');

        let pScore = calculateScore(state.playerHand);
        let bScore = calculateScore(state.bankerHand);
        document.getElementById('player-score').textContent = pScore;
        document.getElementById('banker-score').textContent = bScore;

        if (!isFast) await sleep(state.speed / 2);

        // Third Card Rule
        if (pScore < 8 && bScore < 8) {
            let p3Val = -1;
            if (pScore <= 5) {
                const card = state.deck.pop();
                state.playerHand.push(card);
                renderCard(card, 'player-cards');
                p3Val = getCardValueForBankerRule(card);
                pScore = calculateScore(state.playerHand);
                document.getElementById('player-score').textContent = pScore;
                if (!isFast) await sleep(state.speed / 2);
            }

            if (shouldBankerDraw(calculateScore(state.bankerHand.slice(0, 2)), p3Val)) {
                const card = state.deck.pop();
                state.bankerHand.push(card);
                renderCard(card, 'banker-cards');
                bScore = calculateScore(state.bankerHand);
                document.getElementById('banker-score').textContent = bScore;
                if (!isFast) await sleep(state.speed / 2);
            }
        }

        const finalP = calculateScore(state.playerHand);
        const finalB = calculateScore(state.bankerHand);
        let winner = '';
        if (finalP > finalB) winner = 'PLAYER';
        else if (finalB > finalP) winner = 'BANKER';
        else winner = 'TIE';

        if (state.betSide === winner) {
            if (winner === 'PLAYER') {
                state.money += state.currentBet * 2;
                addLog(`플레이어 승리! +${state.currentBet.toLocaleString()}원 수익`, '#4caf50');
                document.getElementById('game-message').textContent = 'PLAYER WIN!';
            } else if (winner === 'BANKER') {
                const commission = state.currentBet * 0.05;
                state.houseProfit += commission;
                state.totalCommission += commission;
                const payout = state.currentBet * 1.95;
                state.money += payout;
                addLog(`뱅커 승리! (5% 수수료 ${commission.toLocaleString()}원 차감)`, '#ff9800');
                document.getElementById('game-message').textContent = 'BANKER WIN!';
            }
        } else if (winner === 'TIE') {
            state.money += state.currentBet;
            addLog("무승부(TIE) - 배팅금 반환", "#aaa");
            document.getElementById('game-message').textContent = 'TIE (PUSH)';
        } else {
            addLog(`${winner} 승리 - 패배. -${state.currentBet.toLocaleString()}원`, "#ff3131");
            document.getElementById('game-message').textContent = `${winner} WIN!`;
            if (state.betSide === 'PLAYER' && winner === 'BANKER') {
                state.houseProfit += state.currentBet * 0.05;
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

        // Analysis Calculations
        if (winner === 'PLAYER') state.pWins++;
        else if (winner === 'BANKER') state.bWins++;
        else if (winner === 'TIE') state.ties++;

        const isWin = (state.betSide === winner);
        const isTie = (winner === 'TIE');

        if (!isTie) {
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

        updateAnalysis();

    } catch (error) {
        console.error("Baccarat simulation error:", error);
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
            showBankruptcyReport();
        } else if (state.isAutoMode) {
            const isBatterySaving = localStorage.getItem('battery_saving') === 'true';
            const delay = isBatterySaving ? (isFast ? 150 : state.speed * 1.5) : (isFast ? 50 : state.speed);
            setTimeout(startGame, delay);
        }
    }
}

function getCardValueForBankerRule(card) {
    if (['10', 'J', 'Q', 'K'].includes(card.value)) return 0;
    if (card.value === 'A') return 1;
    return parseInt(card.value);
}

function shouldBankerDraw(bScore, p3Val) {
    if (p3Val === -1) return bScore <= 5;
    if (bScore <= 2) return true;
    if (bScore === 3 && p3Val !== 8) return true;
    if (bScore === 4 && [2, 3, 4, 5, 6, 7].includes(p3Val)) return true;
    if (bScore === 5 && [4, 5, 6, 7].includes(p3Val)) return true;
    if (bScore === 6 && [6, 7].includes(p3Val)) return true;
    return false;
}


function toggleAuto() {
    if (state.money <= 0) return;
    state.isAutoMode = !state.isAutoMode;
    if (state.isAutoMode && !state.isPlaying) startGame();
    updateUI();
}

function showBankruptcyReport() {
    document.getElementById('bankruptcy-modal').classList.remove('hidden');
}

function updateAnalysis() {
    const totalValid = state.pWins + state.bWins;
    if (totalValid > 0) {
        const pRate = (state.pWins / totalValid * 100).toFixed(1);
        const bRate = (state.bWins / totalValid * 100).toFixed(1);

        document.getElementById('p-rate-bar').style.width = pRate + '%';
        document.getElementById('b-rate-bar').style.width = bRate + '%';
        document.getElementById('p-rate-text').textContent = `P: ${pRate}%`;
        document.getElementById('b-rate-text').textContent = `B: ${bRate}%`;
    }

    document.getElementById('max-wins').textContent = state.maxWins;
    document.getElementById('max-losses').textContent = state.maxLosses;

    // ROI = (Current Money - Initial Money) / Total Bet Amount
    const netProfit = state.money - state.initialMoney;
    const roi = state.totalBetAmount > 0 ? (netProfit / state.totalBetAmount * 100).toFixed(1) : "0.0";
    const roiEl = document.getElementById('roi-display');
    roiEl.textContent = (roi > 0 ? "+" : "") + roi + "%";
    roiEl.style.color = roi >= 0 ? "#4caf50" : "var(--neon-red)";

    document.getElementById('total-commission').textContent = Math.floor(state.totalCommission).toLocaleString() + '원';
}

function refillMoney() {
    state.money = state.initialMoney;
    state.totalRounds = 0;
    state.houseProfit = 0;
    state.peakBalance = state.initialMoney;
    state.labels = [];
    state.balanceHistory = [];
    // Analysis Reset
    state.pWins = 0;
    state.bWins = 0;
    state.ties = 0;
    state.currentStreak = 0;
    state.maxWins = 0;
    state.maxLosses = 0;
    state.totalBetAmount = 0;
    state.totalCommission = 0;

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
    initDeck();
    initChart();
    updateUI();
};
