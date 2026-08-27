document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const boardElement = document.getElementById('board');
    const cells = document.querySelectorAll('[data-cell]');
    const statusDisplay = document.getElementById('status');
    const restartButton = document.getElementById('restartButton');

    // Control and Stats Elements
    const startTrainingBtn = document.getElementById('startTrainingBtn');
    const stopTrainingBtn = document.getElementById('stopTrainingBtn');
    const playVsAiBtn = document.getElementById('playVsAiBtn');
    const resetTrainingBtn = document.getElementById('resetTrainingBtn');
    const downloadQTableBtn = document.getElementById('downloadQTableBtn');
    
    const gamesPlayedSpan = document.getElementById('gamesPlayed');
    const aiWinRateSpan = document.getElementById('aiWinRate');
    const baselineWinRateSpan = document.getElementById('baselineWinRate');
    const drawRateSpan = document.getElementById('drawRate');

    // --- Constants & State ---
    const PLAYER_X = 'X'; // Rule-based AI
    const PLAYER_O = 'O'; // Q-Learning AI / Human
    const winningCombinations = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6]
    ];
    let qTable = {};
    let trainingInterval;
    let gameMode = 'idle'; // 'training', 'playing'
    let stats = { gamesPlayed: 0, qPlayerWins: 0, rulePlayerWins: 0, draws: 0 };
    
    // --- Q-Learning Parameters ---
    const learningRate = 0.1; // Alpha
    const discountFactor = 0.9; // Gamma
    let explorationRate = 0.3; // Epsilon

    // --- Classes ---

    class Game {
        constructor() {
            this.board = Array(9).fill(null);
            this.currentPlayer = PLAYER_X;
        }

        getStateKey() {
            return this.board.map(cell => cell || '-').join('');
        }

        getEmptyCells() {
            return this.board.map((cell, index) => cell === null ? index : null).filter(val => val !== null);
        }

        makeMove(index, player) {
            if (this.board[index] === null) {
                this.board[index] = player;
                return true;
            }
            return false;
        }

        checkWinner() {
            for (const combination of winningCombinations) {
                const [a, b, c] = combination;
                if (this.board[a] && this.board[a] === this.board[b] && this.board[a] === this.board[c]) {
                    return this.board[a]; // Returns 'X' or 'O'
                }
            }
            return this.getEmptyCells().length === 0 ? 'draw' : null;
        }
    }

    class RuleBasedPlayer {
        chooseAction(game) {
            const board = game.board;
            const emptyCells = game.getEmptyCells();
            
            // 1. Win
            for (const i of emptyCells) {
                const tempBoard = [...board];
                tempBoard[i] = PLAYER_X;
                if (isWinner(tempBoard, PLAYER_X)) return i;
            }
            // 2. Block
            for (const i of emptyCells) {
                const tempBoard = [...board];
                tempBoard[i] = PLAYER_O;
                if (isWinner(tempBoard, PLAYER_O)) return i;
            }
            // 3. Center
            if (board[4] === null) return 4;
            // 4. Corners
            const corners = [0, 2, 6, 8].filter(i => board[i] === null);
            if (corners.length > 0) return corners[Math.floor(Math.random() * corners.length)];
            // 5. Sides
            const sides = [1, 3, 5, 7].filter(i => board[i] === null);
            if (sides.length > 0) return sides[Math.floor(Math.random() * sides.length)];

            return emptyCells[0]; // Should not be reached
        }
    }

    class QLearningPlayer {
        constructor(player) {
            this.player = player;
        }

        getQValue(stateKey, action) {
            return qTable[stateKey]?.[action] || 0.0;
        }

        chooseAction(game, isTraining) {
            const stateKey = game.getStateKey();
            const emptyCells = game.getEmptyCells();

            if (isTraining && Math.random() < explorationRate) {
                // Explore
                return emptyCells[Math.floor(Math.random() * emptyCells.length)];
            } else {
                // Exploit
                let bestMove = -1;
                let maxQValue = -Infinity;

                for (const action of emptyCells) {
                    const qValue = this.getQValue(stateKey, action);
                    if (qValue > maxQValue) {
                        maxQValue = qValue;
                        bestMove = action;
                    }
                }
                
                if (bestMove === -1) { // If all Q-values are 0 or negative
                    return emptyCells[Math.floor(Math.random() * emptyCells.length)];
                }
                return bestMove;
            }
        }

        updateQTable(oldState, action, reward, newState) {
            if (!qTable[oldState]) qTable[oldState] = {};
            
            const oldQValue = this.getQValue(oldState, action);
            const futureMaxQ = Math.max(...Object.values(qTable[newState] || { a: 0.0 }).map(v => v));
            const newQValue = oldQValue + learningRate * (reward + discountFactor * futureMaxQ - oldQValue);

            qTable[oldState][action] = newQValue;
        }
    }

    // --- Main App Logic ---

    const rulePlayer = new RuleBasedPlayer();
    const qPlayer = new QLearningPlayer(PLAYER_O);
    let humanPlayer;
    let currentGame;

    function startTraining() {
        if (trainingInterval) return;
        gameMode = 'training';
        updateControlStates();
        statusDisplay.textContent = 'Training in progress...';
        
        trainingInterval = setInterval(() => {
            const history = [];
            const game = new Game();
            let winner = null;

            while (!winner) {
                const currentPlayer = game.currentPlayer === PLAYER_X ? rulePlayer : qPlayer;
                const stateKey = game.getStateKey();
                const action = currentPlayer.chooseAction(game, true);
                
                game.makeMove(action, game.currentPlayer);
                
                if (game.currentPlayer === PLAYER_O) {
                    history.push({ state: stateKey, action });
                }
                
                winner = game.checkWinner();
                if (winner) break;
                game.currentPlayer = game.currentPlayer === PLAYER_X ? PLAYER_O : PLAYER_X;
            }
            
            // Update Q-table based on result
            let rewardX = 0;
            let rewardO = 0;
            if (winner === PLAYER_X) { rewardX = -1; rewardO = -1; }
            if (winner === PLAYER_O) { rewardX = -1; rewardO = 1; }

            for (const move of history.reverse()) {
                qPlayer.updateQTable(move.state, move.action, rewardO, game.getStateKey());
            }

            // Update stats
            stats.gamesPlayed++;
            if (winner === PLAYER_O) stats.qPlayerWins++;
            else if (winner === PLAYER_X) stats.rulePlayerWins++;
            else stats.draws++;

            updateStatsUI();
            
            // Decay exploration rate
            explorationRate = Math.max(0.01, explorationRate * 0.9999);

        }, 0); // Run as fast as possible
    }

    function stopTraining() {
        clearInterval(trainingInterval);
        trainingInterval = null;
        gameMode = 'idle';
        updateControlStates();
        statusDisplay.textContent = 'Training stopped. Ready to play.';
        saveQTable();
    }

    function playVsAI() {
        stopTraining();
        gameMode = 'playing';
        humanPlayer = PLAYER_O;
        currentGame = new Game();
        updateBoardUI();
        updateControlStates();
        restartButton.style.display = 'block';
        statusDisplay.textContent = 'You are O. Rule AI is X. X starts.';
        // Rule AI makes the first move
        setTimeout(() => {
            const action = rulePlayer.chooseAction(currentGame);
            currentGame.makeMove(action, PLAYER_X);
            updateBoardUI();
            statusDisplay.textContent = 'Your turn (O).';
        }, 500);
    }
    
    function handleCellClick(e) {
        if (gameMode !== 'playing' || currentGame.checkWinner()) return;
        
        const cellIndex = parseInt(e.target.dataset.index);
        
        // Human's move
        if (currentGame.board[cellIndex] === null) {
            currentGame.makeMove(cellIndex, humanPlayer);
            updateBoardUI();
            
            let winner = currentGame.checkWinner();
            if (winner) return handleEndGame(winner);
            
            // Rule AI's turn
            statusDisplay.textContent = 'Rule AI (X) is thinking...';
            setTimeout(() => {
                const aiAction = rulePlayer.chooseAction(currentGame);
                currentGame.makeMove(aiAction, PLAYER_X);
                updateBoardUI();
                winner = currentGame.checkWinner();
                if (winner) return handleEndGame(winner);
                statusDisplay.textContent = 'Your turn (O).';
            }, 500);
        }
    }
    
    function handleEndGame(winner) {
        if (winner === 'draw') {
            statusDisplay.textContent = "It's a draw!";
        } else {
            statusDisplay.textContent = `${winner === humanPlayer ? 'You win!' : 'AI wins!'}`;
        }
    }

    function resetTraining() {
        stopTraining();
        qTable = {};
        stats = { gamesPlayed: 0, qPlayerWins: 0, rulePlayerWins: 0, draws: 0 };
        explorationRate = 0.3;
        localStorage.removeItem('ticTacToeQTable');
        localStorage.removeItem('ticTacToeStats');
        updateStatsUI();
        statusDisplay.textContent = 'Training data reset.';
    }

    function downloadQTable() {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(qTable, null, 2));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", "q_table.json");
        document.body.appendChild(downloadAnchorNode);
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
    }

    // --- UI & Helper Functions ---
    
    function updateBoardUI() {
        cells.forEach((cell, index) => {
            cell.classList.remove(PLAYER_X, PLAYER_O);
            if (currentGame.board[index]) {
                cell.classList.add(currentGame.board[index] === PLAYER_X ? 'x' : 'o');
            }
            cell.dataset.index = index;
        });
    }

    function updateStatsUI() {
        if (stats.gamesPlayed === 0) return;
        gamesPlayedSpan.textContent = stats.gamesPlayed.toLocaleString();
        aiWinRateSpan.textContent = ((stats.qPlayerWins / stats.gamesPlayed) * 100).toFixed(1) + '%';
        baselineWinRateSpan.textContent = ((stats.rulePlayerWins / stats.gamesPlayed) * 100).toFixed(1) + '%';
        drawRateSpan.textContent = ((stats.draws / stats.gamesPlayed) * 100).toFixed(1) + '%';
    }

    function updateControlStates() {
        startTrainingBtn.disabled = gameMode === 'training';
        stopTrainingBtn.disabled = gameMode !== 'training';
        playVsAiBtn.disabled = gameMode === 'training';
        restartButton.style.display = gameMode === 'playing' ? 'block' : 'none';
    }

    function saveQTable() {
        try {
            localStorage.setItem('ticTacToeQTable', JSON.stringify(qTable));
            localStorage.setItem('ticTacToeStats', JSON.stringify(stats));
        } catch (e) {
            console.error("Failed to save Q-table to localStorage:", e);
            statusDisplay.textContent = "Error: Couldn't save training data.";
        }
    }

    function loadQTable() {
        try {
            const savedQTable = localStorage.getItem('ticTacToeQTable');
            const savedStats = localStorage.getItem('ticTacToeStats');
            if (savedQTable) {
                qTable = JSON.parse(savedQTable);
            }
            if (savedStats) {
                stats = JSON.parse(savedStats);
            }
            updateStatsUI();
            statusDisplay.textContent = 'Loaded previous training data.';
        } catch (e) {
            console.error("Failed to load Q-table from localStorage:", e);
            resetTraining();
        }
    }

    function isWinner(board, player) {
        return winningCombinations.some(combination => {
            return combination.every(index => board[index] === player);
        });
    }

    function init() {
        loadQTable();
        updateControlStates();
        cells.forEach(cell => cell.addEventListener('click', handleCellClick));
        startTrainingBtn.addEventListener('click', startTraining);
        stopTrainingBtn.addEventListener('click', stopTraining);
        playVsAiBtn.addEventListener('click', playVsAI);
        restartButton.addEventListener('click', playVsAI); // Restarting a player game just starts a new one
        resetTrainingBtn.addEventListener('click', resetTraining);
        downloadQTableBtn.addEventListener('click', downloadQTable);
    }

    init();
});