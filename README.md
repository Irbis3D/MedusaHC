
# MedusaHC (Beta)

MedusaHC is an open-source toolchanger (hotend-changer) project.  
This is a beta version of the project. It is not finished yet, and there may be bugs during operation. The project will be updated gradually.

The project is fully open. You can do whatever you want with it.  
Only one request: it is not required, but I would be very grateful if you mention me in your modifications and derivatives of this project.

## Support the project

If you have the ability and desire to support the project, you can do it in several ways:

- Patreon — monthly support: https://patreon.com/Irbis3D  
- Ko-fi / Buy Me a Coffee — one-time donations: https://buymeacoffee.com/Irbis3D  
- YouTube Super Thanks — under any video: https://youtube.com/@Irbis3D  

Your support helps me create more content, upgrade gear, and keep experimenting with cool ideas.

Also, by buying parts using my links, you help as well.

## Credits

This project uses some work and ideas from the Dragonburner project by chirpy2605:  
https://github.com/chirpy2605/voron/tree/main/V0/Dragon_Burner

As well as from Sherpa_mini-Extruder by Annex-Engineering  
https://github.com/Annex-Engineering/Sherpa_Mini-Extruder

## Current status and compatibility

Right now, MedusaHC is an add-on for my Duender project:  
https://www.printables.com/model/1300968-duender-mgn9h-2x-creality-ender-3-corexy-convertio

Potentially, the project can be adapted for other classic CoreXY printers (as long as the printer has enough space in the front for the hotends and the bases). Theoretically, with small modifications, MedusaHC can also be adapted for CoreXY with a flying gantry.

The point of the project is that, unlike classic toolchangers, MedusaHC swaps only the hotend as a tool (with heater, thermistor, and fan). I am not the first who did this and I will not be the last. This topic is actively discussed and developed on my  
Discord server - https://discord.gg/ae44FHv786

## Documentation and audience

At the moment, the project does not have a full detailed assembly manual and is intended for experienced users.

Later I will make a full video where I explain how everything works and how to set it up. There is also a chance that, thanks to subscribers, after some time there will be a normal text manual with pictures.

For a general understanding, I recommend watching the first video about this project on my YouTube channel. You will not find all the information there, but you can get a general idea of how it works.

## Parts, BOM, and files

For this project you need to buy quite a lot of parts. I tried not to use expensive and rare components. The list of all required parts can be found in the file MedusaHC_BOM.txt. This file will be updated as the project updates.

You can also find and export the print models yourself from the STEP file (the file was created in Fusion360. There were issues when opening it in FreeCAD, possibly due to some format mismatch).

There are also all STL files. In addition, you can use the 3MF file. This is an exported OrcaSlicer project, where you can see the orientation of all parts, the marked areas where supports are needed, and the settings I used to print the parts. This file will be useful later during setup, because it contains a full slicer config for MedusaHC.

To understand how everything should be assembled, for now use the STEP file. I printed all parts in ABS with 98% infill.

## Important notes

All parts must be printed with good enough quality so that parts do not get stuck inside each other. Some contact surfaces may need a bit of sanding to make them smooth.

When installing magnets (I glued them, and all magnet holes have access from the back for removing magnets), be careful and do not mix up the polarity.

The M3 pins that act as hotend guide pins must be pressed into the plastic as straight as possible. I hammered them in, but it is better to do it carefully using a vise. The two lower M3 30mm pins are mandatory. The upper M3 20mm pins are optional, if the hotend does not hold firmly enough.

On the hotend, the matching holes for the pins must be prepared. Personally, I used M3 inserts for this, and I drilled them first with a 3mm bit (they are usually about 2.9mm), and then with a 3.2mm bit (my bits are closer to 3.1mm). Even though the size looks odd, these drill bits are quite common.

Before drilling the actual part, I recommend testing on some test piece to make sure the hole is not too large. The pins must slide in freely, but must not be loose.

Maybe later it will be possible to use brass bushings of the correct diameter, but they take more space and may not fit.

