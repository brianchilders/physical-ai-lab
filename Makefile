REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
ISAAC_IMAGE_REF := $(shell bash -lc 'set -euo pipefail; cd "$(REPO_ROOT)"; source scripts/lib/env.sh; load_lab_env; isaac_image_ref')

.PHONY: help prepare-storage storage validate config-check compose-check image-status pull-image prepare-runtime-ownership validate-runtime-ownership prepare-smoke-runtime-ownership validate-smoke-runtime-ownership prepare-openusd-lab prepare-openusd-lab-ownership validate-openusd-lab-ownership validate-openusd-lab run-openusd-lab inspect-openusd-lab prepare-usd-composition prepare-usd-composition-ownership validate-usd-composition-ownership run-usd-composition-assets run-usd-composition inspect-usd-composition test-phase5 prepare-physics-foundations prepare-physics-foundations-ownership validate-physics-foundations-ownership create-physics-scene run-physics-experiment inspect-physics-results compare-physics-runs test-phase6 run-headless run-gui logs stop launch-headless launch-gui validate-host

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
	@printf '%s\n' "  make prepare-usd-composition - create Phase 5 directories"
	@printf '%s\n' "  make prepare-usd-composition-ownership - chown Phase 5 paths when CONFIRM_CHOWN=1"
	@printf '%s\n' "  make validate-usd-composition-ownership - verify Phase 5 ownership"
	@printf '%s\n' "  make run-usd-composition-assets - build reusable Phase 5 assets"
	@printf '%s\n' "  make run-usd-composition - build the Phase 5 composed stages"
	@printf '%s\n' "  make inspect-usd-composition - independently inspect the Phase 5 composed stages"
	@printf '%s\n' "  make test-phase5 - run Phase 5 refinement checks"
	@printf '%s\n' "  make prepare-physics-foundations - create Phase 6 directories"
	@printf '%s\n' "  make prepare-physics-foundations-ownership - chown Phase 6 paths when CONFIRM_CHOWN=1"
	@printf '%s\n' "  make validate-physics-foundations-ownership - verify Phase 6 ownership"
	@printf '%s\n' "  make create-physics-scene - author the Phase 6 physics scene"
	@printf '%s\n' "  make run-physics-experiment - execute the Phase 6 physics experiment twice"
	@printf '%s\n' "  make inspect-physics-results - inspect the Phase 6 outputs in read-only mode"
	@printf '%s\n' "  make compare-physics-runs - compare the two Phase 6 runs"
	@printf '%s\n' "  make test-phase6 - run Phase 6 static refinement checks"
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

prepare-usd-composition:
	./scripts/prepare-usd-composition.sh

prepare-usd-composition-ownership:
	./scripts/prepare-usd-composition-ownership.sh

validate-usd-composition-ownership:
	./scripts/validate-usd-composition-ownership.sh

run-usd-composition-assets:
	./scripts/run-usd-composition.sh assets

run-usd-composition:
	./scripts/run-usd-composition.sh composition

inspect-usd-composition:
	./scripts/inspect-usd-composition.sh

test-phase5:
	./tests/phase5-refinement.sh all

prepare-physics-foundations:
	./scripts/prepare-physics-foundations.sh

prepare-physics-foundations-ownership:
	./scripts/prepare-physics-foundations-ownership.sh

validate-physics-foundations-ownership:
	./scripts/validate-physics-foundations-ownership.sh

create-physics-scene:
	./scripts/create-physics-scene.sh

run-physics-experiment:
	./scripts/run-physics-experiment.sh

inspect-physics-results:
	./scripts/inspect-physics-results.sh

compare-physics-runs:
	./scripts/compare-physics-runs.sh

test-phase6:
	./tests/phase6-refinement.sh all

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
