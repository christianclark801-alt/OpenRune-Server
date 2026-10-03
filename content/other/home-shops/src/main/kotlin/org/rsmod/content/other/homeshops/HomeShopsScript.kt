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
import org.rsmod.api.shops.Shops
import org.rsmod.game.entity.Npc
import org.rsmod.map.CoordGrid
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

private enum class HomeShop(
    val npc: String,
    val title: String,
    val suppliesInv: String,
    val gearInv: String,
    val coords: CoordGrid,
    val forIronmen: Boolean,
    val greeting: String,
    val refusal: String,
) {
    Ironman(
        npc = "npc.home_ironman_shopkeeper",
        title = "Ironman Store",
        suppliesInv = "inv.home_ironman_supplies",
        gearInv = "inv.home_ironman_gear",
        coords = CoordGrid(3797, 2569, 0),
        forIronmen = true,
        greeting = "Standing alone takes supplies. Take a look at what I have.",
        refusal = "Sorry, I only trade with Ironmen. Try the General Store just south of me.",
    ),
    General(
        npc = "npc.home_general_shopkeeper",
        title = "General Store",
        suppliesInv = "inv.home_general_supplies",
        gearInv = "inv.home_general_gear",
        coords = CoordGrid(3797, 2568, 0),
        forIronmen = false,
        greeting = "Welcome to the General Store! Have a look around.",
        refusal = "Sorry, Ironmen can't trade here. The Ironman Shopkeeper just north of me can help you.",
    ),
}

private enum class Section {
    Supplies,
    Gear,
}

class HomeShopsScript
@Inject
constructor(
    private val npcRepo: NpcRepository,
    private val shops: Shops,
) : PluginScript() {
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
        access.browse(shop)
    }

    private suspend fun ProtectedAccess.trade(shop: HomeShop, npc: Npc) {
        if (canTrade(shop)) {
            browse(shop)
        } else {
            startDialogue(npc) { chatNpc(neutral, shop.refusal) }
        }
    }

    private suspend fun ProtectedAccess.browse(shop: HomeShop) {
        val section =
            choice2("Supplies", Section.Supplies, "Gear", Section.Gear, title = shop.title)
        val inv = if (section == Section.Supplies) shop.suppliesInv else shop.gearInv
        shops.open(
            player = player,
            title = "${shop.title} - ${section.name}",
            shopInv = inv,
            buyPercentage = BUY_PERCENTAGE,
            sellPercentage = SELL_PERCENTAGE,
            changePercentage = CHANGE_PERCENTAGE,
        )
    }

    private fun ProtectedAccess.canTrade(shop: HomeShop): Boolean = player.isAnyIronman == shop.forIronmen

    private companion object {
        const val BUY_PERCENTAGE = 40.0
        const val SELL_PERCENTAGE = 100.0
        const val CHANGE_PERCENTAGE = 0.0
    }
}