The pressure lever spring for the feeder from the standard Sherpa Mini kit does not fit. I just found a suitable spring in my spare parts. When a spring with known dimensions is selected, I will add this information to the BOM.

The spring for the feeder opener lever is just a regular spring from a ballpoint pen.

Other than that, you just need to assemble everything carefully so nothing is loose and nothing binds. As I said earlier, I will explain more nuances in the video.

## Electronics

For this project, I use the **BTT Manta M8P** board. For a 4-hotend configuration, it can be considered the most optimal option. It has enough ports for absolutely everything, including 4 hotend heaters and even a dedicated Servo port (which is sufficient without a DC-DC converter). My configuration files are set up specifically for this board with a **CB2** module.  
https://s.click.aliexpress.com/e/_oktZaKt

Roughly the same capabilities are provided by boards like **BTT Octopus Pro**, **Kraken**, and other “large” boards, with the main difference being that the HOST is located separately.  
https://s.click.aliexpress.com/e/_c2wuASWJ  
https://s.click.aliexpress.com/e/_c3kPDyx1

When using other boards, it is possible to connect additional boards to a single host.

### Ports required per hotend (on the controller board)

For each hotend, the board must have the following ports:

- heater port (MOSFET-controlled; can be used either hotend heaters or the bed)  
- thermistor port  
- fan port (either PWM-controlled or a constant 24V port)  
- endstop port for the endstop located on the base of that hotend  

### Ports required for the toolhead

- one extruder motor port  
- part cooling fan port(s)  
- toolhead endstop port  
- port for the auto-calibration sensor (I use **BTT Eddy** connected via CAN)  
- servo port — if the board does not have a dedicated servo port capable of supplying stable 5V under load, it is recommended to power the servo via a **24V→5V DC-DC converter** from the main power supply  

### Power considerations

Additional hotends require additional power from the PSU.

From experience, a standard **350W** power supply is reliably sufficient for **2 hotends**.  
For **3 hotends**, it can be enough with a high-quality PSU.  
For **4 hotends**, it is definitely not enough.

In my setup with the **Manta M8P**, I use one **350W** power supply for the heated bed, and another **350W** power supply for everything else.

## Configuration setup

The main printer parameters, as before, are located in the `printer.cfg` file.  
In general, the configuration is no different from a standard Duender config.

The exception is that the extruder configuration block has been moved into the MedusaHC configuration file. More on this below.

### Additional modules

Personally, I use **klipper-tmc-autotune** for tuning motor drivers.  
(This is optional.)

### Display and sensors

In my opinion, the optimal screen is **BTT HDMI5**.

I also use the **Eddy-ng** module for auto-calibration and nozzle tap probing.  
In my setup, Eddy is connected via **CAN** (to save USB ports).

## Arcs support

The `[gcode_arcs]` block and the **Arc fitting** setting in the slicer allow the slicer to use **G2** and **G3** commands to print arcs instead of short straight segments.

On weak HOST systems, problems were observed with this feature. In such cases, it should either be disabled or the resolution should be set higher than **0.1**.

## System configuration files modified for this setup

### sensorless.cfg

This file has been modified quite heavily to make parking safer and to improve parking repeatability without endstops.

Parking is performed in the back-left corner (**X = min, Y = max**).  
First, the **Y axis** is parked (to avoid hitting hotends on the bases), then **X**, with small side movements. After that, **Y and X** are parked once again.

This ensures that the final parking always happens from the same distance relative to zero.

### line_purge.cfg

Modified so that the purge line is printed not along the X axis, but on the left side of the bed along the Y axis.

In my setup, **Adaptive** is disabled, so the line is always printed in the same place. It can be enabled if desired, in which case the line will be printed closer to the model.  
(Optional.)

### klipperScreen.conf

A menu with buttons for the main **MHC macros** has been added.  
(Optional.)

### macros.cfg

The `START_PRINT`, `END_PRINT`, `PAUSE`, and `RESUME` macros were heavily modified.

