#!/usr/bin/env bash
set -euo pipefail

PROJECT="MedusaHC Core"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ACTION="${1:-install}"
shift || true
PURGE=0
YES=0

for argument in "$@"; do
  case "${argument}" in
    --purge) PURGE=1 ;;
    --yes|-y) YES=1 ;;
    *) printf '[%s] Unknown option: %s\n' "${PROJECT}" "${argument}" >&2; exit 2 ;;
  esac
done

log() { printf '[%s] %s\n' "${PROJECT}" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }
confirm() {
  [[ "${YES}" == 1 ]] && return 0
  [[ -t 0 ]] || return 1
  local answer
  read -r -p "$1 [y/N]: " answer
  [[ "${answer}" =~ ^([yY]|[yY][eE][sS])$ ]]
}

detect_user() {
  if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != root ]]; then
    printf '%s' "${SUDO_USER}"
  else
    id -un
  fi
}

INSTALL_USER="${MEDUSAHC_USER:-$(detect_user)}"
if command -v getent >/dev/null 2>&1; then
  INSTALL_HOME="$(getent passwd "${INSTALL_USER}" | cut -d: -f6)"
elif [[ "${INSTALL_USER}" == "$(id -un)" ]]; then
  INSTALL_HOME="${HOME}"
else
  INSTALL_HOME=""
fi
[[ -n "${INSTALL_HOME}" ]] || die "Cannot determine home for ${INSTALL_USER}."
KLIPPER_DIR="${KLIPPER_DIR:-${INSTALL_HOME}/klipper}"
CONFIG_DIR="${PRINTER_CONFIG_DIR:-${INSTALL_HOME}/printer_data/config}"
TARGET_CONFIG_DIR="${MEDUSAHC_CONFIG_DIR:-${CONFIG_DIR}/MedusaHC}"
TARGET_EXTRA_DIR="${KLIPPER_DIR}/klippy/extras"
TARGET_CONTROLLER="${TARGET_EXTRA_DIR}/medusahc.py"
TARGET_PIN_WATCH="${TARGET_EXTRA_DIR}/pin_watch.py"

CONFIG_FILES=(MHC_config.cfg MHC_variables.cfg MHC_macros.cfg)

require_layout() {
  [[ -d "${TARGET_EXTRA_DIR}" ]] || die "Klipper extras not found: ${TARGET_EXTRA_DIR}"
  [[ -d "${CONFIG_DIR}" ]] || die "Printer config directory not found: ${CONFIG_DIR}"
}

install_file() {
  local source="$1" target="$2"
  install -m 0644 "${source}" "${target}"
  if [[ "$(id -u)" == 0 ]]; then
    chown "${INSTALL_USER}:$(id -gn "${INSTALL_USER}")" "${target}"
  fi
}

write_entry_config() {
  local target="$1"
  local temporary
  temporary="$(mktemp "${TARGET_CONFIG_DIR}/.MHC_config.XXXXXX")"
  {
    printf '%s\n' \
      '# MedusaHC example entry point.' \
      '[include MHC_variables.cfg]' \
      '[include MHC_macros.cfg]' \
      ''
    sed '/^\[include MedusaHC\//d' "${SCRIPT_DIR}/Macros/MHC_config.cfg"
  } > "${temporary}"
  chmod 0644 "${temporary}"
  mv "${temporary}" "${target}"
  if [[ "$(id -u)" == 0 ]]; then
    chown "${INSTALL_USER}:$(id -gn "${INSTALL_USER}")" "${target}"
  fi
}

print_manual_steps() {
  cat <<EOF

MedusaHC example configuration installed in:
  ${TARGET_CONFIG_DIR}

The supplied configuration is an example for:
  - Duender
  - BTT Manta M8P V2.0
  - 4 tools
  - V-Front dock layout

IMPORTANT:
MHC_config.cfg contains the complete hotend configuration, including the
primary [extruder] section. Your existing printer configuration probably
already contains [extruder] and other conflicting sections. Klipper cannot
load duplicate sections.

Before enabling MedusaHC, review every MCU name, pin, thermistor, heater,
fan, PID value, tool sensor, dock coordinate, axis limit, offset, and
cleaning/priming position. Remove or comment conflicting sections yourself.

Only after that, add this line to printer.cfg manually:
  [include MedusaHC/MHC_config.cfg]

The installer did not modify printer.cfg and did not restart Klipper.
EOF
}

