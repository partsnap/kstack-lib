# Changelog

All notable changes to kstack-lib will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of kstack-lib
- Redis client factory with async/sync auto-detection
- LocalStack client factory for AWS service emulation
- Route-based configuration discovery (vault + K8s secrets)
- Comprehensive unit test coverage (52 tests)
- Full API documentation with mkdocs
- CI/CD workflow with GitHub Actions

### Features
- Automatic async context detection
- Support for `part-raw` and `part-audit` Redis databases
- LocalStack integration for S3, RDS, and other AWS services
- Vault file configuration for local development
- Kubernetes secret configuration for deployed services
- ConfigMap-based route discovery

## [0.0.1] - 2025-10-04

### Added
- Initial library structure
- Basic client factories
- Configuration discovery system
