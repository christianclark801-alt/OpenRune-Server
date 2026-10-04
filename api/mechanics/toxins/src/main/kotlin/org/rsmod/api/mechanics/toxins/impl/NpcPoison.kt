package org.rsmod.api.mechanics.toxins.impl

import org.rsmod.api.config.refs.done.hitmark_groups
import org.rsmod.api.config.refs.params
import org.rsmod.api.mechanics.status.NpcStatusEffects
import org.rsmod.api.npc.hit.modifier.NpcHitModifier
import org.rsmod.api.npc.hit.queueHit
import org.rsmod.api.npc.vars.typePlayerUidVarn
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player
import org.rsmod.game.entity.PlayerList
import org.rsmod.game.hit.HitType

public object NpcPoison {
    private val NoopModifier = NpcHitModifier {}

    private var Npc.poisonSource by typePlayerUidVarn("varn.poison_source")

    public fun isPoisoned(npc: Npc): Boolean = npc.vars["varn.poison_severity"] > 0

    public fun isImmune(npc: Npc): Boolean =
        (npc.visType.paramOrNull(params.poison_immunity) ?: 0) > 0

    public fun tryPoison(npc: Npc, severity: Int, source: Player? = null): Boolean {
        if (severity <= 0 || isImmune(npc)) {
            return false
        }
        val current = npc.vars["varn.poison_severity"]
        if (current > 0) {
            val currentDamage = PlayerPoison.damageForSeverity(current)
            val incomingDamage = PlayerPoison.damageForSeverity(severity)
            if (incomingDamage < currentDamage) return false
            if (incomingDamage == currentDamage && severity <= current) return false
        }
        npc.poisonSource = source?.uid
        queuePoisonHit(npc, PlayerPoison.damageForSeverity(severity), source)
        setSeverity(npc, severity - 1)
        return true
    }

    public fun clear(npc: Npc) {
        npc.vars["varn.poison_severity"] = 0
        npc.poisonSource = null
        npc.clearTimer("timer.npc_poison")
    }

    public fun onPoisonTimerTick(npc: Npc, players: PlayerList) {
        val severity = npc.vars["varn.poison_severity"]
        if (severity <= 0 || npc.hitpoints <= 0) {
            clear(npc)
            return
        }
        val source = npc.poisonSource?.resolve(players)
        queuePoisonHit(npc, PlayerPoison.damageForSeverity(severity), source)
        setSeverity(npc, severity - 1)
    }

    private fun setSeverity(npc: Npc, severity: Int) {
        if (severity <= 0) {
            clear(npc)
            return
        }
        npc.vars["varn.poison_severity"] = severity
        npc.timer("timer.npc_poison", PlayerPoison.TICK_INTERVAL)
    }

    private fun queuePoisonHit(npc: Npc, damage: Int, source: Player?) {
        val scaled = NpcStatusEffects.poisonDamage(npc, damage)
        repeat(NpcStatusEffects.poisonHits(npc)) { queueScaledPoisonHit(npc, scaled, source) }
    }

    private fun queueScaledPoisonHit(npc: Npc, damage: Int, source: Player?) {
        if (source != null) {
            npc.queueHit(
                source = source,
                delay = 1,
                type = HitType.Typeless,
                damage = damage,
                modifier = NoopModifier,
                hitmark = hitmark_groups.poison_damage,
            )
            return
        }
        npc.queueHit(
            delay = 1,
            type = HitType.Typeless,
            damage = damage,
            modifier = NoopModifier,
            hitmark = hitmark_groups.poison_damage,
        )
    }
}
