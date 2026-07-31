#!/usr/bin/env bash

set -euo pipefail

REPO_DIR="$HOME/posco_project_test1"
KEY_PATH="$HOME/.ssh/molen_iron_detect"
ARCHIVE_NAME="samples_images2.zip"
ARCHIVE_PATH="${1:-$HOME/$ARCHIVE_NAME}"
SSH_COMMAND="ssh -i $KEY_PATH -o IdentitiesOnly=yes"

if [[ ! -f "$KEY_PATH" ]]; then
    echo "Error: GitHub key not found: $KEY_PATH" >&2
    exit 1
fi

if [[ ! -d "$REPO_DIR/.git" ]]; then
    echo "Error: Git repository not found: $REPO_DIR" >&2
    exit 1
fi

if [[ ! -f "$ARCHIVE_PATH" ]]; then
    echo "Error: sample archive not found: $ARCHIVE_PATH" >&2
    echo "Usage: bash task.sh [/full/path/to/$ARCHIVE_NAME]" >&2
    exit 1
fi

echo "Repository: $REPO_DIR"
echo "Sample:     $ARCHIVE_PATH"

GIT_SSH_COMMAND="$SSH_COMMAND" \
    git -C "$REPO_DIR" pull --ff-only origin main

DESTINATION="$REPO_DIR/$ARCHIVE_NAME"
if [[ "$(readlink -f "$ARCHIVE_PATH")" != "$(readlink -f "$DESTINATION" 2>/dev/null || true)" ]]; then
    cp -- "$ARCHIVE_PATH" "$DESTINATION"
fi

git -C "$REPO_DIR" add -- "$ARCHIVE_NAME"

if git -C "$REPO_DIR" diff --cached --quiet; then
    echo "No new changes to send."
    exit 0
fi

git -C "$REPO_DIR" \
    -c user.name="POSCO AI PC" \
    -c user.email="ai@ai" \
    commit -m "Add molten iron detection samples 2"

GIT_SSH_COMMAND="$SSH_COMMAND" \
    git -C "$REPO_DIR" push origin main

echo "Finished: $ARCHIVE_NAME was sent successfully."
