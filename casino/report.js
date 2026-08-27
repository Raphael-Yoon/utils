const state = CasinoStorage.getCombinedState();

const GAME_METADATA = {
    'baccarat': { name: '바카라', icon: '🃏', color: '#ff3131' },
    'roulette': { name: '룰렛', icon: '🎡', color: '#ffc107' },
    'blackjack': { name: '블랙잭', icon: '♠️', color: '#2196f3' },
    'slots': { name: '슬롯머신', icon: '🎰', color: '#ffd700' },
    'sicbo': { name: '식보', icon: '🎲', color: '#4caf50' },
    'bigwheel': { name: '빅휠', icon: '🎯', color: '#e91e63' },
    'casinowar': { name: '카지노 워', icon: '⚔️', color: '#ff5722' },
    'keno': { name: '키노', icon: '🔢', color: '#9c27b0' },
    'caribbean': { name: '캐리비안 포커', icon: '🏝️', color: '#00bcd4' }
};

function initReport() {
    renderGlobalStats();
    renderKillerRanking();
    renderStrategyAnalysis();
    initCharts();
}

function renderGlobalStats() {
    let totalRounds = 0;
    Object.values(state.perGameStats || {}).forEach(g => totalRounds += (g.rounds || 0));

    document.getElementById('total-rounds').textContent = totalRounds.toLocaleString();
    document.getElementById('total-donation').textContent = '₩' + Math.floor(state.houseProfit || 0).toLocaleString();

    // Win Rate Calculation (House Win Rate)
    // Theoretically if money is lost, house win rate is high. 
    // Let's use simple logic: (House Profit / Initial Money) * 100 as an index, capped
    const initial = state.initialMoney || 1000000;
    const profit = state.houseProfit || 0;
    let winRate = 50 + (profit / initial * 50);
    if (winRate > 99.9) winRate = 99.9;
    if (winRate < 50) winRate = 50;

    document.getElementById('global-win-rate').textContent = winRate.toFixed(1) + '%';
}

function renderKillerRanking() {
    const stats = state.perGameStats || {};
    const ranking = Object.keys(stats)
        .filter(id => GAME_METADATA[id])
        .map(id => ({
            id,
            ...stats[id],
            ...GAME_METADATA[id]
        }))
        .sort((a, b) => b.profit - a.profit);

    const container = document.getElementById('killer-ranking');
    container.innerHTML = ranking.map((g, i) => `
        <div class="ranking-item animate-up" style="animation-delay: ${0.2 + (i * 0.1)}s">
            <div class="rank-num">#${i + 1}</div>
            <div class="game-icon">${g.icon}</div>
            <div class="game-info">
                <span class="game-name">${g.name}</span>
                <span class="game-rounds">${g.rounds || 0} Rounds Played</span>
            </div>
            <div class="game-profit">
                <span class="profit-val">₩${Math.floor(g.profit || 0).toLocaleString()}</span>
                <span class="profit-label">House Profit</span>
            </div>
        </div>
    `).join('');
}

function renderStrategyAnalysis() {
    document.getElementById('report-peak').textContent = '₩' + Math.floor(state.peakBalance || 0).toLocaleString();
    document.getElementById('report-final').textContent = '₩' + Math.floor(state.money || 0).toLocaleString();
}

function initCharts() {
    // Win Rate Chart (Circular)
    const winCtx = document.getElementById('winRateChart').getContext('2d');
    const houseProfit = state.houseProfit || 0;
    const playerBalance = state.money || 0;
    const initial = state.initialMoney || 1000000;

    // Actually, let's just make it look cool with 95% fixed vs variable
    const houseWinRate = Math.min(99, 50 + (houseProfit / initial * 45));

    new Chart(winCtx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [houseWinRate, 100 - houseWinRate],
                backgroundColor: ['#ff3131', 'rgba(255,255,255,0.1)'],
                borderWidth: 0
            }]
        },
        options: {
            cutout: '80%',
            plugins: { legend: { display: false }, tooltip: { enabled: false } }
        }
    });

    // Profit Share Chart
    const shareCtx = document.getElementById('profitShareChart').getContext('2d');
    const stats = state.perGameStats || {};
    const labels = [];
    const data = [];
    const colors = [];

    Object.keys(stats).forEach(id => {
        if (GAME_METADATA[id] && stats[id].profit > 0) {
            labels.push(GAME_METADATA[id].name);
            data.push(stats[id].profit);
            colors.push(GAME_METADATA[id].color);
        }
    });

    new Chart(shareCtx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '게임별 하우스 수익 기여도',
                data: data,
                backgroundColor: colors,
                borderRadius: 5
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#666' } },
                y: { ticks: { color: '#fff' } }
            }
        }
    });

    // Peak vs Final
    const pCtx = document.getElementById('peakVsFinalChart').getContext('2d');
    new Chart(pCtx, {
        type: 'line',
        data: {
            labels: ['Start', 'Peak', 'Current'],
            datasets: [{
                data: [state.initialMoney, state.peakBalance, state.money],
                borderColor: '#ffd700',
                backgroundColor: 'rgba(255, 215, 0, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { display: false },
                x: { ticks: { color: '#888' } }
            }
        }
    });
}

function captureReport() {
    alert("이미지 저장 기능은 브라우저의 '스크린샷' 기능을 권장합니다.\n리포트 데이터는 최신 상태로 유지되었습니다.");
}

function resetAndRestart() {
    if (confirm("정말로 모든 데이터를 초기화하시겠습니까? 필승의 법칙을 다시 확인하게 될 것입니다.")) {
        CasinoStorage.resetState();
        window.location.href = 'index.html';
    }
}

window.onload = initReport;
