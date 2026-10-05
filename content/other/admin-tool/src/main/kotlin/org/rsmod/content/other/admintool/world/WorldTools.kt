package org.rsmod.content.other.admintool.world

import dev.openrune.rscm.RSCM
import dev.openrune.rscm.RSCMType
import jakarta.inject.Inject
import jakarta.inject.Singleton
import java.util.WeakHashMap
import org.rsmod.api.config.HomeCoord
import org.rsmod.api.player.hook.TeleportType
import org.rsmod.api.player.input.TileTargets
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.player.protect.ProtectedAccessLauncher
import org.rsmod.game.entity.Player
import org.rsmod.game.entity.PlayerList
import org.rsmod.game.entity.util.PathingEntityCommon
import org.rsmod.game.loc.LocInfo
import org.rsmod.game.loc.LocShape
import org.rsmod.map.CoordGrid
import org.rsmod.routefinder.collision.CollisionFlagMap

enum class WorldAction {
    CopySection,
    Copy30,
    Copy50,
    CopyAroundMe,
    CreateArea,
    PasteSection,
    VisitArea,
    DeleteArea,
    SelectObject,
    SpawnObject,
    SpawnNpcs,
    RemoveNpcs,
    CancelPick,
    SetTeleport,
    Teleports,
    DeleteTeleport,
    SetArrival,
    SpawnPortal,
}

