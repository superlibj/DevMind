#!/bin/bash
# AI Code Development Agent Test Runner Script

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="all"
COVERAGE=true
PARALLEL=false
VERBOSE=false
FAST=false
CLEAN=false

# Print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Show usage information
show_usage() {
    cat << EOF
AI Code Development Agent Test Runner

Usage: $0 [OPTIONS]

Options:
    -t, --type TYPE           Test type: unit, integration, e2e, security, performance, all (default: all)
    -c, --no-coverage         Disable code coverage reporting
    -p, --parallel            Run tests in parallel
    -v, --verbose             Verbose test output
    -f, --fast                Skip slow tests
    -C, --clean               Clean test artifacts before running
    -h, --help                Show this help message

Test Types:
    unit                      Unit tests only
    integration              Integration tests only
    e2e                      End-to-end tests only
    security                 Security-focused tests only
    performance              Performance tests only
    all                      All tests (default)

Examples:
    $0                                    # Run all tests with coverage
    $0 -t unit -p                        # Run unit tests in parallel
    $0 -t integration -v                 # Run integration tests with verbose output
    $0 -f -c                             # Run fast tests without coverage
    $0 -C -t all                         # Clean and run all tests

Environment Variables:
    PYTEST_ARGS               Additional pytest arguments
    TEST_DATABASE_URL          Test database URL override
    CI                        Set to 'true' for CI environment
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--type)
                TEST_TYPE="$2"
                shift 2
                ;;
            -c|--no-coverage)
                COVERAGE=false
                shift
                ;;
            -p|--parallel)
                PARALLEL=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -f|--fast)
                FAST=true
                shift
                ;;
            -C|--clean)
                CLEAN=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Validate test type
validate_test_type() {
    case $TEST_TYPE in
        unit|integration|e2e|security|performance|all)
            ;;
        *)
            print_error "Invalid test type: $TEST_TYPE"
            show_usage
            exit 1
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check if pytest is installed
    if ! command -v pytest &> /dev/null; then
        print_error "pytest is not installed. Please install it with: pip install pytest"
        exit 1
    fi

    # Check if we're in the right directory
    if [[ ! -f "pytest.ini" ]]; then
        print_error "pytest.ini not found. Please run this script from the project root."
        exit 1
    fi

    print_success "Prerequisites check completed"
}

# Clean test artifacts
clean_artifacts() {
    if [[ "$CLEAN" == "true" ]]; then
        print_info "Cleaning test artifacts..."

        # Remove coverage files
        rm -rf htmlcov/
        rm -f coverage.xml
        rm -f .coverage

        # Remove pytest cache
        rm -rf .pytest_cache/

        # Remove test database
        rm -f test.db

        # Remove __pycache__ directories
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

        # Remove .pyc files
        find . -name "*.pyc" -delete 2>/dev/null || true

        print_success "Test artifacts cleaned"
    fi
}

# Set up test environment
setup_environment() {
    print_info "Setting up test environment..."

    # Set test environment variables
    export APP__ENVIRONMENT="test"
    export APP__DEBUG="true"
    export SECURITY__JWT_SECRET_KEY="test-secret-key"

    # Use test database
    if [[ -n "${TEST_DATABASE_URL:-}" ]]; then
        export DATABASE_URL="$TEST_DATABASE_URL"
    else
        export DATABASE_URL="sqlite:///./test.db"
    fi

    export REDIS_URL="redis://localhost:6379/1"

    # Disable external API calls in tests
    export OPENAI_API_KEY="test-key"
    export ANTHROPIC_API_KEY="test-key"

    print_success "Test environment configured"
}

