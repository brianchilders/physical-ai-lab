.PHONY: help prepare-storage storage validate config-check compose-check image-status run-headless run-gui logs stop launch-headless launch-gui validate-host

help:
	@printf '%s\n' "Targets:"
	@printf '%s\n' "  make prepare-storage  - prepare /mnt/nvme/isaac directories"
	@printf '%s\n' "  make validate         - run workstation validation"
	@printf '%s\n' "  make config-check     - verify env and storage configuration"
	@printf '%s\n' "  make compose-check    - validate Compose syntax"
	@printf '%s\n' "  make image-status     - report whether the pinned image exists locally"
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
