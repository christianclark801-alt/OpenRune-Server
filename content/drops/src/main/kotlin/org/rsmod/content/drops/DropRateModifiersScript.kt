package org.rsmod.content.drops

import jakarta.inject.Inject
import org.rsmod.api.config.refs.BaseParams
import org.rsmod.api.droptable.DropRateModifiers
import org.rsmod.api.player.gamemode.bossDropMultiplier
import org.rsmod.api.server.config.ServerConfig
import org.rsmod.game.entity.Npc
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

class DropRateModifiersScript @Inject constructor(private val config: ServerConfig) :
    PluginScript() {
    override fun ScriptContext.startup() {
        val server = config.gameplay.dropRates.multiplier
        require(server > 0.0) { "gameplay.drop-rates.multiplier must be positive, was $server" }
        DropRateModifiers.serverMultiplier = server
        DropRateModifiers.playerMultiplier = { player ->
            val percent = player.vars[PLAYER_MULTIPLIER_VARP]
            if (percent == 0) 1.0 else percent / 100.0
        }
        DropRateModifiers.killMultiplier = { player, npc ->
            if (npc.isBoss()) player.bossDropMultiplier else 1.0
        }
        DropRateModifiers.install()
    }

    private fun Npc.isBoss(): Boolean = paramOrNull(BaseParams.killcount_varp) != null

    companion object {
        const val PLAYER_MULTIPLIER_VARP = "varp.drop_rate_multiplier"
    }
}
