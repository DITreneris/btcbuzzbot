// BTCBuzzBot Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Price refresh functionality
    const refreshButton = document.getElementById('refresh-price');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            refreshBitcoinPrice();
        });
    }

    // Initialize price history chart if the element exists
    const chartCanvas = document.getElementById('price-chart');
    if (chartCanvas) {
        initializePriceChart();
    }

    // Auto-refresh price every 5 minutes
    setInterval(function() {
        if (document.getElementById('current-price')) {
            refreshBitcoinPrice(false); // Silent refresh
        }
    }, 300000); // 5 minutes

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

/**
 * Refresh Bitcoin price via API
 * @param {boolean} showAnimation - Whether to show loading animation
 */
function refreshBitcoinPrice(showAnimation = true) {
    const priceElement = document.getElementById('current-price');
    const changeElement = document.getElementById('price-change');
    const refreshButton = document.getElementById('refresh-price');
    const errorMsgElement = document.querySelector('.price-card .text-muted:last-child');
    
    if (!priceElement || !refreshButton) return;
    
    if (showAnimation) {
        refreshButton.classList.add('refreshing');
        refreshButton.disabled = true;
        
        // Add loading message
        if (errorMsgElement) {
            errorMsgElement.innerHTML = '<i class="fas fa-sync-alt fa-spin me-1"></i> Fetching latest price...';
        }
    }
    
    fetch('/api/price/refresh')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update price display with animation
                priceElement.innerHTML = data.price;
                
                // Determine and update price change display
                if (changeElement) {
                    const changeValue = parseFloat(data.change);
                    let changeClass = 'price-stable';
                    let changeIcon = 'fa-minus';
                    
                    if (changeValue > 0) {
                        changeClass = 'price-up';
                        changeIcon = 'fa-arrow-up';
                    } else if (changeValue < 0) {
                        changeClass = 'price-down';
                        changeIcon = 'fa-arrow-down';
                    }
                    
                    changeElement.className = changeClass;
                    changeElement.innerHTML = `<i class="fas ${changeIcon} me-1"></i>${data.change}`;
                }
                
                // Update timestamp
                if (errorMsgElement) {
                    const now = new Date();
                    errorMsgElement.innerHTML = `<i class="far fa-clock me-1"></i> Last updated: ${now.toISOString()}`;
                }
                
                // Apply fade-in animation
                priceElement.classList.add('fade-in');
                setTimeout(() => {
                    priceElement.classList.remove('fade-in');
                }, 500);
                
                // Show success message
                showAlert('Bitcoin price updated successfully!', 'success');
                
                // Reload chart if it exists
                const chartCanvas = document.getElementById('price-chart');
                if (chartCanvas && window.priceChart) {
                    initializePriceChart();
                }
            } else {
                console.error('Error refreshing price:', data.error);
                if (errorMsgElement) {
                    errorMsgElement.innerHTML = `<i class="fas fa-exclamation-circle me-1"></i> Error: ${data.error || 'Failed to fetch price'}`;
                }
                showAlert('Error refreshing price: ' + (data.error || 'Unknown error'), 'danger');
            }
        })
        .catch(error => {
            console.error('Error fetching price data:', error);
            if (errorMsgElement) {
                errorMsgElement.innerHTML = '<i class="fas fa-exclamation-circle me-1"></i> Network error, please try again';
            }
            showAlert('Network error fetching price data', 'danger');
        })
        .finally(() => {
            if (showAnimation) {
                refreshButton.classList.remove('refreshing');
                refreshButton.disabled = false;
            }
        });
}

/**
 * Initialize Bitcoin price history chart
 */
function initializePriceChart() {
    fetch('/api/price/history')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.prices && data.prices.length > 0) {
                renderPriceChart(data.prices);
            } else {
                console.log('No price history data available');
                const chartContainer = document.querySelector('.chart-container');
                if (chartContainer) {
                    chartContainer.innerHTML = '<div class="alert alert-info text-center my-5"><i class="fas fa-info-circle me-2"></i> No price history data available yet.</div>';
                }
            }
        })
        .catch(error => {
            console.error('Error fetching price history:', error);
        });
}

/**
 * Render price history chart with Chart.js
 * @param {Array} priceData - Array of price objects
 */
function renderPriceChart(priceData) {
    const ctx = document.getElementById('price-chart').getContext('2d');
    
    // Format data for Chart.js
    const timestamps = priceData.map(item => {
        const date = new Date(item.timestamp);
        return date.toLocaleString('en-US', { 
            month: 'short', 
            day: 'numeric',
            hour: 'numeric', 
            minute: 'numeric'
        });
    });
    
    const prices = priceData.map(item => item.price);
    
    // Destroy existing chart if it exists
    if (window.priceChart) {
        window.priceChart.destroy();
    }
    
    // Create gradient fill
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(247, 147, 26, 0.4)');
    gradient.addColorStop(1, 'rgba(247, 147, 26, 0.0)');
    
    // Create new chart
    window.priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [{
                label: 'Bitcoin Price (USD)',
                data: prices,
                backgroundColor: gradient,
                borderColor: '#F7931A',
                borderWidth: 2,
                pointBackgroundColor: '#F7931A',
                pointBorderColor: '#fff',
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#F1F5F9',
                        font: {
                            family: "'Inter', sans-serif",
                            size: 12
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(17, 24, 39, 0.9)',
                    titleColor: '#F1F5F9',
                    bodyColor: '#F1F5F9',
                    borderColor: '#334155',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: function(context) {
                            return `$${context.raw.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94A3B8',
                        maxRotation: 45,
                        minRotation: 45
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94A3B8',
                        callback: function(value) {
                            return '$' + value.toLocaleString('en-US');
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            elements: {
                point: {
                    radius: prices.length > 30 ? 0 : 3
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeOutQuart'
            }
        }
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