# Build pytest command
build_pytest_command() {
    local cmd="pytest"

    # Add test type selection
    case $TEST_TYPE in
        unit)
            cmd="$cmd -m unit"
            ;;
        integration)
            cmd="$cmd -m integration"
            ;;
        e2e)
            cmd="$cmd -m e2e"
            ;;
        security)
            cmd="$cmd -m security"
            ;;
        performance)
            cmd="$cmd -m performance"
            ;;
        all)
            # Run all tests - no specific marker
            ;;
    esac

    # Add coverage options
    if [[ "$COVERAGE" == "true" ]]; then
        cmd="$cmd --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml"
        cmd="$cmd --cov-fail-under=70"  # Minimum coverage threshold
    else
        cmd="$cmd --no-cov"
    fi

    # Add parallel execution
    if [[ "$PARALLEL" == "true" ]]; then
        # Use auto-detection for number of cores
        cmd="$cmd -n auto"
    fi

    # Add verbose output
    if [[ "$VERBOSE" == "true" ]]; then
        cmd="$cmd -v -s"
    fi

    # Skip slow tests if fast mode
    if [[ "$FAST" == "true" ]]; then
        cmd="$cmd -m 'not slow'"
    fi

    # CI-specific options
    if [[ "${CI:-}" == "true" ]]; then
        cmd="$cmd --tb=short --strict-markers --strict-config"
        cmd="$cmd --junit-xml=test-results.xml"
    fi

    # Add any additional pytest arguments
    if [[ -n "${PYTEST_ARGS:-}" ]]; then
        cmd="$cmd $PYTEST_ARGS"
    fi

    echo "$cmd"
}

# Run tests
run_tests() {
    print_info "Running $TEST_TYPE tests..."

    local pytest_cmd
    pytest_cmd=$(build_pytest_command)

    print_info "Executing: $pytest_cmd"

    # Run pytest and capture exit code
    local exit_code=0
    if ! eval "$pytest_cmd"; then
        exit_code=$?
    fi

    return $exit_code
}

# Generate test report
generate_report() {
    print_info "Generating test report..."

    if [[ "$COVERAGE" == "true" && -f ".coverage" ]]; then
        print_info "Coverage report:"
        coverage report --show-missing

        if [[ -d "htmlcov" ]]; then
            print_info "HTML coverage report available at: htmlcov/index.html"
        fi
    fi

    # Show test results summary
    if [[ -f "test-results.xml" ]]; then
        print_info "JUnit test results available at: test-results.xml"
    fi
}

# Check test results
check_results() {
    local exit_code=$1

    if [[ $exit_code -eq 0 ]]; then
        print_success "All tests passed!"
        return 0
    elif [[ $exit_code -eq 1 ]]; then
        print_error "Some tests failed!"
        return 1
    elif [[ $exit_code -eq 2 ]]; then
        print_error "Test execution was interrupted!"
        return 2
    elif [[ $exit_code -eq 3 ]]; then
        print_error "Internal pytest error!"
        return 3
    elif [[ $exit_code -eq 4 ]]; then
        print_error "pytest command line usage error!"
        return 4
    elif [[ $exit_code -eq 5 ]]; then
        print_error "No tests found!"
        return 5
    else
        print_error "Unknown test failure (exit code: $exit_code)!"
        return $exit_code
    fi
}

# Show performance summary
show_performance() {
    if [[ "$TEST_TYPE" == "performance" || "$TEST_TYPE" == "all" ]] && [[ -f ".pytest_cache/README.md" ]]; then
        print_info "Performance test results are cached in .pytest_cache/"
    fi
}

# Main function
main() {
    echo "AI Code Development Agent Test Runner"
    echo "====================================="
    echo ""

    parse_args "$@"
    validate_test_type

    print_info "Running $TEST_TYPE tests with coverage: $COVERAGE, parallel: $PARALLEL"

    check_prerequisites
    clean_artifacts
    setup_environment

    local exit_code
    if run_tests; then
        exit_code=0
    else
        exit_code=$?
    fi

    generate_report
    show_performance

    check_results $exit_code
    local final_exit_code=$?

    if [[ $final_exit_code -eq 0 ]]; then
        print_success "Test run completed successfully!"
    else
        print_error "Test run failed!"
    fi

    exit $final_exit_code
}

# Run main function
main "$@"