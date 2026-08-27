document.addEventListener('DOMContentLoaded', () => {
    initFavicon();
    initMobileUI();
    initGlobalHaptics();
});

function initFavicon() {
    if (!document.querySelector("link[rel*='icon']")) {
        const link = document.createElement('link');
        link.type = 'image/svg+xml';
        link.rel = 'icon';
        link.href = 'favicon.svg';
        document.head.appendChild(link);
    }
}

function initMobileUI() {
    // Inject Bottom Tab Bar if not exists
    if (!document.querySelector('.bottom-tab-bar')) {
        const tabBar = document.createElement('div');
        tabBar.className = 'bottom-tab-bar';
        const isIndex = window.location.pathname.includes('index.html') || window.location.pathname.endsWith('/');
        const isGame = !isIndex;

        tabBar.innerHTML = `
            <a href="index.html" class="tab-item ${isIndex ? 'active' : ''}">
                <span class="tab-icon">🏠</span>
                <span class="tab-label">Home</span>
            </a>
            <div class="tab-item" onclick="openGameSelector()">
                <span class="tab-icon">🎮</span>
                <span class="tab-label">Games</span>
            </div>
            <div class="tab-item" onclick="handleStatsTabClick()">
                <span class="tab-icon">📊</span>
                <span class="tab-label">Stats</span>
            </div>
            <div class="tab-item" onclick="toggleSidePanel('settings')">
                <span class="tab-icon">⚙️</span>
                <span class="tab-label">Settings</span>
            </div>
        `;
        document.body.appendChild(tabBar);
    }

    // Inject Overlays
    injectOverlays();

    // Inject Mini Dashboard for game pages
    if (!window.location.pathname.includes('index.html')) {
        injectMiniDashboard();
    }
}


function injectMiniDashboard() {
    const dash = document.createElement('div');
    dash.id = 'mini-dashboard';
    dash.className = 'mini-dashboard';
    dash.innerHTML = `
        <div class="dash-item">
            <span class="dash-label">Profit</span>
            <span id="dash-profit" class="dash-value red">0</span>
        </div>
        <div class="dash-item">
            <span class="dash-label">Rounds</span>
            <span id="dash-rounds" class="dash-value">0</span>
        </div>
        <div class="dash-toggle" onclick="toggleStatsPanel()">
            <span id="dash-toggle-icon">📊</span>
        </div>
    `;

    const gameArea = document.querySelector('.game-area');
    if (gameArea) {
        gameArea.prepend(dash);
    }

    // Auto-update dashboard
    setInterval(() => {
        if (typeof CasinoStorage === 'undefined') return;
        const state = CasinoStorage.getCombinedState();
        const pEl = document.getElementById('dash-profit');
        const rEl = document.getElementById('dash-rounds');
        if (pEl) {
            const profit = Math.floor(state.houseProfit || 0);
            pEl.textContent = profit.toLocaleString();
            // House profit > 0 means player is losing (Red), <= 0 means player is winning/even (Green)
            pEl.style.color = profit > 0 ? 'var(--neon-red, #ff3131)' : '#4caf50';
        }
        if (rEl) rEl.textContent = state.totalRounds || 0;
    }, 1000);
}

function toggleStatsPanel() {
    const statsPanel = document.querySelector('.stats-panel');
    if (statsPanel) {
        statsPanel.classList.toggle('mobile-visible');
        const isVisible = statsPanel.classList.contains('mobile-visible');
        document.getElementById('dash-toggle-icon').textContent = isVisible ? '✕' : '📊';
    }
}

function injectOverlays() {
    // Game Selector Overlay
    const selector = document.createElement('div');
    selector.id = 'game-selector';
    selector.className = 'game-selector-overlay';
    selector.innerHTML = `
        <div class="selector-header">
            <span class="selector-title">게임 선택</span>
            <span class="close-selector" onclick="closeGameSelector()">✕</span>
        </div>
        <div class="card-swipe-container">
            <a href="baccarat.html" class="game-swipe-card">
                <div class="game-swipe-icon">🃏</div>
                <div class="game-swipe-name">바카라</div>
            </a>
            <a href="roulette.html" class="game-swipe-card">
                <div class="game-swipe-icon">🎡</div>
                <div class="game-swipe-name">룰렛</div>
            </a>
            <a href="blackjack.html" class="game-swipe-card">
                <div class="game-swipe-icon">♠️</div>
                <div class="game-swipe-name">블랙잭</div>
            </a>
            <a href="slots.html" class="game-swipe-card">
                <div class="game-swipe-icon">🎰</div>
                <div class="game-swipe-name">슬롯머신</div>
            </a>
            <a href="sicbo.html" class="game-swipe-card">
                <div class="game-swipe-icon">🎲</div>
                <div class="game-swipe-name">식보</div>
            </a>
            <a href="bigwheel.html" class="game-swipe-card">
                <div class="game-swipe-icon">🎯</div>
                <div class="game-swipe-name">빅휠</div>
            </a>
            <a href="casinowar.html" class="game-swipe-card">
                <div class="game-swipe-icon">⚔️</div>
                <div class="game-swipe-name">카지노 워</div>
            </a>
            <a href="keno.html" class="game-swipe-card">
                <div class="game-swipe-icon">🔢</div>
                <div class="game-swipe-name">키노</div>
            </a>
            <a href="caribbean.html" class="game-swipe-card">
                <div class="game-swipe-icon">🏝️</div>
                <div class="game-swipe-name">캐리비안 포커</div>
            </a>
            <a href="report.html" class="game-swipe-card" style="background: var(--gold); color: #000;">
                <div class="game-swipe-icon">📊</div>
                <div class="game-swipe-name">통합 리포트</div>
            </a>
        </div>
    `;
    document.body.appendChild(selector);

    // Mobile Overlay (Background)
    const overlay = document.createElement('div');
    overlay.id = 'mobile-overlay';
    overlay.className = 'mobile-overlay';
    overlay.onclick = () => {
        closeGameSelector();
        closeSidePanel();
    };
    document.body.appendChild(overlay);

    // Side Panels
    const sidePanel = document.createElement('div');
    sidePanel.id = 'side-panel';
    sidePanel.className = 'side-panel';
    document.body.appendChild(sidePanel);
}

