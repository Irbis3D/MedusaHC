# V-Back Mounts

These **MGN9H** parts are used when the MedusaHC docks are installed behind the print area.

The folder contains left/right MGN9H axis mounts and alternative MedusaHC rear mounts for M3 or M5 hardware. Select only the mounting option that matches the frame and hardware.

V-Back places the docks closer to the XY motors, reducing the influence of belt elasticity during docking and improving repeatability. It also keeps the front of the printer unobstructed.

The standard Duender front mounts remain installed. The MedusaHC docks are attached to the rear frame profile with the new rear mounting parts in this folder.

The complete X axis must be reversed for this layout:

- use the new reversed X-axis mounts;
- move the X rail to the opposite side of the profile;
- route the belts behind the X profile.

Several belt teeth currently need to be removed where the belt is clamped by the toolhead mount. Otherwise, the carriage may not seat fully. A small drop of cyanoacrylate adhesive can be added at the clamped section to reduce the risk of slipping. This is a temporary solution and may be improved in a later revision.

Check rear clearance carefully. It may be necessary to move the complete Z axis and bed assembly forward.

Set `variable_tools_direction: -1`, enter the real dock coordinates, and move printer parking positions safely away from the rear docks.
