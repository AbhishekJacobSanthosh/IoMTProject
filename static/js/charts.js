// This file contains additional chart configurations and utilities
// that can be used across different pages

// Function to generate random colors for charts
function generateRandomColors(count) {
    const colors = [];
    for (let i = 0; i < count; i++) {
        const r = Math.floor(Math.random() * 255);
        const g = Math.floor(Math.random() * 255);
        const b = Math.floor(Math.random() * 255);
        colors.push(`rgba(${r}, ${g}, ${b}, 0.7)`);
    }
    return colors;
}

// Default chart options
const defaultLineChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'top',
        },
        tooltip: {
            mode: 'index',
            intersect: false,
        }
    },
    scales: {
        x: {
            grid: {
                display: false
            }
        },
        y: {
            grid: {
                color: 'rgba(0, 0, 0, 0.05)'
            }
        }
    },
    elements: {
        line: {
            tension: 0.4 // Smoother curves
        },
        point: {
            radius: 3,
            hitRadius: 10,
            hoverRadius: 5
        }
    }
};

// Function to create a standard line chart
function createLineChart(elementId, labels, datasets, options = {}) {
    const ctx = document.getElementById(elementId).getContext('2d');
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: Object.assign({}, defaultLineChartOptions, options)
    });
}