The start macro receives from the slicer the required temperatures for the hotends that will be used during the print and heats them up. At the moment, it does not take into account whether a hotend will be used soon or should wait its turn. I am not happy with this behavior yet, but I have not found a good solution so far.

The pause and resume macros are also heavily adapted for this system. The idea is that during tool changes, the printer remembers which tool it is trying to pick up. In case of a failure, the printer pauses and gives time to fix the issue.

It is enough to manually adjust the hotends so that they are in one of the “correct states” and then press resume. Regardless of what was done manually, the printer will automatically check which hotend it planned to take before the pause, park the X and Y axes (this is necessary if the motors skipped steps), and then ensure that the print continues with the correct hotend.

This procedure still has some shortcomings. A visible defect may remain on the model at that spot. Additionally, when parking with sensorless homing, the zero point may shift slightly, which can appear on the model as a small layer shift. In most cases, this shift is very small.

---

## MedusaHC configuration

The main files responsible for MedusaHC operation are:

- `MHC_config` — configuration of all hardware related to MHC  
- `MHC_variables` — variables for configuring various coordinates, speeds, and similar parameters  
- `MHC_macros` — the main file containing all macros responsible for MHC functionality  

And the `pin_watch.py` script — in the current version, a dedicated script is used to monitor sensor states. It listens to the sensors in real time and updates variable states accordingly. Based on this data, MHC determines what is installed where and checks for errors.

The file must be uploaded via FTP to the folder:

```

/home/biqu/klipper/klippy/extras

```

(` /home/pi/klipper/klippy/extras ` for Raspberry Pi users)

The script was integrated recently and has not been tested on different systems yet. If problems appear, I will make an additional version that works purely on macros, with manual state updates via a macro. (Feedback is required.)

All (or at least almost all) macros are designed to be universal and work with any number of hotends. The number of hotends is defined in the configuration and variables. My current config is for **4 hotends** (higher counts have not been tested yet).

## MHC setup

### MHC_config file

#### [pin_watch io] block

This block configures the `pin_watch` script.

- `sync_toolchanger: 1` — enables tool initialization in klipper-toolchanger (used for auto-calibration; explanation later).  
- `verbose` — enables additional console output with detailed pin state information.  
- `pin_e` — microswitch pin located on the toolhead.  
- `pin_t0`, `pin_t1`, etc. — microswitch pins on the bases of the corresponding hotends.

#### [duplicate_pin_override]

Since a single extruder motor is used for all tools, this block must specify the **step**, **dir**, and **enable** pins for that motor. This allows all extruders to use the same pins without causing configuration errors.

#### [extruder], [extruder1], etc.

Nothing special here. All extruders share the same **step**, **dir**, and **enable** pins. The rest is standard extruder configuration.  
A corresponding `extruder` block must be created for each hotend.

#### [gcode_macro T0], [gcode_macro T1], etc.

Mandatory macros that “create” additional tools in the system.  
The number of these macros must match the number of hotends.

#### [servo my_servo]

The last mandatory block. This defines the servo used to help open the feeder.

After that come optional parameters:

- fan configuration (if you are using controllable fan ports)  
- additional heater parameters  

It is recommended to change heater-related parameters only if there are heating problems, and only as a last resort, preferably temporarily.

---

### MHC_variables file

#### [save_variables]

This block defines the file where tool offsets are stored so they can be restored after a restart.  
(It is required when using auto-calibration.)

#### [gcode_macro TOOL_CFG]

This macro contains the main coordinates and distances used in the system, as well as the speeds and accelerations for the tool change procedure.

- `variable_x_t0`, `variable_x_t1`, etc. — the **X coordinate** where each hotend is mounted on its base.  
  In this configuration, the minimum safe distance between tools is **65 mm**. With small modifications, this distance could probably be reduced slightly, but not by much — maybe **5–10 mm**.

