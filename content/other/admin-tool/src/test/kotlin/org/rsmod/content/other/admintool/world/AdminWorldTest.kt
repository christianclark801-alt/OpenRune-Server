package org.rsmod.content.other.admintool.world

import java.nio.file.Files
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test
import org.rsmod.map.CoordGrid
import org.rsmod.map.zone.ZoneKey

class AdminWorldTest {
    @Test
    fun `a piece is copied onto every level at its destination`() {
        val zones = AreaCanvases.composeZones(listOf(AreaPiece(100, 200, 2, 1, 0, 5, 6)))
        assertEquals(2 * 1 * CoordGrid.LEVEL_COUNT, zones.size)
        assertEquals(ZoneKey(100, 200, 0), zones.getValue(ZoneKey(5, 6, 0)).normalZone())
        assertEquals(ZoneKey(101, 200, 3), zones.getValue(ZoneKey(6, 6, 3)).normalZone())
    }

    @Test
    fun `a rotated piece swaps its footprint and keeps the rotation`() {
        val zones = AreaCanvases.composeZones(listOf(AreaPiece(100, 200, 3, 1, 1, 0, 0)))
        val footprint = zones.keys.filter { it.level == 0 }
        assertEquals(setOf(0), footprint.map { it.x }.toSet())
        assertEquals(setOf(0, 1, 2), footprint.map { it.z }.toSet())
        assertEquals(setOf(1), zones.values.map { it.rotation }.toSet())
    }

    @Test
    fun `a later paste covers an earlier one and pieces are clipped to the canvas`() {
        val zones =
            AreaCanvases.composeZones(
                listOf(AreaPiece(100, 200, 1, 1, 0, 0, 0), AreaPiece(300, 400, 2, 1, 0, 39, 0)) +
                    AreaPiece(500, 600, 1, 1, 0, 0, 0)
            )
        assertEquals(ZoneKey(500, 600, 0), zones.getValue(ZoneKey(0, 0, 0)).normalZone())
        assertEquals(null, zones[ZoneKey(40, 0, 0)])
    }

    @Test
    fun `npcs are laid out in a near square grid around the centre`() {
        val centre = CoordGrid(3200, 3200, 0)
        val five = AdminWorldEditor.npcGrid(centre, 5, 2)
        assertEquals(5, five.size)
        assertEquals(5, five.toSet().size)
        assertEquals(setOf(3198, 3200, 3202), five.map { it.x }.toSet())
        assertEquals(setOf(3199, 3201), five.map { it.z }.toSet())
        assertEquals(List(3) { centre }, AdminWorldEditor.npcGrid(centre, 3, 0))
    }

    @Test
    fun `the world survives a save and reload`() {
        val file = Files.createTempDirectory("admin-world").resolve("admin_world.json")
        val store = AdminWorldStore(file)
        store.world.areas += Area("Arena", mutableListOf(AreaPiece(1, 2, 3, 4, 1, 5, 6)))
        store.world.npcs += NpcSpawn(Spot("Arena", 10, 11, 0), "npc.goblin", 50)
        store.world.locs += LocSpawn(Spot(Spot.WORLD, 3200, 3201, 1), "loc.door", 0, 2, "loc.admin_loc_62401", "Gate")
        store.world.nextLocId = 62402
        store.world.areas.single().arrival = Spot("Arena", 30, 40, 1)
        store.world.teleports += Teleport("Boss room", Spot("Arena", 50, 60, 0))
        store.save()

        val reloaded = AdminWorldStore(file).world
        assertEquals(store.world, reloaded)
    }

    @Test
    fun `saves from before teleports existed still load`() {
        val file = Files.createTempDirectory("admin-world").resolve("admin_world.json")
        Files.writeString(file, """{"areas":[{"name":"Old","pieces":[]}],"nextLocId":62401}""")
        val world = AdminWorldStore(file).world
        assertEquals(null, world.areas.single().arrival)
        assertEquals(emptyList<Teleport>(), world.teleports)
    }
}