function openGameSelector() {
    document.getElementById('game-selector').classList.add('active');
    document.getElementById('mobile-overlay').classList.add('active');
    triggerHaptic(10);
}

function closeGameSelector() {
    document.getElementById('game-selector').classList.remove('active');
    if (!document.getElementById('side-panel').classList.contains('active')) {
        document.getElementById('mobile-overlay').classList.remove('active');
    }
}

function handleStatsTabClick() {
    const statsPanel = document.querySelector('.stats-panel');
    if (statsPanel) {
        if (window.location.pathname.includes('index.html')) {
            toggleSidePanel('stats');
        } else {
            statsPanel.scrollIntoView({ behavior: 'smooth' });
            triggerHaptic(10);
        }
    } else {
        toggleSidePanel('stats');
    }
}

function toggleStatsPanel() {
    const statsPanel = document.querySelector('.stats-panel');
    if (statsPanel) {
        statsPanel.scrollIntoView({ behavior: 'smooth' });
        triggerHaptic(10);
    }
}
function toggleSidePanel(type) {
    const panel = document.getElementById('side-panel');
    const overlay = document.getElementById('mobile-overlay');

    if (panel.classList.contains('active')) {
        panel.classList.remove('active');
        overlay.classList.remove('active');
    } else {
        renderPanelContent(type);
        panel.classList.add('active');
        overlay.classList.add('active');
        triggerHaptic(10);
    }
}

function closeSidePanel() {
    document.getElementById('side-panel').classList.remove('active');
    if (!document.getElementById('game-selector').classList.contains('active')) {
        document.getElementById('mobile-overlay').classList.remove('active');
    }
}

function renderPanelContent(type) {
    const panel = document.getElementById('side-panel');
    const state = typeof CasinoStorage !== 'undefined' ? CasinoStorage.getCombinedState() : {};

    if (type === 'stats') {
        panel.innerHTML = `
            <div class="selector-header">
                <span class="selector-title">종합 통계</span>
                <span class="close-selector" onclick="closeSidePanel()">✕</span>
            </div>
            <div class="stats-group">
                <div class="stat-box" style="margin-bottom:15px; width:100%;">
                    <span class="stat-label">총 보유 자산</span>
                    <span class="stat-value" style="font-size:1.5rem;">${(state.money || 0).toLocaleString()}원</span>
                </div>
                <div class="stat-box" style="margin-bottom:15px; width:100%;">
                    <span class="stat-label">카지노 누적 수익</span>
                    <span class="stat-value" style="color:var(--neon-red);">${(state.houseProfit || 0).toLocaleString()}원</span>
                </div>
                <div class="stat-box" style="margin-bottom:15px; width:100%;">
                    <span class="stat-label">최고 자산 기록</span>
                    <span class="stat-value" style="color:var(--gold);">${(state.peakBalance || 0).toLocaleString()}원</span>
                </div>
            </div>
        `;
    } else if (type === 'settings') {
        panel.innerHTML = `
            <div class="selector-header">
                <span class="selector-title">설정</span>
                <span class="close-selector" onclick="closeSidePanel()">✕</span>
            </div>
            <div class="settings-group">
                <div class="setting-item" style="margin-bottom:20px;">
                    <label style="display:block; margin-bottom:10px; color:#aaa;">배터리 절약 모드 (FPS 제한)</label>
                    <button class="secondary-btn" style="width:100%;" onclick="toggleBatterySaving(this)">
                        ${localStorage.getItem('battery_saving') === 'true' ? '절약 모드 ON' : '절약 모드 OFF'}
                    </button>
                </div>
                <div class="setting-item">
                    <button class="secondary-btn" style="width:100%; border-color:#ff3131; color:#ff3131;" onclick="resetAllData()">
                        전체 데이터 초기화
                    </button>
                </div>
            </div>
        `;
    }
}

function triggerHaptic(duration) {
    if (window.navigator && window.navigator.vibrate) {
        window.navigator.vibrate(duration);
    }
}

function initGlobalHaptics() {
    document.addEventListener('click', (e) => {
        const target = e.target.closest('button, .bet-spot, .nav-link, .game-swipe-card, .tab-item, .dash-toggle');
        if (target) {
            target.classList.add('haptic-touch');
            setTimeout(() => target.classList.remove('haptic-touch'), 150);
            triggerHaptic(15);
        }
    });
}

function toggleBatterySaving(btn) {
    const isSaving = localStorage.getItem('battery_saving') === 'true';
    localStorage.setItem('battery_saving', !isSaving);
    btn.textContent = !isSaving ? '절약 모드 ON' : '절약 모드 OFF';
}

function resetAllData() {
    if (confirm('모든 진척도와 자산이 초기화됩니다. 계속하시겠습니까?')) {
        CasinoStorage.resetState();
        location.reload();
    }
}
