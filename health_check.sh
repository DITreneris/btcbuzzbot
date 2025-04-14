#!/bin/bash
# BTCBuzzBot Health Check Script

# Configuration
APP_URL="http://localhost:8000/health"
SCHEDULER_PROCESS="python -m src.scheduler"
LOG_FILE="/var/log/btcbuzzbot/health.log"
NOTIFICATION_EMAIL="admin@example.com"

# Timestamp for logs
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Check if the script is running as root or with appropriate permissions
if [[ $EUID -ne 0 ]] && [[ ! -w $(dirname "$LOG_FILE") ]]; then
    echo "[$TIMESTAMP] ERROR: This script must be run as root or with write access to $(dirname "$LOG_FILE")" >&2
    exit 1
fi

# Check if web interface is running
WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $APP_URL)
if [ $WEB_STATUS -eq 200 ]; then
    # Get JSON response and check if status is healthy
    RESPONSE=$(curl -s $APP_URL)
    if [[ $RESPONSE == *"\"status\":\"healthy\""* ]]; then
        echo "[$TIMESTAMP] Web interface is healthy (200 OK)" | tee -a $LOG_FILE
        WEB_HEALTHY=true
    else
        echo "[$TIMESTAMP] Web interface returned 200 but unhealthy status" | tee -a $LOG_FILE
        WEB_HEALTHY=false
    fi
else
    echo "[$TIMESTAMP] Web interface is not responding (HTTP $WEB_STATUS)" | tee -a $LOG_FILE
    WEB_HEALTHY=false
fi

# Check if scheduler process is running
pgrep -f "$SCHEDULER_PROCESS" > /dev/null
SCHEDULER_STATUS=$?
if [ $SCHEDULER_STATUS -eq 0 ]; then
    echo "[$TIMESTAMP] Scheduler is running" | tee -a $LOG_FILE
    SCHEDULER_HEALTHY=true
else
    echo "[$TIMESTAMP] Scheduler is not running" | tee -a $LOG_FILE
    SCHEDULER_HEALTHY=false
fi

# Take action if any component is unhealthy
if [ "$WEB_HEALTHY" = false ] || [ "$SCHEDULER_HEALTHY" = false ]; then
    echo "[$TIMESTAMP] WARNING: BTCBuzzBot is unhealthy" | tee -a $LOG_FILE
    
    # Attempt to restart services
    if [ "$WEB_HEALTHY" = false ]; then
        echo "[$TIMESTAMP] Attempting to restart web service..." | tee -a $LOG_FILE
        systemctl restart btcbuzzbot-web.service
    fi
    
    if [ "$SCHEDULER_HEALTHY" = false ]; then
        echo "[$TIMESTAMP] Attempting to restart scheduler..." | tee -a $LOG_FILE
        systemctl restart btcbuzzbot.service
    fi
    
    # Send notification email
    echo "[$TIMESTAMP] Sending notification email to $NOTIFICATION_EMAIL" | tee -a $LOG_FILE
    echo "BTCBuzzBot health check failed at $TIMESTAMP
    
Web Interface: $([ "$WEB_HEALTHY" = true ] && echo "Healthy" || echo "Unhealthy")
Scheduler: $([ "$SCHEDULER_HEALTHY" = true ] && echo "Healthy" || echo "Unhealthy")

Auto-recovery has been attempted.

Please check the logs at $LOG_FILE for more details." | mail -s "BTCBuzzBot Health Alert" $NOTIFICATION_EMAIL
    
    exit 1
else
    echo "[$TIMESTAMP] SUCCESS: BTCBuzzBot is healthy" | tee -a $LOG_FILE
    exit 0
fi 