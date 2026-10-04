package org.rsmod.content.skills.poisonmastery

import dev.openrune.types.HitmarkTypeGroup
import org.rsmod.api.config.refs.done.hitmark_groups
import org.rsmod.api.config.refs.params
import org.rsmod.api.mechanics.status.NpcStatusEffects
import org.rsmod.api.mechanics.toxins.impl.NpcPoison
import org.rsmod.api.npc.hit.modifier.NpcHitModifier
import org.rsmod.api.npc.hit.queueHit
import org.rsmod.api.player.output.ChatType
import org.rsmod.api.player.output.mes
import org.rsmod.api.random.GameRandom
import org.rsmod.content.other.soulforge.PoisonBladesForge
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player
import org.rsmod.game.hit.HitType

/**
 * Forged Poison Blades procs. Every proc queues its own hits, so procs never merge or refresh:
 * several can be pending on one npc at once, each landing on its own timer.
 */
internal object PoisonBladesVenom {
    private const val POISON_CHANCE = 30
    private const val POISON_DAMAGE = 40
    private const val VENOM_CHANCE = 10
    private val VENOM_DAMAGE = 50..300
    private const val FIRST_HIT_DELAY = 1
    private const val FADE_DELAY = 10

    private val NoopModifier = NpcHitModifier {}

    fun roll(tier: Int, source: Player, npc: Npc, random: GameRandom) {
        when (tier) {
            PoisonBladesForge.POISON_TIER -> poison(source, npc, random)
            PoisonBladesForge.VENOM_TIER -> venom(source, npc, random)
        }
    }

    private fun poison(source: Player, npc: Npc, random: GameRandom) {
        if (random.of(100) >= POISON_CHANCE || NpcPoison.isImmune(npc)) {
            return
        }
        val damage = NpcStatusEffects.poisonDamage(npc, POISON_DAMAGE, source)
        hit(source, npc, FIRST_HIT_DELAY, damage, hitmark_groups.poison_damage)
        hit(source, npc, FIRST_HIT_DELAY + FADE_DELAY, damage, hitmark_groups.poison_damage)
        source.mes("Your blades poison the target!", ChatType.Spam)
    }

    private fun venom(source: Player, npc: Npc, random: GameRandom) {
        if (random.of(100) >= VENOM_CHANCE || isVenomImmune(npc)) {
            return
        }
        val damage = NpcStatusEffects.venomDamage(npc, random.of(VENOM_DAMAGE), source)
        hit(source, npc, FIRST_HIT_DELAY + FADE_DELAY, damage, hitmark_groups.venom)
        source.mes("Venom seeps into the wound...", ChatType.Spam)
    }

    private fun isVenomImmune(npc: Npc): Boolean =
        NpcPoison.isImmune(npc) || (npc.visType.paramOrNull(params.venom_immunity) ?: 0) > 0

    private fun hit(source: Player, npc: Npc, delay: Int, damage: Int, hitmark: HitmarkTypeGroup) {
        npc.queueHit(
            source = source,
            delay = delay,
            type = HitType.Typeless,
            damage = damage,
            modifier = NoopModifier,
            hitmark = hitmark,
        )
    }
}
