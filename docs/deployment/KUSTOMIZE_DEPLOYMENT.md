# Kubernetes Deployment with Kustomize

## Overview

WaveForge Pro uses **Kustomize** for multi-stage Kubernetes deployments, providing a declarative approach to manage configurations across different environments (development, staging, production) while maintaining a single source of truth.

## Table of Contents

- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Environments](#environments)
- [Prerequisites](#prerequisites)
- [Deployment Guide](#deployment-guide)
- [Configuration Inheritance](#configuration-inheritance)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Architecture

### Kustomize Structure

```
deployment/k8s/
├── base/                          # Base configuration (shared)
│   ├── kustomization.yaml        # Base kustomization
│   ├── namespace.yaml            # Namespace definition
│   ├── deployment.yaml           # Deployment specification
│   ├── configmap.yaml            # Configuration settings
│   ├── pvc.yaml                  # Persistent volume claim
│   └── ingress.yaml              # Ingress configuration
│
└── overlays/                      # Environment-specific overrides
    ├── development/
    │   ├── kustomization.yaml    # Dev kustomization
    │   ├── deployment-patch.yaml # Dev deployment patches
    │   └── ingress-patch.yaml    # Dev ingress patches
    │
    ├── staging/
    │   ├── kustomization.yaml    # Staging kustomization
    │   ├── deployment-patch.yaml # Staging deployment patches
    │   ├── ingress-patch.yaml    # Staging ingress patches
    │   └── pvc-patch.yaml        # Staging storage patches
    │
    └── production/
        ├── kustomization.yaml    # Prod kustomization
        ├── deployment-patch.yaml # Prod deployment patches
        ├── ingress-patch.yaml    # Prod ingress patches
        ├── pvc-patch.yaml        # Prod storage patches
        └── hpa-patch.yaml        # Horizontal Pod Autoscaler
```

### Configuration Inheritance Model

```
┌─────────────────────────────────────────┐
│           BASE Configuration            │
│  (Shared across all environments)       │
│  - Namespace structure                  │
│  - Core deployment spec                 │
│  - Service definitions                  │
│  - Basic ConfigMaps                     │
│  - PVC templates                        │
│  - Ingress templates                    │
└─────────────────┬───────────────────────┘
                  │
         ┌────────┴────────┬────────────┐
         │                 │            │
         ▼                 ▼            ▼
┌─────────────────┐ ┌──────────┐ ┌─────────────┐
│  DEVELOPMENT    │ │ STAGING  │ │ PRODUCTION  │
│  - 1 replica    │ │ - 2 reps │ │ - 3+ reps   │
│  - Low res      │ │ - Med res│ │ - High res  │
│  - Debug on     │ │ - Info   │ │ - Warn logs │
│  - Dev domain   │ │ - Stg dom│ │ - Prod dom  │
│  - 128-256Mi    │ │ - 256-512│ │ - 512Mi-1Gi │
└─────────────────┘ └──────────┘ └─────────────┘
```

## Directory Structure

### Base Configuration

The `base/` directory contains the fundamental Kubernetes manifests that are shared across all environments:

**kustomization.yaml**
- Defines resources to include
- Sets common labels and annotations
- Configures base images
- Generates base ConfigMaps

**Resources:**
- `namespace.yaml` - Creates the waveforge-pro namespace
- `deployment.yaml` - Main application deployment
- `configmap.yaml` - Application configuration
- `pvc.yaml` - Persistent storage for uploaded files
- `ingress.yaml` - HTTP/HTTPS routing

### Overlay Configurations

Each overlay inherits from base and applies environment-specific patches:

**Development Overlay** (`overlays/development/`)
- Single replica for cost efficiency
- Debug logging enabled
- Lower resource limits (128-256Mi RAM)
- Development domain (dev.waveforge-pro.example.com)
- Staging TLS certificates

**Staging Overlay** (`overlays/staging/`)
- 2 replicas for limited HA
- Info-level logging
- Medium resource limits (256-512Mi RAM)
- Staging domain (staging.waveforge-pro.example.com)
- Health checks configured
- 20Gi storage

**Production Overlay** (`overlays/production/`)
- 3+ replicas for high availability
- Warning-level logging
- High resource limits (512Mi-1Gi RAM)
- Production domain (waveforge-pro.example.com)
- Production TLS certificates
- Pod anti-affinity for distribution
- Horizontal Pod Autoscaler (3-10 pods)
- 50Gi storage
- Comprehensive health checks

## Environments

### Environment Comparison

| Feature | Development | Staging | Production |
|---------|-------------|---------|------------|
| **Namespace** | waveforge-dev | waveforge-staging | waveforge-prod |
| **Replicas** | 1 | 2 | 3-10 (HPA) |
| **CPU Request** | 100m | 250m | 500m |
| **CPU Limit** | 250m | 500m | 1000m |
| **Memory Request** | 128Mi | 256Mi | 512Mi |
| **Memory Limit** | 256Mi | 512Mi | 1Gi |
| **Storage** | 10Gi | 20Gi | 50Gi |
| **Log Level** | debug | info | warning |
| **Debug Mode** | true | false | false |
| **Domain** | dev.waveforge-pro.example.com | staging.waveforge-pro.example.com | waveforge-pro.example.com |
| **TLS Issuer** | letsencrypt-staging | letsencrypt-staging | letsencrypt-prod |
| **Max Upload** | 50MB | 100MB | 200MB |
| **Rate Limiting** | - | 100 req/s | 200 req/s |
| **Monitoring** | Basic | Enabled | Full + Alerting |
| **Backup** | None | Enabled | Enabled + Retention |

## Prerequisites

### Required Tools

1. **kubectl** - Kubernetes command-line tool
   ```bash
   # macOS
   brew install kubectl
   
   # Linux
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   chmod +x kubectl
   sudo mv kubectl /usr/local/bin/
   ```

2. **kustomize** - Kubernetes native configuration management
   ```bash
   # macOS
   brew install kustomize
   
   # Linux
   curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
   sudo mv kustomize /usr/local/bin/
   ```

3. **Kubernetes Cluster** - Access to a K8s cluster
   - Minikube (local development)
   - Kind (Kubernetes in Docker)
   - GKE, EKS, AKS (cloud providers)
   - On-premises cluster

### Cluster Setup

#### Option 1: Minikube (Local)

```bash
# Install minikube
brew install minikube

# Start cluster
minikube start --memory=4096 --cpus=2

# Enable ingress
minikube addons enable ingress

# Get cluster info
kubectl cluster-info
```

#### Option 2: Kind (Kubernetes in Docker)

```bash
# Install kind
brew install kind

# Create cluster with ingress
cat <<EOF | kind create cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
  - containerPort: 443
    hostPort: 443
EOF
```

### Required Kubernetes Components

1. **Ingress Controller** (NGINX)
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml
   ```

2. **Cert-Manager** (TLS certificates)
   ```bash
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
   ```

3. **Metrics Server** (for HPA in production)
   ```bash
   kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
   ```

## Deployment Guide

### Quick Start

Use the provided deployment script for easy management:

```bash
# Deploy to development
./scripts/deploy-k8s.sh deploy development

# Deploy to staging
./scripts/deploy-k8s.sh deploy staging

# Deploy to production
./scripts/deploy-k8s.sh deploy production
```

### Manual Deployment

#### 1. Build Manifests (Preview)

```bash
# Build development manifests
kustomize build deployment/k8s/overlays/development

# Build staging manifests
kustomize build deployment/k8s/overlays/staging

# Build production manifests
kustomize build deployment/k8s/overlays/production
```

#### 2. Validate Configuration

```bash
# Validate before deploying
kustomize build deployment/k8s/overlays/development | kubectl apply --dry-run=server -f -
```

#### 3. Deploy to Environment

```bash
# Deploy to development
kustomize build deployment/k8s/overlays/development | kubectl apply -f -

# Deploy to staging
kustomize build deployment/k8s/overlays/staging | kubectl apply -f -

# Deploy to production
kustomize build deployment/k8s/overlays/production | kubectl apply -f -
```

#### 4. Verify Deployment

```bash
# Check deployment status
./scripts/deploy-k8s.sh status <environment>

# Or manually:
kubectl get all -n waveforge-dev        # Development
kubectl get all -n waveforge-staging    # Staging
kubectl get all -n waveforge-prod       # Production
```

### Deployment Script Commands

The `deploy-k8s.sh` script provides comprehensive deployment management:

```bash
# Deploy
./scripts/deploy-k8s.sh deploy <env>              # Deploy to environment
./scripts/deploy-k8s.sh deploy <env> --dry-run    # Dry run (preview changes)

# Validate
./scripts/deploy-k8s.sh validate <env>            # Validate manifests

# Status
./scripts/deploy-k8s.sh status <env>              # Show deployment status

# Diff
./scripts/deploy-k8s.sh diff <env>                # Show configuration differences

# Build
./scripts/deploy-k8s.sh build <env>               # Build and display manifests

# Delete
./scripts/deploy-k8s.sh delete <env>              # Delete deployment (with confirmation)
```

### Rollback

Use the rollback script to revert deployments:

```bash
# Rollback to previous version
./scripts/rollback-k8s.sh <environment>

# Rollback to specific revision
./scripts/rollback-k8s.sh <environment> <revision>

# Examples:
./scripts/rollback-k8s.sh staging
./scripts/rollback-k8s.sh production 3
```

## Configuration Inheritance

### How Kustomize Inheritance Works

1. **Base Layer** - Defines common resources
2. **Overlay Layer** - Applies environment-specific patches
3. **Merge Strategy** - Strategic merge or JSON patch

### Example: Deployment Inheritance

**Base Deployment** (`base/deployment.yaml`)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: waveforge-pro
spec:
  replicas: 1  # Default
  template:
    spec:
      containers:
      - name: waveforge-pro
        image: waveforge-pro:latest
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
```

**Production Patch** (`overlays/production/deployment-patch.yaml`)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: waveforge-pro
spec:
  replicas: 3  # Override: 3 replicas
  template:
    spec:
      containers:
      - name: waveforge-pro
        resources:
          requests:
            memory: "512Mi"  # Override: More memory
            cpu: "500m"      # Override: More CPU
```

**Result**: Production deployment gets 3 replicas with higher resources while inheriting all other settings from base.

### ConfigMap Inheritance

ConfigMaps use a **merge behavior** to combine base and overlay values:

**Base ConfigMap**
```yaml
configMapGenerator:
  - name: app-config-base
    literals:
      - APP_NAME=WaveForge Pro
      - LOG_FORMAT=json
```

**Production Overlay**
```yaml
configMapGenerator:
  - name: app-config
    behavior: merge
    literals:
      - ENVIRONMENT=production
      - LOG_LEVEL=warning
```

**Result**: Combined ConfigMap with all settings.

### Common Customization Patterns

#### 1. Namespace Transformation
```yaml
# In kustomization.yaml
namespace: waveforge-prod
```

#### 2. Name Prefix/Suffix
```yaml
# In kustomization.yaml
namePrefix: prod-
nameSuffix: -v1
```

#### 3. Label Injection
```yaml
# In kustomization.yaml
commonLabels:
  environment: production
  team: platform
```

#### 4. Image Tag Override
```yaml
# In kustomization.yaml
images:
  - name: waveforge-pro
    newTag: v1.2.3
```

#### 5. Resource Patches
```yaml
# In kustomization.yaml
patchesStrategicMerge:
  - deployment-patch.yaml
  - service-patch.yaml
```

## Best Practices

### 1. Version Control
- ✅ Keep all Kustomize configurations in Git
- ✅ Use branches for major configuration changes
- ✅ Tag production deployments with version numbers
- ✅ Review changes via pull requests

### 2. Configuration Management
- ✅ Store secrets in Kubernetes Secrets, not ConfigMaps
- ✅ Use external secret management (Vault, AWS Secrets Manager)
- ✅ Keep sensitive data out of Git (use `.gitignore`)
- ✅ Document all configuration options

### 3. Deployment Strategy
- ✅ Always deploy to dev → staging → production
- ✅ Use `--dry-run` to preview changes
- ✅ Run `validate` before deploying
- ✅ Monitor deployments with `kubectl rollout status`
- ✅ Keep rollback plan ready

### 4. Resource Management
- ✅ Set resource requests and limits for all containers
- ✅ Use HPA for production workloads
- ✅ Configure pod anti-affinity for HA
- ✅ Set appropriate termination grace periods

### 5. Monitoring and Observability
- ✅ Enable health checks (liveness/readiness probes)
- ✅ Configure logging with appropriate levels
- ✅ Set up metrics collection (Prometheus)
- ✅ Configure alerting for critical issues

### 6. Security
- ✅ Use TLS for all ingress endpoints
- ✅ Enable RBAC for Kubernetes access
- ✅ Run containers as non-root users
- ✅ Scan images for vulnerabilities
- ✅ Keep base images updated

### 7. Testing
- ✅ Test configurations in development first
- ✅ Use staging as production replica
- ✅ Validate manifests before applying
- ✅ Test rollback procedures regularly

## Troubleshooting

### Common Issues

#### 1. Deployment Fails to Start

```bash
# Check pod status
kubectl get pods -n <namespace>

# View pod logs
kubectl logs <pod-name> -n <namespace>

# Describe pod for events
kubectl describe pod <pod-name> -n <namespace>
```

#### 2. Image Pull Errors

```bash
# Check image name and tag
kubectl get deployment <name> -n <namespace> -o yaml | grep image:

# Verify image exists
docker pull <image-name>:<tag>

# Check image pull secrets
kubectl get secrets -n <namespace>
```

#### 3. Configuration Issues

```bash
# View current ConfigMap
kubectl get configmap -n <namespace>
kubectl describe configmap <name> -n <namespace>

# Check environment variables
kubectl exec <pod-name> -n <namespace> -- env
```

#### 4. Ingress Not Working

```bash
# Check ingress status
kubectl get ingress -n <namespace>
kubectl describe ingress <name> -n <namespace>

# Check ingress controller
kubectl get pods -n ingress-nginx

# View ingress controller logs
kubectl logs -n ingress-nginx <controller-pod>
```

#### 5. Storage Issues

```bash
# Check PVC status
kubectl get pvc -n <namespace>
kubectl describe pvc <name> -n <namespace>

# Check PV
kubectl get pv
```

#### 6. Resource Limits

```bash
# Check resource usage
kubectl top pods -n <namespace>
kubectl top nodes

# View resource requests/limits
kubectl describe pod <name> -n <namespace> | grep -A 5 Limits
```

### Debug Commands

```bash
# Get all resources
kubectl get all -n <namespace>

# Check events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Port-forward for local testing
kubectl port-forward -n <namespace> pod/<pod-name> 8000:8000

# Execute commands in pod
kubectl exec -it <pod-name> -n <namespace> -- /bin/bash

# View logs with follow
kubectl logs -f <pod-name> -n <namespace>

# Check deployment rollout status
kubectl rollout status deployment/<name> -n <namespace>

# View rollout history
kubectl rollout history deployment/<name> -n <namespace>
```

### Kustomize-Specific Issues

#### Validation Errors

```bash
# Check Kustomize build output
kustomize build deployment/k8s/overlays/<env>

# Validate against cluster
kustomize build deployment/k8s/overlays/<env> | kubectl apply --dry-run=server -f -
```

#### Patch Not Applying

```bash
# Verify patch syntax
kustomize build deployment/k8s/overlays/<env> | grep -A 10 <resource-name>

# Check strategic merge keys
# Ensure patches match resource names exactly
```

#### ConfigMap Not Merging

```bash
# Check merge behavior
# In kustomization.yaml:
configMapGenerator:
  - name: app-config
    behavior: merge  # Must be set for merging
```

## Advanced Topics

### Multi-Cluster Deployment

For deploying across multiple clusters:

```bash
# Set context for each cluster
kubectl config use-context dev-cluster
kustomize build overlays/development | kubectl apply -f -

kubectl config use-context staging-cluster
kustomize build overlays/staging | kubectl apply -f -

kubectl config use-context prod-cluster
kustomize build overlays/production | kubectl apply -f -
```

### GitOps Integration

Integrate with ArgoCD or Flux:

```yaml
# ArgoCD Application
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: waveforge-pro-prod
  namespace: argocd
spec:
  source:
    repoURL: https://github.com/yourusername/waveforge-pro
    targetRevision: main
    path: deployment/k8s/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: waveforge-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Deploy to Kubernetes
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Kustomize
        run: |
          curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
          sudo mv kustomize /usr/local/bin/
      
      - name: Deploy to Staging
        run: |
          kustomize build deployment/k8s/overlays/staging | kubectl apply -f -
```

## Additional Resources

- [Kustomize Documentation](https://kustomize.io/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)

## Support

For issues or questions:
- GitHub Issues: https://github.com/yourusername/waveforge-pro/issues
- Documentation: See `docs/` directory
- API Reference: See `docs/api/REST_API.md`

---

**Last Updated**: November 2025  
**Version**: 1.0.0  
**Maintainer**: Berthold Maier 