- `variable_y_safe` — the **Y coordinate** where the extruder with an inserted hotend can freely move left and right without hitting other hotends on their bases.  
  In my case, this coordinate is **negative**, because I used slightly extended profiles on the Y axis. This way, I do not lose any printable area. With standard profiles, there is a chance you will lose **5–10 mm** on the Y axis.

- `variable_y_latch` — the **Y coordinate** where the toolhead fully engages with the hotend.  
  This must be set very precisely so that the toolhead presses firmly against the hotend, but without causing the motors to skip steps.

- `variable_x_shift` — the distance the hotend needs to move along the X axis from `variable_x_t` in order to remove it from the base keyhole.

- `variable_fast_accel`  
- `variable_fast_speed` — speeds and accelerations for tool changes. During the change process, there are slowdowns that are calculated as proportions of these parameters.

- `variable_y_prime` — the **Y coordinate** where it is safe to prime filament into the bin.  
- `variable_y_brush` — the **Y coordinate** of the approximate center of the nozzle cleaning brush.  
- `variable_x_prime_shift` — the **X distance** from `variable_x_t` to the priming point.

#### [gcode_macro GLOBAL_STATE]

- `variable_max_tool: 4` — required by the macros to operate with the specified number of hotends.

- `variable_prime_amount` — the amount of filament (in mm) extruded during priming.  
  A small value (**7–8 mm**) is suitable when printing with a draft/wipe tower.  
  A larger value (**14–16 mm**) can be used for printing without a tower.

- `variable_prime_speed` — priming speed.

- `variable_prime_retract`, `variable_prime_retract_speed` — length and speed of the retract after priming.

- `variable_clean_move` — `1` to perform a clean move, `0` to skip it and just move to `y_safe`.

- `variable_clean_move_x`  
- `variable_clean_move_y`  
- `variable_clean_move_speed` — during cleaning, the hotend moves to the center of the brush and then performs a movement away from it using the parameters defined here.  
  Distances: a **positive** value moves in the positive direction, a **negative** value moves in the negative direction.

- `variable_clean_retract`  
- `variable_clean_retract_speed` — additional retract after cleaning.

Keep in mind that the lengths of these two retracts are linked to the slicer parameter **“Retraction when switching material”**.  
If the priming retract and the cleaning retract are **1 mm** each, then **“Retraction when switching material”** must be set to **2 mm**.

In some situations, with certain filaments and when printing without a draft tower, these parameters require additional calibration.

After this, there are parameters that are used internally by the macros.  
They should **not** be changed.

## Main macros file

And finally, the most important file. Nothing needs to be configured here (hopefully it will stay that way).  
I will not describe the system operation in full detail here. I will explain it a bit more in the video.  
Below is a short overview, just to understand the main algorithms.

---

### [delayed_gcode INIT_SENSOR_STATE]

This is a special G-code that runs on startup.  
It is responsible for:

- assigning variables that depend on printer parameters  
- initial tool assignment  
- applying tool offset values from the `saved_vars` file to the variables in `[gcode_macro TOOL_OFFSET]`

---

### Feeder control macros: OPEN, CLOSE and sub-macros

These macros control the feeder.

Running **two OPEN commands in a row is not allowed**, as this can cause the mechanism to jam.

There are no dedicated sensors to track the feeder state, so the state is stored in a variable. The printer uses this variable to determine whether the feeder is open or closed.

Since closing the feeder is relatively safe, it is forced on printer startup. From that moment on, the printer knows the feeder state and will not try to open it incorrectly.

#### Known issue

There is a known bug that I have not solved yet, related to opening the feeder.

If the printer received a motor disable command (`M84`) or if the motors were disabled by timeout, then on the **first feeder OPEN after that**, the extruder motor does not activate for some reason.

If the printer has been idle for a long time, or if you manually disabled the motors, then **before the next tool changes** you must execute the `OPEN` macro and then the `CLOSE` macro once.

After that, all further OPEN operations will work correctly.

I also added this procedure to the slicer start G-code, so this issue should definitely not occur during printing.

