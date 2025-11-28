# TUS Upload System Deployment Guide

## Overview

This guide covers deployment configurations for the TUS (Resumable Upload Protocol) system integrated into WaveForge Pro.

## Environment Variables

### TUS-Specific Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TUS_ENABLED` | `true` | Enable/disable TUS upload protocol |
| `TUS_MAX_SIZE` | `10737418240` | Maximum file size (10GB) |
| `TUS_CHUNK_SIZE` | `524288` | Sub-chunk size for TUS (512KB) |
| `TUS_EXPIRATION` | `86400` | Session expiration in seconds (24 hours) |
| `TUS_UPLOAD_DIR` | `/app/data/tus_uploads` | Directory for TUS chunk storage |
| `TUS_SESSION_DIR` | `/app/data/tus_sessions` | Directory for session metadata |
| `TUS_TEMP_DIR` | `/app/data/tus_temp` | Temporary directory for assembly |
| `DEFAULT_UPLOAD_METHOD` | `tus` | Default upload method (`tus` or `custom`) |

### Security Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_HOSTS` | `["localhost", "127.0.0.1"]` | JSON list of allowed hostnames |
| `CORS_ORIGINS` | `["http://localhost:8000"]` | JSON list of allowed CORS origins |
| `SECRET_KEY` | `default...` | Secret key for cryptographic operations |
| `ENVIRONMENT` | `development` | App environment (development/production) |

## Storage Requirements

### Persistent Volumes

The TUS system requires three persistent storage volumes:

1. **uploaded-data** (10Gi) - Completed uploads
2. **tus-uploads** (50Gi) - Active TUS chunk storage
3. **tus-sessions** (1Gi) - Session metadata and state

### Temporary Storage

- **tus-temp** - EmptyDir volume (5Gi) for chunk assembly operations

## Docker Deployment

### Using Docker Compose

```bash
cd deployment/docker
docker-compose up -d
```

The `docker-compose.yml` automatically configures:
- TUS environment variables
- Volume mounts for chunk storage
- Network configuration
- Health checks

### Building Custom Image

```bash
docker build -f deployment/docker/Dockerfile -t waveforge-pro:latest .
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.19+)
- kubectl configured
- Storage class supporting ReadWriteMany (e.g., NFS, EFS)

### Deploy to Development

```bash
cd deployment/k8s
kubectl apply -k overlays/development/
```

### Deploy to Production

```bash
cd deployment/k8s
kubectl apply -k overlays/production/
```

### Verify Deployment

```bash
# Check pods
kubectl get pods -n waveforge-pro

# Check PVCs
kubectl get pvc -n waveforge-pro

# Check logs
kubectl logs -n waveforge-pro -l app=waveforge-pro --tail=100
```

## Storage Configuration

### Local Development

Directories created by `start.sh`:
```
backend/uploaded_data/
├── temp/              # Temporary custom chunks
├── completed/         # Assembled files
├── tus_uploads/       # TUS chunk storage
├── tus_sessions/      # TUS session metadata
└── tus_temp/          # TUS assembly temp
```

### Kubernetes Storage Classes

**Development/Staging:**
```yaml
storageClassName: standard
```

**Production:**
```yaml
storageClassName: fast-ssd  # Or your high-performance storage class
```

Update in `overlays/production/pvc-patch.yaml` as needed.

## Health Checks

### Endpoints

- **Liveness:** `GET /health`
- **Readiness:** `GET /health`
- **TUS Status:** `GET /files/{session_id}/status`

### Docker Health Check

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

## Scaling Considerations

### Horizontal Scaling

TUS protocol is **session-based** and requires:

1. **Sticky Sessions** - Client must reach same pod for resume
2. **Shared Storage** - All pods must access same PVC (ReadWriteMany)
3. **Session Sync** - Consider Redis for distributed session management

**Production Configuration:**

```yaml
# deployment-patch.yaml
spec:
  replicas: 3  # Adjust based on load
  
# service.yaml
spec:
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 86400  # 24 hours
```

### Vertical Scaling

Adjust resources based on upload concurrency:

```yaml
resources:
  requests:
    memory: "512Mi"   # Base + (50MB × concurrent uploads)
    cpu: "500m"       # Base + (100m × concurrent uploads)
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

## Monitoring

### Metrics to Track

- **Active TUS sessions:** Session directory file count
- **Chunk storage usage:** TUS uploads PVC usage
- **Upload success rate:** Completed vs. failed uploads
- **Average resume count:** Resume frequency per session
- **Storage efficiency:** Chunk cleanup after assembly

### Prometheus Metrics (Future)

```
# Recommended custom metrics
waveforge_tus_active_sessions
waveforge_tus_uploads_total
waveforge_tus_uploads_completed
waveforge_tus_uploads_failed
waveforge_tus_resume_count
waveforge_tus_storage_bytes
```

## Backup Strategy

### Critical Data

