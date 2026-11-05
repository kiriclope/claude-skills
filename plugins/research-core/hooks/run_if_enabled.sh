#!/bin/sh
# Plugin hooks are opt-in: run the hook only when the user enabled the plugin's `hooks_enabled`
# option (claude plugin config / at install). Off → exit 0 at once, so the hook is a no-op.
# Usage (hooks.json): sh "${CLAUDE_PLUGIN_ROOT}/hooks/run_if_enabled.sh" <script.py> [args...]
case "$(printf '%s' "${CLAUDE_PLUGIN_OPTION_HOOKS_ENABLED:-}" | tr '[:upper:]' '[:lower:]')" in
  true|1|yes|on) exec python3 "$@" ;;
  *) exit 0 ;;
esac
