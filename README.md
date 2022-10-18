## Fast Bottom Infill

This Plugin is plagiarized from an initial existing Cura Plugin : [Cura-Slow-Z](https://github.com/5axes/Cura-Slow-Z) by [5axes](https://github.com/5axes)

Cura uses the same speed for top and bottom layers infill.

This plugin adds a setting named "Enable Bottom Layers Speed Adjustments" to the speed settings in the Custom print setup of Cura. It allows for a specific speed for initial and bottom layers infill and initial wall.

This is usefull when using tri-hexagon infill at less than 50%, as the infill roof need to be done at a very small speed so that the infill holes can be filled (I use 40mm/s for 25% infill), but the bottom layers can still be printed fast.

These settings can be found in the Custom print setup by using the Search field on top of the settings (you WON'T SEE IT if you don't use "Search"!). If you want to make the setting permanently visible in the sidebar, right click and select "Keep this setting visible".

## Options

        Enable Bottom Layers Speed Adjustments : Activate plugin.
        Initial Layer Infill Speed : Initial Layer Infill Speed.
        Initial Layer Wall Speed : Initial Layer Wall Speed
        Bottom Layers Infill Speed : Bottom Layers Infill Speed

If you enter a speed of 0 in an option, this particular option becomes disabled.

## Installation

Create the directory "FastBottomInfill" in the plugins directory of Cura (Linux: ~/.local/share/cura/5.2/plugins), and put the contents there (so for example you will have ~/.local/share/cura/5.2/plugins/FastBottomInfill/README.md) and restart Cura.
