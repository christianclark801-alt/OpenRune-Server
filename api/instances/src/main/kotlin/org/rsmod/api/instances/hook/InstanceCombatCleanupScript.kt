package org.rsmod.api.instances.hook

import jakarta.inject.Inject
import org.rsmod.api.instances.InstanceManager
import org.rsmod.api.instances.events.InstancePlayerLeaveUnboundEvent
import org.rsmod.api.player.vars.intVarp
import org.rsmod.api.script.onEvent
import org.rsmod.game.entity.Player
import org.rsmod.game.interact.InteractionPlayer
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

internal class InstanceCombatCleanupScript
@Inject
constructor(private val manager: InstanceManager) : PluginScript() {
    private var Player.lastCombat by intVarp("varp.lastcombat")

    override fun ScriptContext.startup() {
        onEvent<InstancePlayerLeaveUnboundEvent> {
            for (npc in manager.npcsForInstance(instanceId)) {
                val target = (npc.interaction as? InteractionPlayer)?.target
                if (target === player) {
                    npc.defaultMode()
                }
            }
            player.clearQueue("queue.hit")
            player.clearInteraction()
            player.lastCombat = 0
        }
    }
}
