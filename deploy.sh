#!/bin/bash

# AI-Powered Feature Deployment Script
# Handles safe deployment and restart of the running challenge application

set -e  # Exit on any error

echo "🤖 AI Feature Deployment Starting..."
echo "Timestamp: $(date)"
echo "========================================="

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        log "❌ Docker not found. Please install Docker first."
        exit 1
    fi
    log "✅ Docker is available"
}

# Function to find the application container
find_app_container() {
    log "🔍 Looking for application container..."
    
    # Try to find container by common patterns
    local containers=$(docker ps --format "{{.Names}}" 2>/dev/null || echo "")
    
    for container in $containers; do
        if [[ $container =~ (strava|running|challenge|app|flask|python) ]]; then
            echo $container
            return 0
        fi
    done
    
    # Try to find by port
    local container_by_port=$(docker ps --filter "publish=5001" --format "{{.Names}}" 2>/dev/null | head -1)
    if [ ! -z "$container_by_port" ]; then
        echo $container_by_port
        return 0
    fi
    
    local container_by_port=$(docker ps --filter "publish=5000" --format "{{.Names}}" 2>/dev/null | head -1)
    if [ ! -z "$container_by_port" ]; then
        echo $container_by_port
        return 0
    fi
    
    return 1
}

# Function to backup current state
backup_state() {
    local container_name=$1
    log "💾 Creating backup of current state..."
    
    # Get container image
    local image=$(docker inspect --format='{{.Config.Image}}' $container_name 2>/dev/null)
    if [ $? -eq 0 ]; then
        log "📦 Current image: $image"
        echo $image > /tmp/backup_image.txt
    fi
    
    # Save current logs
    docker logs --tail 50 $container_name > /tmp/backup_logs.txt 2>&1 || true
    log "📝 Logs backed up to /tmp/backup_logs.txt"
}

# Function to restart container safely
restart_container() {
    local container_name=$1
    log "🔄 Restarting container: $container_name"
    
    # Graceful restart with timeout
    if timeout 60 docker restart $container_name; then
        log "✅ Container restarted successfully"
        return 0
    else
        log "❌ Container restart failed or timed out"
        return 1
    fi
}

# Function to wait for application to be ready
wait_for_app() {
    local max_wait=60
    local wait_time=0
    
    log "⏳ Waiting for application to be ready..."
    
    while [ $wait_time -lt $max_wait ]; do
        # Check if app is responding on port 5001
        if curl -s http://localhost:5001/ > /dev/null 2>&1; then
            log "✅ Application is responding"
            return 0
        fi
        
        # Also try port 5000
        if curl -s http://localhost:5000/ > /dev/null 2>&1; then
            log "✅ Application is responding on port 5000"
            return 0
        fi
        
        sleep 2
        wait_time=$((wait_time + 2))
        echo -n "."
    done
    
    echo ""
    log "❌ Application not responding after ${max_wait}s"
    return 1
}

# Function to validate deployment
validate_deployment() {
    local container_name=$1
    log "🔍 Validating deployment..."
    
    # Check container status
    local status=$(docker inspect --format='{{.State.Status}}' $container_name 2>/dev/null)
    if [ "$status" != "running" ]; then
        log "❌ Container is not running (status: $status)"
        return 1
    fi
    
    # Check application health
    if wait_for_app; then
        log "✅ Deployment validation successful"
        return 0
    else
        log "❌ Deployment validation failed"
        return 1
    fi
}

# Function to rollback on failure
rollback() {
    local container_name=$1
    log "🔙 Attempting rollback..."
    
    if [ -f /tmp/backup_image.txt ]; then
        local backup_image=$(cat /tmp/backup_image.txt)
        log "📦 Rolling back to image: $backup_image"
        # This would require more complex logic depending on your setup
        log "⚠️  Manual rollback required - check logs and restart manually"
    else
        log "⚠️  No backup found - manual intervention required"
    fi
    
    # Display recent logs for debugging
    log "📝 Recent logs:"
    docker logs --tail 20 $container_name 2>&1 || true
}

# Main deployment function
main() {
    log "🚀 Starting AI-powered deployment process"
    
    # Check prerequisites
    check_docker
    
    # Find application container
    local container_name=$(find_app_container)
    if [ $? -ne 0 ] || [ -z "$container_name" ]; then
        log "❌ No application container found"
        log "Available containers:"
        docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null || true
        exit 1
    fi
    
    log "🎯 Found application container: $container_name"
    
    # Backup current state
    backup_state $container_name
    
    # Restart container
    if restart_container $container_name; then
        # Validate deployment
        if validate_deployment $container_name; then
            log "🎉 Deployment completed successfully!"
            log "📊 Container: $container_name"
            log "🌐 Application should be available at http://localhost:5001/"
            exit 0
        else
            log "❌ Deployment validation failed"
            rollback $container_name
            exit 1
        fi
    else
        log "❌ Container restart failed"
        rollback $container_name
        exit 1
    fi
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "find")
        container=$(find_app_container)
        if [ $? -eq 0 ]; then
            echo "Container found: $container"
        else
            echo "No container found"
            exit 1
        fi
        ;;
    "status")
        container=$(find_app_container)
        if [ $? -eq 0 ]; then
            echo "Container: $container"
            docker ps --filter "name=$container" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
            echo ""
            echo "Recent logs:"
            docker logs --tail 10 $container 2>&1
        else
            echo "No container found"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 [deploy|find|status]"
        echo "  deploy - Deploy features and restart container (default)"
        echo "  find   - Find application container"
        echo "  status - Show container status and logs"
        exit 1
        ;;
esac