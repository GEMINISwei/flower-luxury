#!/usr/bin/env bash
# 由 runner 傳送到遠端, 因此舊 tag 也可驗證; 不依賴主機安裝 Python.
set -euo pipefail

# shellcheck source=scripts/lib/compose.sh
source scripts/lib/compose.sh
load_env
require_env COMPOSE_PROJECT_NAME
require_mode

wait_for_deployment_health() {
    local attempt service container report process_state health_state pending
    for attempt in $(seq 1 36); do
        pending=false
        for service in api web postgres line-collector nginx; do
            container="${COMPOSE_PROJECT_NAME}-${service}"
            if ! report="$(docker inspect --format \
                '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' \
                "${container}" </dev/null)"; then
                echo "::error::無法查詢容器 ${container}" >&2
                return 1
            fi
            read -r process_state health_state <<< "${report}"
            printf '%s: %s\n' "${container}" "${report}"
            if [ "${process_state}" != running ]; then
                echo "::error::容器 ${container} 未在執行" >&2
                return 1
            fi
            # nginx 沒有 Docker healthcheck, 其餘四個服務必須 healthy.
            if [ "${service}" != nginx ]; then
                case "${health_state}" in
                    healthy) ;;
                    starting) pending=true ;;
                    *) echo "::error::容器 ${container} 健康檢查失敗" >&2; return 1 ;;
                esac
            fi
        done
        [ "${pending}" = true ] || return 0
        [ "${attempt}" -eq 36 ] || sleep 5
    done
    echo "::error::等待服務健康狀態逾時" >&2
    return 1
}

if ! wait_for_deployment_health; then
    exit 1
fi

deployment_expected_version="$(app_version)"
deployment_api="${COMPOSE_PROJECT_NAME}-api"
deployment_worker="${COMPOSE_PROJECT_NAME}-line-collector"
deployment_actual_version="$(docker exec -w /app "${deployment_api}" python -c \
    'from app.config import APP_VERSION; print(APP_VERSION)' </dev/null)"
if [ "${deployment_actual_version}" != "${deployment_expected_version}" ]; then
    echo "::error::API 容器版本 ${deployment_actual_version} 與 checkout ${deployment_expected_version} 不一致" >&2
    exit 1
fi

deployment_api_image="$(docker inspect --format '{{.Image}}' "${deployment_api}" </dev/null)"
deployment_worker_image="$(docker inspect --format '{{.Image}}' "${deployment_worker}" </dev/null)"
if [ "${deployment_api_image}" != "${deployment_worker_image}" ]; then
    echo "::error::API 與 worker 使用不同映像" >&2
    exit 1
fi
printf '已驗證容器版本：v%s；API 與 worker 映像一致。\n' "${deployment_actual_version}"
