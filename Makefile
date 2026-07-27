REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
ISAAC_IMAGE_REF := $(shell bash -lc 'set -euo pipefail; cd "$(REPO_ROOT)"; source scripts/lib/env.sh; load_lab_env; isaac_image_ref')

.PHONY: help prepare-storage storage validate config-check compose-check image-status pull-image prepare-runtime-ownership validate-runtime-ownership prepare-smoke-runtime-ownership validate-smoke-runtime-ownership prepare-openusd-lab prepare-openusd-lab-ownership validate-openusd-lab-ownership validate-openusd-lab run-openusd-lab inspect-openusd-lab run-headless run-gui logs stop launch-headless launch-gui validate-host

help:
	@printf '%s\n' "Targets:"
	@printf '%s\n' "  make prepare-storage  - prepare /mnt/nvme/isaac directories"
	@printf '%s\n' "  make validate         - run workstation validation"
	@printf '%s\n' "  make config-check     - verify env and storage configuration"
	@printf '%s\n' "  make compose-check    - validate Compose syntax"
	@printf '%s\n' "  make image-status     - report whether the pinned image exists locally"
	@printf '%s\n' "  make pull-image       - pull the pinned Isaac Sim image when CONFIRM_PULL=1"
	@printf '%s\n' "  make prepare-runtime-ownership - chown approved Isaac runtime paths when CONFIRM_CHOWN=1"
	@printf '%s\n' "  make validate-runtime-ownership - verify approved Isaac runtime ownership and writability"
	@printf '%s\n' "  make prepare-smoke-runtime-ownership - chown smoke runtime paths when CONFIRM_CHOWN=1"
	@printf '%s\n' "  make validate-smoke-runtime-ownership - verify smoke runtime ownership and writability"
	@printf '%s\n' "  make prepare-openusd-lab - create OpenUSD foundations directories"
	@printf '%s\n' "  make prepare-openusd-lab-ownership - chown OpenUSD foundations paths when CONFIRM_CHOWN=1"
	@printf '%s\n' "  make validate-openusd-lab-ownership - verify OpenUSD foundations ownership"
	@printf '%s\n' "  make validate-openusd-lab - run Phase 4 static validation checks"
	@printf '%s\n' "  make run-openusd-lab - launch the OpenUSD foundations lab in Isaac Sim"
	@printf '%s\n' "  make inspect-openusd-lab - inspect the saved OpenUSD stage in Isaac Sim"
	@printf '%s\n' "  make run-headless     - launch Isaac Sim headless via Compose"
	@printf '%s\n' "  make run-gui          - launch Isaac Sim GUI via Compose"
	@printf '%s\n' "  make logs             - follow Isaac Sim container logs"
	@printf '%s\n' "  make stop             - stop Isaac Sim containers"
	@printf '%s\n' "  make storage          - alias for prepare-storage"
	@printf '%s\n' "  make validate-host    - run host validation directly"
	@printf '%s\n' "  make launch-headless  - alias for run-headless"
	@printf '%s\n' "  make launch-gui       - alias for run-gui"

prepare-storage:
	./prepare-storage.sh

storage: prepare-storage

validate:
	./validate-workstation.sh

validate-host:
	./scripts/validate-host.sh

config-check:
	./tests/phase2-refinement.sh config-check

compose-check:
	./tests/phase2-refinement.sh compose-check

image-status:
	./tests/phase2-refinement.sh image-status

pull-image:
	@printf 'Resolved Isaac Sim image: %s\n' '$(ISAAC_IMAGE_REF)'
	@if [ "$(CONFIRM_PULL)" != "1" ]; then \
		printf '%s\n' "FAIL: set CONFIRM_PULL=1 to pull the pinned Isaac Sim image." >&2; \
		exit 1; \
	fi
	@docker pull $(ISAAC_IMAGE_REF)

prepare-runtime-ownership:
	./scripts/prepare-runtime-ownership.sh

validate-runtime-ownership:
	./scripts/validate-runtime-ownership.sh

prepare-smoke-runtime-ownership:
	./scripts/prepare-smoke-runtime-ownership.sh

validate-smoke-runtime-ownership:
	./scripts/validate-smoke-runtime-ownership.sh

prepare-openusd-lab:
	./scripts/prepare-openusd-foundations.sh

prepare-openusd-lab-ownership:
	./scripts/prepare-openusd-foundations-ownership.sh

validate-openusd-lab-ownership:
	./scripts/validate-openusd-foundations-ownership.sh

validate-openusd-lab:
	./tests/phase4-refinement.sh all

run-openusd-lab:
	./scripts/run-openusd-foundations.sh

inspect-openusd-lab:
	./scripts/inspect-openusd-foundations.sh

run-headless:
	./launch-headless.sh

launch-headless: run-headless

run-gui:
	./launch-gui.sh

launch-gui: run-gui

logs:
	./scripts/compose-logs.sh

stop:
	./stop.sh
