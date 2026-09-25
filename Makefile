# Synthetic Enterprise Lab — a customer's IT estate on your laptop.
# DOMAIN=aarohan (fintech) is the first domain. SCALE=tiny for CI.

DOMAIN   ?= aarohan
SCALE    ?= tiny
SEED     ?= 20260907
COMPOSE  := docker compose
PROFILE  := --profile minio
export DOMAIN SCALE SEED

.PHONY: help up up-nominio down seed reset verify advance break heal logs ps catalog test \
	prove-separation status check-contract install-reboot

help:
	@echo "Synthetic Enterprise Lab — customer IT you can start and stop"
	@echo "  make up            start every source (MinIO on). DOMAIN=$(DOMAIN) SCALE=$(SCALE)"
	@echo "  make up-nominio    same without the object store"
	@echo "  make verify        pass/fail vs the domain's verification.json"
	@echo "  make check-contract  output/aarohan/verification.json byte-equals expected/tiny"
	@echo "  make status        one screen: sources, counts, minio keys, contract"
	@echo "  make prove-separation  nine DSNs, cross-db errors, I01, minio-down+heal"
	@echo "  make catalog       print /healthz"
	@echo "  make reset         reload the same seed"
	@echo "  make seed          regenerate then reload"
	@echo "  make advance       move the world one day"
	@echo "  make break <flag>  lms-slow | s2-late | minio-down | erp-500"
	@echo "  make heal          clear breaks"
	@echo "  make down          stop and wipe volumes"
	@echo "  make install-reboot  @reboot crontab if crontab(1) exists (no sudo)"
	@echo "  make test          unit tests (no Docker)"
	@echo ""
	@echo "Health page:  http://127.0.0.1:18082/"
	@echo "Client sheet: docs/CONNECT_SHEET.md    ports: docs/PORTS.md"
	@echo "S1 lms_ro @ :55432  S4 coll_ro @ :55433  S8 gl_ro @ :55434  S5 gold_ro @ :55435"

test:
	PYTHONPATH=domains:. python3 -m unittest discover -s tests -v
	PYTHONPATH=domains python3 -m unittest discover -s domains/aarohan/tests -v

up: dirs doctor-net
	$(COMPOSE) $(PROFILE) up --build -d --wait --wait-timeout 300
	@$(MAKE) --no-print-directory wait-landing
	@echo "Up. Health: http://127.0.0.1:18082/   then  make verify"

up-nominio: dirs doctor-net
	MINIO_OPTIONAL=1 $(COMPOSE) up --build -d --wait --wait-timeout 300
	@$(MAKE) --no-print-directory wait-landing
	@echo "Up without MinIO. Health: http://127.0.0.1:18082/"

doctor-net:
	@sysctl -w net.bridge.bridge-nf-call-iptables=0 >/dev/null 2>&1 || \
	  sudo sysctl -w net.bridge.bridge-nf-call-iptables=0 >/dev/null 2>&1 || \
	  echo "If containers cannot reach postgres: sudo sysctl -w net.bridge.bridge-nf-call-iptables=0"

down:
	$(COMPOSE) $(PROFILE) down -v --remove-orphans || true
	$(COMPOSE) down -v --remove-orphans || true

seed: dirs
	$(COMPOSE) $(PROFILE) exec -e DOMAIN=$(DOMAIN) -e SCALE=$(SCALE) -e SEED=$(SEED) loader python -m runtime.load --force-generate

reset:
	$(COMPOSE) $(PROFILE) exec -e DOMAIN=$(DOMAIN) -e SCALE=$(SCALE) -e SEED=$(SEED) loader python -m runtime.load --reset
	curl -sf -X POST http://127.0.0.1:18082/heal >/dev/null || true
	$(COMPOSE) $(PROFILE) start minio || true

verify: wait-landing
	@python3 scripts/print_verify.py

check-contract:
	@python3 scripts/check_verification.py

status:
	@python3 scripts/status.py

prove-separation:
	@python3 scripts/prove_separation.py

install-reboot:
	@sh scripts/install-reboot.sh

catalog:
	@curl -sS http://127.0.0.1:18082/healthz | python3 -m json.tool

advance:
	curl -sS -X POST -H "Authorization: Bearer aarohan-dev" \
	  "http://127.0.0.1:18081/advance?days=$(or $(DAYS),1)"
	@echo

break:
	@flag="$(filter-out break,$(MAKECMDGOALS))"; \
	if [ -z "$$flag" ]; then echo "usage: make break lms-slow|s2-late|minio-down|erp-500"; exit 2; fi; \
	curl -sf -X POST "http://127.0.0.1:18082/chaos/$$flag" >/dev/null; \
	if [ "$$flag" = "minio-down" ]; then $(COMPOSE) $(PROFILE) stop minio; fi; \
	echo "broke $$flag"

heal:
	curl -sf -X POST http://127.0.0.1:18082/heal >/dev/null || true
	$(COMPOSE) $(PROFILE) start minio || true
	@sleep 3
	@echo "healed"

logs:
	$(COMPOSE) $(PROFILE) logs -f --tail=80

ps:
	$(COMPOSE) $(PROFILE) ps

dirs:
	@mkdir -p output/$(DOMAIN) output/landing

wait-landing:
	@echo "waiting for partner files..."; \
	i=0; \
	while [ $$i -lt 25 ]; do \
	  n=$$(find output/landing -type f 2>/dev/null | wc -l | tr -d ' '); \
	  if [ "$$n" -ge 4 ]; then echo "landing files: $$n"; exit 0; fi; \
	  sleep 1; i=$$((i+1)); \
	done; \
	echo "warning: only $$(find output/landing -type f 2>/dev/null | wc -l) landing files"

lms-slow s2-late minio-down erp-500:
	@:
