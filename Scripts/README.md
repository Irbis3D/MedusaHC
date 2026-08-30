# Scripts

This folder contains the additional Python scripts used by the MedusaHC configuration and slicer workflow.

## `medusahc.py`

The main MedusaHC Klipper controller. It performs tool pickup and parking,
feeder control, cleaning and priming, offset application, and sensor-state
verification. Copy it to Klipper's `klippy/extras` directory together with
`pin_watch.py`, keep `[medusahc]` enabled in `MHC_macros.cfg`, and restart
Klipper.

## `pin_watch.py`

Klipper extension that monitors the toolhead and dock switches in real time. It determines which tool is installed, detects invalid sensor combinations, and can synchronize the active tool and status colors with the Mainsail/Fluidd tool panel.

Optional compatibility synchronization with `klipper-toolchanger` remains
available but is disabled by default. Enable it only after installing and
configuring that plugin separately; MedusaHC itself does not require it.

Copy it to the Klipper extras directory and restart Klipper. Common locations are:

```text
/home/biqu/klipper/klippy/extras
/home/pi/klipper/klippy/extras
```

The exact path depends on the host installation.

## `SET_FINISH.py`

OrcaSlicer post-processing script. It adjusts the first travel moves after a tool change and converts temperature-wait commands after the first layer where required by this workflow.

## `SET_FINISH_Snapmaker_Orca.py`

Alternative post-processing script used for the Snapmaker Orca workflow. It adjusts the post-tool-change travel order without the additional temperature-command conversion performed by `SET_FINISH.py`.

Python must be installed on the slicing computer. Configure the local Python and script paths in OrcaSlicer; paths saved on another computer will not work.
