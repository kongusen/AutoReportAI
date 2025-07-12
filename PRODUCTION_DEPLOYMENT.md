# AutoReportAI Production Deployment Guide

This guide provides comprehensive instructions for securely deploying AutoReportAI in a production environment.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Security Hardening](#security-hardening)
3. [Infrastructure Setup](#infrastructure-setup)
4. [Environment Configuration](#environment-configuration)
5. [Database Setup](#database-setup)
6. [SSL/TLS Configuration](#ssltls-configuration)
7. [Deployment Process](#deployment-process)
8. [Monitoring and Logging](#monitoring-and-logging)
9. [Backup and Recovery](#backup-and-recovery)
10. [Maintenance and Updates](#maintenance-and-updates)
11. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04 LTS or later, CentOS 8+, or RHEL 8+
- **CPU**: Minimum 4 cores, Recommended 8+ cores
- **RAM**: Minimum 8GB, Recommended 16GB+
- **Storage**: Minimum 100GB SSD, Recommended 500GB+ SSD
- **Network**: Stable internet connection with static IP

### Software Dependencies

- Docker 20.10+
- Docker Compose 2.0+
- PostgreSQL 13+ (if not using Docker)
- Redis 6.0+ (if not using Docker)
- Nginx 1.18+ (for reverse proxy)
- Certbot (for SSL certificates)

## Security Hardening

### 1. System Security

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install security updates automatically
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Configure firewall
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Disable root login and password authentication
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
# Set: PasswordAuthentication no
sudo systemctl restart ssh

# Install fail2ban for intrusion prevention
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 2. Docker Security

```bash
# Create non-root user for Docker
sudo groupadd docker
sudo usermod -aG docker $USER

# Configure Docker daemon securely
sudo nano /etc/docker/daemon.json
```

```json
{
  "live-restore": true,
  "userland-proxy": false,
  "no-new-privileges": true,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### 3. Network Security

```bash
# Configure iptables for additional security
sudo iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --set
sudo iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --update --seconds 60 --hitcount 4 -j DROP

# Save iptables rules
sudo iptables-save > /etc/iptables/rules.v4
```

## Infrastructure Setup

### 1. Directory Structure

```bash
# Create application directory
sudo mkdir -p /opt/autoreport
sudo chown $USER:$USER /opt/autoreport
cd /opt/autoreport

# Create subdirectories
mkdir -p {data,logs,backups,ssl,config}
```

### 2. Clone and Prepare Application

```bash
# Clone the repository
git clone https://github.com/your-org/AutoReportAI.git .

# Copy environment configuration
cp .env.example .env

# Set proper permissions
chmod 600 .env
chmod +x scripts/*.sh
```

## Environment Configuration

### 1. Generate Security Keys

```bash
# Generate JWT secret key
openssl rand -hex 32

# Generate encryption key for sensitive data
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate strong passwords
openssl rand -base64 32
```

### 2. Configure Environment Variables

Edit `.env` file with production values:

```bash
# Critical security settings
SECRET_KEY=your_generated_jwt_secret_key
ENCRYPTION_KEY=your_generated_fernet_key
DATABASE_URL=postgresql://autoreport_user:strong_password@localhost:5432/autoreport_db
REDIS_URL=redis://:redis_password@localhost:6379

# Production settings
NODE_ENV=production
DEBUG=false
LOG_LEVEL=INFO

# Domain configuration
DOMAIN=yourdomain.com
NEXT_PUBLIC_APP_URL=https://yourdomain.com
NEXT_PUBLIC_API_URL=https://api.yourdomain.com

# Email configuration
SMTP_HOST=smtp.yourmailserver.com
SMTP_PORT=587
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password
EMAILS_FROM_EMAIL=noreply@yourdomain.com
```

## Database Setup

### 1. PostgreSQL Configuration

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
```

```sql
-- Create database and user
CREATE USER autoreport_user WITH PASSWORD 'your_strong_password';
CREATE DATABASE autoreport_db OWNER autoreport_user;
GRANT ALL PRIVILEGES ON DATABASE autoreport_db TO autoreport_user;

-- Configure security
ALTER USER autoreport_user CREATEDB;
\q
```

### 2. Database Security Hardening

```bash
# Edit PostgreSQL configuration
sudo nano /etc/postgresql/13/main/postgresql.conf

# Set secure configurations:
# ssl = on
# shared_preload_libraries = 'pg_stat_statements'
# log_statement = 'all'
# log_min_duration_statement = 1000

# Configure client authentication
sudo nano /etc/postgresql/13/main/pg_hba.conf

# Ensure only local connections are allowed:
# local   all             all                                     md5
# host    all             all             127.0.0.1/32            md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### 3. Redis Configuration

```bash
# Install Redis
sudo apt install redis-server

# Configure Redis securely
sudo nano /etc/redis/redis.conf

# Set secure configurations:
# requirepass your_redis_password
# bind 127.0.0.1
# protected-mode yes
# maxmemory 256mb
# maxmemory-policy allkeys-lru

# Restart Redis
sudo systemctl restart redis-server
```

## SSL/TLS Configuration

### 1. Obtain SSL Certificate

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot certonly --nginx -d yourdomain.com -d api.yourdomain.com

# Set up automatic renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. Nginx Configuration

```bash
# Install Nginx
sudo apt install nginx

# Create configuration
sudo nano /etc/nginx/sites-available/autoreport
```

```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;

# Frontend server
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}

# API server
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;

    # Rate limiting
    location /api/v1/login {
        limit_req zone=login burst=10 nodelay;
        proxy_pass http://localhost:8000;
        include proxy_params;
    }

    location / {
        limit_req zone=api burst=200 nodelay;
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site and restart Nginx
sudo ln -s /etc/nginx/sites-available/autoreport /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Deployment Process

### 1. Build and Deploy

```bash
# Build Docker images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Run database migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Create initial superuser
docker-compose -f docker-compose.prod.yml exec backend python -c "
from app.initial_data import init_db
init_db()
"
```

### 2. Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    container_name: autoreport_db_prod
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped
    networks:
      - autoreport_network

  redis:
    image: redis:alpine
    container_name: autoreport_redis_prod
    command: redis-server --requirepass ${REDIS_PASSWORD}
    restart: unless-stopped
    networks:
      - autoreport_network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    container_name: autoreport_backend_prod
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      - db
      - redis
    restart: unless-stopped
    networks:
      - autoreport_network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    container_name: autoreport_frontend_prod
    environment:
      - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - autoreport_network

  scheduler:
    build:
      context: ./scheduler
      dockerfile: Dockerfile.prod
    container_name: autoreport_scheduler_prod
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - autoreport_network

volumes:
  postgres_data:

networks:
  autoreport_network:
    driver: bridge
```

## Monitoring and Logging

### 1. Log Management

```bash
# Configure log rotation
sudo nano /etc/logrotate.d/autoreport
```

```
/opt/autoreport/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
}
```

### 2. Health Checks

Create `scripts/health-check.sh`:

```bash
#!/bin/bash

# Health check script
BACKEND_URL="http://localhost:8000/health"
FRONTEND_URL="http://localhost:3000"

# Check backend
if curl -f -s $BACKEND_URL > /dev/null; then
    echo "Backend: OK"
else
    echo "Backend: FAILED"
    # Send alert notification
fi

# Check frontend
if curl -f -s $FRONTEND_URL > /dev/null; then
    echo "Frontend: OK"
else
    echo "Frontend: FAILED"
    # Send alert notification
fi

# Check database
if docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U ${POSTGRES_USER}; then
    echo "Database: OK"
else
    echo "Database: FAILED"
    # Send alert notification
fi
```

### 3. Monitoring Setup

```bash
# Add to crontab for regular health checks
crontab -e
# Add: */5 * * * * /opt/autoreport/scripts/health-check.sh >> /opt/autoreport/logs/health.log 2>&1
```

## Backup and Recovery

### 1. Database Backup

Create `scripts/backup-db.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/opt/autoreport/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/autoreport_backup_$DATE.sql"

# Create backup
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Remove backups older than 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

### 2. Automated Backups

```bash
# Add to crontab
crontab -e
# Add: 0 2 * * * /opt/autoreport/scripts/backup-db.sh
```

### 3. Recovery Process

```bash
# Stop services
docker-compose -f docker-compose.prod.yml down

# Restore database
gunzip -c /opt/autoreport/backups/autoreport_backup_YYYYMMDD_HHMMSS.sql.gz | \
docker-compose -f docker-compose.prod.yml exec -T db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

## Maintenance and Updates

### 1. Regular Maintenance Tasks

```bash
# Weekly maintenance script
#!/bin/bash

# Update system packages
sudo apt update && sudo apt upgrade -y

# Clean Docker resources
docker system prune -f

# Rotate logs
sudo logrotate -f /etc/logrotate.d/autoreport

# Check disk space
df -h

# Check service status
docker-compose -f docker-compose.prod.yml ps
```

### 2. Application Updates

```bash
# Update deployment script
#!/bin/bash

# Backup before update
./scripts/backup-db.sh

# Pull latest code
git pull origin main

# Build new images
docker-compose -f docker-compose.prod.yml build

# Rolling update
docker-compose -f docker-compose.prod.yml up -d --no-deps backend
docker-compose -f docker-compose.prod.yml up -d --no-deps frontend

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Verify deployment
./scripts/health-check.sh
```

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check logs
   docker-compose -f docker-compose.prod.yml logs service_name
   
   # Check resource usage
   docker stats
   ```

2. **Database connection issues**
   ```bash
   # Test database connection
   docker-compose -f docker-compose.prod.yml exec backend python -c "
   from app.db.session import engine
   print(engine.execute('SELECT 1').scalar())
   "
   ```

3. **SSL certificate issues**
   ```bash
   # Check certificate status
   sudo certbot certificates
   
   # Renew certificate
   sudo certbot renew --dry-run
   ```

### Emergency Procedures

1. **Service Outage**
   - Check system resources (CPU, memory, disk)
   - Review recent logs
   - Restart affected services
   - Escalate to development team if needed

2. **Security Incident**
   - Immediately isolate affected systems
   - Review security logs
   - Change all passwords and keys
   - Update security measures
   - Document incident

### Support Contacts

- **System Administrator**: admin@yourdomain.com
- **Development Team**: dev@yourdomain.com
- **Emergency Contact**: +1-XXX-XXX-XXXX

---

**Important**: This deployment guide contains security-sensitive information. Ensure it's stored securely and access is limited to authorized personnel only. 