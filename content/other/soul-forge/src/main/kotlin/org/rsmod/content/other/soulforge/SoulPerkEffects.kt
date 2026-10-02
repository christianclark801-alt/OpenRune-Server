package org.rsmod.content.other.soulforge

import dev.openrune.rscm.RSCM.asRSCM
import dev.openrune.rscm.RSCMType
import jakarta.inject.Singleton
import org.rsmod.api.config.refs.BaseParams
import org.rsmod.api.config.refs.params
import org.rsmod.api.npc.hit.NpcDamageContributor
import org.rsmod.api.npc.hit.modifier.PlayerNpcDamageModifier
import org.rsmod.api.player.stat.statHeal
import org.rsmod.content.other.bossatlas.Boss
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player
import org.rsmod.game.hit.HitBuilder

private val RAIDS = listOf(Boss.ChambersOfXeric, Boss.TheatreOfBlood, Boss.TombsOfAmascut)

@Singleton
class SoulLifestealContributor : NpcDamageContributor {
    override fun onPlayerDamageNpc(npc: Npc, source: Player, damage: Int) {
        if (damage <= 0) {
            return
        }
        val state = source.soulDice
        if (!state.has(SoulPerk.Lifesteal)) {
            return
        }
        val heal = maxOf(1, damage * state.percent(SoulPerk.Lifesteal) / 100)
        source.statHeal("stat.hitpoints", constant = heal, percent = 0)
    }
}

@Singleton
class SoulDamageModifier : PlayerNpcDamageModifier {
    private val raidNpcs: Set<Int> by lazy {
        RAIDS.flatMap { it.npcs }
            .mapNotNull { runCatching { it.asRSCM(RSCMType.NPC) }.getOrNull() }
            .toSet()
    }

    override fun modify(hit: HitBuilder, target: Npc, source: Player) {
        if (hit.damage <= 0) {
            return
        }
        val state = source.soulDice
        var percent = 0
        if (target.isBoss()) {
            percent += state.percent(SoulPerk.BossDamage)
        }
        if (target.type.param(params.demon) != 0) {
            percent += state.percent(SoulPerk.DemonDamage)
        }
        if (target.id in raidNpcs) {
            percent += state.percent(SoulPerk.RaidDamage)
        }
        if (percent > 0) {
            hit.damage = hit.damage * (100 + percent) / 100
        }
    }

    private fun Npc.isBoss(): Boolean = paramOrNull(BaseParams.killcount_varp) != null
}
