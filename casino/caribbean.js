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
    // Simulation Specs
    dealerQualifies: 0,
    opportunityLoss: 0,
    totalBetAmount: 0,
    // Game State
    playerHand: [],
    dealerHand: [],
    deck: [],
    isDecisionPhase: false
};

const SUITS = ['♠', '♥', '♣', '♦'];
const VALUES = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'];
const VALUE_MAP = { '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14 };

const HAND_RANKS = {
    ROYAL_FLUSH: 10,
    STRAIGHT_FLUSH: 9,
    FOUR_OF_A_KIND: 8,
    FULL_HOUSE: 7,
    FLUSH: 6,
    STRAIGHT: 5,
    THREE_OF_A_KIND: 4,
    TWO_PAIR: 3,
    ONE_PAIR: 2,
    HIGH_CARD: 1
};

const PAYOUT_TABLE = {
    10: 100, // Royal Flush
    9: 50,  // Straight Flush
    8: 20,  // 4 of a Kind
    7: 7,   // Full House
    6: 5,   // Flush
    5: 4,   // Straight
    4: 3,   // 3 of a Kind
    3: 2,   // 2 Pair
    2: 1,   // 1 Pair
    1: 1    // High Card (Only if wins against dealer)
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
                borderColor: '#4caf50',
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
    document.getElementById('ante-amount').textContent = state.currentBet.toLocaleString();

    const autoBtn = document.getElementById('auto-btn');
    autoBtn.textContent = state.isAutoMode ? '시뮬레이션 중지' : '자동 시뮬레이션 시작';
    autoBtn.classList.toggle('active', state.isAutoMode);

    const playOnceBtn = document.getElementById('play-once-btn');
    if (playOnceBtn) {
        playOnceBtn.disabled = state.isPlaying || state.isAutoMode || state.isDecisionPhase;
    }
}

function adjustBet(amount) {
    if (state.isPlaying || state.isDecisionPhase) return;
    const nextBet = state.currentBet + amount;
    if (nextBet >= 10000 && nextBet <= state.money) {
        state.currentBet = nextBet;
        updateUI();
    }
}

function updateSpeed(val) {
    const sliderVal = parseInt(val);
    state.speed = Math.floor(1000 / sliderVal);
}

function createDeck() {
    const deck = [];
    for (const suit of SUITS) {
        for (const value of VALUES) {
            deck.push({ suit, value, score: VALUE_MAP[value], isRed: (suit === '♥' || suit === '♦') });
        }
    }
    return deck.sort(() => Math.random() - 0.5);
}

function renderCard(card, containerId, hidden = false) {
    const container = document.getElementById(containerId);
    const div = document.createElement('div');
    div.className = `card ${hidden ? 'hidden' : (card.isRed ? 'red' : '')}`;
    if (hidden) {
        div.innerHTML = '<div class="card-back">광진</div>';
    } else {
        div.innerHTML = `
            <div class="card-top">${card.value}${card.suit}</div>
            <div class="card-mid">${card.suit}</div>
            <div class="card-bot">${card.value}${card.suit}</div>
        `;
    }
    container.appendChild(div);
}

async function deal() {
    if (state.isPlaying || state.isDecisionPhase) return;
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

    document.getElementById('dealer-cards').innerHTML = '';
    document.getElementById('player-cards').innerHTML = '';
    document.getElementById('call-amount').textContent = '0';
    document.getElementById('dealer-rank').textContent = '?';
    document.getElementById('player-rank').textContent = '-';

    state.deck = createDeck();
    state.playerHand = [state.deck.pop(), state.deck.pop(), state.deck.pop(), state.deck.pop(), state.deck.pop()];
    state.dealerHand = [state.deck.pop(), state.deck.pop(), state.deck.pop(), state.deck.pop(), state.deck.pop()];

    // Deal Animation
    const isFast = state.speed <= 250;
    for (let i = 0; i < 5; i++) {
        renderCard(state.playerHand[i], 'player-cards');
        renderCard(state.dealerHand[i], 'dealer-cards', i !== 0); // Only first card revealed
        if (!isFast) await sleep(150);
    }

    const pRank = evaluateHand(state.playerHand);
    document.getElementById('player-rank').textContent = pRank.name;
    document.getElementById('game-message').textContent = `당신의 패: ${pRank.name}. 대결하시겠습니까?`;

    state.isDecisionPhase = true;
    document.getElementById('action-overlay').classList.remove('hidden');

    if (state.isAutoMode) {
        // AI Logic: Call if Pair or better, or if AK and high dealer card shown
        setTimeout(() => {
            if (pRank.rank >= HAND_RANKS.ONE_PAIR || (pRank.rank === HAND_RANKS.HIGH_CARD && isAKPlus(state.playerHand))) {
                call();
            } else {
                fold();
            }
        }, isFast ? 100 : 800);
    }
}

function fold() {
    document.getElementById('action-overlay').classList.add('hidden');
    state.isDecisionPhase = false;
    state.houseProfit += state.currentBet;
    CasinoLogger.add("폴드. 안티 베팅금을 잃었습니다.", "#aaa");
    finishRound();
}

async function call() {
    document.getElementById('action-overlay').classList.add('hidden');
    state.isDecisionPhase = false;

    const callBet = state.currentBet * 2;
    if (state.money < callBet) {
        CasinoLogger.add("자산 부족으로 강제 폴드합니다.", "var(--neon-red)");
        fold();
        return;
    }

    state.money -= callBet;
    state.totalBetAmount += callBet;
    document.getElementById('call-amount').textContent = callBet.toLocaleString();
    updateUI();

    // Reveal Dealer
    const dArea = document.getElementById('dealer-cards');
    dArea.innerHTML = '';
    state.dealerHand.forEach(c => renderCard(c, 'dealer-cards'));

    const dRank = evaluateHand(state.dealerHand);
    const pRank = evaluateHand(state.playerHand);
    document.getElementById('dealer-rank').textContent = dRank.name;

    const qualifies = isDealerQualified(state.dealerHand);
    if (qualifies) state.dealerQualifies++;

    if (!qualifies) {
        // Dealer doesn't qualify
        state.money += (state.currentBet * 2) + callBet; // Ante(1:1) + Call(Return)
        state.houseProfit -= state.currentBet;
        const msg = `딜러 자격 미달. 안티 베팅만 승리! (+${state.currentBet.toLocaleString()}원)`;
        document.getElementById('game-message').textContent = msg;
        CasinoLogger.add(msg, "#4caf50");

        // Opportunity Loss tracking
        if (pRank.rank > HAND_RANKS.ONE_PAIR) {
            const potentialGain = state.currentBet * 2 * (PAYOUT_TABLE[pRank.rank] - 1);
            if (potentialGain > 0) {
                state.opportunityLoss += potentialGain;
                CasinoLogger.add(`[기회분실] ${pRank.name}의 보너스를 놓쳤습니다 (-${potentialGain.toLocaleString()}원)`, "rgba(255,49,49,0.5)");
            }
        }
    } else {
        // Dealer Qualifies
        const winner = compareHands(pRank, dRank);
        if (winner === 'PLAYER') {
            const anteWin = state.currentBet * 2;
            const callWin = callBet + (callBet * PAYOUT_TABLE[pRank.rank]);
            state.money += anteWin + callWin;
            state.houseProfit -= (state.currentBet + (callBet * PAYOUT_TABLE[pRank.rank]));
            const msg = `플레이어 승리! ${pRank.name} (${PAYOUT_TABLE[pRank.rank]}배 지급)`;
            document.getElementById('game-message').textContent = msg;
            CasinoLogger.add(msg, "var(--gold)");
            vibrate(30);
        } else if (winner === 'DEALER') {
            state.houseProfit += (state.currentBet + callBet);
            const msg = `딜러 승리. 모든 베팅금을 잃었습니다.`;
            document.getElementById('game-message').textContent = msg;
            CasinoLogger.add(msg, "var(--neon-red)");
        } else {
            // Push
            state.money += state.currentBet + callBet;
            document.getElementById('game-message').textContent = "무승부! 모든 베팅금이 반환됩니다.";
            CasinoLogger.add("푸시(Push) - 무승부", "#aaa");
        }
    }

    finishRound();
}

function finishRound() {
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
        setTimeout(autoTick, state.speed);
    }
}

