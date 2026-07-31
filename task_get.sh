#!/usr/bin/env bash

set -euo pipefail

TASK_URL="https://raw.githubusercontent.com/huseinahalim/posco-person-detect/main/task.sh"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TASK_PATH="$SCRIPT_DIR/task.sh"
TEMP_PATH="$SCRIPT_DIR/.task.sh.download"

cleanup() {
    rm -f -- "$TEMP_PATH"
}
trap cleanup EXIT

echo "Getting the latest task.sh..."

if command -v wget >/dev/null 2>&1; then
    wget --quiet --show-progress -O "$TEMP_PATH" "$TASK_URL"
elif command -v curl >/dev/null 2>&1; then
    curl --fail --location --show-error --progress-bar \
        --output "$TEMP_PATH" "$TASK_URL"
else
    echo "Error: wget or curl is required." >&2
    exit 1
fi

if [[ ! -s "$TEMP_PATH" ]]; then
    echo "Error: the downloaded task.sh is empty." >&2
    exit 1
fi

if [[ "$(head -n 1 "$TEMP_PATH")" != "#!/usr/bin/env bash" ]]; then
    echo "Error: the downloaded file is not the expected task.sh." >&2
    exit 1
fi

mv -- "$TEMP_PATH" "$TASK_PATH"
chmod 700 "$TASK_PATH"

echo "Updated: $TASK_PATH"
echo "Next command: bash $TASK_PATH"
