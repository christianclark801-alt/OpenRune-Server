package org.rsmod.content.skills.poisonmastery

import jakarta.inject.Singleton
import org.rsmod.api.mechanics.status.NpcStatusEffects
import org.rsmod.api.mechanics.status.StatusEffectTypes
import org.rsmod.api.npc.hit.NpcDamageContributor
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player
import org.rsmod.game.hit.Hit

/** Poison gear marks every npc its wearer hits, refreshing the mark on each hit. */
@Singleton
class PoisonGearEffects : NpcDamageContributor {
    override fun onPlayerDamageNpc(npc: Npc, source: Player, damage: Int) {}

    override fun onPlayerHitNpc(npc: Npc, source: Player, hit: Hit) {
        if (hit.damage <= 0) {
            return
        }
        if (RING_OBJS.any { it in source.worn }) {
            NpcStatusEffects.apply(npc, StatusEffectTypes.toxic_mark, MARK_TICKS)
        }
        if (ROBE_SETS.any { set -> set.all { it in source.worn } }) {
            NpcStatusEffects.apply(npc, StatusEffectTypes.toxic_shroud, MARK_TICKS)
        }
    }

    private companion object {
        const val MARK_TICKS = 30

        val RING_OBJS: List<String> = emptyList()
        val ROBE_SETS: List<List<String>> = emptyList()
    }
}
