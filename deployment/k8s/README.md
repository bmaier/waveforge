# WaveForge Pro Kustomize Deployment

This directory contains Kustomize configurations for multi-stage Kubernetes deployments.

## Quick Start

```bash
# Deploy to development
./scripts/deploy-k8s.sh deploy development

# Deploy to staging
./scripts/deploy-k8s.sh deploy staging

# Deploy to production
./scripts/deploy-k8s.sh deploy production
```

## Structure

```
k8s/
├── base/                   # Base configuration (shared)
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── configmap.yaml
│   ├── pvc.yaml
│   └── ingress.yaml
│
└── overlays/              # Environment-specific
    ├── development/       # Dev environment
    ├── staging/          # Staging environment
    └── production/       # Production environment
```

## Environments

| Environment | Namespace | Replicas | Domain | HTTPS | HSTS |
|------------|-----------|----------|--------|-------|------|
| Development | waveforge-dev | 1 | dev.waveforge-pro.example.com | ✅ (Staging) | ❌ |
| Staging | waveforge-staging | 2 | staging.waveforge-pro.example.com | ✅ (Staging) | ❌ |
| Production | waveforge-prod | 3-10 | waveforge-pro.example.com | ✅ (Prod) | ✅ |

## 🔒 Security Features

### HTTPS by Default

All deployments automatically include:
- ✅ **Automatic TLS/SSL** - Certificates via cert-manager + Let's Encrypt
- ✅ **Forced HTTPS** - All HTTP traffic redirected to HTTPS
- ✅ **HSTS** - HTTP Strict Transport Security (production)
- ✅ **Security Headers** - X-Frame-Options, X-Content-Type-Options, etc.
- ✅ **Auto-Renewal** - Certificates renewed automatically

### Certificate Management

- **Development/Staging**: Let's Encrypt Staging (for testing)
- **Production**: Let's Encrypt Production
- **Renewal**: Automatic (30 days before expiration)
- **Validity**: 90 days per certificate

## Documentation

- **Full Guide**: See [docs/deployment/KUSTOMIZE_DEPLOYMENT.md](../../docs/deployment/KUSTOMIZE_DEPLOYMENT.md)
- **HTTPS Configuration**: See [docs/deployment/HTTPS_CONFIGURATION.md](../../docs/deployment/HTTPS_CONFIGURATION.md)
- **Quick Reference**: See [docs/deployment/KUSTOMIZE_QUICK_REFERENCE.md](../../docs/deployment/KUSTOMIZE_QUICK_REFERENCE.md)

## Prerequisites

- kubectl
- kustomize
- Kubernetes cluster access

## Commands

```bash
# Deploy
./scripts/deploy-k8s.sh deploy <environment>

# Status
./scripts/deploy-k8s.sh status <environment>

# Rollback
./scripts/rollback-k8s.sh <environment>

# Validate
./scripts/deploy-k8s.sh validate <environment>
```

## Configuration Inheritance

All overlays inherit from the base configuration and apply environment-specific patches:

- **Development**: Lower resources, debug logging, single replica
- **Staging**: Medium resources, info logging, 2 replicas
- **Production**: High resources, warning logging, 3+ replicas with HPA

For detailed information, see the full documentation.
