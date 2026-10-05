package org.rsmod.content.other.admintool.world

/**
 * Everything built with the Admin Tool's World tab, saved to [AdminWorldStore.FILE] and replayed
 * on startup. Positions are [Spot]s: normal map coords for the world, or coords local to an
 * [Area]'s canvas, because a canvas lands in a different instance slot after every restart.
 */
data class AdminWorld(
    val areas: MutableList<Area> = mutableListOf(),
    val removedLocs: MutableList<RemovedLoc> = mutableListOf(),
    val locs: MutableList<LocSpawn> = mutableListOf(),
    val npcs: MutableList<NpcSpawn> = mutableListOf(),
    val entrances: MutableList<Entrance> = mutableListOf(),
    val teleports: MutableList<Teleport> = mutableListOf(),
    var nextLocId: Int = FIRST_RENAMED_LOC_ID,
) {
    companion object {
        /** First loc id after the cache's own (`max-ids.toml` loc = 62400). */
        const val FIRST_RENAMED_LOC_ID: Int = 62401
    }
}

data class Spot(val scope: String, val x: Int, val z: Int, val level: Int) {
    companion object {
        const val WORLD: String = "world"
    }
}

/**
 * A named 320x320 instance canvas built from copied pieces of the map. [arrival] is where Visit
 * and linked entrances drop players; without it they land in the middle of the first piece.
 */
data class Area(
    val name: String,
    val pieces: MutableList<AreaPiece> = mutableListOf(),
    var arrival: Spot? = null,
)

/**
 * A block of map zones copied onto a canvas, on every level. Zones are 8x8 tiles; [rotation] turns
 * the block clockwise in 90 degree steps.
 */
data class AreaPiece(
    val sourceZoneX: Int,
    val sourceZoneZ: Int,
    val widthZones: Int,
    val lengthZones: Int,
    val rotation: Int,
    val destZoneX: Int,
    val destZoneZ: Int,
)

/** An original map loc the admin deleted, rotated or renamed (its replacement is a [LocSpawn]). */
data class RemovedLoc(val spot: Spot, val type: String, val shape: Int, val angle: Int)

/**
 * A loc placed by the admin. [renamedType] is a new loc type that copies [type], with
 * [renamedName] as its name and [customOption] as its first option when set; it only exists
 * after the next cache build, so until then [type] is spawned.
 */
data class LocSpawn(
    val spot: Spot,
    val type: String,
    val shape: Int,
    val angle: Int,
    val renamedType: String? = null,
    val renamedName: String? = null,
    val customOption: String? = null,
)

data class NpcSpawn(val spot: Spot, val type: String, val respawnTicks: Int)

/** A named admin teleport destination, in the world or inside an area. */
data class Teleport(val name: String, val spot: Spot)

/** A loc that takes whoever clicks its first option into [area], at the area's arrival point. */
data class Entrance(val spot: Spot, val shape: Int, val area: String, val arrival: Spot)