1. **Completed uploads** - `uploaded-data` PVC
2. **Active TUS sessions** - `tus-sessions` PVC (for recovery)
3. **In-progress chunks** - `tus-uploads` PVC (optional)

### Backup Commands

```bash
# Kubernetes PVC backup example
kubectl exec -n waveforge-pro <pod-name> -- tar czf /backup/tus-sessions.tar.gz /app/data/tus_sessions
kubectl cp waveforge-pro/<pod-name>:/backup/tus-sessions.tar.gz ./tus-sessions-backup.tar.gz
```

## Cleanup & Maintenance

### Automatic Cleanup

TUS sessions expire after `TUS_EXPIRATION` seconds (default: 24 hours).

### Manual Cleanup

```bash
# Remove expired sessions (older than 24 hours)
find backend/uploaded_data/tus_sessions -type f -mtime +1 -delete
find backend/uploaded_data/tus_uploads -type f -mtime +1 -delete
```

### Kubernetes CronJob (Recommended)

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: tus-cleanup
  namespace: waveforge-pro
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: cleanup
            image: waveforge-pro:latest
            command:
            - /bin/sh
            - -c
            - |
              find /app/data/tus_sessions -type f -mtime +1 -delete
              find /app/data/tus_uploads -type f -mtime +1 -delete
            volumeMounts:
            - name: tus-uploads
              mountPath: /app/data/tus_uploads
            - name: tus-sessions
              mountPath: /app/data/tus_sessions
          restartPolicy: OnFailure
          volumes:
          - name: tus-uploads
            persistentVolumeClaim:
              claimName: waveforge-tus-uploads-pvc
          - name: tus-sessions
            persistentVolumeClaim:
              claimName: waveforge-tus-sessions-pvc
```

## Troubleshooting

### Issue: TUS Uploads Failing

**Check:**
1. PVC mounts: `kubectl describe pod -n waveforge-pro <pod-name>`
2. Permissions: Ensure pod user can write to volumes
3. Environment variables: `kubectl exec -n waveforge-pro <pod-name> -- env | grep TUS`

### Issue: Resume Not Working

**Check:**
1. Session affinity: Verify `sessionAffinity: ClientIP` in Service
2. Session directory: Verify session metadata exists
3. Chunk directory: Verify chunks exist at expected paths

### Issue: Storage Full

**Check:**
1. PVC usage: `kubectl exec -n waveforge-pro <pod-name> -- df -h`
2. Old sessions: Run cleanup job manually
3. Expand PVC: `kubectl patch pvc waveforge-tus-uploads-pvc -n waveforge-pro -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'`

### Issue: Multiple Pods, Different Sessions

**Solution:** Implement Redis-backed session store for distributed environments:

```python
# Future enhancement - backend/app/routes/tus_upload.py
import redis
redis_client = redis.Redis(host='redis-service', port=6379, decode_responses=True)

# Store session in Redis instead of local dict
upload_sessions[session_id] = {...}  # Current
redis_client.hset(f"tus:session:{session_id}", mapping={...})  # Distributed
```

## Security Considerations

### Production Checklist

- [ ] Enable HTTPS/TLS for all connections
- [ ] Set `CORS_ORIGINS` to specific domains
- [ ] Implement rate limiting on TUS endpoints
- [ ] Add authentication/authorization for upload endpoints
- [ ] Enable network policies to restrict pod communication
- [ ] Use secrets for sensitive environment variables
- [ ] Regular security scanning of container images
- [ ] Monitor for suspicious upload patterns

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: waveforge-network-policy
  namespace: waveforge-pro
spec:
  podSelector:
    matchLabels:
      app: waveforge-pro
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 53  # DNS
```

## Performance Tuning

### For High Concurrency

1. **Increase worker processes:** Adjust uvicorn workers
2. **Optimize chunk size:** Balance between resumability and overhead
3. **Use faster storage:** SSD-backed storage classes
4. **Enable caching:** Consider Redis for session caching
5. **Load balancing:** Multiple replicas with proper affinity

### Recommended Production Settings

```yaml
env:
- name: UVICORN_WORKERS
  value: "4"
- name: TUS_CHUNK_SIZE
  value: "1048576"  # 1MB for faster networks
- name: MAX_CONCURRENT_UPLOADS
  value: "10"

resources:
  requests:
    memory: "1Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "4000m"
```

## Migration from Custom to TUS

If upgrading from custom upload system:

1. **Deploy with both methods enabled** - Allow clients to choose
2. **Monitor adoption** - Track which method is used
3. **Gradual rollout** - Change `DEFAULT_UPLOAD_METHOD` to `tus`
4. **Deprecation period** - Keep custom method for 30-90 days
5. **Remove custom** - Once TUS adoption is complete

## Support

For issues or questions:
- Architecture docs: `docs/architecture/TUS_UPLOAD_SYSTEM.md`
- GitHub Issues: https://github.com/bmaier/waveforge/issues
- Email: support@waveforge.pro
