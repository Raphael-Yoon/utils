const savedState = CasinoStorage.getCombinedState();
const state = {
    money: savedState.money,
    initialMoney: savedState.initialMoney,
    totalRounds: savedState.totalRounds,
    peakBalance: savedState.peakBalance,
    zeroCount: 0,
    currentBet: 10000,
    betSide: 'RED',
    houseProfit: savedState.houseProfit,
    isAutoMode: false,
    speed: 500, // ms
    chart: null,
    labels: [],
    balanceHistory: [],
    // Analysis Stats
    redWins: 0,
    blackWins: 0,
    zeroWins: 0,
    currentStreak: 0,
    maxWins: 0,
    maxLosses: 0,
    totalBetAmount: 0,
    wheelRotation: 0,
    isSpinning: false
};

const RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
// European Roulette order for wheel positioning
const WHEEL_NUMBERS = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26];

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
    document.getElementById('total-rounds').textContent = state.totalRounds;
    document.getElementById('house-profit').textContent = Math.floor(state.houseProfit).toLocaleString();
    document.getElementById('peak-balance').textContent = Math.floor(state.peakBalance).toLocaleString();
    document.getElementById('current-bet-display').textContent = state.currentBet.toLocaleString();

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
        playOnceBtn.disabled = state.isSpinning || state.isAutoMode;
    }

    // Update betting table UI
    document.getElementById('bet-area-red').classList.remove('active');
    document.getElementById('bet-area-black').classList.remove('active');
    document.getElementById('chip-red').classList.add('hidden');
    document.getElementById('chip-black').classList.add('hidden');

    if (state.betSide === 'RED') {
        document.getElementById('bet-area-red').classList.add('active');
        document.getElementById('chip-red').classList.remove('hidden');
        document.getElementById('chip-red').textContent = (state.currentBet / 1000) + 'K';
    } else {
        document.getElementById('bet-area-black').classList.add('active');
        document.getElementById('chip-black').classList.remove('hidden');
        document.getElementById('chip-black').textContent = (state.currentBet / 1000) + 'K';
    }
}

function addLog(msg, color = '#eee') {
    CasinoLogger.add(msg, color);
}

function adjustBet(amount) {
    if (state.isAutoMode) return;
    const nextBet = state.currentBet + amount;
    if (nextBet >= 10000 && nextBet <= state.money) {
        state.currentBet = nextBet;
        updateUI();
    }
}

function selectBetSide(side) {
    if (state.isAutoMode || state.isSpinning) return;
    state.betSide = side;
    updateUI();
}

function updateSpeed(val) {
    const sliderVal = parseInt(val);
    state.speed = Math.floor(1000 / sliderVal);
    document.getElementById('speed-val').textContent = sliderVal + 'x';
}

async function spin() {
    if (state.isSpinning) return;
    if (state.money < state.currentBet) {
        state.isAutoMode = false;
        showBankruptcy();
        updateUI();
        return;
    }

    const isFast = state.speed <= 250;
    state.isSpinning = true;

    state.totalRounds++;
    state.totalBetAmount += state.currentBet;
    state.money -= state.currentBet;
    updateUI();

    try {
        const result = Math.floor(Math.random() * 37);
        const resultIndex = WHEEL_NUMBERS.indexOf(result);

        // Simulation of spinning
        if (!isFast) {
            const wheel = document.getElementById('roulette-wheel');
            const ball = document.getElementById('wheel-ball');

            // Random many turns + offset to land on the number
            // Each pocket is 360/37 degrees
            const pocketDeg = 360 / 37;
            const extraRotation = 360 * 5; // 5 full turns
            state.wheelRotation += extraRotation;

            // The ball counter-rotates and lands in a pocket
            // For simplicity, we rotate the wheel and position the ball relative to it
            wheel.style.transition = `transform ${state.speed * 2}ms cubic-bezier(0.1, 0, 0.1, 1)`;
            wheel.style.transform = `rotate(${state.wheelRotation}deg)`;

            // Calculate ball position relative to wheel rotation
            // This is a simplified visual landing
            ball.style.transition = `transform ${state.speed * 2}ms cubic-bezier(0.1, 0, 0.1, 1)`;
            const ballRotation = -state.wheelRotation + (resultIndex * pocketDeg);
            ball.style.transform = `rotate(${ballRotation}deg)`;

            await new Promise(r => setTimeout(r, state.speed * 2));
        }

        let colorClass = 'zero';
        let win = false;

        if (result === 0) {
            state.zeroWins++;
            colorClass = 'zero';
            state.houseProfit += state.currentBet;
        } else if (RED_NUMBERS.includes(result)) {
            state.redWins++;
            colorClass = 'red';
            if (state.betSide === 'RED') win = true;
        } else {
            state.blackWins++;
            colorClass = 'black';
            if (state.betSide === 'BLACK') win = true;
        }

        const display = document.getElementById('roulette-display');
        display.textContent = result;
        display.className = `roulette-display ${colorClass}`;

        if (win) {
            const payout = state.currentBet * 2;
            state.money += payout;
            addLog(`${result} (${colorClass.toUpperCase()}) - 승리! +${state.currentBet.toLocaleString()}원`, '#4caf50');
            highlightBetArea(state.betSide, true);
        } else {
            if (result === 0) {
                addLog(`!!! '0' 발생 !!! 모든 배팅금이 카지노로 몰수됩니다.`, '#00ff41');
            } else {
                addLog(`${result} (${colorClass.toUpperCase()}) - 패배. -${state.currentBet.toLocaleString()}원`, '#ff3131');
                state.houseProfit += state.currentBet;
            }
            highlightBetArea(state.betSide, false);
        }

        if (state.money > state.peakBalance) state.peakBalance = state.money;

        // Streak tracking
        if (win) {
            if (state.currentStreak > 0) state.currentStreak++;
            else state.currentStreak = 1;
            if (state.currentStreak > state.maxWins) state.maxWins = state.currentStreak;
        } else {
            if (state.currentStreak < 0) state.currentStreak--;
            else state.currentStreak = -1;
            if (Math.abs(state.currentStreak) > state.maxLosses) state.maxLosses = Math.abs(state.currentStreak);
        }

        state.labels.push(state.totalRounds);
        state.balanceHistory.push(state.money);

        if (state.labels.length > 50) {
            state.labels.shift();
            state.balanceHistory.shift();
        }
        state.chart.update('none');
        updateAnalysis();
    } catch (error) {
        console.error("Roulette simulation error:", error);
    } finally {
        state.isSpinning = false;
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
            // Battery Saving Mode
            const isBatterySaving = localStorage.getItem('battery_saving') === 'true';
            const delay = isBatterySaving ? (isFast ? 150 : state.speed * 1.5) : (isFast ? 50 : state.speed);
            setTimeout(spin, delay);
        }
    }
}

