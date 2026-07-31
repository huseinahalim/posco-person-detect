#!/usr/bin/env bash

set -euo pipefail

SCRIPT_URL="https://raw.githubusercontent.com/huseinahalim/posco-person-detect/main/split_train_val.py"
SCRIPT_PATH="$PWD/split_train_val.py"
TEMP_PATH="$PWD/.split_train_val.py.download"
DOWNLOAD_URL="$SCRIPT_URL?v=$(date +%s)"

cleanup() {
    rm -f -- "$TEMP_PATH"
}
trap cleanup EXIT

echo "Downloading split_train_val.py..."

if command -v wget >/dev/null 2>&1; then
    wget --quiet --show-progress -O "$TEMP_PATH" "$DOWNLOAD_URL"
elif command -v curl >/dev/null 2>&1; then
    curl --fail --location --show-error --progress-bar \
        --output "$TEMP_PATH" "$DOWNLOAD_URL"
else
    echo "Error: wget or curl is required." >&2
    exit 1
fi

if [[ ! -s "$TEMP_PATH" ]]; then
    echo "Error: the downloaded Python file is empty." >&2
    exit 1
fi

if [[ "$(head -n 1 "$TEMP_PATH")" != "#!/usr/bin/env python3" ]]; then
    echo "Error: the downloaded file is not split_train_val.py." >&2
    exit 1
fi

mv -- "$TEMP_PATH" "$SCRIPT_PATH"
chmod 700 "$SCRIPT_PATH"

echo "Downloaded: $SCRIPT_PATH"
echo "Example:"
echo "python split_train_val.py --inputfolder /path/to/dataset/"
