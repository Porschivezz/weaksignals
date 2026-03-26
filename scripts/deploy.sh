#!/bin/bash
set -euo pipefail

# WeakSignals Deploy Script for ws.huginnmuninn.tech
# Run this on your VPS after initial setup

DOMAIN="ws.huginnmuninn.tech"
PROJECT_DIR="/opt/weaksignals"
REPO_URL="https://github.com/Porschivezz/weaksignals.git"
BRANCH="main"

echo "=== WeakSignals Deploy Script ==="

# -------------------------------------------------------
# Step 1: Install dependencies (first run only)
# -------------------------------------------------------
install_deps() {
    echo "[1/6] Installing system dependencies..."
    apt-get update
    apt-get install -y \
        docker.io \
        docker-compose-plugin \
        git \
        certbot \
        ufw

    # Enable Docker
    systemctl enable docker
    systemctl start docker

    # Firewall
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable

    echo "Dependencies installed."
}

# -------------------------------------------------------
# Step 2: Clone or pull repo
# -------------------------------------------------------
setup_repo() {
    echo "[2/6] Setting up repository..."
    if [ -d "$PROJECT_DIR" ]; then
        cd "$PROJECT_DIR"
        git fetch origin
        git checkout "$BRANCH"
        git pull origin "$BRANCH"
    else
        git clone "$REPO_URL" "$PROJECT_DIR"
        cd "$PROJECT_DIR"
        git checkout "$BRANCH"
    fi
    echo "Repository ready."
}

# -------------------------------------------------------
# Step 3: Setup .env.prod
# -------------------------------------------------------
setup_env() {
    echo "[3/6] Checking environment file..."
    if [ ! -f "$PROJECT_DIR/.env.prod" ]; then
        cp "$PROJECT_DIR/.env.prod.example" "$PROJECT_DIR/.env.prod"
        echo ""
        echo "!!! IMPORTANT !!!"
        echo "Edit $PROJECT_DIR/.env.prod with real passwords before continuing!"
        echo "Run: nano $PROJECT_DIR/.env.prod"
        echo ""
        echo "Generate JWT secret with: openssl rand -hex 64"
        echo "Generate passwords with: openssl rand -base64 32"
        echo ""
        exit 1
    fi
    echo "Environment file exists."
}

# -------------------------------------------------------
# Step 4: Get SSL certificate
# -------------------------------------------------------
setup_ssl() {
    echo "[4/6] Setting up SSL certificate..."

    CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

    if [ -f "$CERT_PATH" ]; then
        echo "SSL certificate already exists."
        return
    fi

    # Start nginx temporarily for ACME challenge
    # Use a minimal nginx config that only serves .well-known
    mkdir -p /tmp/certbot-webroot

    # Stop any running nginx
    docker compose -f docker-compose.prod.yml down nginx 2>/dev/null || true

    # Get certificate using standalone mode
    certbot certonly \
        --standalone \
        --non-interactive \
        --agree-tos \
        --email admin@huginnmuninn.tech \
        -d "$DOMAIN"

    # Copy certs to docker volume location
    echo "SSL certificate obtained."
}

# -------------------------------------------------------
# Step 5: Build and start services
# -------------------------------------------------------
start_services() {
    echo "[5/6] Building and starting services..."
    cd "$PROJECT_DIR"

    # Copy certs into docker volume
    docker compose -f docker-compose.prod.yml build
    docker compose -f docker-compose.prod.yml up -d

    echo "Services started."
}

# -------------------------------------------------------
# Step 6: Run migrations and seed
# -------------------------------------------------------
post_deploy() {
    echo "[6/6] Running post-deploy tasks..."
    cd "$PROJECT_DIR"

    # Wait for postgres
    echo "Waiting for Postgres to be ready..."
    sleep 10

    # Run seed data
    docker compose -f docker-compose.prod.yml exec backend python scripts/seed_data.py

    echo ""
    echo "=== Deploy Complete ==="
    echo "Dashboard: https://$DOMAIN"
    echo "API:       https://$DOMAIN/api/v1/health"
    echo ""
    echo "Demo accounts:"
    echo "  ceo@techventures.com / demo123"
    echo "  ceo@biopharm.com / demo123"
}

# -------------------------------------------------------
# Main
# -------------------------------------------------------
case "${1:-deploy}" in
    install)
        install_deps
        ;;
    ssl)
        setup_ssl
        ;;
    deploy)
        setup_repo
        setup_env
        start_services
        post_deploy
        ;;
    full)
        install_deps
        setup_repo
        setup_env
        setup_ssl
        start_services
        post_deploy
        ;;
    update)
        setup_repo
        docker compose -f "$PROJECT_DIR/docker-compose.prod.yml" build
        docker compose -f "$PROJECT_DIR/docker-compose.prod.yml" up -d
        echo "Update complete."
        ;;
    *)
        echo "Usage: $0 {install|ssl|deploy|full|update}"
        exit 1
        ;;
esac
