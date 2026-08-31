# MedusaHC Core installation

This page covers the Python-based MedusaHC Core from the `main` branch. The
installer is deliberately semi-manual: it places the required files in a
standard Klipper layout, but it does not attempt to rewrite an existing printer
configuration.

> [!WARNING]
> Do not install, update, remove, or restart Klipper during a print. Keep a
> backup of the working printer configuration before enabling MedusaHC.

## Requirements

- An existing Klipper installation.
- A normal `printer_data/config` directory.
- `curl` and `tar` for the online installer.
- Permission to write to the Klipper extras and printer configuration
  directories. Run the command as the printer user when those directories are
  owned by that user. Use `sudo` only if the local installation requires it.

The installer normally detects the current user and uses:

- `~/klipper/klippy/extras/`
- `~/printer_data/config/`
- `~/printer_data/config/MedusaHC/`

## Install

Run this command in an SSH terminal on the printer:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Irbis3D/MedusaHC/main/install-online.sh)"
```

The installer:

1. Downloads the current `main` branch into a temporary directory.
2. Copies `medusahc.py` and `pin_watch.py` into Klipper's `klippy/extras`
   directory.
3. Creates `~/printer_data/config/MedusaHC/`.
4. Places editable example configuration files in that directory.
5. Prints the manual configuration steps that remain.

The optional macro and purge examples are installed as `macros_examples.cfg`
and `Line_Purge_examples.cfg`. These files are not included automatically and
can be copied from selectively if needed.

It does **not**:

- edit `printer.cfg`;
- restart Klipper or any other service;
- modify Moonraker;
- overwrite an existing `MedusaHC` configuration directory;
- migrate settings from an older installation.

The supplied configuration is an example for a four-tool V-Front Duender with
a BTT Manta M8P V2.0. It is not a universal ready-to-run printer configuration.

Before enabling it, review every MCU name, pin, thermistor, heater, fan, PID
value, tool sensor, tool count, dock coordinate, axis limit, offset, cleaning
position, and priming position.

`MHC_config.cfg` includes complete hotend definitions, including the primary
`[extruder]` section. If the same sections already exist in `printer.cfg` or an
included file, move, remove, or comment the duplicates manually. Klipper cannot
load two sections with the same name.

Only after resolving those conflicts, add this line to `printer.cfg`:

```ini
[include MedusaHC/MHC_config.cfg]
```

Then review the Klipper configuration and perform a firmware restart while the
printer is idle.

## Status

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Irbis3D/MedusaHC/main/install-online.sh)" -- status
```

This reports whether the two Python modules and the MedusaHC configuration
directory are present. It does not change anything.

## Update

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Irbis3D/MedusaHC/main/install-online.sh)" -- update
```

An update replaces only `medusahc.py` and `pin_watch.py`. The active user
configuration is preserved. Current example files are written to:

```text
~/printer_data/config/MedusaHC/upstream-examples/
```

They are references for manual comparison and are not included automatically.
Klipper is not restarted by the updater.

## Uninstall

First remove dependent modules such as MedusaHC-Calibrate, MedusaHC Control,
and MedusaHC Mainsail. The Core uninstaller refuses to continue while detected
dependent components remain.

Remove the Python modules while keeping all configuration:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Irbis3D/MedusaHC/main/install-online.sh)" -- uninstall
```

Afterward, manually remove or comment this line in `printer.cfg` before
restarting Klipper:

```ini
[include MedusaHC/MHC_config.cfg]
```

To also delete the complete `~/printer_data/config/MedusaHC/` directory, use:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Irbis3D/MedusaHC/main/install-online.sh)" -- uninstall --purge
```

The purge action asks for confirmation and is irreversible unless a separate
backup exists. It does not edit `printer.cfg` for you.

## Manual installation

Clone or download the repository, then copy the two Klipper modules:

```bash
git clone https://github.com/Irbis3D/MedusaHC.git ~/MedusaHC-source
install -m 0644 ~/MedusaHC-source/Scripts/medusahc.py ~/klipper/klippy/extras/medusahc.py
install -m 0644 ~/MedusaHC-source/Scripts/pin_watch.py ~/klipper/klippy/extras/pin_watch.py
mkdir -p ~/printer_data/config/MedusaHC
cp ~/MedusaHC-source/Macros/{MHC_config.cfg,MHC_variables.cfg,MHC_macros.cfg} ~/printer_data/config/MedusaHC/
cp ~/MedusaHC-source/Macros/macros.cfg ~/printer_data/config/MedusaHC/macros_examples.cfg
cp ~/MedusaHC-source/Macros/Line_Purge.cfg ~/printer_data/config/MedusaHC/Line_Purge_examples.cfg
```

The copied `MHC_config.cfg` already starts with the required relative includes:

```ini
[include MHC_variables.cfg]
[include MHC_macros.cfg]
```

Do not add a second copy of them.

Configure the files for the actual printer, resolve duplicate Klipper sections,
and finally add `[include MedusaHC/MHC_config.cfg]` to `printer.cfg`.

Manual removal is the reverse operation: remove the include from `printer.cfg`,
delete `medusahc.py` and `pin_watch.py` from `klippy/extras`, and delete the
`MedusaHC` configuration directory only if its settings are no longer needed.

## Non-standard paths

The local `install.sh` also accepts path overrides through environment
variables:

```bash
MEDUSAHC_USER=biqu \
KLIPPER_DIR=/home/biqu/klipper \
PRINTER_CONFIG_DIR=/home/biqu/printer_data/config \
bash ./install.sh install
```

`MEDUSAHC_CONFIG_DIR` can override the destination configuration directory.
Keep it inside the printer configuration directory if purge support is needed.
