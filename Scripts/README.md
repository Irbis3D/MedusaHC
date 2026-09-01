# Scripts

This folder contains optional post-processing scripts for the slicer workflow.
The Klipper modules are stored separately in `klippy/extras/`, matching their
installation destination.

## `SET_FINISH.py`

OrcaSlicer post-processing script. It adjusts the first travel moves after a tool change and converts temperature-wait commands after the first layer where required by this workflow.

## `SET_FINISH_Snapmaker_Orca.py`

Alternative post-processing script used for the Snapmaker Orca workflow. It adjusts the post-tool-change travel order without the additional temperature-command conversion performed by `SET_FINISH.py`.

Python must be installed on the slicing computer. Configure the local Python and script paths in OrcaSlicer; paths saved on another computer will not work.
