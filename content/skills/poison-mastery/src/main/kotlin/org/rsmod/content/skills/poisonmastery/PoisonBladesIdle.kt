package org.rsmod.content.skills.poisonmastery

import org.rsmod.api.player.isInCombat
import org.rsmod.api.player.righthand
import org.rsmod.api.player.vars.VarPlayerIntMapSetter
import org.rsmod.api.script.onContentEquipObj
import org.rsmod.api.script.onContentUnequipObj
import org.rsmod.api.script.onPlayerCoordsChanged
import org.rsmod.api.script.onPlayerLogin
import org.rsmod.api.script.onPlayerSoftTimer
import org.rsmod.game.entity.Player
import org.rsmod.game.entity.util.PathingEntityCommon
import org.rsmod.game.inv.isType
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

/**
 * Replays the looping poison spotanim over the wielded blades' idle stance. Spotanims don't
 * loop, so a timer re-sends it once per 6-tick loop while the player stands still out of combat,
 * and it is cleared as soon as they move, attack or unwield.
 */
class PoisonBladesIdle : PluginScript() {
    override fun ScriptContext.startup() {
        onContentEquipObj(CONTENT) { player.softTimer(TIMER, LOOP_TICKS) }
        onContentUnequipObj(CONTENT) {
            player.clearSoftTimer(TIMER)
            hide(player)
        }
        onPlayerLogin {
            if (player.righthand.isType(BLADES)) {
                player.softTimer(TIMER, LOOP_TICKS)
            }
        }
        onPlayerSoftTimer(TIMER) { player.replay() }
        onPlayerCoordsChanged { hide(player) }
    }

    private fun Player.replay() {
        if (!righthand.isType(BLADES)) {
            clearSoftTimer(TIMER)
            hide(this)
            return
        }
        if (hasMovedThisCycle || isInCombat()) {
            hide(this)
            return
        }
        spotanim(SPOTANIM, slot = SLOT)
        VarPlayerIntMapSetter.set(this, VAR_SHOWN, 1)
    }

    companion object {
        private const val CONTENT = "content.poison_blades"
        private const val BLADES = "obj.poison_blades"
        private const val TIMER = "timer.poison_blades_idle_fx"
        private const val SPOTANIM = "spotanim.poison_blades_idle_fx"
        private const val VAR_SHOWN = "varp.poison_blades_idle_fx"
        private const val LOOP_TICKS = 6
        private const val SLOT = 3
        private const val NO_SPOTANIM = 65535

        fun hide(player: Player) {
            if (player.vars[VAR_SHOWN] == 0) {
                return
            }
            PathingEntityCommon.spotanim(player, NO_SPOTANIM, delay = 0, height = 0, slot = SLOT)
            VarPlayerIntMapSetter.set(player, VAR_SHOWN, 0)
        }
    }
}
