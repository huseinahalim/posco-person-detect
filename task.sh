#!/usr/bin/env bash

set -euo pipefail

REPO_DIR="$HOME/posco_project_test1"
KEY_PATH="$HOME/.ssh/molen_iron_detect"
ARCHIVE_NAME="samples_images2.zip"
ARCHIVE_PATH="${1:-$HOME/$ARCHIVE_NAME}"
SSH_COMMAND="ssh -i $KEY_PATH -o IdentitiesOnly=yes"

# GitHub rejects normal Git files of 100 MB or more. Use 90 MiB pieces.
CHUNK_SIZE="90M"
CHUNK_LIMIT_BYTES=$((90 * 1024 * 1024))

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

GIT_SSH_COMMAND="$SSH_COMMAND" git -C "$REPO_DIR" fetch origin main

ahead_count="$(git -C "$REPO_DIR" rev-list --count origin/main..HEAD)"
behind_count="$(git -C "$REPO_DIR" rev-list --count HEAD..origin/main)"

if (( ahead_count > 0 && behind_count > 0 )); then
    echo "Error: the local and GitHub histories have separated." >&2
    echo "Please stop here and ask for assistance." >&2
    exit 1
fi

if (( ahead_count > 0 )); then
    unexpected_paths="$(
        git -C "$REPO_DIR" diff --name-only origin/main..HEAD |
            grep -Ev "^${ARCHIVE_NAME//./\\.}(\.part-[0-9]+|\.sha256)?$" || true
    )"

    if [[ -n "$unexpected_paths" ]]; then
        echo "Error: there are unrelated local changes that were not pushed:" >&2
        echo "$unexpected_paths" >&2
        echo "Please stop here and ask for assistance." >&2
        exit 1
    fi

    if git -C "$REPO_DIR" ls-tree -r --name-only HEAD -- "$ARCHIVE_NAME" |
        grep -Fxq "$ARCHIVE_NAME"; then
        echo "Removing the previous rejected large-file commit..."
        git -C "$REPO_DIR" reset --mixed origin/main
    else
        echo "Finishing a previously interrupted small-part upload..."
        GIT_SSH_COMMAND="$SSH_COMMAND" git -C "$REPO_DIR" push origin main
    fi
elif (( behind_count > 0 )); then
    git -C "$REPO_DIR" merge --ff-only origin/main
fi

archive_size="$(stat -c '%s' -- "$ARCHIVE_PATH")"
files_to_send=()

if (( archive_size > CHUNK_LIMIT_BYTES )); then
    echo "Large archive detected. Splitting it into $CHUNK_SIZE pieces..."

    find "$REPO_DIR" -maxdepth 1 -type f \
        -name "$ARCHIVE_NAME.part-*" -delete

    split -b "$CHUNK_SIZE" -d -a 3 -- \
        "$ARCHIVE_PATH" "$REPO_DIR/$ARCHIVE_NAME.part-"

    while IFS= read -r part_path; do
        files_to_send+=("$(basename "$part_path")")
    done < <(
        find "$REPO_DIR" -maxdepth 1 -type f \
            -name "$ARCHIVE_NAME.part-*" -print | sort
    )

    archive_hash="$(sha256sum -- "$ARCHIVE_PATH" | awk '{print $1}')"
    printf '%s  %s\n' "$archive_hash" "$ARCHIVE_NAME" \
        >"$REPO_DIR/$ARCHIVE_NAME.sha256"
    files_to_send+=("$ARCHIVE_NAME.sha256")

    destination="$REPO_DIR/$ARCHIVE_NAME"
    if [[ -f "$destination" ]] &&
        [[ "$(readlink -f "$ARCHIVE_PATH")" != "$(readlink -f "$destination")" ]]; then
        rm -- "$destination"
    fi
else
    destination="$REPO_DIR/$ARCHIVE_NAME"
    if [[ "$(readlink -f "$ARCHIVE_PATH")" != \
        "$(readlink -f "$destination" 2>/dev/null || true)" ]]; then
        cp -- "$ARCHIVE_PATH" "$destination"
    fi
    files_to_send+=("$ARCHIVE_NAME")
fi

for file_name in "${files_to_send[@]}"; do
    git -C "$REPO_DIR" add -- "$file_name"

    if git -C "$REPO_DIR" diff --cached --quiet; then
        echo "Already sent: $file_name"
        continue
    fi

    git -C "$REPO_DIR" \
        -c user.name="POSCO AI PC" \
        -c user.email="ai@ai" \
        commit -m "Add $file_name"

    echo "Sending: $file_name"
    GIT_SSH_COMMAND="$SSH_COMMAND" git -C "$REPO_DIR" push origin main
done

echo "Finished sending $ARCHIVE_NAME."

if (( archive_size > CHUNK_LIMIT_BYTES )); then
    echo "To rebuild it after downloading, run:"
    echo "cat $ARCHIVE_NAME.part-* > $ARCHIVE_NAME"
    echo "sha256sum -c $ARCHIVE_NAME.sha256"
fi
