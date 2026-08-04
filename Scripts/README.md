# Scripts

This folder contains the additional Python scripts used by the MedusaHC configuration and slicer workflow.

## `pin_watch.py`

Klipper extension that monitors the toolhead and dock switches in real time. It determines which tool is installed, detects invalid sensor combinations, and can synchronize the active tool and status colors with klipper-toolchanger and the Mainsail/Fluidd tool panel.

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
