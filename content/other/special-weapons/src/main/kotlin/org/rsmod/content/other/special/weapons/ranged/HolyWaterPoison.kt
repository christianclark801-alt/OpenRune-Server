package org.rsmod.content.other.special.weapons.ranged

import org.rsmod.api.config.refs.done.hitmark_groups
import org.rsmod.api.mechanics.status.NpcStatusEffects
import org.rsmod.api.mechanics.toxins.impl.NpcPoison
import org.rsmod.api.npc.hit.modifier.NpcHitModifier
import jakarta.inject.Inject
import org.rsmod.api.npc.hit.queueHit
import org.rsmod.api.npc.vars.typePlayerUidVarn
import org.rsmod.api.script.onNpcTimer
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player
import org.rsmod.game.entity.PlayerList
import org.rsmod.game.hit.HitType
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

object HolyWaterPoison {
    private const val HITS_VARN = "varn.holy_water_poison_hits"
    private const val DAMAGE_VARN = "varn.holy_water_poison_damage"
    private const val VENOM_VARN = "varn.holy_water_poison_venom"
    private const val TIMER = "timer.npc_holy_water_poison"
    private const val BASE_DAMAGE = 4
    private const val UPGRADED_DAMAGE = 8
    private const val VENOM_TIER = 2
    private const val VENOM_RAMP = 2
    private const val INTERVAL = 3
    private const val HITS = 10

    private val NoopModifier = NpcHitModifier {}

    private var Npc.poisonSource by typePlayerUidVarn("varn.holy_water_poison_source")

    fun apply(npc: Npc, hitDelay: Int, tier: Int, source: Player) {
        if (NpcPoison.isImmune(npc)) {
            return
        }
        npc.poisonSource = source.uid
        val damage = if (tier > 0) UPGRADED_DAMAGE else BASE_DAMAGE
        val venom = tier >= VENOM_TIER
        if (npc.vars[HITS_VARN] > 0) {
            npc.vars[HITS_VARN] = HITS
            if (venom) {
                npc.vars[VENOM_VARN] = 1
            }
            if (damage > npc.vars[DAMAGE_VARN]) {
                npc.vars[DAMAGE_VARN] = damage
            }
            return
        }
        npc.vars[DAMAGE_VARN] = damage
        npc.vars[VENOM_VARN] = if (venom) 1 else 0
        proc(npc, hitDelay, source)
        npc.vars[HITS_VARN] = HITS - 1
        npc.timer(TIMER, hitDelay + INTERVAL)
    }

    fun onTimerTick(npc: Npc, players: PlayerList) {
        val remaining = npc.vars[HITS_VARN]
        if (remaining <= 0 || npc.hitpoints <= 0) {
            clear(npc)
            return
        }
        proc(npc, delay = 1, npc.poisonSource?.resolve(players))
        if (remaining == 1) {
            clear(npc)
            return
        }
        npc.vars[HITS_VARN] = remaining - 1
        npc.timer(TIMER, INTERVAL)
    }

    private fun proc(npc: Npc, delay: Int, source: Player?) {
        val damage = npc.vars[DAMAGE_VARN]
        val venom = npc.vars[VENOM_VARN] == 1
        val hitmark = if (venom) hitmark_groups.venom else hitmark_groups.poison_damage
        val scaled =
            if (venom) {
                NpcStatusEffects.venomDamage(npc, damage)
            } else {
                NpcStatusEffects.poisonDamage(npc, damage)
            }
        repeat(NpcStatusEffects.poisonHits(npc)) {
            if (source != null) {
                npc.queueHit(
                    source = source,
                    delay = delay,
                    type = HitType.Typeless,
                    damage = scaled,
                    modifier = NoopModifier,
                    hitmark = hitmark,
                )
            } else {
                npc.queueHit(
                    delay = delay,
                    type = HitType.Typeless,
                    damage = scaled,
                    modifier = NoopModifier,
                    hitmark = hitmark,
                )
            }
        }
        if (venom) {
            npc.vars[DAMAGE_VARN] = damage + VENOM_RAMP
        }
    }

    private fun clear(npc: Npc) {
        npc.vars[HITS_VARN] = 0
        npc.vars[DAMAGE_VARN] = 0
        npc.vars[VENOM_VARN] = 0
        npc.poisonSource = null
        npc.clearTimer(TIMER)
    }
}

class HolyWaterPoisonScript @Inject constructor(private val players: PlayerList) : PluginScript() {
    override fun ScriptContext.startup() {
        onNpcTimer("timer.npc_holy_water_poison") { HolyWaterPoison.onTimerTick(npc, players) }
    }
}
