package org.rsmod.content.slayer

import dev.openrune.types.MoveRestrict
import jakarta.inject.Inject
import org.rsmod.api.repo.npc.NpcRepository
import org.rsmod.api.script.onGameStartup
import org.rsmod.game.entity.Npc
import org.rsmod.game.map.Direction
import org.rsmod.map.CoordGrid
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

private val START = CoordGrid(3787, 2563, 0)

private val MASTERS =
    listOf(
        "npc.slayer_master_1_tureal",
        "npc.slayer_master_9_active",
        "npc.slayer_master_2_mazchna",
        "npc.slayer_master_3",
        "npc.slayer_master_4",
        "npc.slayer_master_8",
        "npc.slayer_master_nieve",
        "npc.slayer_master_5_duradel",
        "npc.slayer_master_7",
    )

private val MORTIMER_COORDS = START.translate(-(MASTERS.size - 1), 1)

class SlayerMasterSpawns @Inject constructor(private val npcRepo: NpcRepository) : PluginScript() {
    override fun ScriptContext.startup() {
        onGameStartup { spawnMasters() }
    }

    private fun spawnMasters() {
        MASTERS.forEachIndexed { index, master -> spawn(master, START.translateX(-index)) }
        spawn("npc.slayer_master_mortimer_vis", MORTIMER_COORDS)
    }

    private fun spawn(master: String, coords: CoordGrid) {
        val npc =
            Npc(master, coords).apply {
                respawnDir = Direction.North
                moveRestrict = MoveRestrict.NoMove
            }
        npcRepo.add(npc, Int.MAX_VALUE)
    }
}
