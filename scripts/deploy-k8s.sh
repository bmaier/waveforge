#!/bin/bash

# WaveForge Pro - Kustomize Deployment Script
# Multi-stage deployment with environment selection

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
K8S_DIR="$PROJECT_ROOT/deployment/k8s"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

print_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

print_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

# Function to check if kubectl is installed
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    print_success "kubectl is installed"
}

# Function to check if kustomize is installed
check_kustomize() {
    if ! command -v kustomize &> /dev/null; then
        print_error "kustomize is not installed. Please install kustomize first."
        echo "Install with: brew install kustomize (macOS) or visit https://kubectl.docs.kubernetes.io/installation/kustomize/"
        exit 1
    fi
    print_success "kustomize is installed (version: $(kustomize version --short))"
}

# Function to verify kubernetes cluster connection
check_cluster() {
    print_info "Checking Kubernetes cluster connectivity..."
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    print_success "Connected to Kubernetes cluster: $(kubectl config current-context)"
}

# Function to build kustomize manifests
build_manifests() {
    local env=$1
    print_info "Building Kustomize manifests for ${env} environment..."
    
    if [ ! -d "$K8S_DIR/overlays/$env" ]; then
        print_error "Environment overlay not found: $env"
        exit 1
    fi
    
    kustomize build "$K8S_DIR/overlays/$env"
}

# Function to deploy to environment
deploy_environment() {
    local env=$1
    local dry_run=${2:-false}
    
    print_info "Deploying to ${env} environment..."
    
    if [ "$dry_run" = true ]; then
        print_warning "DRY RUN MODE - No actual deployment will occur"
        kustomize build "$K8S_DIR/overlays/$env" | kubectl apply --dry-run=client -f -
    else
        kustomize build "$K8S_DIR/overlays/$env" | kubectl apply -f -
        print_success "Deployment completed for ${env} environment"
    fi
}

# Function to delete environment
delete_environment() {
    local env=$1
    
    print_warning "Deleting ${env} environment..."
    read -p "Are you sure you want to delete the ${env} environment? (yes/no): " confirm
    
    if [ "$confirm" = "yes" ]; then
        kustomize build "$K8S_DIR/overlays/$env" | kubectl delete -f -
        print_success "Environment ${env} deleted"
    else
        print_info "Deletion cancelled"
    fi
}

# Function to show diff
show_diff() {
    local env=$1
    print_info "Showing diff for ${env} environment..."
    kustomize build "$K8S_DIR/overlays/$env" | kubectl diff -f - || true
}

# Function to validate manifests
validate_manifests() {
    local env=$1
    print_info "Validating manifests for ${env} environment..."
    kustomize build "$K8S_DIR/overlays/$env" | kubectl apply --dry-run=server -f -
    print_success "Manifests are valid"
}

# Function to display help
show_help() {
    cat << EOF
${GREEN}WaveForge Pro - Kustomize Deployment Script${NC}

Usage: $0 <command> <environment> [options]

${YELLOW}Commands:${NC}
  deploy        Deploy to specified environment
  delete        Delete deployment from environment
  diff          Show differences between current and desired state
  validate      Validate manifests without deploying
  build         Build and display manifests
  status        Show deployment status

${YELLOW}Environments:${NC}
  development   Development environment (dev.waveforge-pro.example.com)
  staging       Staging environment (staging.waveforge-pro.example.com)
  production    Production environment (waveforge-pro.example.com)

${YELLOW}Options:${NC}
  --dry-run     Simulate deployment without applying changes

${YELLOW}Examples:${NC}
  $0 deploy development
  $0 deploy production --dry-run
  $0 diff staging
  $0 validate production
  $0 build development
  $0 delete development
  $0 status production

${YELLOW}Prerequisites:${NC}
  - kubectl installed and configured
  - kustomize installed
  - Access to Kubernetes cluster
  - Appropriate RBAC permissions

EOF
}

# Function to show deployment status
show_status() {
    local env=$1
    local namespace=""
    
    case $env in
        development)
            namespace="waveforge-dev"
            ;;
        staging)
            namespace="waveforge-staging"
            ;;
        production)
            namespace="waveforge-prod"
            ;;
        *)
            print_error "Unknown environment: $env"
            exit 1
            ;;
    esac
    
    print_info "Status for ${env} environment (namespace: ${namespace}):"
    echo ""
    
    print_info "Deployments:"
    kubectl get deployments -n "$namespace" 2>/dev/null || print_warning "No deployments found"
    echo ""
    
    print_info "Pods:"
    kubectl get pods -n "$namespace" 2>/dev/null || print_warning "No pods found"
    echo ""
    
    print_info "Services:"
    kubectl get services -n "$namespace" 2>/dev/null || print_warning "No services found"
    echo ""
    
    print_info "Ingress:"
    kubectl get ingress -n "$namespace" 2>/dev/null || print_warning "No ingress found"
    echo ""
    
    print_info "PVCs:"
    kubectl get pvc -n "$namespace" 2>/dev/null || print_warning "No PVCs found"
}

# Main script logic
main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi
    
    local command=$1
    local environment=$2
    local dry_run=false
    
    # Check for --dry-run flag
    if [ "$3" = "--dry-run" ]; then
        dry_run=true
    fi
    
    # Check prerequisites for commands that need them
    if [ "$command" != "help" ] && [ "$command" != "build" ]; then
        check_kubectl
        check_kustomize
    fi
    
    case $command in
        deploy)
            if [ -z "$environment" ]; then
                print_error "Environment not specified"
                show_help
                exit 1
            fi
            check_cluster
            validate_manifests "$environment"
            deploy_environment "$environment" "$dry_run"
            ;;
        delete)
            if [ -z "$environment" ]; then
                print_error "Environment not specified"
                show_help
                exit 1
            fi
            check_cluster
            delete_environment "$environment"
            ;;
        diff)
            if [ -z "$environment" ]; then
                print_error "Environment not specified"
                show_help
                exit 1
            fi
            check_cluster
            show_diff "$environment"
            ;;
        validate)
            if [ -z "$environment" ]; then
                print_error "Environment not specified"
                show_help
                exit 1
            fi
            check_cluster
            validate_manifests "$environment"
            ;;
        build)
            if [ -z "$environment" ]; then
                print_error "Environment not specified"
                show_help
                exit 1
            fi
            check_kustomize
            build_manifests "$environment"
            ;;
        status)
            if [ -z "$environment" ]; then
                print_error "Environment not specified"
                show_help
                exit 1
            fi
            check_cluster
            show_status "$environment"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
