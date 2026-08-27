document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const startStopBtn = document.getElementById('startStopBtn');
    const resetBtn = document.getElementById('resetBtn');
    const totalRollsSpan = document.getElementById('totalRolls');
    const chartCanvas = document.getElementById('diceChart');

    // --- Chart.js Setup ---
    const labels = Array.from({ length: 11 }, (_, i) => i + 2); // Sums from 2 to 12
    let rollCounts = Array(11).fill(0); // Index 0 for sum 2, ..., Index 10 for sum 12
    let totalRolls = 0;
    let simulationInterval;
    let isSimulating = false;

    const diceChart = new Chart(chartCanvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Frequency',
                data: rollCounts,
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Occurrences'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Sum of Two Dice'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Distribution of Dice Roll Sums'
                }
            }
        }
    });

    // --- Simulation Functions ---

    function rollDice() {
        const die1 = Math.floor(Math.random() * 6) + 1;
        const die2 = Math.floor(Math.random() * 6) + 1;
        const sum = die1 + die2;

        rollCounts[sum - 2]++; // sum 2 goes to index 0, sum 12 to index 10
        totalRolls++;

        updateUI();
    }

    function updateUI() {
        diceChart.data.datasets[0].data = rollCounts;
        diceChart.update();
        totalRollsSpan.textContent = totalRolls.toLocaleString();
    }

    function startSimulation() {
        if (isSimulating) {
            stopSimulation();
        } else {
            isSimulating = true;
            startStopBtn.textContent = 'Stop Simulation';
            // Use setTimeout for rapid, but non-blocking updates
            simulationInterval = setInterval(rollDice, 1); // Roll every 1ms
        }
    }

    function stopSimulation() {
        isSimulating = false;
        startStopBtn.textContent = 'Start Simulation';
        clearInterval(simulationInterval);
    }

    function resetSimulation() {
        stopSimulation();
        rollCounts.fill(0);
        totalRolls = 0;
        updateUI();
    }

    // --- Event Listeners ---
    startStopBtn.addEventListener('click', startSimulation);
    resetBtn.addEventListener('click', resetSimulation);

    // Initial UI update
    updateUI();
});