---

### Tool change macros: SET, DROP and sub-macros

Next come the `SET` and `DROP` macros and their sub-macros.

Splitting procedures into multiple macros is required, because within a single macro the firmware does not see variable updates. I will explain this in more detail in the video.

In general terms:

The **main macro responsible for all tool change procedures is `SET`**. This is the macro called by the `T` macros.

When `SET` is called with a tool parameter (`SET T=0`, `SET T=1`, etc.), the printer checks what is currently installed, based on data from the `pin_watch` script object.

- If no hotend is installed, the printer will pick up the requested hotend.  
- If a different hotend is installed, the printer will first drop it, then pick up the requested one.  
- If the requested hotend is already installed, the printer will simply apply the offsets for the selected tool and finish.

All of this happens automatically, without the need to manually specify anything.

Thanks to the `pin_watch` script, the printer always knows its state, even if you manually remove or install hotends.

---

### DROP macro and error handling

The `DROP` macro can be used independently from `SET` to drop the currently installed hotend.  
However, for manual dropping it is better to use the dedicated `DROP_CLOSE` macro.

All pickup and drop macros include checks.

If after dropping or picking up a hotend the script detects that the sensor state does not match the expected one (for example, the drop failed, pickup failed, or some other hotend fell off its base), the printer will pause and enter an error state.

After fixing the problem and resuming, the printer will pick up the planned tool and continue printing.

As mentioned earlier, this logic works, but still requires further optimization.

---

## Orca Slicer configuration

All slicer settings can be viewed by opening the file `4Rca cube.3mf` as a project.

All MHC-specific parameters are located in the printer settings.

### Machine G-code tab

The following sections are modified:

- Start G-code  
- End G-code  
- Change filament G-code  

The **Layer change G-code** also includes a modification that assigns a layer variable. It is not used at the moment, but may be useful in the future.

### Multimaterial tab

You must specify the number of extruders. After that, separate tabs with settings for each hotend will appear.

All print parameters related to multimaterial printing are also located in the **Multimaterial** tab.

---

## G-code post-processing script

In addition, to optimize the workflow, I use a G-code post-processing script called `SET_FINISH.py`.

This script slightly changes the order of movements when transitioning back to printing after a tool change.  
It also replaces some temperature commands that include waiting with non-waiting commands.

This is done so that, when **Ooze prevention** is enabled, the printer does not wait for temperature stabilization after every tool change.

Be careful with **Ooze prevention** settings. The heating time must always be sufficient for the hotend to reach the target temperature.

To use this script, **Python must be installed on the computer**.  
You must specify the path to Python and to the script itself in the **Others** tab, in the **Post-processing Scripts** section.

In my case, this block looks like this:

```

"C:\Users\their\AppData\Local\Python\pythoncore-3.14-64\python.exe" "C:\Firmware\Medusa HC Beta CONFIG\SET_FINISH.py" 12
;

```

## Tool offset calibration

Offsets work relative to the first tool.  
That means all offsets for **T0** are equal to `0`, and all other tools are calculated relative to **T0**.

Keep in mind that this system uses **G-code offsets**.  
That is, how much the entire coordinate system needs to be shifted so that the hotend ends up in the same position as **T0**.

Do not confuse this with *tool offset*, where the value indicates how much the hotend itself is shifted from the desired point.

As a result, **tool offset has the opposite sign of the G-code offset**.

---

### Manual tool offset calibration

In the `MHC_macros` file, inside the `INIT_SENSOR_STATE` macro, you need to comment out  
(add `#` at the beginning of each line) the entire **“Initial tool offset setup”** block.

---

### Z offset calibration

Z calibration is done manually, via the web interface or the printer menu.

Lower each hotend to the bed and calculate the offset relative to the first hotend.

---

### XY offset calibration

For this, you need to print special calibration models.  
I used this one:

https://www.printables.com/model/129617-offset-xy-dual-extruder-idex-calibration

