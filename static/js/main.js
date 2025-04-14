// BTCBuzzBot Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Price refresh functionality
    const priceRefreshBtn = document.getElementById('refresh-price');
    if (priceRefreshBtn) {
        priceRefreshBtn.addEventListener('click', async function() {
            try {
                const response = await fetch('/api/price/refresh');
                const data = await response.json();
                
                if (data.success) {
                    const priceElement = document.getElementById('current-price');
                    const changeElement = document.getElementById('price-change');
                    
                    if (priceElement) {
                        priceElement.textContent = data.price;
                    }
                    
                    if (changeElement) {
                        changeElement.textContent = data.change;
                        
                        // Update price direction indicator
                        changeElement.className = '';
                        if (parseFloat(data.change) > 0) {
                            changeElement.classList.add('price-up');
                        } else if (parseFloat(data.change) < 0) {
                            changeElement.classList.add('price-down');
                        } else {
                            changeElement.classList.add('price-stable');
                        }
                    }
                    
                    // Show success message
                    showAlert('Price refreshed successfully!', 'success');
                    
                    // If we have a chart, update it
                    if (window.priceChart) {
                        updatePriceChart();
                    }
                } else {
                    showAlert('Failed to refresh price: ' + data.error, 'danger');
                }
            } catch (error) {
                showAlert('Error refreshing price data', 'danger');
                console.error('Error:', error);
            }
        });
    }

    // Initialize price history chart if container exists
    const chartContainer = document.getElementById('price-chart');
    if (chartContainer) {
        initPriceChart();
    }

    // Toggle tweet scheduler
    const schedulerToggle = document.getElementById('scheduler-toggle');
    if (schedulerToggle) {
        schedulerToggle.addEventListener('change', async function() {
            const isEnabled = this.checked;
            
            try {
                const response = await fetch('/api/scheduler/toggle', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ enabled: isEnabled })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showAlert(`Scheduler ${isEnabled ? 'enabled' : 'disabled'} successfully!`, 'success');
                } else {
                    showAlert('Failed to update scheduler: ' + data.error, 'danger');
                    // Revert toggle if failed
                    this.checked = !isEnabled;
                }
            } catch (error) {
                showAlert('Error updating scheduler status', 'danger');
                console.error('Error:', error);
                // Revert toggle if failed
                this.checked = !isEnabled;
            }
        });
    }
});

// Initialize price chart
function initPriceChart() {
    fetch('/api/price/history')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                createPriceChart(data.prices);
            } else {
                console.error('Failed to get price history:', data.error);
            }
        })
        .catch(error => {
            console.error('Error fetching price history:', error);
        });
}

// Create price chart with Chart.js
function createPriceChart(priceData) {
    const ctx = document.getElementById('price-chart').getContext('2d');
    
    const labels = priceData.map(item => new Date(item.timestamp).toLocaleDateString());
    const prices = priceData.map(item => item.price);
    
    window.priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Bitcoin Price (USD)',
                data: prices,
                fill: false,
                borderColor: '#f7931a',
                tension: 0.1,
                pointBackgroundColor: '#f7931a',
                pointRadius: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return '$' + context.raw.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

// Update price chart with new data
function updatePriceChart() {
    fetch('/api/price/history')
        .then(response => response.json())
        .then(data => {
            if (data.success && window.priceChart) {
                const labels = data.prices.map(item => new Date(item.timestamp).toLocaleDateString());
                const prices = data.prices.map(item => item.price);
                
                window.priceChart.data.labels = labels;
                window.priceChart.data.datasets[0].data = prices;
                window.priceChart.update();
            }
        })
        .catch(error => {
            console.error('Error updating price chart:', error);
        });
}

// Display alert messages
function showAlert(message, type = 'info') {
    const alertContainer = document.querySelector('.container.mt-3');
    if (!alertContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => {
            alert.remove();
        }, 150);
    }, 5000);
} 