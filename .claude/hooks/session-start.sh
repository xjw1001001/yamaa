#!/usr/bin/env bash
# Prepare a Claude Code cloud session for the Rust engine. Local sessions are
# left alone. See .claude/cloud-environment.md for the environment this pairs
# with and the reasons behind each setting.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(cd -- "$(dirname -- "$0")/../.." && pwd)}"
WORKSPACE="$ROOT/rust"

# Full debug info gives each of the ~240 integration-test binaries about
# 100 MB and a plain `cargo test` overruns the 30 GB session disk. Debug
# information changes nothing CI asserts; panic locations are still reported.
export CARGO_PROFILE_DEV_DEBUG=0
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export CARGO_PROFILE_DEV_DEBUG=0' >> "$CLAUDE_ENV_FILE"
fi

# Install the toolchain and components rust/rust-toolchain.toml pins, and make
# it the default so cargo started outside rust/ (maturin from python/, for
# example) uses the same compiler, as RUSTUP_TOOLCHAIN does in CI.
read -r channel components < <(python3 -I - "$WORKSPACE/rust-toolchain.toml" <<'PY'
import sys, tomllib
with open(sys.argv[1], "rb") as handle:
    toolchain = tomllib.load(handle)["toolchain"]
print(toolchain["channel"], ",".join(toolchain.get("components", [])) or "-")
PY
)
installed=$(rustup component list --installed --toolchain "$channel" 2>/dev/null || true)
missing=0
if [ -z "$installed" ]; then
  missing=1
elif [ "$components" != "-" ]; then
  for component in ${components//,/ }; do
    grep -Eq "^$component(-|\$)" <<< "$installed" || missing=1
  done
fi
if [ "$missing" = 1 ]; then
  args=(toolchain install "$channel" --profile minimal --no-self-update)
  [ "$components" = "-" ] || args+=(--component "$components")
  rustup "${args[@]}" >&2
fi
rustup default "$channel" >&2

cd "$WORKSPACE"
cargo fetch --locked >&2

# Compile the default-member tests and the CI clippy set in the background, at
# low priority, so the session starts at once. Cargo holds a lock on the build
# directory, so a cargo command started meanwhile waits and then reuses the
# result. Set YAMAA_WARM_BUILD=0 in the environment to skip it.
log=/tmp/yamaa-warm-build.log
if [ "${YAMAA_WARM_BUILD:-1}" != 0 ]; then
  setsid nice -n 10 bash -c '
    set -x
    cargo test --locked --no-run
    cargo clippy --locked -p yamaa-core -p yamaa-engine -p yamaa-adapters -p yamaa-python --all-targets -- -D warnings
    uv sync --project ../python --locked --no-install-project
    echo "warm build finished"
  ' < /dev/null > "$log" 2>&1 &
  warm="A background warm build is compiling the default-member tests, then the CI clippy set (log: $log). Cargo commands in rust/ wait for its build lock and then reuse its output. Select tests at workspace scope to reuse it (cargo test --locked --test rounding); -p yamaa-core or -p yamaa-engine alone resolves features differently and recompiles."
else
  warm="The background warm build is off (YAMAA_WARM_BUILD=0)."
fi

cat <<EOF
Rust engine session setup: toolchain $channel is the default and rust/Cargo.lock dependencies are fetched. CARGO_PROFILE_DEV_DEBUG=0 keeps test builds within the 30 GB disk; do not override it for whole-workspace builds. $warm
EOF
