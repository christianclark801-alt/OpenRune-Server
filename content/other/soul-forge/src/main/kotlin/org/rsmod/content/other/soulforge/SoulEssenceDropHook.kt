package org.rsmod.content.other.soulforge

import jakarta.inject.Inject
import jakarta.inject.Singleton
import org.rsmod.api.config.constants
import org.rsmod.api.config.refs.BaseParams
import org.rsmod.api.death.NpcDeathKillContext
import org.rsmod.api.death.NpcDeathKillHook
import org.rsmod.api.player.output.ClientScripts
import org.rsmod.api.random.GameRandom
import org.rsmod.api.repo.obj.ObjRepository
import org.rsmod.content.interfaces.collectionlog.CollectionLog
import org.rsmod.game.entity.Npc

internal const val SOUL_ESSENCE = "obj.soul_essence"

private const val DROP_RATE = 50

@Singleton
class SoulEssenceDropHook
@Inject
constructor(private val objRepo: ObjRepository, private val random: GameRandom) : NpcDeathKillHook {
    override fun onKill(context: NpcDeathKillContext) {
        val npc = context.npc
        if (!npc.isBoss() || random.of(DROP_RATE) != 0) {
            return
        }
        val player = context.hero
        val duration = player.lootDropDuration ?: constants.lootdrop_duration
        CollectionLog.grant(player, SOUL_ESSENCE)
        val spawned = objRepo.add(SOUL_ESSENCE, context.dropCoords, duration, player, 1)
        ClientScripts.lootTrackerAddLoot(
            player,
            npc.id,
            context.lootTrackerEventId,
            spawned.type,
            spawned.count,
        )
    }

    private fun Npc.isBoss(): Boolean = paramOrNull(BaseParams.killcount_varp) != null
}
