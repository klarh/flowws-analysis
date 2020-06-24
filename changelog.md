# v0.6.0 - 2020/06/24

## Added

- Support per-particle diameters in Garnett
- `draw_scale` argument in Plato
- Dynamic versions of rectangle and convex hull selections in Selection
- Menu item in ViewQt to toggle the display of the stage configuration panel
- Ability to filter records by group in GTAR
- `disable_selection` argument in Plato
- `display_box` argument in Plato

## Fixed

- Bug with overwriting quantities in Selection
- Repeated filtering bug in Selection

# v0.5.1 - 2020/04/23

## Fixed

- Fixed scaling of `Diffraction` for triclinic boxes

# v0.5 - 2020/04/15

## Added

- `Diffraction` module (experimental status)
- Ability to link rotations of various plato-related visuals
- CIF file support in `Garnett`
- Basic `SaveGarnett` module for individual frames (improved functionality to come at a later time)

## Fixed

- Improved robustness of `Plato` when colors aren't given
- Added scrollbar to `ViewQt` configuration panel
- Increase the number of decimal places for `ViewQt` floating-point widgets

# v0.4 - 2020/03/27

## Added

- `Center` module
- `Selection` module

## Fixed

- Fixed `Garnett` for garnett 0.7 API change
- Set `clip_scale` for plato visuals in `ViewNotebook`
- Made `ViewNotebook` and `ViewQt` update features from plato scenes

# v0.3 - 2020/02/27

## Added

- `Garnett`

## Updated

- Qt libraries other than pyside2 can be used in `ViewQt`
- Colors can be directly read from getar files using `GTAR`

# v0.2 - 2020/02/25

## Added

- `Save`
- `loop_frames` argument in `GTAR` to loop over entire trajectories

## Updated

- `ViewQt` uses antialiasing by default for plato scenes
- More configuration options for rendering in `Plato`
- Improved configuration for many modules in `ViewQt`

# v0.1 - 2020/02/13

## Added

- `Colormap`
- `GTAR`
- `Plato`
- `Pyriodic`
- `ViewNotebook`
- `ViewQt`
