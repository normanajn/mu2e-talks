#!/usr/bin/env bash
# Post JSON records to the Mu2eTalks API.
#
# Usage:
#   ./scripts/api-post.sh [OPTIONS]
#
# Options:
#   -u URL          Base application URL (default: $MU2E_TALKS_URL or http://localhost:8000)
#   -t TOKEN        API token (default: $MU2E_API_TOKEN)
#   --token-file    File containing API token (default: $MU2E_API_TOKEN_FILE)
#   -r RESOURCE     Resource to create: talks, institutions, conferences
#   -p PATH         Explicit API path, overriding --resource
#   -d JSON         JSON request body
#   -f FILE         Read JSON request body from FILE
#   --curl-args     Additional argument string passed to curl
#   --dry-run       Print the request target and JSON body without posting
#   -h              Show this help message

set -euo pipefail

BASE_URL="${MU2E_TALKS_URL:-http://localhost:8000}"
TOKEN="${MU2E_API_TOKEN:-}"
TOKEN_FILE="${MU2E_API_TOKEN_FILE:-}"
RESOURCE=""
API_PATH=""
JSON_BODY=""
JSON_FILE=""
CURL_ARGS=()
DRY_RUN=false

usage() {
    awk '/^# Usage:/{show=1} show && /^#/{sub(/^# ?/, ""); print; next} show{exit}' "$0"
    exit 0
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

trim_trailing_slash() {
    local value="$1"
    while [[ "$value" == */ ]]; do
        value="${value%/}"
    done
    printf '%s' "$value"
}

resource_path() {
    case "$1" in
        talk|talks) printf '/api/v1/talks/' ;;
        institution|institutions) printf '/api/v1/institutions/' ;;
        conference|conferences) printf '/api/v1/conferences/' ;;
        *) die "Unknown resource '$1'. Use talks, institutions, or conferences." ;;
    esac
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -u|--url|--base-url)
            [[ $# -ge 2 ]] || die "$1 requires a value."
            BASE_URL="$2"
            shift 2
            ;;
        -t|--token)
            [[ $# -ge 2 ]] || die "$1 requires a value."
            TOKEN="$2"
            shift 2
            ;;
        --token-file)
            [[ $# -ge 2 ]] || die "$1 requires a value."
            TOKEN_FILE="$2"
            shift 2
            ;;
        -r|--resource)
            [[ $# -ge 2 ]] || die "$1 requires a value."
            RESOURCE="$2"
            shift 2
            ;;
        -p|--path)
            [[ $# -ge 2 ]] || die "$1 requires a value."
            API_PATH="$2"
            shift 2
            ;;
        -d|--data)
            [[ $# -ge 2 ]] || die "$1 requires a value."
            JSON_BODY="$2"
            shift 2
            ;;
        -f|--file)
            [[ $# -ge 2 ]] || die "$1 requires a value."
            JSON_FILE="$2"
            shift 2
            ;;
        --curl-args)
            [[ $# -ge 2 ]] || die "$1 requires a value."
            # shellcheck disable=SC2206
            CURL_ARGS+=($2)
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            die "Unknown option: $1"
            ;;
    esac
done

command -v curl >/dev/null 2>&1 || die "curl is required."

if [[ -n "$JSON_BODY" && -n "$JSON_FILE" ]]; then
    die "Use either --data or --file, not both."
fi

if [[ -z "$JSON_BODY" && -z "$JSON_FILE" ]]; then
    die "Provide a JSON body with --data or --file."
fi

if [[ -z "$TOKEN" && -n "$TOKEN_FILE" ]]; then
    [[ -r "$TOKEN_FILE" ]] || die "Token file is not readable: $TOKEN_FILE"
    IFS= read -r TOKEN < "$TOKEN_FILE" || true
fi

[[ -n "$TOKEN" ]] || die "Provide an API token with --token, MU2E_API_TOKEN, or --token-file."

if [[ -n "$API_PATH" && -n "$RESOURCE" ]]; then
    die "Use either --path or --resource, not both."
fi

if [[ -z "$API_PATH" ]]; then
    [[ -n "$RESOURCE" ]] || die "Provide --resource or --path."
    API_PATH="$(resource_path "$RESOURCE")"
fi

if [[ "$API_PATH" != /* ]]; then
    API_PATH="/${API_PATH}"
fi

BASE_URL="$(trim_trailing_slash "$BASE_URL")"
URL="${BASE_URL}${API_PATH}"

if [[ -n "$JSON_FILE" ]]; then
    [[ -r "$JSON_FILE" ]] || die "JSON file is not readable: $JSON_FILE"
fi

if [[ "$DRY_RUN" == true ]]; then
    echo "POST ${URL}"
    echo "Authorization: Bearer ${TOKEN:0:12}..."
    echo ""
    if [[ -n "$JSON_FILE" ]]; then
        sed -n '1,200p' "$JSON_FILE"
    else
        printf '%s\n' "$JSON_BODY"
    fi
    exit 0
fi

if [[ -n "$JSON_FILE" ]]; then
    CURL_COMMAND=(
        curl --fail --show-error --silent
        -X POST "$URL" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        --data-binary "@${JSON_FILE}"
    )
else
    CURL_COMMAND=(
        curl --fail --show-error --silent
        -X POST "$URL" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        --data-binary "$JSON_BODY"
    )
fi

if [[ ${#CURL_ARGS[@]} -gt 0 ]]; then
    CURL_COMMAND+=("${CURL_ARGS[@]}")
fi

"${CURL_COMMAND[@]}"

echo ""
