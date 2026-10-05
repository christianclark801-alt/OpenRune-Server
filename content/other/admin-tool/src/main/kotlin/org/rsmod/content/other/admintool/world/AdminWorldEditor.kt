package org.rsmod.content.other.admintool.world

import dev.openrune.ServerCacheManager
import dev.openrune.rscm.RSCM
import dev.openrune.rscm.RSCMType
import jakarta.inject.Inject
import jakarta.inject.Singleton
import java.util.IdentityHashMap
import kotlin.math.ceil
import kotlin.math.sqrt
import org.rsmod.api.repo.loc.LocRepository
import org.rsmod.api.repo.npc.NpcRepository
import org.rsmod.game.entity.Npc
import org.rsmod.game.interact.InteractionOp
import org.rsmod.game.type.hasOp
import org.rsmod.game.loc.LocAngle
import org.rsmod.game.loc.LocEntity
import org.rsmod.game.loc.LocInfo
import org.rsmod.map.CoordGrid
import org.rsmod.routefinder.loc.LocLayerConstants

/**
 * Applies the saved [AdminWorld] to the live game and records every change the admin makes, so
 * the same world is rebuilt after a restart.
 */
@Singleton
class AdminWorldEditor
@Inject
constructor(
    private val store: AdminWorldStore,
    private val canvases: AreaCanvases,
    private val locRepo: LocRepository,
    private val npcRepo: NpcRepository,
    private val renames: LocRenameFiles,
) {
    private val world: AdminWorld
        get() = store.world

    private val liveNpcs = IdentityHashMap<NpcSpawn, Npc>()

    val areas: List<Area>
        get() = world.areas

    fun area(name: String): Area? = world.areas.firstOrNull { it.name.equals(name, ignoreCase = true) }

    fun startup() {
        for (area in world.areas) {
            canvases.build(area)
        }
        applyScope(Spot.WORLD)
        for (area in world.areas) {
            applyScope(area.name)
        }
    }

    /**
     * Replays one scope: original locs are removed before the admin's locs are added, so a
     * rotated or renamed map loc never sits on top of its own replacement.
     */
    fun applyScope(scope: String) {
        for (removed in world.removedLocs.filter { it.spot.scope == scope }) {
            val coords = canvases.toCoords(removed.spot) ?: continue
            val typeId = RSCM.getRSCMOrNull(removed.type, RSCMType.LOC) ?: continue
            val loc = locRepo.findAll(coords).firstOrNull { it.id == typeId && it.shapeId == removed.shape }
            if (loc != null) {
                locRepo.del(loc, Int.MAX_VALUE)
            }
        }
        for (spawn in world.locs.filter { it.spot.scope == scope }) {
            spawnLoc(spawn)
        }
        for (spawn in world.npcs.filter { it.spot.scope == scope }) {
            spawnNpc(spawn)
        }
    }

    // Areas

    fun createArea(name: String, piece: AreaPiece): Area {
        val area = Area(name, mutableListOf(piece))
        world.areas += area
        store.save()
        rebuild(area)
        return area
    }

    fun paste(area: Area, piece: AreaPiece) {
        area.pieces += piece
        store.save()
        rebuild(area)
    }

    fun deleteArea(area: Area) {
        dropNpcs { it.spot.scope == area.name }
        canvases.destroy(area.name)
        world.areas.remove(area)
        world.removedLocs.removeAll { it.spot.scope == area.name }
        world.locs.removeAll { it.spot.scope == area.name }
        world.npcs.removeAll { it.spot.scope == area.name }
        world.entrances.removeAll { it.spot.scope == area.name || it.area == area.name }
        world.teleports.removeAll { it.spot.scope == area.name }
        store.save()
        renames.write(world)
    }

    private fun rebuild(area: Area) {
        dropNpcs { it.spot.scope == area.name }
        canvases.build(area)
        applyScope(area.name)
    }

    fun setArrival(area: Area, spot: Spot) {
        area.arrival = spot
        store.save()
    }

    // Teleports

    val teleports: List<Teleport>
        get() = world.teleports

    fun setTeleport(name: String, spot: Spot) {
        world.teleports.removeAll { it.name.equals(name, ignoreCase = true) }
        world.teleports += Teleport(name, spot)
        store.save()
    }

    fun deleteTeleport(teleport: Teleport) {
        world.teleports.remove(teleport)
        store.save()
    }

    // Locs

    fun locsAt(coords: CoordGrid): List<LocInfo> = locRepo.findAll(coords).toList()

    fun turn(loc: LocInfo, turns: Int) {
        val spawn = takeOver(loc)
        val turned = spawn.copy(angle = LocAngle[spawn.angle].turn(turns).id)
        replaceSpawn(spawn, turned)
    }

    fun delete(loc: LocInfo) {
        val spawn = takeOver(loc)
        despawnLoc(spawn)
        world.locs.remove(spawn)
        world.entrances.removeAll { it.spot == spawn.spot && it.shape == spawn.shape }
        store.save()
        renames.write(world)
    }

    /**
     * Gives this one loc its own type named [name]. The type is written into the admin tool's
     * gamevals and pack config and only exists once the cache is rebuilt, so the loc keeps its
     * old name until then.
     */
    fun rename(loc: LocInfo, name: String) {
        val spawn = takeOver(loc)
        replaceSpawn(spawn, spawn.copy(renamedType = ownType(spawn), renamedName = name))
        renames.write(world)
    }

    /** The loc's own generated type, allocating one the first time it's customised. */
    private fun ownType(spawn: LocSpawn): String = spawn.renamedType ?: "loc.admin_loc_${world.nextLocId++}"

    fun spawnLocAt(coords: CoordGrid, type: String, shape: Int, angle: Int) {
        val spawn = LocSpawn(canvases.toSpot(coords), type, shape, angle)
        world.locs += spawn
        store.save()
        spawnLoc(spawn)
    }

    /**
     * Makes [loc] an entrance to [area]. Players can only click a loc that has a first option, so
     * a loc without one (a table, a statue) gets its own type with an "Enter" option; that needs
     * a cache rebuild, which the return value reports.
     */
    fun linkEntrance(loc: LocInfo, area: Area, arrival: Spot): Boolean {
        val spot = canvases.toSpot(loc.coords)
        world.entrances.removeAll { it.spot == spot && it.shape == loc.shapeId }
        world.entrances += Entrance(spot, loc.shapeId, area.name, arrival)
        store.save()
        if (ServerCacheManager.getObject(loc.id)?.hasOp(InteractionOp.Op1) == true) {
            return false
        }
        val spawn = takeOver(loc)
        replaceSpawn(spawn, spawn.copy(renamedType = ownType(spawn), customOption = ENTER_OPTION))
        renames.write(world)
        return true
    }

    /** Places an admin portal at [coords] that leads into [area]; false until the cache has it. */
    fun spawnPortal(coords: CoordGrid, area: Area, arrival: Spot): Boolean {
        val portal = RSCM.getRSCMOrNull(PORTAL, RSCMType.LOC) ?: return false
        if (ServerCacheManager.getObject(portal) == null) return false
        val spawn = LocSpawn(canvases.toSpot(coords), PORTAL, PORTAL_SHAPE, 0)
        world.locs.removeAll { it.spot == spawn.spot && it.shape == spawn.shape }
        world.locs += spawn
        world.entrances.removeAll { it.spot == spawn.spot && it.shape == spawn.shape }
        world.entrances += Entrance(spawn.spot, spawn.shape, area.name, arrival)
        store.save()
        spawnLoc(spawn)
        return true
    }

    fun unlinkEntrance(loc: LocInfo): Boolean {
        val spot = canvases.toSpot(loc.coords)
        val removed = world.entrances.removeAll { it.spot == spot && it.shape == loc.shapeId }
        if (removed) store.save()
        return removed
    }

    fun entranceAt(coords: CoordGrid, shape: Int): Entrance? {
        val spot = canvases.toSpot(coords)
        return world.entrances.firstOrNull { it.spot == spot && it.shape == shape }
    }

    fun displayName(loc: LocInfo): String {
        val spawn = spawnAt(loc)
        val name = spawn?.renamedName ?: ServerCacheManager.getObject(loc.id)?.name
        return name?.takeIf { it.isNotBlank() && it != "null" } ?: typeName(loc.id)
    }

    /**
     * The admin's own record of [loc], creating one when it's an original map loc: the original
     * is remembered as removed and replaced by an identical spawned copy that edits can change.
     */
    private fun takeOver(loc: LocInfo): LocSpawn {
        spawnAt(loc)?.let { return it }
        val spot = canvases.toSpot(loc.coords)
        val type = typeName(loc.id)
        world.removedLocs += RemovedLoc(spot, type, loc.shapeId, loc.angleId)
        locRepo.del(loc, Int.MAX_VALUE)
        val spawn = LocSpawn(spot, type, loc.shapeId, loc.angleId)
        world.locs += spawn
        spawnLoc(spawn)
        return spawn
    }

    private fun spawnAt(loc: LocInfo): LocSpawn? {
        val spot = canvases.toSpot(loc.coords)
        return world.locs.firstOrNull { it.spot == spot && it.shape == loc.shapeId }
    }

    private fun replaceSpawn(old: LocSpawn, new: LocSpawn) {
        despawnLoc(old)
        world.locs[world.locs.indexOf(old)] = new
        store.save()
        spawnLoc(new)
    }

    private fun spawnLoc(spawn: LocSpawn) {
        val coords = canvases.toCoords(spawn.spot) ?: return
        val typeId = liveTypeId(spawn) ?: return
        val loc = LocInfo(LocLayerConstants.of(spawn.shape), coords, LocEntity(typeId, spawn.shape, spawn.angle))
        locRepo.add(loc, Int.MAX_VALUE)
    }

    private fun despawnLoc(spawn: LocSpawn) {
        val coords = canvases.toCoords(spawn.spot) ?: return
        val loc = locRepo.findAll(coords).firstOrNull { it.shapeId == spawn.shape } ?: return
        locRepo.del(loc, Int.MAX_VALUE)
    }

    /** The renamed type once the cache has been rebuilt with it, otherwise the original. */
    private fun liveTypeId(spawn: LocSpawn): Int? {
        val renamed = spawn.renamedType?.let { RSCM.getRSCMOrNull(it, RSCMType.LOC) }
        if (renamed != null && ServerCacheManager.getObject(renamed) != null) {
            return renamed
        }
        return RSCM.getRSCMOrNull(spawn.type, RSCMType.LOC)
    }

    // Npcs

    fun spawnNpcs(center: CoordGrid, type: String, count: Int, spacing: Int, respawnTicks: Int): Int {
        val spawns = npcGrid(center, count, spacing).map { NpcSpawn(canvases.toSpot(it), type, respawnTicks) }
        world.npcs += spawns
        store.save()
        spawns.forEach(::spawnNpc)
        return spawns.size
    }

    /** Removes every saved npc spawned on [coords] or currently standing there. */
    fun removeNpcsAt(coords: CoordGrid): Int {
        val spot = canvases.toSpot(coords)
        val doomed =
            world.npcs.filter { spawn -> spawn.spot == spot || liveNpcs[spawn]?.coords == coords }
        doomed.forEach { spawn -> liveNpcs.remove(spawn)?.let { npcRepo.del(it, Int.MAX_VALUE) } }
        world.npcs.removeAll { spawn -> doomed.any { it === spawn } }
        if (doomed.isNotEmpty()) store.save()
        return doomed.size
    }

    private fun spawnNpc(spawn: NpcSpawn) {
        val coords = canvases.toCoords(spawn.spot) ?: return
        if (RSCM.getRSCMOrNull(spawn.type, RSCMType.NPC) == null) return
        val npc = Npc(spawn.type, coords)
        npc.respawnTicks = spawn.respawnTicks
        npcRepo.add(npc, Int.MAX_VALUE)
        liveNpcs[spawn] = npc
    }

    private fun dropNpcs(predicate: (NpcSpawn) -> Boolean) {
        val iterator = liveNpcs.entries.iterator()
        while (iterator.hasNext()) {
            val (spawn, npc) = iterator.next()
            if (predicate(spawn)) {
                npcRepo.del(npc, Int.MAX_VALUE)
                iterator.remove()
            }
        }
    }

    companion object {
        /** 30 seconds. */
        const val DEFAULT_RESPAWN_TICKS: Int = 50

        const val PORTAL: String = "loc.admin_portal"
        private const val PORTAL_SHAPE = 10
        private const val ENTER_OPTION = "Enter"

        fun typeName(locId: Int): String = RSCM.getReverseMapping(RSCMType.LOC, locId)

        /**
         * [count] tiles in a near-square grid centred on [center], [spacing] tiles apart (0 stacks
         * them on one tile), filled row by row from the south-west.
         */
        fun npcGrid(center: CoordGrid, count: Int, spacing: Int): List<CoordGrid> {
            if (count <= 0) return emptyList()
            val columns = ceil(sqrt(count.toDouble())).toInt()
            val rows = (count + columns - 1) / columns
            val west = center.x - (columns - 1) * spacing / 2
            val south = center.z - (rows - 1) * spacing / 2
            return List(count) { index ->
                CoordGrid(west + (index % columns) * spacing, south + (index / columns) * spacing, center.level)
            }
        }
    }
}
