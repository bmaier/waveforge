#!/bin/bash

# WaveForge Pro - Rollback Script
# Rollback deployments to previous version

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to get namespace from environment
get_namespace() {
    local env=$1
    case $env in
        development)
            echo "waveforge-dev"
            ;;
        staging)
            echo "waveforge-staging"
            ;;
        production)
            echo "waveforge-prod"
            ;;
        *)
            print_error "Unknown environment: $env"
            exit 1
            ;;
    esac
}

# Function to show rollout history
show_history() {
    local env=$1
    local namespace=$(get_namespace "$env")
    local deployment=$(kubectl get deployments -n "$namespace" -o jsonpath='{.items[0].metadata.name}')
    
    print_info "Rollout history for ${env} environment:"
    kubectl rollout history deployment/"$deployment" -n "$namespace"
}

# Function to rollback deployment
rollback_deployment() {
    local env=$1
    local revision=$2
    local namespace=$(get_namespace "$env")
    local deployment=$(kubectl get deployments -n "$namespace" -o jsonpath='{.items[0].metadata.name}')
    
    print_warning "Rolling back ${env} environment..."
    
    if [ -z "$revision" ]; then
        kubectl rollout undo deployment/"$deployment" -n "$namespace"
    else
        kubectl rollout undo deployment/"$deployment" -n "$namespace" --to-revision="$revision"
    fi
    
    print_info "Waiting for rollback to complete..."
    kubectl rollout status deployment/"$deployment" -n "$namespace"
    print_success "Rollback completed for ${env} environment"
}

# Main script
if [ $# -eq 0 ]; then
    echo "Usage: $0 <environment> [revision]"
    echo ""
    echo "Environments: development, staging, production"
    echo "Revision: Optional revision number to rollback to (omit for previous)"
    echo ""
    echo "Examples:"
    echo "  $0 staging              # Rollback to previous version"
    echo "  $0 production 3         # Rollback to revision 3"
    exit 0
fi

environment=$1
revision=$2

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed"
    exit 1
fi

# Show history
show_history "$environment"
echo ""

# Confirm rollback
read -p "Do you want to rollback? (yes/no): " confirm
if [ "$confirm" = "yes" ]; then
    rollback_deployment "$environment" "$revision"
else
    print_info "Rollback cancelled"
fi
