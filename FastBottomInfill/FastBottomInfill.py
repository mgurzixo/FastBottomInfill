# ------------------------------------------------------------------------------------------------------------------------------------
# Initial Copyright(c) 2020 Shane Bumpurs  (VMaxx ?)
#
# All modification after 05/2022 Copyright(c) 2022 5@xes
# All modification after 10/2022 Copyright(c) 2022 gurzixo
#
# Based on an existing Plugin https://github.com/VMaxx/SlowZ
# The SlowZ is released under the terms of the AGPLv3 or higher.
#
# Description:  postprocessing script to force bottom infill speed
#
# ------------------------------------------------------------------------------------------------------------------------------------
#
#   Version 1.0.0  16/10/2022 Initial version
#
# ------------------------------------------------------------------------------------------------------------------------------------

import re
from collections import OrderedDict

from UM.Extension import Extension
from UM.Application import Application
from UM.Settings.SettingDefinition import SettingDefinition
from UM.Settings.DefinitionContainer import DefinitionContainer
from UM.Settings.ContainerRegistry import ContainerRegistry
from UM.Logger import Logger


def is_begin_layer_line(line: str) -> bool:
    """Check if current line is the start of a layer section.

    Args:
        line (str): Gcode line

    Returns:
        bool: True if the line is the start of a layer section
    """
    return line.startswith(";LAYER:")


def is_z_line(line: str) -> bool:
    """Check if current line is a Z line

    Args:
        line (str): Gcode line

    Returns:
        bool: True if the line is a Z line segment
    """
    return "G0" in line and "Z" in line and not "E" in line


