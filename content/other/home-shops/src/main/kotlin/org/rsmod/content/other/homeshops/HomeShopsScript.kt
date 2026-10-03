package org.rsmod.content.other.homeshops

import com.github.michaelbull.logging.InlineLogger
import jakarta.inject.Inject
import org.rsmod.api.player.dialogue.Dialogue
import org.rsmod.api.player.ironman.isAnyIronman
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.repo.npc.NpcRepository
import org.rsmod.api.script.onGameStartup
import org.rsmod.api.script.onOpNpc1
import org.rsmod.api.script.onOpNpc3
import org.rsmod.content.interfaces.omnishop.openOmnishop
import org.rsmod.game.entity.Npc
import org.rsmod.map.CoordGrid
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

private enum class HomeShop(
    val npc: String,
    val row: String,
    val coords: CoordGrid,
    val forIronmen: Boolean,
    val greeting: String,
    val refusal: String,
) {
    Ironman(
        npc = "npc.home_ironman_shopkeeper",
        row = "dbrow.home_ironman_shop",
        coords = CoordGrid(3797, 2569, 0),
        forIronmen = true,
        greeting = "Standing alone takes supplies. Take a look at what I have.",
        refusal = "Sorry, I only trade with Ironmen. Try the General Store just south of me.",
    ),
    General(
        npc = "npc.home_general_shopkeeper",
        row = "dbrow.home_general_shop",
        coords = CoordGrid(3797, 2568, 0),
        forIronmen = false,
        greeting = "Welcome to the General Store! Have a look around.",
        refusal = "Sorry, Ironmen can't trade here. The Ironman Shopkeeper just north of me can help you.",
    ),
}

class HomeShopsScript @Inject constructor(private val npcRepo: NpcRepository) : PluginScript() {
    private val logger = InlineLogger()

    override fun ScriptContext.startup() {
        onGameStartup { spawnShopkeepers() }

        for (shop in HomeShop.entries) {
            onOpNpc1(shop.npc) { startDialogue(it.npc) { talk(shop) } }
            onOpNpc3(shop.npc) { trade(shop, it.npc) }
        }
    }

    private fun spawnShopkeepers() {
        for (shop in HomeShop.entries) {
            runCatching { npcRepo.add(Npc(shop.npc, shop.coords), Int.MAX_VALUE) }
                .onFailure { logger.warn(it) { "Unable to spawn ${shop.npc}; rebuild the cache with buildCache." } }
        }
    }

    private suspend fun Dialogue.talk(shop: HomeShop) {
        if (!access.canTrade(shop)) {
            chatNpc(neutral, shop.refusal)
            return
        }
        chatNpc(happy, shop.greeting)
        access.openOmnishop(shop.row)
    }

    private suspend fun ProtectedAccess.trade(shop: HomeShop, npc: Npc) {
        if (canTrade(shop)) {
            openOmnishop(shop.row)
        } else {
            startDialogue(npc) { chatNpc(neutral, shop.refusal) }
        }
    }

    private fun ProtectedAccess.canTrade(shop: HomeShop): Boolean = player.isAnyIronman == shop.forIronmen
}
