/**
 * 광진랜드 공통 헤더 로더
 * 모든 게임 페이지에서 동일한 헤더 구조를 보장합니다.
 */
document.addEventListener('DOMContentLoaded', () => {
    const headerRoot = document.getElementById('global-header');
    if (!headerRoot) return;

    // 현재 페이지 파일명 확인
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';

    // 게임별 규칙 정보 정의
    const gameRules = {
        'baccarat.html': {
            title: '게임 규칙 (Baccarat Rules)',
            desc: '플레이어(Player)와 뱅커(Banker) 중 합이 9에 더 가까운 쪽을 맞추는 게임입니다. 뱅커 승리 시 5%의 수수료(Commission)를 제외하고 지급합니다.'
        },
        'roulette.html': {
            title: '게임 규칙 (Roulette Rules)',
            desc: "'0(Zero)'은 카지노의 핵심 수익원입니다. Red/Black 배팅 시 0이 나오면 모든 배팅금은 카지노가 몰수합니다."
        },
        'blackjack.html': {
            title: '게임 규칙 (Blackjack Rules)',
            desc: '플레이어는 반드시 딜러보다 먼저 카드를 받아야 하며, 21점을 초과(Bust)하면 즉시 패배합니다. 블랙잭은 1.5배의 배당을 줍니다.'
        },
        'slots.html': {
            title: '게임 규칙 (Slots Rules)',
            desc: 'RTP 94.0%로 설정된 고정형 머신입니다. 장기적으로 베팅액의 6%를 반드시 잃게 설계되어 있습니다.'
        },
        'sicbo.html': {
            title: '게임 규칙 (Sic Bo Rules)',
            desc: "세 주사위의 합을 맞추는 게임입니다. 세 숫자가 모두 같은 '트리플' 발생 시 대(Big)/소(Small) 배팅은 무조건 패배합니다."
        },
        'bigwheel.html': {
            title: '게임 규칙 (Big Wheel Rules)',
            desc: '회전하는 휠이 멈추는 숫자를 맞추는 게임입니다. 각 숫자마다 배당과 출현 빈도가 다르게 설정되어 있습니다.'
        },
        'casinowar.html': {
            title: '게임 규칙 (Casino War Rules)',
            desc: "딜러와 각 1장의 카드로 높은 쪽이 승리합니다. 무승부 시 '전쟁(War)'을 선택하면 추가 베팅 후 승부를 냅니다. 전쟁 시의 수학적 불리함에 주목하십시오."
        },
        'keno.html': {
            title: '게임 규칙 (Keno Rules)',
            desc: "1~80 중 최대 10개의 숫자를 선택합니다. 하우스는 20개의 번호를 뽑으며, 일치하는 개수(Catch)에 따라 배당금이 지급됩니다. 하우스 엣지가 가장 높은 게임 중 하나입니다."
        },
        'caribbean.html': {
            title: '게임 규칙 (Caribbean Stud Rules)',
            desc: "딜러와 5장 대결을 펼칩니다. 딜러는 최소 AK 이상의 패를 가져야 자격이 생기며, 자격 미달 시 당신이 로열 플러시를 들고 있어도 안티 베팅에 대해서만 보상을 받게 됩니다."
        }
    };

    const currentRule = gameRules[currentPage] || { title: '광진랜드', desc: '최고의 시뮬레이션 경험을 제공합니다.' };

    const navItems = [
        { name: '바카라', href: 'baccarat.html' },
        { name: '룰렛', href: 'roulette.html' },
        { name: '블랙잭', href: 'blackjack.html' },
        { name: '슬롯머신', href: 'slots.html' },
        { name: '식보', href: 'sicbo.html' },
        { name: '빅휠', href: 'bigwheel.html' },
        { name: '카지노 워', href: 'casinowar.html' },
        { name: '키노', href: 'keno.html' },
        { name: '캐리비안 포커', href: 'caribbean.html' }
    ];

    const navHtml = navItems.map(item => `
        <a href="${item.href}" class="nav-link ${currentPage === item.href ? 'active' : ''}">${item.name}</a>
    `).join('');

    headerRoot.innerHTML = `
        <div class="logo-group">
            <a href="index.html" class="back-btn">←</a>
            <div class="logo">광진랜드</div>
            <div class="rule-info">
                <strong>${currentRule.title}</strong>
                ${currentRule.desc}
            </div>
        </div>
        <nav class="game-nav">
            ${navHtml}
        </nav>
        <div class="status-panel">
            <div class="stat-box">
                <span class="stat-label">보유 자산</span>
                <span id="money" class="stat-value">0</span><span class="unit">원</span>
            </div>
            <div class="stat-box">
                <span class="stat-label">고정 배팅액</span>
                <span id="current-bet-display" class="stat-value">0</span><span class="unit">원</span>
            </div>
        </div>
    `;

    // UI 업데이트 함수가 있으면 실행 (초기 잔액 바인딩)
    if (typeof updateUI === 'function') {
        updateUI();
    }
});
