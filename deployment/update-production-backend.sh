#!/usr/bin/env bash
set -Eeuo pipefail

readonly CURRENT_CONTAINER="tailorahub-backend"
readonly CANDIDATE_CONTAINER="tailorahub-backend-candidate"
readonly IMAGE="495680546669.dkr.ecr.eu-north-1.amazonaws.com/tailorahub-backend:private-admin-20260830"
readonly DEPLOY_DIR="${HOME}/tailorahub-deploy/private-admin-20260830"
readonly ALLOWLIST_FILE="${DEPLOY_DIR}/admin-allowlist.env"
readonly INSPECT_ENV="${DEPLOY_DIR}/current-env.json"
readonly RUNTIME_ENV="${DEPLOY_DIR}/runtime.env"
readonly ROLLBACK_CONTAINER="tailorahub-backend-rollback-20260830"

mkdir -p "${DEPLOY_DIR}"
chmod 700 "${DEPLOY_DIR}"

if [[ ! -s "${ALLOWLIST_FILE}" ]]; then
  echo "Missing ${ALLOWLIST_FILE}" >&2
  exit 1
fi

docker inspect --format '{{json .Config.Env}}' "${CURRENT_CONTAINER}" > "${INSPECT_ENV}"
chmod 600 "${INSPECT_ENV}"

python3 - "${INSPECT_ENV}" "${ALLOWLIST_FILE}" "${RUNTIME_ENV}" <<'PY'
import ipaddress
import json
import os
import sys

inspect_path, allowlist_path, output_path = sys.argv[1:]
with open(inspect_path, encoding="utf-8") as handle:
    entries = json.load(handle)

environment = {}
ignored = {
    "GPG_KEY", "HOME", "HOSTNAME", "PATH", "PWD", "PYTHON_SHA256", "PYTHON_VERSION",
}
for entry in entries:
    key, separator, value = entry.partition("=")
    if separator and key not in ignored:
        environment[key] = value

with open(allowlist_path, encoding="utf-8") as handle:
    line = next((item.strip() for item in handle if item.strip().startswith("ADMIN_ALLOWED_NETWORKS=")), "")
if not line:
    raise SystemExit("ADMIN_ALLOWED_NETWORKS is missing")

allowlist = line.split("=", 1)[1].strip()
networks = [item.strip() for item in allowlist.split(",") if item.strip()]
if not networks:
    raise SystemExit("ADMIN_ALLOWED_NETWORKS is empty")
for network in networks:
    parsed = ipaddress.ip_network(network, strict=False)
    if parsed.version != 4 or parsed.prefixlen != 32:
        raise SystemExit("Every production admin allowlist entry must be an IPv4 /32")

environment["ADMIN_ALLOWED_NETWORKS"] = ",".join(networks)
environment["ADMIN_TRUSTED_PROXY_NETWORKS"] = "127.0.0.1/32,::1/128,172.17.0.0/16"

flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
descriptor = os.open(output_path, flags, 0o600)
with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
    for key in sorted(environment):
        handle.write(f"{key}={environment[key]}\n")
PY

rm -f "${INSPECT_ENV}"
chmod 600 "${RUNTIME_ENV}"

docker rm -f "${CANDIDATE_CONTAINER}" >/dev/null 2>&1 || true
docker run -d \
  --name "${CANDIDATE_CONTAINER}" \
  --env-file "${RUNTIME_ENV}" \
  -p 127.0.0.1:18001:8001 \
  "${IMAGE}" >/dev/null

candidate_ready="false"
for _ in $(seq 1 30); do
  if curl --fail --silent --show-error http://127.0.0.1:18001/api/health >/dev/null; then
    candidate_ready="true"
    break
  fi
  sleep 2
done

if [[ "${candidate_ready}" != "true" ]]; then
  docker logs --tail 100 "${CANDIDATE_CONTAINER}" >&2 || true
  docker rm -f "${CANDIDATE_CONTAINER}" >/dev/null 2>&1 || true
  echo "Candidate health check failed; production was not changed." >&2
  exit 1
fi

docker rm -f "${CANDIDATE_CONTAINER}" >/dev/null
docker rm -f "${ROLLBACK_CONTAINER}" >/dev/null 2>&1 || true
docker stop "${CURRENT_CONTAINER}" >/dev/null
docker rename "${CURRENT_CONTAINER}" "${ROLLBACK_CONTAINER}"

restore_previous() {
  docker rm -f "${CURRENT_CONTAINER}" >/dev/null 2>&1 || true
  docker rename "${ROLLBACK_CONTAINER}" "${CURRENT_CONTAINER}" >/dev/null 2>&1 || true
  docker start "${CURRENT_CONTAINER}" >/dev/null 2>&1 || true
}
trap restore_previous ERR

docker run -d \
  --name "${CURRENT_CONTAINER}" \
  --restart unless-stopped \
  --env-file "${RUNTIME_ENV}" \
  -p 8001:8001 \
  "${IMAGE}" >/dev/null

production_ready="false"
for _ in $(seq 1 30); do
  if curl --fail --silent --show-error http://127.0.0.1:8001/api/health >/dev/null; then
    production_ready="true"
    break
  fi
  sleep 2
done

if [[ "${production_ready}" != "true" ]]; then
  docker logs --tail 100 "${CURRENT_CONTAINER}" >&2 || true
  echo "Production health check failed; restoring previous container." >&2
  false
fi

trap - ERR
echo "TailoraHub backend updated successfully. Rollback container: ${ROLLBACK_CONTAINER}"
