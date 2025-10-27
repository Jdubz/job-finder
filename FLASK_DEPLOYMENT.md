# Flask Deployment Guide

This guide covers deploying the Job Finder Worker as a standalone Flask application.

## Architecture

The worker runs as a Flask application with:
- **HTTP API** for health checks and control
- **Background thread** for processing queue items
- **Graceful shutdown** via HTTP endpoint
- **No Docker dependency** - runs directly with Python

## Quick Start

### Development

```bash
# 1. Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys and Firebase credentials

# 4. Start the worker
./run_dev.sh
```

The worker will start on `http://127.0.0.1:5555`

### Production

```bash
# 1. Set up virtual environment (same as dev)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure production environment
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase-key.json
export WORKER_PORT=5555
export WORKER_HOST=0.0.0.0

# 3. Start the worker
./run_prod.sh
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKER_PORT` | 5555 | Port for Flask HTTP API |
| `WORKER_HOST` | 127.0.0.1 (dev)<br>0.0.0.0 (prod) | Host to bind to |
| `QUEUE_WORKER_LOG_FILE` | logs/worker.log | Log file location |
| `FLASK_ENV` | development | Flask environment mode |
| `GOOGLE_APPLICATION_CREDENTIALS` | - | Path to Firebase service account key (required) |
| `ANTHROPIC_API_KEY` | - | Claude API key (optional) |
| `OPENAI_API_KEY` | - | OpenAI API key (optional) |
| `POLL_INTERVAL` | 60 | Seconds between queue polls |

### Configuration File

Edit `config/config.dev.yaml` or create `config/config.prod.yaml`:

```yaml
profile:
  source: "firestore"
  firestore:
    database_name: "job-finder"
    user_id: "your-user-id"

ai:
  enabled: true
  provider: "claude"  # or "openai"
  model: "claude-3-5-sonnet-20241022"
  min_match_score: 70

storage:
  database_name: "job-finder-staging"

scraping:
  delay_between_requests: 2
  max_retries: 3
```

## HTTP API Endpoints

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "uptime": 3600,
  "items_processed": 42
}
```

### GET /status

Detailed worker status.

**Response:**
```json
{
  "status": "running",
  "uptime": 3600,
  "stats": {
    "items_processed_total": 42,
    "last_poll_time": "2025-10-27T00:00:00Z",
    "poll_interval": 60,
    "iteration": 60,
    "running": true,
    "last_error": null
  }
}
```

### POST /shutdown

Gracefully shutdown the worker.

**Response:**
```json
{
  "status": "shutting_down",
  "message": "Worker will stop after current batch"
}
```

## Process Management

### Using systemd (Recommended for Production)

Create `/etc/systemd/system/job-finder-worker.service`:

```ini
[Unit]
Description=Job Finder Queue Worker
After=network.target

[Service]
Type=simple
User=jobfinder
WorkingDirectory=/opt/job-finder-worker
Environment="GOOGLE_APPLICATION_CREDENTIALS=/opt/job-finder-worker/credentials/firebase-key.json"
Environment="WORKER_PORT=5555"
Environment="WORKER_HOST=0.0.0.0"
ExecStart=/opt/job-finder-worker/venv/bin/python3 -m job_finder.flask_worker
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable job-finder-worker
sudo systemctl start job-finder-worker
sudo systemctl status job-finder-worker
```

### Using supervisor

Install supervisor:
```bash
pip install supervisor
```

Create `supervisor.conf`:
```ini
[supervisord]
logfile=logs/supervisord.log
loglevel=info

[program:job-finder-worker]
command=/path/to/venv/bin/python3 -m job_finder.flask_worker
directory=/path/to/job-finder-worker
autostart=true
autorestart=true
stderr_logfile=logs/worker.err.log
stdout_logfile=logs/worker.out.log
environment=GOOGLE_APPLICATION_CREDENTIALS="/path/to/firebase-key.json",WORKER_PORT="5555"
```

Start supervisor:
```bash
supervisord -c supervisor.conf
supervisorctl status
```

### Using PM2 (Alternative)

If you prefer PM2:
```bash
npm install -g pm2

# Create ecosystem.config.js
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'job-finder-worker',
    script: 'venv/bin/python3',
    args: '-m job_finder.flask_worker',
    cwd: '/path/to/job-finder-worker',
    env: {
      GOOGLE_APPLICATION_CREDENTIALS: '/path/to/firebase-key.json',
      WORKER_PORT: 5555,
      WORKER_HOST: '0.0.0.0'
    },
    autorestart: true,
    watch: false,
    max_restarts: 10,
    min_uptime: '10s'
  }]
};
EOF

pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

## Monitoring

### Health Checks

Set up health check monitoring with curl:
```bash
# Simple health check
curl http://localhost:5555/health

# Detailed status
curl http://localhost:5555/status
```

### Log Monitoring

Tail the logs:
```bash
tail -f logs/worker.log
```

View structured JSON logs:
```bash
tail -f logs/worker.log | jq '.'
```

### Metrics Collection

The worker logs include structured data for monitoring:
- Items processed count
- Poll iterations
- Error rates
- Processing times

Parse these from logs or implement a metrics endpoint.

## Scaling

### Horizontal Scaling

Run multiple worker instances:
```bash
# Worker 1
WORKER_PORT=5555 ./run_prod.sh &

# Worker 2
WORKER_PORT=5556 ./run_prod.sh &

# Worker 3
WORKER_PORT=5557 ./run_prod.sh &
```

Each worker will poll the queue independently and process available items.

### Load Balancing

Put workers behind a load balancer (nginx, HAProxy, etc.) for the health check endpoint:

```nginx
upstream workers {
    server localhost:5555;
    server localhost:5556;
    server localhost:5557;
}

server {
    listen 80;
    
    location /health {
        proxy_pass http://workers;
    }
    
    location /status {
        proxy_pass http://workers;
    }
}
```

## Troubleshooting

### Worker won't start

1. **Check virtual environment:**
   ```bash
   source venv/bin/activate
   python3 --version
   ```

2. **Check dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Check environment variables:**
   ```bash
   echo $GOOGLE_APPLICATION_CREDENTIALS
   ```

4. **Check logs:**
   ```bash
   cat logs/worker.log
   ```

### Worker stops unexpectedly

1. **Check system resources:**
   ```bash
   free -m  # Memory
   df -h    # Disk space
   ```

2. **Check for errors in logs:**
   ```bash
   grep ERROR logs/worker.log
   ```

3. **Enable debug logging:**
   ```bash
   export LOG_LEVEL=DEBUG
   ./run_dev.sh
   ```

### No items being processed

1. **Check queue status:**
   ```bash
   curl http://localhost:5555/status
   ```

2. **Verify Firebase connection:**
   - Check credentials file exists
   - Verify database name is correct
   - Check network connectivity

3. **Check poll interval:**
   - Default is 60 seconds
   - Set `POLL_INTERVAL=10` for faster polling (development only)

### High memory usage

1. **Reduce poll interval** to process fewer items per batch
2. **Lower AI model complexity** (use faster/smaller models)
3. **Add memory limits** in process manager configuration

## Security

### Production Checklist

- [ ] Use `WORKER_HOST=0.0.0.0` only if needed (prefer 127.0.0.1)
- [ ] Secure Firebase credentials file (chmod 600)
- [ ] Set up firewall rules for port 5555
- [ ] Enable HTTPS if exposing to internet
- [ ] Rotate API keys regularly
- [ ] Monitor logs for suspicious activity
- [ ] Keep dependencies updated

### Firewall Configuration

```bash
# Allow only from specific IPs
sudo ufw allow from 192.168.1.0/24 to any port 5555

# Or allow from localhost only
sudo ufw deny 5555
```

## Updates

### Updating the Worker

```bash
# 1. Stop the worker
curl -X POST http://localhost:5555/shutdown

# 2. Pull updates
git pull

# 3. Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# 4. Restart the worker
./run_prod.sh
```

### Zero-Downtime Updates (Multiple Workers)

```bash
# Update workers one at a time
# 1. Stop worker 1
curl -X POST http://localhost:5555/shutdown

# 2. Update and restart worker 1
git pull && pip install -r requirements.txt
WORKER_PORT=5555 ./run_prod.sh &

# 3. Repeat for workers 2 and 3
```

## Backup and Recovery

### Backup Strategy

The worker is stateless - all data is in Firebase:
- No worker-specific backups needed
- Ensure Firebase backups are configured
- Keep configuration files in version control

### Disaster Recovery

1. **Worker failure:** Restart the worker (systemd handles this)
2. **Server failure:** Start worker on new server with same config
3. **Data loss:** Restore Firebase from backups

## Performance Tuning

### Optimal Settings

**Development:**
```bash
export POLL_INTERVAL=30  # Faster feedback
export WORKER_HOST=127.0.0.1  # Localhost only
```

**Production:**
```bash
export POLL_INTERVAL=60  # Balanced
export WORKER_HOST=0.0.0.0  # If multi-host monitoring needed
```

**High-Volume:**
```bash
export POLL_INTERVAL=10  # Faster processing
# Run multiple workers (3-5 instances)
```

### Resource Requirements

**Minimum:**
- 512 MB RAM
- 1 CPU core
- 1 GB disk space

**Recommended:**
- 1 GB RAM
- 2 CPU cores
- 5 GB disk space

**High-Volume:**
- 2 GB RAM per worker
- 2 CPU cores per worker
- 10 GB disk space

## Support

For issues or questions:
1. Check logs: `logs/worker.log`
2. Review configuration: `config/config.*.yaml`
3. Test API endpoints: `curl http://localhost:5555/health`
4. See main README.md for general usage

---

**Last Updated:** 2025-10-27  
**Version:** 1.0.0  
**Deployment Type:** Flask (No Docker)
