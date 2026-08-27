const CasinoStorage = {
    DEFAULT_STATE: {
        money: 1000000,
        initialMoney: 1000000,
        totalRounds: 0,
        peakBalance: 1000000,
        houseProfit: 0,
        batterySaving: false,
        perGameStats: {} // New: Tracks { rounds: 0, bet: 0, payout: 0, profit: 0 } per game
    },

    getCombinedState() {
        const stored = sessionStorage.getItem('casino_state');
        let state = { ...this.DEFAULT_STATE };
        if (stored) {
            try {
                const parsed = JSON.parse(stored);
                state = { ...this.DEFAULT_STATE, ...parsed };
                // Ensure perGameStats is merged or at least exists
                state.perGameStats = parsed.perGameStats || { ...this.DEFAULT_STATE.perGameStats };
            } catch (e) {
                console.error("Storage parse error", e);
            }
        }
        return state;
    },

    saveState(state) {
        const currentState = this.getCombinedState();
        const page = window.location.pathname.split('/').pop() || 'index.html';
        const gameKey = page.replace('.html', '');

        // Update Global Stats
        const finalState = {
            ...currentState,
            ...state,
            peakBalance: Math.max(state.money || currentState.money, currentState.peakBalance || 0)
        };

        // Ensure perGameStats exists
        if (!finalState.perGameStats) finalState.perGameStats = {};

        // Update Per-Game Stats
        if (gameKey !== 'index' && gameKey !== 'report') {
            if (!finalState.perGameStats[gameKey]) {
                finalState.perGameStats[gameKey] = { rounds: 0, profit: 0, bet: 0, payout: 0 };
            }

            // Map common game state keys to per-game stats
            if (state.totalRounds !== undefined) finalState.perGameStats[gameKey].rounds = state.totalRounds;
            if (state.houseProfit !== undefined) finalState.perGameStats[gameKey].profit = state.houseProfit;

            // If the game provides totalBetAmount (some do), use it
            if (state.totalBetAmount !== undefined) finalState.perGameStats[gameKey].bet = state.totalBetAmount;
            if (state.totalPayout !== undefined) finalState.perGameStats[gameKey].payout = state.totalPayout;
        }

        sessionStorage.setItem('casino_state', JSON.stringify(finalState));
    },

    // New: Advanced stat logging
    logGameAction(gameId, data) {
        const state = this.getCombinedState();
        if (!state.perGameStats[gameId]) {
            state.perGameStats[gameId] = { rounds: 0, bet: 0, payout: 0, profit: 0 };
        }

        const g = state.perGameStats[gameId];
        g.rounds += (data.rounds || 0);
        g.bet += (data.bet || 0);
        g.payout += (data.payout || 0);
        g.profit += (data.bet || 0) - (data.payout || 0);

        state.money = data.money;
        state.houseProfit += (data.bet || 0) - (data.payout || 0);
        state.peakBalance = Math.max(state.money, state.peakBalance);

        sessionStorage.setItem('casino_state', JSON.stringify(state));
    },

    // Specific version for rounds persistence
    updateStats(money, rounds, profit) {
        const state = this.getCombinedState();
        state.money = money;
        state.totalRounds = rounds;
        state.houseProfit = profit;
        state.peakBalance = Math.max(money, state.peakBalance);
        sessionStorage.setItem('casino_state', JSON.stringify(state));
    },

    resetState() {
        sessionStorage.setItem('casino_state', JSON.stringify(this.DEFAULT_STATE));
    }
};

// Global Logger with Virtual Scroll behavior
const CasinoLogger = {
    logs: [],
    maxLogs: 50,
    containerId: 'game-log',

    add(msg, color = '#eee') {
        const time = new Date().toLocaleTimeString();
        this.logs.push({ msg, color, time });

        if (this.logs.length > this.maxLogs) {
            this.logs.shift();
        }

        this.render();
    },

    render() {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        container.innerHTML = this.logs.map(log => `
            <div class="log-item" style="color: ${log.color}; border-bottom: 1px solid rgba(255,255,255,0.05); padding: 5px 0; font-size: 0.8rem;">
                <span style="color: #666; font-size: 0.7rem;">[${log.time}]</span> ${log.msg}
            </div>
        `).reverse().join('');
    }
};
