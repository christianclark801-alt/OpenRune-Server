package org.rsmod.content.skills.poisonmastery

import dev.openrune.rscm.RSCM.asRSCM
import dev.openrune.rscm.RSCMType
import dev.openrune.types.HitmarkTypeGroup
import jakarta.inject.Singleton
import org.rsmod.api.combat.commons.npc.resolveCombatXpMultiplier
import org.rsmod.api.config.refs.done.hitmark_groups
import org.rsmod.api.npc.hit.NpcDamageContributor
import org.rsmod.api.player.stat.statAdvance
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player
import org.rsmod.game.hit.Hit

@Singleton
class PoisonMasteryXp : NpcDamageContributor {
    override fun onPlayerDamageNpc(npc: Npc, source: Player, damage: Int) {}

    override fun onPlayerHitNpc(npc: Npc, source: Player, hit: Hit) {
        if (hit.damage <= 0 || !hit.isToxic()) {
            return
        }
        source.statAdvance(POISON_MASTERY, hit.damage * XP_PER_DAMAGE * npc.resolveCombatXpMultiplier())
    }

    private fun Hit.isToxic(): Boolean =
        matches(hitmark_groups.poison_damage) || matches(hitmark_groups.venom)

    private fun Hit.matches(group: HitmarkTypeGroup): Boolean {
        val lit = group.lit.asRSCM(RSCMType.HITMARK)
        val tint = group.tint?.asRSCM(RSCMType.HITMARK)
        return hitmark.self == lit || (tint != null && hitmark.self == tint)
    }

    private companion object {
        const val POISON_MASTERY = "stat.sailing"
        const val XP_PER_DAMAGE = 4.0
    }
}