class FastBottomInfill(Extension):
    def __init__(self):
        super().__init__()

        self._application = Application.getInstance()

        self._i18n_catalog = None

        self._settings_dict = OrderedDict()
        self._settings_dict["fbi_enable"] = {
            "label": "Enable Bottom Layers Speed Adjust",
            "description": "Enable Bottom Layers Speed Adjustments",
            "type": "bool",
            "default_value": False,
            "settable_per_mesh": False,
            "settable_per_extruder": False,
            "settable_per_meshgroup": False
        }
        self._settings_dict["fbi0_speed"] = {
            "label": "Initial Layer Infill Speed",
            "description": "Initial Layer Infill Speed.",
            "type": "float",
            "unit": "mm/s",
            "default_value": 50,
            "minimum_value": "10",
            "maximum_value_warning": "200",
            "enabled": "fbi_enable",
            "settable_per_mesh": False,
            "settable_per_extruder": False,
            "settable_per_meshgroup": False
        }
        self._settings_dict["wbi0_speed"] = {
            "label": "Initial Layer Wall Speed",
            "description": "Initial Layer Wall Speed.",
            "type": "float",
            "unit": "mm/s",
            "default_value": 50,
            "minimum_value": "10",
            "maximum_value_warning": "200",
            "enabled": "fbi_enable",
            "settable_per_mesh": False,
            "settable_per_extruder": False,
            "settable_per_meshgroup": False
        }
        self._settings_dict["fbi_speed"] = {
            "label": "Bottom Layers Infill Speed",
            "description": "Bottom Layers Infill Speed.",
            "type": "float",
            "unit": "mm/s",
            "default_value": 50,
            "minimum_value": "10",
            "maximum_value_warning": "200",
            "enabled": "fbi_enable",
            "settable_per_mesh": False,
            "settable_per_extruder": False,
            "settable_per_meshgroup": False
        }
        ContainerRegistry.getInstance().containerLoadComplete.connect(
            self._onContainerLoadComplete)

        self._application.getOutputDeviceManager().writeStarted.connect(self._filterGcode)

    def _onContainerLoadComplete(self, container_id):
        if not ContainerRegistry.getInstance().isLoaded(container_id):
            # skip containers that could not be loaded, or subsequent findContainers() will cause an infinite loop
            return

        try:
            container = ContainerRegistry.getInstance(
            ).findContainers(id=container_id)[0]

        except IndexError:
            # the container no longer exists
            return

        if not isinstance(container, DefinitionContainer):
            # skip containers that are not definitions
            return
        if container.getMetaDataEntry("type") == "extruder":
            # skip extruder definitions
            return

        speed_category = container.findDefinitions(key="speed")
        fbi_enable = container.findDefinitions(
            key=list(self._settings_dict.keys())[0])
        fbi0Speed = container.findDefinitions(
            key=list(self._settings_dict.keys())[1])
        wbi0Speed = container.findDefinitions(
            key=list(self._settings_dict.keys())[2])
        fbiSpeed = container.findDefinitions(
            key=list(self._settings_dict.keys())[3])

        if speed_category and not fbiSpeed and not fbi0Speed and not wbi0Speed:
            speed_category = speed_category[0]
            for setting_key, setting_dict in self._settings_dict.items():

                definition = SettingDefinition(
                    setting_key, container, speed_category, self._i18n_catalog)
                definition.deserialize(setting_dict)

                # add the setting to the already existing platform adhesion setting definition
                speed_category._children.append(definition)
                container._definition_cache[setting_key] = definition
                container._updateRelations(definition)

    def _filterGcode(self, output_device):
        scene = self._application.getController().getScene()

        global_container_stack = self._application.getGlobalContainerStack()
        if not global_container_stack:
            return

        # get setting from Cura
        fbi0Speed = global_container_stack.getProperty("fbi0_speed", "value")
        wbi0Speed = global_container_stack.getProperty("wbi0_speed", "value")
        fbiSpeed = global_container_stack.getProperty("fbi_speed", "value")
        fbi_enable = global_container_stack.getProperty("fbi_enable", "value")

        if not fbi_enable:
            return

        gcode_dict = getattr(scene, "gcode_dict", {})
        if not gcode_dict:  # this also checks for an empty dict
            Logger.log("w", "Scene has no gcode to process")
            return

        dict_changed = False

        for plate_id in gcode_dict:
            gcode_list = gcode_dict[plate_id]
            if len(gcode_list) < 2:
                Logger.log(
                    "w", "G-Code %s does not contain any layers", plate_id)
                continue

            if ";FAST_BOTTOM_INFILL\n" not in gcode_list[0]:
                layercount = 0
                currentlayer = 0
                idl = 0  # Start
                doPatchF = 0
                doPatchF0 = 0
                doPatchW0 = 0
                if ";LAYER_COUNT:" in gcode_list[1]:
                    if ";LAYER:0\n" in gcode_list[1]:
                        # layer 0 somehow got appended to the start gcode chunk
                        # left this in as it appears to be preventative for an error.
                        chunks = gcode_list[1].split(";LAYER:0\n")
                        gcode_list[1] = chunks[0]
                        gcode_list.insert(2, ";LAYER:0\n" + chunks[1])

                    # flines = gcode_list[1].split("\n")
                    # Logger.log("w", "gcode_list %d", len(gcode_list))
                    # for (fline_nr, fline) in enumerate(flines):
                    #     if fline.startswith(";LAYER_COUNT:"):
                    #         Logger.log("w", "found LAYER_COUNT %s", fline[13:])
                    #         layercount=float(fline[13:])
                    # Logger.log("w", "layercount %f", layercount)
                    # go through each layer
                    for i in range(len(gcode_list)):
                        lines = gcode_list[i].split("\n")
                        for (line_nr, line) in enumerate(lines):

                            if idl == 0 and line.startswith(";LAYER:1"):
                                idl = 1

                            if idl == 1 and line.startswith(";TYPE:FILL"):
                                idl = 2

                            # Initial Layer
                            if idl == 0:
                                if line.startswith(";TYPE:SKIN") and fbi0Speed > 0:
                                    doPatchF0 = 1
                                elif line.startswith(";TYPE:"):
                                    doPatchF0 = 0

                                if (line.startswith(";TYPE:WALL-INNER") or line.startswith(";TYPE:WALL-OUTER")) and wbi0Speed > 0:
                                    doPatchW0 = 1
                                elif line.startswith(";TYPE:"):
                                    doPatchW0 = 0

                                # Initial Infill
                                if doPatchF0 == 1:
                                    if line.startswith("G1 F"):
                                        res = re.sub(
                                            'G1 F[0-9.]+', 'G1 F'+str(fbi0Speed * 60), line)
                                        lines[line_nr] = res

                                # Initial Walls
                                if doPatchW0 == 1:
                                    if line.startswith("G1 F"):
                                        res = re.sub(
                                            'G1 F[0-9.]+', 'G1 F'+str(wbi0Speed * 60), line)
                                        lines[line_nr] = res

                            # Other bottom layers
                            if idl == 1:
                                if line.startswith(";TYPE:SKIN") and fbiSpeed > 0:
                                    doPatchF = 1
                                    lines
                                elif line.startswith(";TYPE:"):
                                    doPatchF = 0

                                if doPatchF == 1:
                                    if line.startswith("G1 F"):
                                        res = re.sub(
                                            'G1 F[0-9.]+', 'G1 F'+str(fbiSpeed * 60), line)
                                        lines[line_nr] = res

                        gcode_list[i] = "\n".join(lines)
                    gcode_list[0] += ";FAST_BOTTOM_INFILL\n"
                    gcode_dict[plate_id] = gcode_list
                    dict_changed = True
            else:
                Logger.log(
                    "d", "G-Code %s has already been processed", plate_id)
                continue

        if dict_changed:
            setattr(scene, "gcode_dict", gcode_dict)