function autoTick() {
    if (!state.isAutoMode || state.money < state.currentBet) return;
    if (state.isDecisionPhase) {
        const pRank = evaluateHand(state.playerHand);
        if (pRank.rank >= HAND_RANKS.ONE_PAIR || (pRank.rank === HAND_RANKS.HIGH_CARD && isAKPlus(state.playerHand))) {
            call();
        } else {
            fold();
        }
    } else if (!state.isPlaying) {
        deal();
    }
}

function isDealerQualified(hand) {
    const rank = evaluateHand(hand);
    if (rank.rank >= HAND_RANKS.ONE_PAIR) return true;
    return isAKPlus(hand);
}

function isAKPlus(hand) {
    const scores = hand.map(c => c.score).sort((a, b) => b - a);
    return scores[0] === 14 && scores[1] === 13; // Ace and King present
}

function evaluateHand(hand) {
    const scores = hand.map(c => c.score).sort((a, b) => a - b);
    const suits = hand.map(c => c.suit);
    const isFlush = new Set(suits).size === 1;
    const isStraight = scores.every((s, i) => i === 0 || s === scores[i - 1] + 1);

    if (isFlush && isStraight && scores[0] === 10) return { rank: 10, name: "Royal Flush", scores };
    if (isFlush && isStraight) return { rank: 9, name: "Straight Flush", scores };

    const counts = {};
    scores.forEach(s => counts[s] = (counts[s] || 0) + 1);
    const valCounts = Object.values(counts).sort((a, b) => b - a);
    const uniqueScores = Object.keys(counts).map(Number).sort((a, b) => {
        if (counts[b] !== counts[a]) return counts[b] - counts[a];
        return b - a;
    });

    if (valCounts[0] === 4) return { rank: 8, name: "4 of a Kind", scores: uniqueScores };
    if (valCounts[0] === 3 && valCounts[1] === 2) return { rank: 7, name: "Full House", scores: uniqueScores };
    if (isFlush) return { rank: 6, name: "Flush", scores };
    if (isStraight) return { rank: 5, name: "Straight", scores };
    if (valCounts[0] === 3) return { rank: 4, name: "3 of a Kind", scores: uniqueScores };
    if (valCounts[0] === 2 && valCounts[1] === 2) return { rank: 3, name: "Two Pair", scores: uniqueScores };
    if (valCounts[0] === 2) return { rank: 2, name: "One Pair", scores: uniqueScores };

    return { rank: 1, name: "High Card", scores: uniqueScores };
}

function compareHands(p, d) {
    if (p.rank > d.rank) return 'PLAYER';
    if (d.rank > p.rank) return 'DEALER';
    // Deep compare scores
    for (let i = 0; i < p.scores.length; i++) {
        if (p.scores[i] > d.scores[i]) return 'PLAYER';
        if (d.scores[i] > p.scores[i]) return 'DEALER';
    }
    return 'TIE';
}

function updateAnalysis() {
    const qualRate = state.totalRounds > 0 ? (state.dealerQualifies / state.totalRounds * 100).toFixed(1) : "0.0";
    document.getElementById('qual-bar').style.width = qualRate + '%';
    document.getElementById('qual-text').textContent = `자격 충족: ${qualRate}%`;
    document.getElementById('non-qual-text').textContent = `미달: ${(100 - qualRate).toFixed(1)}%`;
    document.getElementById('opp-loss').textContent = Math.floor(state.opportunityLoss).toLocaleString() + '원';

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
    state.dealerQualifies = 0;
    state.opportunityLoss = 0;
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
function vibrate(p) { if (window.navigator && window.navigator.vibrate) window.navigator.vibrate(p); }

window.onload = () => {
    initChart();
    updateUI();
};