install_core() {
  require_layout
  [[ -f "${SCRIPT_DIR}/Scripts/medusahc.py" ]] || die "medusahc.py is missing from the package."
  [[ -f "${SCRIPT_DIR}/Scripts/pin_watch.py" ]] || die "pin_watch.py is missing from the package."
  if [[ -e "${TARGET_CONFIG_DIR}" ]]; then
    die "${TARGET_CONFIG_DIR} already exists. Existing configuration was not changed. Use update or choose another MEDUSAHC_CONFIG_DIR."
  fi
  mkdir -p "${TARGET_CONFIG_DIR}"
  if [[ "$(id -u)" == 0 ]]; then
    chown "${INSTALL_USER}:$(id -gn "${INSTALL_USER}")" "${TARGET_CONFIG_DIR}"
  fi
  write_entry_config "${TARGET_CONFIG_DIR}/MHC_config.cfg"
  for name in "${CONFIG_FILES[@]:1}"; do
    install_file "${SCRIPT_DIR}/Macros/${name}" "${TARGET_CONFIG_DIR}/${name}"
  done
  install_file "${SCRIPT_DIR}/Macros/macros.cfg" "${TARGET_CONFIG_DIR}/macros_examples.cfg"
  install_file "${SCRIPT_DIR}/Macros/Line_Purge.cfg" "${TARGET_CONFIG_DIR}/Line_Purge_examples.cfg"
  install_file "${SCRIPT_DIR}/Scripts/medusahc.py" "${TARGET_CONTROLLER}"
  install_file "${SCRIPT_DIR}/Scripts/pin_watch.py" "${TARGET_PIN_WATCH}"
  print_manual_steps
}

update_core() {
  require_layout
  [[ -d "${TARGET_CONFIG_DIR}" ]] || die "Core is not installed in ${TARGET_CONFIG_DIR}. Run install first."
  [[ -f "${SCRIPT_DIR}/Scripts/medusahc.py" ]] || die "medusahc.py is missing from the package."
  [[ -f "${SCRIPT_DIR}/Scripts/pin_watch.py" ]] || die "pin_watch.py is missing from the package."
  install_file "${SCRIPT_DIR}/Scripts/medusahc.py" "${TARGET_CONTROLLER}"
  install_file "${SCRIPT_DIR}/Scripts/pin_watch.py" "${TARGET_PIN_WATCH}"
  local examples="${TARGET_CONFIG_DIR}/upstream-examples"
  mkdir -p "${examples}"
  if [[ "$(id -u)" == 0 ]]; then
    chown "${INSTALL_USER}:$(id -gn "${INSTALL_USER}")" "${examples}"
  fi
  write_entry_config "${examples}/MHC_config.cfg"
  for name in "${CONFIG_FILES[@]:1}"; do
    install_file "${SCRIPT_DIR}/Macros/${name}" "${examples}/${name}"
  done
  install_file "${SCRIPT_DIR}/Macros/macros.cfg" "${examples}/macros_examples.cfg"
  install_file "${SCRIPT_DIR}/Macros/Line_Purge.cfg" "${examples}/Line_Purge_examples.cfg"
  log "Python scripts updated. Live configuration was preserved."
  log "New reference configs: ${examples}"
  log "Klipper was not restarted."
}

uninstall_core() {
  require_layout
  if [[ -f "${TARGET_EXTRA_DIR}/medusahc_calibrate.py" ]]; then
    die "MedusaHC-Calibrate is still installed. Remove it before removing Core."
  fi
  if [[ -f /var/lib/medusahc-control/config.json ]]; then
    die "MedusaHC Control is still installed. Remove it before removing Core."
  fi
  rm -f -- "${TARGET_CONTROLLER}" "${TARGET_PIN_WATCH}"
  log "Removed MedusaHC Python scripts from Klipper extras."
  if [[ "${PURGE}" == 1 ]]; then
    local config_root target_root
    config_root="$(realpath -m -- "${CONFIG_DIR}")"
    target_root="$(realpath -m -- "${TARGET_CONFIG_DIR}")"
    case "${target_root}" in
      "${config_root}"/*) ;;
      *) die "Refusing to purge a path outside the printer config directory: ${target_root}" ;;
    esac
    confirm "Delete ${TARGET_CONFIG_DIR} and all configuration inside it?" || die "Configuration purge cancelled."
    rm -rf -- "${TARGET_CONFIG_DIR}"
    log "Removed ${TARGET_CONFIG_DIR}."
  else
    log "Configuration kept: ${TARGET_CONFIG_DIR}"
  fi
  log "Remove [include MedusaHC/MHC_config.cfg] manually if it is present."
  log "Klipper was not restarted."
}

show_status() {
  [[ -f "${TARGET_CONTROLLER}" ]] && controller=installed || controller=missing
  [[ -f "${TARGET_PIN_WATCH}" ]] && watcher=installed || watcher=missing
  [[ -d "${TARGET_CONFIG_DIR}" ]] && configuration=present || configuration=missing
  log "medusahc.py: ${controller}"
  log "pin_watch.py: ${watcher}"
  log "configuration: ${configuration} (${TARGET_CONFIG_DIR})"
}

case "${ACTION}" in
  install) install_core ;;
  update) update_core ;;
  uninstall|remove) uninstall_core ;;
  status) show_status ;;
  *) die "Usage: $0 [install|update|uninstall|status] [--purge] [--yes]" ;;
esac