function highlightBetArea(side, isWin) {
    const area = document.getElementById(`bet-area-${side.toLowerCase()}`);
    if (isWin) {
        area.style.animation = 'win-pulse 0.5s 2';
        setTimeout(() => area.style.animation = '', 1000);
    }
}

// Add CSS animation for win pulse to the document
const style = document.createElement('style');
style.innerHTML = `
@keyframes win-pulse {
    0% { transform: scale(1); box-shadow: 0 0 0px var(--gold); }
    50% { transform: scale(1.05); box-shadow: 0 0 30px var(--gold); }
    100% { transform: scale(1); box-shadow: 0 0 0px var(--gold); }
}`;
document.head.appendChild(style);

function toggleAuto() {
    if (state.money <= 0) return;
    state.isAutoMode = !state.isAutoMode;
    if (state.isAutoMode && !state.isSpinning) spin();
    updateUI();
}

function showBankruptcy() {
    document.getElementById('bankruptcy-modal').classList.remove('hidden');
}

function updateAnalysis() {
    const totalColor = state.redWins + state.blackWins;
    if (totalColor > 0) {
        const redRate = (state.redWins / totalColor * 100).toFixed(1);
        const blackRate = (state.blackWins / totalColor * 100).toFixed(1);

        document.getElementById('red-rate-bar').style.width = redRate + '%';
        document.getElementById('black-rate-bar').style.width = blackRate + '%';
        document.getElementById('red-rate-text').textContent = `R: ${redRate}%`;
        document.getElementById('black-rate-text').textContent = `B: ${blackRate}%`;
    } else {
        document.getElementById('red-rate-bar').style.width = '0%';
        document.getElementById('black-rate-bar').style.width = '0%';
        document.getElementById('red-rate-text').textContent = `R: 0.0%`;
        document.getElementById('black-rate-text').textContent = `B: 0.0%`;
    }

    document.getElementById('max-wins').textContent = state.maxWins;
    document.getElementById('max-losses').textContent = state.maxLosses;
    document.getElementById('zero-count').textContent = state.zeroWins;

    const netProfit = state.money - state.initialMoney;
    const roi = state.totalBetAmount > 0 ? (netProfit / state.totalBetAmount * 100).toFixed(1) : "0.0";
    const roiEl = document.getElementById('roi-display');
    roiEl.textContent = (roi > 0 ? "+" : "") + roi + "%";
    roiEl.style.color = roi >= 0 ? "#4caf50" : "var(--neon-red)";
}

function refill() {
    state.money = state.initialMoney;
    state.totalRounds = 0;
    state.houseProfit = 0;
    state.peakBalance = state.initialMoney;
    state.labels = [];
    state.balanceHistory = [];
    // Analysis Reset
    state.redWins = 0;
    state.blackWins = 0;
    state.zeroWins = 0;
    state.currentStreak = 0;
    state.maxWins = 0;
    state.maxLosses = 0;
    state.totalBetAmount = 0;

    state.chart.update();
    document.getElementById('bankruptcy-modal').classList.add('hidden');
    document.getElementById('log-area').innerHTML = '';
    updateAnalysis();
    updateUI();
}

window.onload = () => {
    initChart();
    updateUI();
};
