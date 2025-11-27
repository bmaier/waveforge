# Kustomize Quick Reference

## Quick Commands

### Deploy
```bash
# Development
./scripts/deploy-k8s.sh deploy development

# Staging
./scripts/deploy-k8s.sh deploy staging

# Production
./scripts/deploy-k8s.sh deploy production

# Dry run
./scripts/deploy-k8s.sh deploy production --dry-run
```

### Status
```bash
./scripts/deploy-k8s.sh status <environment>
```

### Rollback
```bash
# Rollback to previous
./scripts/rollback-k8s.sh <environment>

# Rollback to specific revision
./scripts/rollback-k8s.sh <environment> <revision>
```

### Validate
```bash
./scripts/deploy-k8s.sh validate <environment>
```

### Build & View
```bash
./scripts/deploy-k8s.sh build <environment>
```

### Diff
```bash
./scripts/deploy-k8s.sh diff <environment>
```

### Delete
```bash
./scripts/deploy-k8s.sh delete <environment>
```

## Environment Endpoints

All environments use **HTTPS by default** with automatic TLS/SSL:

- **Development**: https://dev.waveforge-pro.example.com (Let's Encrypt Staging)
- **Staging**: https://staging.waveforge-pro.example.com (Let's Encrypt Staging)
- **Production**: https://waveforge-pro.example.com (Let's Encrypt Production)
  - HSTS enabled (1 year)
  - Security headers enabled
  - Auto-renewal of certificates

**Note**: HTTP requests are automatically redirected to HTTPS.

## Namespaces

- Development: `waveforge-dev`
- Staging: `waveforge-staging`
- Production: `waveforge-prod`

## Manual Commands

```bash
# Build manifests
kustomize build deployment/k8s/overlays/<environment>

# Deploy
kustomize build deployment/k8s/overlays/<environment> | kubectl apply -f -

# Delete
kustomize build deployment/k8s/overlays/<environment> | kubectl delete -f -

# Check status
kubectl get all -n <namespace>

# View logs
kubectl logs -f deployment/<name> -n <namespace>

# Port forward
kubectl port-forward -n <namespace> svc/<service-name> 8000:80
```

## Troubleshooting

### General
```bash
# View pod logs
kubectl logs <pod-name> -n <namespace>

# Describe pod
kubectl describe pod <pod-name> -n <namespace>

# Get events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Check resources
kubectl top pods -n <namespace>

# Exec into pod
kubectl exec -it <pod-name> -n <namespace> -- /bin/bash
```

### HTTPS/TLS Troubleshooting
```bash
# Check certificate status
kubectl get certificate -n <namespace>
kubectl describe certificate <name> -n <namespace>

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Verify TLS secret
kubectl get secret <tls-secret-name> -n <namespace>

# Test HTTPS connection
curl -v https://<your-domain>

# Check HSTS headers (production)
curl -I https://<your-domain> | grep -i strict-transport-security
```

For detailed HTTPS troubleshooting, see [HTTPS_CONFIGURATION.md](HTTPS_CONFIGURATION.md)

## Configuration Files

### Base
- `deployment/k8s/base/kustomization.yaml` - Base configuration
- `deployment/k8s/base/*.yaml` - Base resources

### Overlays
- `deployment/k8s/overlays/<env>/kustomization.yaml` - Environment config
- `deployment/k8s/overlays/<env>/*-patch.yaml` - Environment patches

## Common Modifications

### Change Replicas
Edit `deployment/k8s/overlays/<env>/deployment-patch.yaml`:
```yaml
spec:
  replicas: <number>
```

### Change Domain
Edit `deployment/k8s/overlays/<env>/ingress-patch.yaml`:
```yaml
spec:
  rules:
    - host: <your-domain.com>
```

### Change Image Tag
Edit `deployment/k8s/overlays/<env>/kustomization.yaml`:
```yaml
images:
  - name: waveforge-pro
    newTag: <your-tag>
```

### Change Resources
Edit `deployment/k8s/overlays/<env>/deployment-patch.yaml`:
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

### Change Storage
Edit `deployment/k8s/overlays/<env>/pvc-patch.yaml`:
```yaml
spec:
  resources:
    requests:
      storage: 50Gi
```

## Order of Operations

1. **Validate**: `./scripts/deploy-k8s.sh validate <env>`
2. **Dry Run**: `./scripts/deploy-k8s.sh deploy <env> --dry-run`
3. **Deploy**: `./scripts/deploy-k8s.sh deploy <env>`
4. **Verify**: `./scripts/deploy-k8s.sh status <env>`
5. **Monitor**: `kubectl logs -f deployment/<name> -n <namespace>`

## Prerequisites

### Required
- kubectl installed and configured
- kustomize installed
- Access to Kubernetes cluster
- Appropriate RBAC permissions

### For HTTPS/TLS (Recommended)
- cert-manager installed in cluster
- Let's Encrypt ClusterIssuers configured
- DNS pointing to ingress controller
- Port 80/443 accessible

See [HTTPS_CONFIGURATION.md](HTTPS_CONFIGURATION.md) for setup instructions.

## Help

```bash
./scripts/deploy-k8s.sh help
./scripts/rollback-k8s.sh
```