Place **one fewer copy** of this model than the number of hotends on the bed.

- The bottom part of all copies is printed with **T0**
- The top parts are printed with different hotends: **T1, T2**, and so on

Keep in mind that this test shows **tool offset**, so for MHC you need to **invert the sign** of the obtained values.

The resulting offsets must be written into the corresponding variables in the  
`MHC_variables` file, inside the `TOOL_OFFSET` macro.

---

## Automatic Z offset calibration using Eddy-ng

Basic Eddy-ng installation is done according to the standard instructions.

The Eddy mount in this project is made without adjustment and fits the Bambulab hotend clones that I use.

Eddy is quite sensitive to installation height, so you may need to slightly shift the holes in the model and reprint the mount.

The standard Eddy-ng feature set does **not** support working with multiple tools.

For auto-calibration to work, you must replace the `probe_eddy_ng.py` script located in:

```

/home/biqu/eddy-ng

```

with the modified `probe_eddy_ng.py` from this project.

This version can pass the required data to calculate offsets for all tools.

To enable auto-calibration, you need to include the file `eddy_ng_features.cfg`.  
It contains all the required macros.

Automatic calibration of all available tools can be started with the macro:

```

TOOL_Z_CALIBRATION

```

For accurate calibration, make sure the nozzles of all tools are clean.

After auto-calibration, the calculated offsets are saved to the `saved_vars` file and will be applied on every printer startup.

---

## Full auto-calibration using Sexball

Theoretically, I have an almost working script for auto-calibration using the Sexball sensor.  
However, I am not satisfied with how the values are calculated.

Because of this, I added the ability to partially integrate the **klipper-toolchanger** plugin by Viesturs Zariņš into MHC:

https://github.com/viesturz/klipper-toolchanger

The plugin is installed using the command from its manual:

```

wget -O - [https://raw.githubusercontent.com/viesturz/klipper-toolchanger/main/install.sh](https://raw.githubusercontent.com/viesturz/klipper-toolchanger/main/install.sh) | bash

```

Configuration settings for klipper-toolchanger are located in `toolchanger.cfg`.

The configuration is minimal:

- a `[toolchanger]` block with everything disabled  
- one `[tool T0]`, `[tool T1]`, etc. block for each hotend  

In practice, klipper-toolchanger does almost nothing.  
All MHC functionality still works exactly as before.

The only thing klipper-toolchanger needs for auto-calibration is to know which tool is currently active and to pass calibration data back.

To synchronize MHC state with it, you must set:

```

sync_toolchanger: 1

```

in the `[pin_watch io]` script configuration.

To receive calibration data, you must place the modified `tools_calibrate.py` script into:

```

/home/biqu/klipper-toolchanger/klipper/extras

```

Since we are modifying an internal script, automatic updates of klipper-toolchanger will show an error.

Because of this, at this stage I do **not** recommend enabling auto-update for klipper-toolchanger in `moonraker.conf`.

If this approach remains the same, a separate fork with updates will be required.

---

## Auto-calibration settings

The base auto-calibration settings have not changed.  
They are located in `calibrate-offsets.cfg`, in the `[tools_calibrate]` block.

In the `CALIBRATE_MOVE_OVER_PROBE` macro, you must specify an approximate point above the center of the Sexball sphere.

The standard macros from klipper-toolchanger are not suitable.  
A modified `calibrate-offsets.cfg` is also included in this project.

For fully automatic calibration with saving and applying all offsets, run the macro:

```

CALIBRATE_AND_SAVE_OFFSETS

```

---

## Final notes

This project is fully open source. You are free to use it, modify it, and build your own derivatives.

If you find the project useful, any kind of support helps — it allows me to spend more time on development, testing, and experiments. The project will be updated gradually, as new ideas appear and as I have the time and resources to work on it.

Most discussions about this project and similar toolchanger concepts take place on my  
Discord server:

https://discord.gg/ae44FHv786

That is where new ideas are tested, problems are discussed, and future directions are shaped.