/** The Admin Tool's World tab: building areas, editing locs and placing npcs by clicking tiles. */
@Singleton
class WorldTools
@Inject
constructor(
    private val editor: AdminWorldEditor,
    private val canvases: AreaCanvases,
    private val tileTargets: TileTargets,
    private val launcher: ProtectedAccessLauncher,
    private val players: PlayerList,
    private val collision: CollisionFlagMap,
) {
    private class Clipboard(val zoneX: Int, val zoneZ: Int, val width: Int, val length: Int, val level: Int)

    private val clipboards = WeakHashMap<Player, Clipboard>()

    suspend fun run(access: ProtectedAccess, action: WorldAction): Unit =
        with(access) {
            when (action) {
                WorldAction.CopySection -> copySection()
                WorldAction.Copy30 -> copyAround(30)
                WorldAction.Copy50 -> copyAround(50)
                WorldAction.CopyAroundMe -> copyAround(countDialog("Size of the square to copy, in tiles:"))
                WorldAction.SetTeleport -> setTeleport()
                WorldAction.Teleports -> chooseTeleport("Teleport where?")?.let { teleport(it) }
                WorldAction.DeleteTeleport -> deleteTeleport()
                WorldAction.SetArrival -> setArrival()
                WorldAction.SpawnPortal -> spawnPortal()
                WorldAction.CreateArea -> createArea()
                WorldAction.PasteSection -> pasteSection()
                WorldAction.VisitArea -> chooseArea("Visit which area?")?.let { visit(it) }
                WorldAction.DeleteArea -> deleteArea()
                WorldAction.SelectObject -> pickTile("Click the tile of the object to select.") { selectObject(it) }
                WorldAction.SpawnObject -> spawnObject()
                WorldAction.SpawnNpcs -> spawnNpcs()
                WorldAction.RemoveNpcs -> pickTile("Click a tile to remove the npcs spawned there.") { removeNpcs(it) }
                WorldAction.CancelPick -> mes(if (tileTargets.cancel(player)) "Tile pick cancelled." else "Nothing to cancel.")
            }
        }

    /**
     * Closes the tool and hands the player's next map click to [then]. The click arrives outside
     * this script, so [then] runs in a fresh protected access.
     */
    private fun ProtectedAccess.pickTile(prompt: String, then: suspend ProtectedAccess.(CoordGrid) -> Unit) {
        ifClose()
        mes("$prompt <col=7f7f7f>(World tab > Cancel pick to stop)</col>")
        val player = player
        tileTargets.request(player) { coords ->
            launcher.launch(player, busyText = "You're busy; finish what you're doing and try again.") {
                then(coords)
            }
        }
    }

    // Areas

    private fun ProtectedAccess.copySection() {
        pickTile("Click the first corner of the section to copy.") { first ->
            if (!inWorld(first)) return@pickTile
            pickTile("Click the opposite corner.") { second ->
                if (!inWorld(second)) return@pickTile
                if (second.level != first.level) {
                    mes("Both corners must be on the same level.")
                    return@pickTile
                }
                copyBetween(first, second)
            }
        }
    }

    /** Copies a [size] x [size] tile square centred on the player, no clicking needed. */
    private fun ProtectedAccess.copyAround(size: Int) {
        val tiles = size.coerceIn(8, AreaCanvases.CANVAS_ZONES * 8)
        val centre = player.coords
        if (!inWorld(centre)) return
        val west = centre.x - tiles / 2
        val south = centre.z - tiles / 2
        copyBetween(
            CoordGrid(west, south, centre.level),
            CoordGrid(west + tiles - 1, south + tiles - 1, centre.level),
        )
    }

    /** Copies every zone touched by the rectangle between two corners, on all levels. */
    private fun ProtectedAccess.copyBetween(first: CoordGrid, second: CoordGrid) {
        val zoneX = minOf(first.x, second.x) shr 3
        val zoneZ = minOf(first.z, second.z) shr 3
        val width = ((maxOf(first.x, second.x) shr 3) - zoneX + 1).coerceAtMost(AreaCanvases.CANVAS_ZONES)
        val length = ((maxOf(first.z, second.z) shr 3) - zoneZ + 1).coerceAtMost(AreaCanvases.CANVAS_ZONES)
        clipboards[player] = Clipboard(zoneX, zoneZ, width, length, first.level)
        mes(
            "Copied ${width * 8}x${length * 8} tiles (all levels) from ${zoneX * 8}, ${zoneZ * 8}. " +
                "Use Create area or Paste section."
        )
    }

    private suspend fun ProtectedAccess.createArea() {
        val clip = clipboard() ?: return
        val name = stringDialog("Name the new area:").trim()
        if (name.isBlank() || name.equals(Spot.WORLD, ignoreCase = true)) {
            mes("That isn't a usable name.")
            return
        }
        if (editor.area(name) != null) {
            mes("There's already an area called $name.")
            return
        }
        val rotation = chooseRotation()
        val (width, length) = turnedSize(clip, rotation)
        val piece =
            AreaPiece(
                clip.zoneX, clip.zoneZ, clip.width, clip.length, rotation,
                destZoneX = (AreaCanvases.CANVAS_ZONES - width) / 2,
                destZoneZ = (AreaCanvases.CANVAS_ZONES - length) / 2,
            )
        val area = editor.createArea(name, piece)
        if (canvases.region(area.name) == null) {
            mes("There's no free instance space to build $name right now.")
            return
        }
        mes("Built area $name. It will be rebuilt every time the server starts.")
        visit(area)
    }

    private suspend fun ProtectedAccess.pasteSection() {
        val clip = clipboard() ?: return
        val area = chooseArea("Paste into which area?") ?: return
        val rotation = chooseRotation()
        pickTile("Click inside ${area.name} where the section's south-west corner goes.") { target ->
            val spot = canvases.toSpot(target)
            if (spot.scope != area.name) {
                mes("Click a tile inside ${area.name}.")
                return@pickTile
            }
            val inside = playersInside(area)
            editor.paste(
                area,
                AreaPiece(clip.zoneX, clip.zoneZ, clip.width, clip.length, rotation, spot.x shr 3, spot.z shr 3),
            )
            for ((other, otherSpot) in inside) {
                canvases.toCoords(otherSpot)?.let { PathingEntityCommon.telejump(other, collision, it) }
            }
            mes("Pasted into ${area.name}.")
        }
    }

    private suspend fun ProtectedAccess.deleteArea() {
        val area = chooseArea("Delete which area?") ?: return
        if (!choice2("Yes", true, "No", false, title = "Delete ${area.name} and everything in it?")) {
            return
        }
        for ((other, _) in playersInside(area)) {
            PathingEntityCommon.telejump(other, collision, HomeCoord)
        }
        editor.deleteArea(area)
        mes("Deleted ${area.name}.")
    }

    fun visitSpot(area: Area): Spot {
        area.arrival?.let { return it }
        val first = area.pieces.first()
        val (width, length) =
            if (first.rotation % 2 == 0) first.widthZones to first.lengthZones
            else first.lengthZones to first.widthZones
        return Spot(area.name, first.destZoneX * 8 + width * 4, first.destZoneZ * 8 + length * 4, 0)
    }

    private fun ProtectedAccess.visit(area: Area) {
        val coords = canvases.toCoords(visitSpot(area))
        if (coords == null) {
            mes("${area.name} isn't built right now.")
            return
        }
        telejump(coords, TeleportType.Exempt)
    }

    private fun playersInside(area: Area): List<Pair<Player, Spot>> =
        players.mapNotNull { other ->
            val spot = canvases.toSpot(other.coords)
            if (spot.scope == area.name) other to spot else null
        }

    // Teleports

    private suspend fun ProtectedAccess.setTeleport() {
        val name = stringDialog("Name this teleport:").trim()
        if (name.isBlank()) return
        val spot = canvases.toSpot(player.coords)
        editor.setTeleport(name, spot)
        val where = if (spot.scope == Spot.WORLD) "here" else "here in ${spot.scope}"
        mes("Saved teleport '$name' $where.")
    }

    private suspend fun ProtectedAccess.deleteTeleport() {
        val teleport = chooseTeleport("Delete which teleport?") ?: return
        editor.deleteTeleport(teleport)
        mes("Deleted teleport '${teleport.name}'.")
    }

    private fun ProtectedAccess.teleport(teleport: Teleport) {
        val coords = canvases.toCoords(teleport.spot)
        if (coords == null) {
            mes("${teleport.spot.scope} isn't built right now.")
            return
        }
        telejump(coords, TeleportType.Exempt)
    }

    private suspend fun ProtectedAccess.chooseTeleport(title: String): Teleport? {
        val teleports = editor.teleports
        if (teleports.isEmpty()) {
            mes("No teleports saved yet. Stand somewhere and use Set teleport here.")
            return null
        }
        val labels =
            teleports.map { if (it.spot.scope == Spot.WORLD) it.name else "${it.name} (${it.spot.scope})" }
        return teleports.getOrNull(menu(title, hotkeys = false, choices = labels))
    }

    private fun ProtectedAccess.setArrival() {
        val spot = canvases.toSpot(player.coords)
        val area = editor.area(spot.scope)
        if (area == null) {
            mes("Stand inside one of your areas to set where players arrive.")
            return
        }
        editor.setArrival(area, spot)
        mes("Players visiting ${area.name} or using its entrances now arrive here.")
    }

    private suspend fun ProtectedAccess.spawnPortal() {
        val area = chooseArea("Where should the portal lead?") ?: return
        pickTile("Click where to place the portal.") { coords ->
            if (canvases.toSpot(coords).scope == area.name) {
                mes("Place the portal outside ${area.name}; use Set area arrival for the way in.")
                return@pickTile
            }
            if (editor.spawnPortal(coords, area, visitSpot(area))) {
                mes("Placed a portal to ${area.name}.")
            } else {
                mes("The portal object isn't in the cache yet: run 'gradlew mergePluginGamevals buildCache' and restart.")
            }
        }
    }

    // Objects

    private suspend fun ProtectedAccess.selectObject(coords: CoordGrid) {
        val locs = editor.locsAt(coords)
        if (locs.isEmpty()) {
            mes("There's no object on that tile.")
            return
        }
        val loc =
            if (locs.size == 1) {
                locs.single()
            } else {
                val labels = locs.map { "${editor.displayName(it)} (${LocShape[it.shapeId]})" }
                locs[menu("Which object?", hotkeys = false, choices = labels)]
            }
        val name = editor.displayName(loc)
        val options =
            listOf("Rotate clockwise", "Rotate anticlockwise", "Delete", "Rename", "Link as area entrance",
                "Unlink entrance")
        when (menu(name, hotkeys = false, choices = options)) {
            0 -> editor.turn(loc, 1).also { mes("Rotated $name.") }
            1 -> editor.turn(loc, 3).also { mes("Rotated $name.") }
            2 -> editor.delete(loc).also { mes("Deleted $name.") }
            3 -> rename(loc, name)
            4 -> {
                val area = chooseArea("Which area does it lead to?") ?: return
                if (editor.linkEntrance(loc, area, visitSpot(area))) {
                    mes(
                        "$name now leads into ${area.name}, but it has no option to click yet: it gets " +
                            "an 'Enter' option after 'gradlew mergePluginGamevals buildCache' and a restart."
                    )
                } else {
                    mes("$name now takes players into ${area.name}.")
                }
            }
            5 -> mes(if (editor.unlinkEntrance(loc)) "$name is no longer an entrance." else "$name wasn't an entrance.")
        }
    }

    private suspend fun ProtectedAccess.rename(loc: LocInfo, old: String) {
        val name = stringDialog("New name for $old:").trim()
        if (name.isBlank()) return
        editor.rename(loc, name)
        mes(
            "Renamed to '$name'. Run 'gradlew mergePluginGamevals buildCache' and restart the server " +
                "and client to see the new name."
        )
    }

    private suspend fun ProtectedAccess.spawnObject() {
        val input = stringDialog("Object name or id [angle 0-3] [shape]:").trim().split(Regex(" +"))
        val type = resolve(input.getOrNull(0) ?: "", "loc", RSCMType.LOC)
        if (type == null) {
            mes("No object called '${input.getOrNull(0)}'.")
            return
        }
        val angle = input.getOrNull(1)?.toIntOrNull()?.coerceIn(0, 3) ?: 0
        val shape = input.getOrNull(2)?.toIntOrNull() ?: LocShape.CentrepieceStraight.id
        pickTile("Click where to place it.") { coords ->
            editor.spawnLocAt(coords, type, shape, angle)
            mes("Placed ${type.removePrefix("loc.")}.")
        }
    }

    // Npcs

    private suspend fun ProtectedAccess.spawnNpcs() {
        val type = resolve(stringDialog("Npc name or id:").trim(), "npc", RSCMType.NPC)
        if (type == null) {
            mes("No npc by that name.")
            return
        }
        val count = countDialog("How many?").coerceIn(1, MAX_NPCS)
        val spacing = countDialog("Spacing in tiles (0 = same tile):").coerceIn(0, MAX_SPACING)
        pickTile("Click the centre tile for the npcs.") { center ->
            val spawned =
                editor.spawnNpcs(center, type, count, spacing, AdminWorldEditor.DEFAULT_RESPAWN_TICKS)
            mes("Spawned $spawned ${type.removePrefix("npc.")}. They respawn 30 seconds after dying.")
        }
    }

    private fun ProtectedAccess.removeNpcs(coords: CoordGrid) {
        val removed = editor.removeNpcsAt(coords)
        mes(if (removed == 0) "No spawned npcs there." else "Removed $removed npc spawn(s).")
    }

    // Helpers

    private fun ProtectedAccess.inWorld(coords: CoordGrid): Boolean {
        if (canvases.toSpot(coords).scope == Spot.WORLD) return true
        mes("Copy from the normal map, not from inside an area.")
        return false
    }

    private fun ProtectedAccess.clipboard(): Clipboard? {
        val clip = clipboards[player]
        if (clip == null) mes("Copy a section first.")
        return clip
    }

    private suspend fun ProtectedAccess.chooseArea(title: String): Area? {
        val areas = editor.areas
        if (areas.isEmpty()) {
            mes("There are no areas yet. Copy a section, then Create area.")
            return null
        }
        return areas.getOrNull(menu(title, hotkeys = false, choices = areas.map { it.name }))
    }

    private suspend fun ProtectedAccess.chooseRotation(): Int =
        menu("Rotation", hotkeys = false, choices = listOf("None", "90 clockwise", "180", "90 anticlockwise"))
            .coerceIn(0, 3)

    private fun turnedSize(clip: Clipboard, rotation: Int): Pair<Int, Int> =
        if (rotation % 2 == 0) clip.width to clip.length else clip.length to clip.width

    private fun resolve(text: String, table: String, type: RSCMType): String? {
        if (text.isBlank()) return null
        text.toIntOrNull()?.let { id ->
            return runCatching { RSCM.getReverseMapping(type, id) }.getOrNull()
        }
        val key = text.lowercase().replace(' ', '_').removePrefix("$table.")
        val name = "$table.$key"
        return name.takeIf { RSCM.getRSCMOrNull(it, type) != null }
    }

    private companion object {
        const val MAX_NPCS = 50
        const val MAX_SPACING = 10
    }
}
