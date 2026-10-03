package org.rsmod.api.mechanics.toxins

import jakarta.inject.Inject
import org.rsmod.api.mechanics.toxins.impl.NpcPoison
import org.rsmod.api.script.onNpcTimer
import org.rsmod.game.entity.PlayerList
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

public class NpcPoisonTimerScript @Inject constructor(private val players: PlayerList) :
    PluginScript() {
    override fun ScriptContext.startup() {
        onNpcTimer("timer.npc_poison") { NpcPoison.onPoisonTimerTick(npc, players) }
    }
}
