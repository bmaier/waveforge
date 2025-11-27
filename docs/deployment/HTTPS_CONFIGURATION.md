# HTTPS Configuration

## Overview

WaveForge Pro is configured to use **HTTPS by default** across all environments for secure communication.

## Configuration Summary

### Base Configuration
- **SSL Redirect**: Enabled (`ssl-redirect: true`)
- **Force SSL**: Enabled (`force-ssl-redirect: true`)
- **TLS Certificates**: Managed by cert-manager with Let's Encrypt

### Environment-Specific HTTPS Settings

| Environment | TLS Issuer | HSTS | Security Headers | Domain |
|------------|------------|------|------------------|--------|
| Development | letsencrypt-staging | No | Basic | dev.waveforge-pro.example.com |
| Staging | letsencrypt-staging | No | Basic | staging.waveforge-pro.example.com |
| Production | letsencrypt-prod | Yes (1 year) | Full | waveforge-pro.example.com |

## Production Security Features

### HSTS (HTTP Strict Transport Security)
- **Enabled**: Yes
- **Max Age**: 31536000 seconds (1 year)
- **Include Subdomains**: Yes
- **Preload**: Yes

### Security Headers
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

## Certificate Management

### Automatic Certificate Provisioning

Certificates are automatically provisioned and renewed by **cert-manager** using Let's Encrypt:

```yaml
# Production
cert-manager.io/cluster-issuer: "letsencrypt-prod"

# Development/Staging
cert-manager.io/cluster-issuer: "letsencrypt-staging"
```

### Certificate Renewal
- Certificates are automatically renewed 30 days before expiration
- No manual intervention required
- Renewal happens in the background without downtime

## Local Development

When running locally with `./start.sh`, the server runs on HTTP:
```
http://localhost:8000
```

**Note**: HTTPS is automatically enabled when deployed to Kubernetes with the provided configurations.

## Setup Instructions

### Prerequisites

1. **Install cert-manager** in your Kubernetes cluster:
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

2. **Create ClusterIssuers** for Let's Encrypt:

**Staging Issuer** (for dev/staging):
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
    - http01:
        ingress:
          class: nginx
```

**Production Issuer**:
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

Apply the issuers:
```bash
kubectl apply -f letsencrypt-staging.yaml
kubectl apply -f letsencrypt-prod.yaml
```

### Verify Certificate Status

```bash
# Check certificate
kubectl get certificate -n <namespace>

# Describe certificate for details
kubectl describe certificate <name> -n <namespace>

# Check certificate secret
kubectl get secret <tls-secret-name> -n <namespace>
```

## CORS Configuration

HTTPS-enabled CORS origins are configured per environment:

### Development
```yaml
CORS_ORIGINS: https://dev.waveforge-pro.example.com,http://localhost:3000,http://localhost:8000
```

### Staging
```yaml
CORS_ORIGINS: https://staging.waveforge-pro.example.com
```

### Production
```yaml
CORS_ORIGINS: https://waveforge-pro.example.com,https://www.waveforge-pro.example.com
```

## Testing HTTPS

### 1. Test Certificate
```bash
curl -v https://waveforge-pro.example.com
```

### 2. Verify HSTS Headers (Production)
```bash
curl -I https://waveforge-pro.example.com | grep -i strict-transport-security
```

### 3. Test SSL/TLS Configuration
```bash
# Using testssl.sh
testssl.sh https://waveforge-pro.example.com

# Using SSL Labs (web-based)
# Visit: https://www.ssllabs.com/ssltest/
```

### 4. Check Force HTTPS Redirect
```bash
# Should redirect to HTTPS
curl -I http://waveforge-pro.example.com
```

## Troubleshooting

### Certificate Not Issued

```bash
# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Check certificate status
kubectl describe certificate <name> -n <namespace>

# Check challenges
kubectl get challenges -n <namespace>
```

### Common Issues

1. **DNS not configured**: Ensure your domain points to the ingress controller
2. **ClusterIssuer not found**: Create the ClusterIssuer (see Setup Instructions)
3. **HTTP-01 challenge failing**: Check ingress controller and firewall rules
4. **Rate limits**: Use staging issuer for testing, production for final deployment

### Force Certificate Renewal

```bash
# Delete certificate to force renewal
kubectl delete certificate <name> -n <namespace>

# Certificate will be automatically recreated
```

## Best Practices

1. ✅ **Always use HTTPS in production**
2. ✅ **Enable HSTS for production** (already configured)
3. ✅ **Use staging issuer for testing** to avoid rate limits
4. ✅ **Monitor certificate expiration** (automatic with cert-manager)
5. ✅ **Test SSL configuration regularly** with SSL Labs
6. ✅ **Keep cert-manager updated** for security fixes
7. ✅ **Use strong ciphers** (handled by nginx ingress controller)
8. ✅ **Enable security headers** (already configured in production)

## Security Considerations

### TLS Version
- Minimum: TLS 1.2
- Recommended: TLS 1.3

### Cipher Suites
The nginx ingress controller uses Mozilla's "Intermediate" configuration by default, which provides a good balance between security and compatibility.

### Certificate Validity
- Let's Encrypt certificates are valid for 90 days
- Automatic renewal occurs at 60 days
- cert-manager handles this automatically

## Additional Resources

- [cert-manager Documentation](https://cert-manager.io/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [nginx Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [SSL Labs Testing](https://www.ssllabs.com/ssltest/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)

## Support

For HTTPS-related issues:
1. Check cert-manager logs
2. Verify ClusterIssuer configuration
3. Test DNS resolution
4. Review ingress annotations
5. See [KUSTOMIZE_DEPLOYMENT.md](KUSTOMIZE_DEPLOYMENT.md) for general deployment issues

---

**Last Updated**: November 2025  
**Version**: 1.0.0
