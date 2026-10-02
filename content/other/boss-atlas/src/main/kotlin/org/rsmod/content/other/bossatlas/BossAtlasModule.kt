package org.rsmod.content.other.bossatlas

import dev.openrune.ServerCacheManager
import dev.openrune.rscm.RSCM.asRSCM
import dev.openrune.rscm.RSCMType
import jakarta.inject.Inject
import org.rsmod.api.config.refs.BaseParams
import org.rsmod.api.death.NpcDeathKillContext
import org.rsmod.api.death.NpcDeathKillHook
import org.rsmod.api.death.NpcLootListener
import org.rsmod.api.market.MarketPrices
import org.rsmod.api.player.output.mes
import org.rsmod.api.player.vars.VarPlayerIntMapSetter
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player
import org.rsmod.plugin.module.PluginModule

class BossAtlasModule : PluginModule() {
    override fun bind() {
        newSetBinding<BossKillListener>()
        addSetBinding<NpcDeathKillHook>(BossAtlasKillHook::class.java)
        addSetBinding<NpcLootListener>(BossAtlasLootListener::class.java)
    }
}

class BossAtlasKillHook @Inject constructor(private val stats: BossStats) : NpcDeathKillHook {
    override fun onKill(context: NpcDeathKillContext) {
        val npc = context.npc
        if (npc.vars["varn.skip_killcount"] == 1) {
            return
        }
        val symbol = npc.type.internalName
        val boss = Boss.forNpc(symbol) ?: return
        val player = context.hero
        if (npc.paramOrNull(BaseParams.killcount_varp) == null) {
            val source = boss.kills.firstOrNull { symbol in it.npcs } ?: return
            val count = player.vars[source.varp] + 1
            VarPlayerIntMapSetter.set(player, source.varp, count)
            player.mes("Your ${boss.displayName} kill count is: <col=ff0000>$count</col>")
        }
        stats.notifyKill(player, boss)
    }
}

class BossAtlasLootListener
@Inject
constructor(private val stats: BossStats, private val prices: MarketPrices) : NpcLootListener {
    override fun onLoot(player: Player, npc: Npc, obj: String, count: Int) {
        val boss = Boss.forNpc(npc.type.internalName) ?: return
        val type = ServerCacheManager.getItem(obj.asRSCM(RSCMType.OBJ)) ?: return
        val price = prices[type] ?: return
        stats.addLoot(player, boss, price.toLong() * count)
    }
}
