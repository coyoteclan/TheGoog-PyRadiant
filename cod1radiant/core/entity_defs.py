"""
CoD1 Entity Definitions based on cod.def.

This module provides entity class definitions, properties, and spawnflags
for all CoD1 entities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from enum import IntFlag


# ============================================================================
# Spawnflag Definitions
# ============================================================================

class LightSpawnflags(IntFlag):
    """Spawnflags for light entity."""
    LINEAR = 1  # Linear falloff instead of inverse square
    ANGLE = 2   # Light:surface angle calculation (linear only)


class CoronaSpawnflags(IntFlag):
    """Spawnflags for corona entity."""
    START_OFF = 1


class DoorSpawnflags(IntFlag):
    """Spawnflags for func_door entity."""
    START_OPEN = 1
    TOGGLE = 4
    CRUSHER = 8
    TOUCH = 16
    SHOOT_THRU = 32


class DoorRotatingSpawnflags(IntFlag):
    """Spawnflags for func_door_rotating entity."""
    X_AXIS = 4
    Y_AXIS = 8
    REVERSE = 16
    FORCE = 32


class RotatingSpawnflags(IntFlag):
    """Spawnflags for func_rotating entity."""
    START_ON = 1
    STARTINVIS = 2
    X_AXIS = 4
    Y_AXIS = 8


class StaticSpawnflags(IntFlag):
    """Spawnflags for func_static entity."""
    START_INVIS = 1
    PAIN = 2
    PAINEFX = 4


class TriggerSpawnflags(IntFlag):
    """Spawnflags for trigger_multiple entity."""
    AI_AXIS = 1
    AI_ALLIES = 2
    AI_NEUTRAL = 4
    NOTPLAYER = 8
    VEHICLE = 16


class TriggerHurtSpawnflags(IntFlag):
    """Spawnflags for trigger_hurt entity."""
    START_OFF = 1
    PLAYER_ONLY = 2
    SILENT = 4
    NO_PROTECTION = 8
    SLOW = 16
    ONCE = 32


class TriggerDamageSpawnflags(IntFlag):
    """Spawnflags for trigger_damage entity."""
    PISTOL_NO = 1
    RIFLE_NO = 2
    PROJ_NO = 4
    SPLASH_NO = 8
    MELEE_NO = 16
    FLAME_NO = 32


class NodeSpawnflags(IntFlag):
    """Spawnflags for AI nodes."""
    DONT_LINK = 1
    NOT_CHAIN = 2
    DONT_STAND = 4
    DONT_CROUCH = 8
    DONT_PRONE = 16


class MiscModelSpawnflags(IntFlag):
    """Spawnflags for misc_model entity."""
    ORIENT_LOD = 1
    NO_SHADOW = 2


class ItemSpawnflags(IntFlag):
    """Spawnflags for item entities."""
    SUSPENDED = 1
    SPIN = 2
    RESPAWN = 4


# ============================================================================
# Entity Property Definitions
# ============================================================================

@dataclass
class PropertyDef:
    """Definition of an entity property."""
    name: str
    prop_type: Literal["string", "integer", "float", "color", "vector", "angle"]
    default: str = ""
    description: str = ""


@dataclass
class EntityDef:
    """Definition of an entity class."""
    classname: str
    description: str = ""
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)  # Editor color
    size: tuple[tuple[float, float, float], tuple[float, float, float]] | None = None  # Bounding box
    properties: list[PropertyDef] = field(default_factory=list)
    spawnflags: dict[int, str] = field(default_factory=dict)
    is_point_entity: bool = True  # False for brush entities


# ============================================================================
# Entity Definitions Dictionary
# ============================================================================

ENTITY_DEFINITIONS: dict[str, EntityDef] = {}


def _register(entity: EntityDef):
    """Register an entity definition."""
    ENTITY_DEFINITIONS[entity.classname] = entity


# ----------------------------------------------------------------------------
# Worldspawn
# ----------------------------------------------------------------------------

_register(EntityDef(
    classname="worldspawn",
    description="World entity - contains all static brushes",
    is_point_entity=False,
    properties=[
        PropertyDef("music", "string", "", "Music WAV file (optional intro & loop)"),
        PropertyDef("ambienttrack", "string", "", "Ambient WAV file"),
        PropertyDef("gravity", "integer", "800", "Gravity value"),
        PropertyDef("message", "string", "", "Text during connection"),
        PropertyDef("ambient", "float", "", "Ambient light (1=full, 2=overbright)"),
        PropertyDef("_color", "color", "1 1 1", "Ambient light color RGB"),
        PropertyDef("sun", "string", "", "Sun image shader"),
        PropertyDef("suncolor", "color", "", "Sun RGB color (0-1 scale)"),
        PropertyDef("sunlight", "float", "", "Sun intensity"),
        PropertyDef("sundiffusecolor", "color", "", "Diffuse sun RGB"),
        PropertyDef("diffusefraction", "float", "", "Diffuse light fraction (0-1)"),
        PropertyDef("sundirection", "vector", "", "Pitch Yaw Roll to sun"),
        PropertyDef("northyaw", "float", "", "Yaw angle for north"),
    ],
))


# ----------------------------------------------------------------------------
# Light Entities
# ----------------------------------------------------------------------------

_register(EntityDef(
    classname="light",
    description="Non-displayed light source",
    color=(1.0, 1.0, 0.0),
    size=((-8, -8, -8), (8, 8, 8)),
    properties=[
        PropertyDef("light", "integer", "300", "Light intensity"),
        PropertyDef("_color", "color", "1 1 1", "Light color RGB"),
        PropertyDef("radius", "float", "64", "Spotlight radius at target"),
        PropertyDef("exponent", "float", "0", "Angle falloff exponent"),
        PropertyDef("fade", "float", "1.0", "Falloff/radius adjustment"),
        PropertyDef("overbrightShift", "integer", "0", "Overbright radius control"),
        PropertyDef("target", "string", "", "Target for spotlight"),
    ],
    spawnflags={
        1: "linear",
        2: "angle",
    },
))

_register(EntityDef(
    classname="corona",
    description="Visible light corona effect",
    color=(1.0, 0.8, 0.0),
    size=((-4, -4, -4), (4, 4, 4)),
    properties=[
        PropertyDef("color", "color", "1 1 1", "Corona color RGB (0-1)"),
        PropertyDef("scale", "float", "1.0", "Size multiplier"),
    ],
    spawnflags={
        1: "START_OFF",
    },
))


# ----------------------------------------------------------------------------
# Info Entities
# ----------------------------------------------------------------------------

_register(EntityDef(
    classname="info_player_start",
    description="Player start point",
    color=(0.0, 1.0, 0.0),
    size=((-16, -16, 0), (16, 16, 72)),
    properties=[
        PropertyDef("angles", "angle", "0 0 0", "Pitch Yaw Roll"),
    ],
))

_register(EntityDef(
    classname="info_null",
    description="Invisible position point for calculations",
    color=(0.5, 0.5, 0.5),
    size=((-4, -4, -4), (4, 4, 4)),
))

_register(EntityDef(
    classname="info_notnull",
    description="Position point that persists in game",
    color=(0.5, 0.5, 0.5),
    size=((-4, -4, -4), (4, 4, 4)),
))

_register(EntityDef(
    classname="info_notnull_big",
    description="info_notnull with larger box",
    color=(0.5, 0.5, 0.5),
    size=((-16, -16, -16), (16, 16, 16)),
))

_register(EntityDef(
    classname="info_grenade_hint",
    description="AI grenade throw hint",
    color=(1.0, 0.5, 0.0),
    size=((-8, -8, -8), (8, 8, 8)),
    properties=[
        PropertyDef("target", "string", "", "Target position"),
    ],
))

_register(EntityDef(
    classname="info_vehicle_node",
    description="Vehicle path node",
    color=(0.0, 0.5, 1.0),
    size=((-16, -16, -16), (16, 16, 16)),
    properties=[
        PropertyDef("target", "string", "", "Next node"),
        PropertyDef("speed", "float", "", "Speed at this node"),
    ],
))


# ----------------------------------------------------------------------------
# Misc Entities
# ----------------------------------------------------------------------------

_register(EntityDef(
    classname="misc_model",
    description="Places an XModel in the map",
    color=(1.0, 0.5, 0.0),
    size=((-16, -16, 0), (16, 16, 32)),
    properties=[
        PropertyDef("model", "string", "", "XModel path"),
        PropertyDef("modelscale", "float", "1", "Uniform scale"),
        PropertyDef("modelscale_vec", "vector", "1 1 1", "Per-axis scale"),
        PropertyDef("targetname", "string", "", "Script name (makes server-side)"),
        PropertyDef("angles", "angle", "0 0 0", "Rotation"),
    ],
    spawnflags={
        1: "ORIENT_LOD",
        2: "NO_SHADOW",
    },
))

_register(EntityDef(
    classname="misc_mg42",
    description="MG42 turret emplacement",
    color=(0.5, 0.0, 0.0),
    size=((-32, -32, 0), (32, 32, 48)),
    properties=[
        PropertyDef("weaponinfo", "string", "", "Weapon info"),
        PropertyDef("leftarc", "float", "", "Horizontal left arc"),
        PropertyDef("rightarc", "float", "", "Horizontal right arc"),
        PropertyDef("toparc", "float", "", "Vertical top arc"),
        PropertyDef("bottomarc", "float", "", "Vertical bottom arc"),
        PropertyDef("convergencetime", "float", "", "Time to acquire target"),
        PropertyDef("maxrange", "float", "", "Maximum range"),
        PropertyDef("damage", "float", "", "NPC damage"),
        PropertyDef("accuracy", "float", "", "Accuracy (1.0 = 100%)"),
        PropertyDef("angles", "angle", "0 0 0", "Rotation"),
    ],
))

_register(EntityDef(
    classname="misc_turret",
    description="General turret emplacement",
    color=(0.5, 0.0, 0.0),
    size=((-32, -32, 0), (32, 32, 48)),
    properties=[
        PropertyDef("weaponinfo", "string", "", "Weapon info"),
        PropertyDef("leftarc", "float", "", "Horizontal left arc"),
        PropertyDef("rightarc", "float", "", "Horizontal right arc"),
        PropertyDef("toparc", "float", "", "Vertical top arc"),
        PropertyDef("bottomarc", "float", "", "Vertical bottom arc"),
        PropertyDef("angles", "angle", "0 0 0", "Rotation"),
    ],
))

_register(EntityDef(
    classname="misc_prefab",
    description="Prefab reference (CoD2, loaded at compile time)",
    color=(0.7, 0.7, 0.0),
    size=((-8, -8, -8), (8, 8, 8)),
    properties=[
        PropertyDef("model", "string", "", "Prefab .map path"),
        PropertyDef("angles", "angle", "0 0 0", "Rotation"),
    ],
))


# ----------------------------------------------------------------------------
# Function Entities (Brush-based)
# ----------------------------------------------------------------------------

_register(EntityDef(
    classname="func_group",
    description="Groups brushes in editor (becomes worldspawn at compile)",
    is_point_entity=False,
))

_register(EntityDef(
    classname="func_cullgroup",
    description="Groups brushes for portal-based culling",
    is_point_entity=False,
))

_register(EntityDef(
    classname="func_door",
    description="Moving door",
    is_point_entity=False,
    properties=[
        PropertyDef("key", "integer", "0", "Key number (0=unlocked)"),
        PropertyDef("angle", "float", "", "Opening direction"),
        PropertyDef("speed", "float", "100", "Movement speed"),
        PropertyDef("closespeed", "float", "", "Closing speed"),
        PropertyDef("wait", "float", "3", "Wait before return (-1=never)"),
        PropertyDef("lip", "float", "8", "Remaining lip"),
        PropertyDef("dmg", "integer", "2", "Damage when blocked"),
        PropertyDef("health", "integer", "", "Health (if shootable)"),
        PropertyDef("teamname", "string", "", "Team for sync opening"),
        PropertyDef("noisescale", "float", "", "AI alert volume multiplier"),
        PropertyDef("targetname", "string", "", "Target name"),
    ],
    spawnflags={
        1: "START_OPEN",
        4: "TOGGLE",
        8: "CRUSHER",
        16: "TOUCH",
        32: "SHOOT-THRU",
    },
))

_register(EntityDef(
    classname="func_door_rotating",
    description="Rotating door (requires origin brush)",
    is_point_entity=False,
    properties=[
        PropertyDef("degrees", "float", "90", "Rotation degrees"),
        PropertyDef("speed", "float", "100", "Rotation speed"),
        PropertyDef("time", "integer", "", "Opening time in milliseconds"),
        PropertyDef("targetname", "string", "", "Target name"),
    ],
    spawnflags={
        4: "X_AXIS",
        8: "Y_AXIS",
        16: "REVERSE",
        32: "FORCE",
    },
))

_register(EntityDef(
    classname="func_rotating",
    description="Continuously rotating object (requires origin brush)",
    is_point_entity=False,
    properties=[
        PropertyDef("speed", "float", "100", "Rotation speed"),
        PropertyDef("dmg", "integer", "2", "Damage when blocked"),
        PropertyDef("targetname", "string", "", "Target name"),
    ],
    spawnflags={
        1: "START_ON",
        2: "STARTINVIS",
        4: "X_AXIS",
        8: "Y_AXIS",
    },
))

_register(EntityDef(
    classname="func_bobbing",
    description="Up/down moving object",
    is_point_entity=False,
    properties=[
        PropertyDef("height", "float", "32", "Movement amplitude"),
        PropertyDef("speed", "float", "4", "Cycle duration in seconds"),
        PropertyDef("phase", "float", "0", "Starting phase 0.0-1.0"),
        PropertyDef("targetname", "string", "", "Target name"),
    ],
))

_register(EntityDef(
    classname="func_pendulum",
    description="Swinging object (requires origin brush)",
    is_point_entity=False,
    properties=[
        PropertyDef("speed", "float", "30", "Swing angle in degrees"),
        PropertyDef("phase", "float", "0", "Starting phase 0.0-1.0"),
        PropertyDef("targetname", "string", "", "Target name"),
    ],
))

_register(EntityDef(
    classname="func_static",
    description="Static brush model (can be triggered on/off)",
    is_point_entity=False,
    properties=[
        PropertyDef("targetname", "string", "", "Target name"),
        PropertyDef("shardtype", "integer", "4", "Shard type (0=glass,1=wood,2=metal,3=ceramic,4=pebble)"),
    ],
    spawnflags={
        1: "start_invis",
        2: "pain",
        4: "painEFX",
    },
))


# ----------------------------------------------------------------------------
# Trigger Entities
# ----------------------------------------------------------------------------

_register(EntityDef(
    classname="trigger_multiple",
    description="Trigger that can fire multiple times",
    is_point_entity=False,
    color=(0.5, 0.5, 1.0),
    properties=[
        PropertyDef("wait", "float", "0.5", "Seconds between triggers"),
        PropertyDef("random", "float", "", "Random variance for wait"),
        PropertyDef("target", "string", "", "Target to fire"),
        PropertyDef("targetname", "string", "", "Target name"),
    ],
    spawnflags={
        1: "AI_AXIS",
        2: "AI_ALLIES",
        4: "AI_NEUTRAL",
        8: "NOTPLAYER",
        16: "VEHICLE",
    },
))

_register(EntityDef(
    classname="trigger_once",
    description="Trigger that fires once (trigger_multiple with wait=-1)",
    is_point_entity=False,
    color=(0.5, 0.5, 1.0),
    properties=[
        PropertyDef("target", "string", "", "Target to fire"),
        PropertyDef("targetname", "string", "", "Target name"),
    ],
    spawnflags={
        1: "AI_AXIS",
        2: "AI_ALLIES",
        4: "AI_NEUTRAL",
        8: "NOTPLAYER",
        16: "VEHICLE",
    },
))

_register(EntityDef(
    classname="trigger_hurt",
    description="Damage trigger",
    is_point_entity=False,
    color=(1.0, 0.0, 0.0),
    properties=[
        PropertyDef("dmg", "integer", "5", "Damage per frame"),
        PropertyDef("life", "float", "0", "Lifetime (0=infinite)"),
        PropertyDef("targetname", "string", "", "Target name"),
    ],
    spawnflags={
        1: "START_OFF",
        2: "PLAYER_ONLY",
        4: "SILENT",
        8: "NO_PROTECTION",
        16: "SLOW",
        32: "ONCE",
    },
))

_register(EntityDef(
    classname="trigger_damage",
    description="Trigger that responds to damage",
    is_point_entity=False,
    color=(1.0, 0.5, 0.0),
    properties=[
        PropertyDef("accumulate", "float", "", "Total damage needed"),
        PropertyDef("threshold", "float", "", "Minimum damage per hit"),
        PropertyDef("target", "string", "", "Target to fire"),
        PropertyDef("targetname", "string", "", "Target name"),
    ],
    spawnflags={
        1: "PISTOL_NO",
        2: "RIFLE_NO",
        4: "PROJ_NO",
        8: "SPLASH_NO",
        16: "MELEE_NO",
        32: "FLAME_NO",
    },
))

_register(EntityDef(
    classname="trigger_use",
    description="Use-key trigger",
    is_point_entity=False,
    color=(0.0, 1.0, 0.5),
    properties=[
        PropertyDef("delay", "float", "", "Delay before reuse"),
        PropertyDef("cursorhint", "string", "", "Cursor type (HINT_ACTIVATE, HINT_DOOR, etc.)"),
        PropertyDef("hintstring", "string", "", "Hint text"),
        PropertyDef("target", "string", "", "Target to fire"),
        PropertyDef("targetname", "string", "", "Target name"),
    ],
))


# ----------------------------------------------------------------------------
# AI Pathfinding Nodes
# ----------------------------------------------------------------------------

_ai_node_properties = [
    PropertyDef("targetname", "string", "", "Node name"),
    PropertyDef("target", "string", "", "Target node"),
    PropertyDef("angles", "angle", "0 0 0", "Facing direction"),
    PropertyDef("script_noteworthy", "string", "", "Script identifier"),
]

_ai_node_spawnflags = {
    1: "DONT_LINK",
    2: "NOT_CHAIN",
    4: "DONT_STAND",
    8: "DONT_CROUCH",
    16: "DONT_PRONE",
}

_register(EntityDef(
    classname="node_pathnode",
    description="Standard navigation node",
    color=(0.0, 1.0, 1.0),
    size=((-8, -8, 0), (8, 8, 8)),
    properties=_ai_node_properties,
    spawnflags=_ai_node_spawnflags,
))

_register(EntityDef(
    classname="node_cover_stand",
    description="Standing cover position",
    color=(0.0, 0.8, 0.0),
    size=((-8, -8, 0), (8, 8, 72)),
    properties=_ai_node_properties,
    spawnflags=_ai_node_spawnflags,
))

_register(EntityDef(
    classname="node_cover_crouch",
    description="Crouching cover position",
    color=(0.0, 0.6, 0.0),
    size=((-8, -8, 0), (8, 8, 48)),
    properties=_ai_node_properties,
    spawnflags=_ai_node_spawnflags,
))

_register(EntityDef(
    classname="node_cover_prone",
    description="Prone cover position",
    color=(0.0, 0.4, 0.0),
    size=((-8, -8, 0), (8, 8, 16)),
    properties=_ai_node_properties,
    spawnflags=_ai_node_spawnflags,
))

_register(EntityDef(
    classname="node_cover_right",
    description="Right lean cover position",
    color=(0.0, 0.8, 0.2),
    size=((-8, -8, 0), (8, 8, 72)),
    properties=_ai_node_properties,
    spawnflags=_ai_node_spawnflags,
))

_register(EntityDef(
    classname="node_cover_left",
    description="Left lean cover position",
    color=(0.2, 0.8, 0.0),
    size=((-8, -8, 0), (8, 8, 72)),
    properties=_ai_node_properties,
    spawnflags=_ai_node_spawnflags,
))

_register(EntityDef(
    classname="node_cover_wide_right",
    description="Wide right cover position",
    color=(0.0, 0.6, 0.2),
    size=((-8, -8, 0), (8, 8, 72)),
    properties=_ai_node_properties,
    spawnflags=_ai_node_spawnflags,
))

_register(EntityDef(
    classname="node_cover_wide_left",
    description="Wide left cover position",
    color=(0.2, 0.6, 0.0),
    size=((-8, -8, 0), (8, 8, 72)),
    properties=_ai_node_properties,
    spawnflags=_ai_node_spawnflags,
))

_register(EntityDef(
    classname="node_concealment_stand",
    description="Standing concealment position",
    color=(0.5, 0.8, 0.0),
    size=((-8, -8, 0), (8, 8, 72)),
    properties=_ai_node_properties,
    spawnflags=_ai_node_spawnflags,
))

_register(EntityDef(
    classname="node_concealment_crouch",
    description="Crouching concealment position",
    color=(0.5, 0.6, 0.0),
    size=((-8, -8, 0), (8, 8, 48)),
    properties=_ai_node_properties,
    spawnflags=_ai_node_spawnflags,
))

_register(EntityDef(
    classname="node_concealment_prone",
    description="Prone concealment position",
    color=(0.5, 0.4, 0.0),
    size=((-8, -8, 0), (8, 8, 16)),
    properties=_ai_node_properties,
    spawnflags=_ai_node_spawnflags,
))

_register(EntityDef(
    classname="node_reacquire",
    description="Target reacquisition node",
    color=(1.0, 1.0, 0.0),
    size=((-8, -8, 0), (8, 8, 8)),
    properties=_ai_node_properties,
    spawnflags=_ai_node_spawnflags,
))

_register(EntityDef(
    classname="node_balcony",
    description="Balcony position",
    color=(0.0, 0.5, 0.8),
    size=((-8, -8, 0), (8, 8, 72)),
    properties=_ai_node_properties,
    spawnflags=_ai_node_spawnflags,
))

_register(EntityDef(
    classname="node_scripted",
    description="Scripted animation node",
    color=(1.0, 0.0, 1.0),
    size=((-8, -8, 0), (8, 8, 72)),
    properties=_ai_node_properties + [
        PropertyDef("animscript", "string", "", "Animation script name"),
    ],
    spawnflags=_ai_node_spawnflags,
))

_register(EntityDef(
    classname="node_negotiation_begin",
    description="Start of climb/jump animation",
    color=(0.8, 0.0, 0.8),
    size=((-8, -8, 0), (8, 8, 8)),
    properties=_ai_node_properties,
))

_register(EntityDef(
    classname="node_negotiation_end",
    description="End of climb/jump animation",
    color=(0.8, 0.2, 0.8),
    size=((-8, -8, 0), (8, 8, 8)),
    properties=_ai_node_properties,
))


# ----------------------------------------------------------------------------
# Script Entities
# ----------------------------------------------------------------------------

_register(EntityDef(
    classname="script_brushmodel",
    description="Scriptable brush model",
    is_point_entity=False,
    properties=[
        PropertyDef("targetname", "string", "", "Script name"),
    ],
))

_register(EntityDef(
    classname="script_model",
    description="Scriptable XModel",
    color=(1.0, 0.5, 1.0),
    size=((-16, -16, 0), (16, 16, 32)),
    properties=[
        PropertyDef("model", "string", "", "XModel path"),
        PropertyDef("targetname", "string", "", "Script name"),
        PropertyDef("angles", "angle", "0 0 0", "Rotation"),
    ],
))

_register(EntityDef(
    classname="script_origin",
    description="Scriptable origin point",
    color=(1.0, 0.5, 1.0),
    size=((-8, -8, -8), (8, 8, 8)),
    properties=[
        PropertyDef("targetname", "string", "", "Script name"),
    ],
))

_register(EntityDef(
    classname="script_vehicle",
    description="Scriptable vehicle",
    color=(0.5, 0.5, 1.0),
    size=((-32, -32, 0), (32, 32, 32)),
    properties=[
        PropertyDef("model", "string", "", "Vehicle model"),
        PropertyDef("targetname", "string", "", "Script name"),
        PropertyDef("vehicletype", "string", "", "Vehicle type"),
        PropertyDef("angles", "angle", "0 0 0", "Rotation"),
    ],
))


# ----------------------------------------------------------------------------
# Multiplayer Entities
# ----------------------------------------------------------------------------

_register(EntityDef(
    classname="mp_deathmatch_spawn",
    description="Deathmatch spawn point",
    color=(1.0, 0.0, 0.0),
    size=((-16, -16, 0), (16, 16, 72)),
    properties=[
        PropertyDef("angles", "angle", "0 0 0", "Spawn direction"),
    ],
))

_register(EntityDef(
    classname="mp_target_location",
    description="Location marker (for compass/text)",
    color=(1.0, 1.0, 0.0),
    size=((-64, -64, -16), (64, 64, 16)),
    properties=[
        PropertyDef("message", "string", "", "Location name"),
        PropertyDef("count", "integer", "0", "Color (0=white,1=red,2=green,3=yellow,4=blue,5=cyan,6=magenta)"),
    ],
))


# ----------------------------------------------------------------------------
# Item Entities
# ----------------------------------------------------------------------------

_register(EntityDef(
    classname="item_health_small",
    description="Small health kit",
    color=(0.0, 1.0, 0.0),
    size=((-8, -8, 0), (8, 8, 16)),
    spawnflags={
        1: "SUSPENDED",
        2: "SPIN",
        4: "RESPAWN",
    },
))

_register(EntityDef(
    classname="item_health",
    description="Medium health kit",
    color=(0.0, 1.0, 0.0),
    size=((-16, -16, 0), (16, 16, 16)),
    spawnflags={
        1: "SUSPENDED",
        2: "SPIN",
        4: "RESPAWN",
    },
))

_register(EntityDef(
    classname="item_health_large",
    description="Large health kit",
    color=(0.0, 1.0, 0.0),
    size=((-16, -16, 0), (16, 16, 24)),
    spawnflags={
        1: "SUSPENDED",
        2: "SPIN",
        4: "RESPAWN",
    },
))


# ----------------------------------------------------------------------------
# Special Entities
# ----------------------------------------------------------------------------

_register(EntityDef(
    classname="props_skyportal",
    description="Skybox portal for 3D skybox",
    color=(0.5, 0.5, 1.0),
    size=((-8, -8, -8), (8, 8, 8)),
    properties=[
        PropertyDef("fov", "float", "90", "Field of View"),
        PropertyDef("fogcolor", "color", "", "Fog color RGB (0-1)"),
        PropertyDef("fognear", "float", "", "Fog start distance"),
        PropertyDef("fogfar", "float", "", "Fog end distance (opaque)"),
    ],
))


# ============================================================================
# Helper Functions
# ============================================================================

def get_entity_def(classname: str) -> EntityDef | None:
    """Get entity definition by classname."""
    return ENTITY_DEFINITIONS.get(classname)


def get_all_classnames() -> list[str]:
    """Get list of all registered entity classnames."""
    return list(ENTITY_DEFINITIONS.keys())


def get_point_entity_classnames() -> list[str]:
    """Get list of point entity classnames."""
    return [name for name, edef in ENTITY_DEFINITIONS.items() if edef.is_point_entity]


def get_brush_entity_classnames() -> list[str]:
    """Get list of brush entity classnames."""
    return [name for name, edef in ENTITY_DEFINITIONS.items() if not edef.is_point_entity]


def get_entity_color(classname: str) -> tuple[float, float, float]:
    """Get editor color for an entity class."""
    edef = get_entity_def(classname)
    if edef:
        return edef.color
    return (1.0, 1.0, 1.0)  # Default white


def get_entity_size(classname: str) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    """Get bounding box for a point entity class."""
    edef = get_entity_def(classname)
    if edef and edef.size:
        return edef.size
    return None
