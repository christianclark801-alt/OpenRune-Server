package org.rsmod.content.generic.npcs.banker

import com.github.michaelbull.logging.InlineLogger
import jakarta.inject.Inject
import org.rsmod.api.repo.loc.LocRepository
import org.rsmod.api.repo.npc.NpcRepository
import org.rsmod.api.script.onGameStartup
import org.rsmod.game.entity.Npc
import org.rsmod.game.loc.LocAngle
import org.rsmod.game.loc.LocShape
import org.rsmod.game.map.Direction
import org.rsmod.map.CoordGrid
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

private val BOOTH_COORDS = CoordGrid(3797, 2572, 0)
private val BANKER_COORDS = CoordGrid(3798, 2572, 0)

class HomeBank
@Inject
constructor(private val locRepo: LocRepository, private val npcRepo: NpcRepository) :
    PluginScript() {
    private val logger = InlineLogger()

    override fun ScriptContext.startup() {
        onGameStartup { spawn() }
    }

    private fun spawn() {
        runCatching {
            locRepo.add(
                BOOTH_COORDS,
                "loc.bankbooth",
                Int.MAX_VALUE,
                LocAngle.North,
                LocShape.CentrepieceStraight,
            )
            val banker = Npc("npc.banker1", BANKER_COORDS).apply { respawnDir = Direction.West }
            npcRepo.add(banker, Int.MAX_VALUE)
        }.onFailure { logger.warn(it) { "Unable to spawn the home bank." } }
    }
}
