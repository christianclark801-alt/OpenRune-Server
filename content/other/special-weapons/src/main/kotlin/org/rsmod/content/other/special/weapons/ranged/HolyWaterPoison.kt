package org.rsmod.content.other.special.weapons.ranged

import org.rsmod.api.config.refs.done.hitmark_groups
import org.rsmod.api.mechanics.toxins.impl.NpcPoison
import org.rsmod.api.npc.hit.modifier.NpcHitModifier
import org.rsmod.api.npc.hit.queueHit
import org.rsmod.api.script.onNpcTimer
import org.rsmod.game.entity.Npc
import org.rsmod.game.hit.HitType
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

object HolyWaterPoison {
    private const val HITS_VARN = "varn.holy_water_poison_hits"
    private const val TIMER = "timer.npc_holy_water_poison"
    private const val DAMAGE = 4
    private const val INTERVAL = 3
    private const val HITS = 10

    private val NoopModifier = NpcHitModifier {}

    fun apply(npc: Npc, hitDelay: Int) {
        if (NpcPoison.isImmune(npc)) {
            return
        }
        if (npc.vars[HITS_VARN] > 0) {
            npc.vars[HITS_VARN] = HITS
            return
        }
        queuePoisonHit(npc, hitDelay)
        npc.vars[HITS_VARN] = HITS - 1
        npc.timer(TIMER, hitDelay + INTERVAL)
    }

    fun onTimerTick(npc: Npc) {
        val remaining = npc.vars[HITS_VARN]
        if (remaining <= 0 || npc.hitpoints <= 0) {
            clear(npc)
            return
        }
        queuePoisonHit(npc, delay = 1)
        if (remaining == 1) {
            clear(npc)
            return
        }
        npc.vars[HITS_VARN] = remaining - 1
        npc.timer(TIMER, INTERVAL)
    }

    private fun clear(npc: Npc) {
        npc.vars[HITS_VARN] = 0
        npc.clearTimer(TIMER)
    }

    private fun queuePoisonHit(npc: Npc, delay: Int) {
        npc.queueHit(
            delay = delay,
            type = HitType.Typeless,
            damage = DAMAGE,
            modifier = NoopModifier,
            hitmark = hitmark_groups.poison_damage,
        )
    }
}

class HolyWaterPoisonScript : PluginScript() {
    override fun ScriptContext.startup() {
        onNpcTimer("timer.npc_holy_water_poison") { HolyWaterPoison.onTimerTick(npc) }
    }
}
