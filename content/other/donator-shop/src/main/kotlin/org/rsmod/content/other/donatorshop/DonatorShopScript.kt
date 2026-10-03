package org.rsmod.content.other.donatorshop

import com.github.michaelbull.logging.InlineLogger
import dev.openrune.ServerCacheManager
import dev.openrune.definition.type.widget.IfEvent
import dev.openrune.rscm.RSCM.asRSCM
import dev.openrune.rscm.RSCMType
import dev.or2.central.account.Rights
import jakarta.inject.Inject
import org.rsmod.api.player.dialogue.Dialogue
import org.rsmod.api.player.output.ChatType
import org.rsmod.api.player.output.mes
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.player.protect.ProtectedAccessLauncher
import org.rsmod.api.player.vars.intVarBit
import org.rsmod.api.repo.npc.NpcRepository
import org.rsmod.api.repo.obj.ObjRepository
import org.rsmod.api.script.onCommand
import org.rsmod.api.script.onGameStartup
import org.rsmod.api.script.onIfModalButton
import org.rsmod.api.script.onOpHeld1
import org.rsmod.api.script.onOpNpc1
import org.rsmod.api.script.onOpNpc3
import org.rsmod.api.script.onOpNpc4
import org.rsmod.game.cheat.Cheat
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player
import org.rsmod.game.entity.PlayerList
import org.rsmod.map.CoordGrid
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

private const val NPC = "npc.donator_peer"
private const val INTERFACE = "interface.donator_shop"
private const val BOXES = "component.donator_shop:boxes"
private const val REWARDS = "component.donator_shop:rewards"

private const val CARD_COMSUBS = 6

private val PEER_COORDS = CoordGrid(3797, 2564, 0)

private var Player.selectedBox by intVarBit("varbit.donator_shop_selected")

class DonatorShopScript
@Inject
constructor(
    private val protectedAccess: ProtectedAccessLauncher,
    private val npcRepo: NpcRepository,
    private val objRepo: ObjRepository,
    private val playerList: PlayerList,
) : PluginScript() {
    private val logger = InlineLogger()

    override fun ScriptContext.startup() {
        onGameStartup { spawnPeer() }

        onOpNpc1(NPC) { startDialogue(it.npc) { peerDialogue() } }
        onOpNpc3(NPC) { open() }
        onOpNpc4(NPC) { mes(pointsMessage(player)) }

        onIfModalButton(BOXES) {
            val box = DonatorBox.forId(it.comsub / CARD_COMSUBS) ?: return@onIfModalButton
            when (it.op.slot) {
                1 -> select(box)
                2 -> buy(box)
            }
        }
        onIfModalButton(REWARDS) { it.obj?.let { obj -> inspect(obj.id) } }
        onIfModalButton("component.donator_shop:buy") { selected()?.let { buy(it) } }
        onIfModalButton("component.donator_shop:buyopen") {
            val box = selected() ?: return@onIfModalButton
            if (buy(box)) {
                openBox(box, slot = null)
            }
        }

        for (box in DonatorBox.entries) {
            onOpHeld1(box.obj) { openBox(box, it.slot) }
        }

        onCommand("donatorshop") {
            desc = "Open the donator store"
            requiredRights = Rights.ADMINISTRATOR
            cheat { protectedAccess.launch(player, busyText = "You can't do that right now.") { open() } }
        }
        onCommand("givedonator") {
            desc = "Credit donator points: ::givedonator <name> <amount>"
            requiredRights = Rights.ADMINISTRATOR
            cheat { giveDonator() }
        }
        onCommand("takedonator") {
            desc = "Remove donator points: ::takedonator <name> <amount>"
            requiredRights = Rights.ADMINISTRATOR
            cheat { takeDonator() }
        }
        onCommand("donatorpoints") {
            desc = "Check donator points: ::donatorpoints [name]"
            requiredRights = Rights.ADMINISTRATOR
            cheat { checkDonator() }
        }
    }

    private fun spawnPeer() {
        runCatching {
            val peer = Npc(NPC, PEER_COORDS).apply { respawnDir = respawnDir.opposite }
            npcRepo.add(peer, Int.MAX_VALUE)
        }
            .onFailure { logger.warn(it) { "Unable to spawn Peer the Seer; rebuild the cache with buildCache." } }
    }

    private suspend fun Dialogue.peerDialogue() {
        chatNpc(happy, "Greetings, adventurer. I foresee great treasures in your future... for those who support the realm.")
        val choice =
            choice3(
                "Show me the donator store.",
                1,
                "How do I get donator points?",
                2,
                "How many donator points do I have?",
                3,
            )
        when (choice) {
            1 -> {
                chatPlayer(happy, "Show me the donator store.")
                access.open()
            }
            2 -> {
                chatPlayer(quiz, "How do I get donator points?")
                chatNpc(
                    neutral,
                    "Every dollar you donate grants you one donator point. Once your donation " +
                        "is confirmed, a member of staff will add the points to your account.",
                )
                chatNpc(happy, "Spend them here on my boxes. Each one holds a reward I cannot quite foresee!")
            }
            3 -> {
                chatPlayer(quiz, "How many donator points do I have?")
                chatNpc(neutral, "The spirits tell me you have ${points(player.donatorPoints)}.")
            }
        }
    }

    private fun ProtectedAccess.open() {
        ifOpenMainModal(INTERFACE)
        ifSetEvents(BOXES, 0 until DonatorBox.entries.size * CARD_COMSUBS, IfEvent.Op1, IfEvent.Op2)
        ifSetEvents(REWARDS, 0 until DonatorBox.MAX_REWARDS, IfEvent.Op1)
        if (selected() == null) {
            player.selectedBox = DonatorBox.entries.first().id + 1
        }
        drawPoints()
        drawCards()
        drawDetails()
    }

    private fun ProtectedAccess.select(box: DonatorBox) {
        player.selectedBox = box.id + 1
        drawCards()
        drawDetails()
    }

    private fun ProtectedAccess.inspect(objId: Int) {
        val box = selected() ?: return
        val reward = box.rewards.firstOrNull { it.obj.asRSCM(RSCMType.OBJ) == objId } ?: return
        val amount = if (reward.max > reward.min) " (${"%,d".format(reward.min)} - ${"%,d".format(reward.max)})" else ""
        mes("${objName(reward.obj)}$amount: ${box.chanceText(reward)} chance from the ${box.displayName}.")
    }

    private fun ProtectedAccess.buy(box: DonatorBox): Boolean {
        if (player.donatorPoints < box.price) {
            mes(
                "<col=ef1020>You need ${points(box.price)} to buy the ${box.displayName}, " +
                    "but only have ${player.donatorPoints}.</col> Talk to Peer the Seer to learn how to get more.",
            )
            return false
        }
        if (inv.isFull()) {
            mes("You need a free inventory slot to buy the ${box.displayName}.")
            return false
        }
        if (!DonatorPoints.spend(player, box.price)) {
            return false
        }
        if (invAdd(inv, box.obj).failure) {
            player.donatorPoints += box.price
            mes("You need a free inventory slot to buy the ${box.displayName}.")
            return false
        }
        mes("You buy a ${box.displayName} for ${points(box.price)}. You have ${points(player.donatorPoints)} left.")
        if (player.ui.containsModal(INTERFACE)) {
            drawPoints()
            drawCards()
        }
        return true
    }

    private fun ProtectedAccess.openBox(box: DonatorBox, slot: Int?) {
        if (invDel(inv, box.obj, slot = slot).failure) {
            return
        }
        val reward = box.rewardAt(random.of(box.totalWeight))
        val count = random.of(reward.min, reward.max)
        val inInventory = invAddOrDrop(objRepo, reward.obj, count)
        val name = objName(reward.obj)
        val amount = if (count > 1) "${"%,d".format(count)} x " else ""
        mes("You open the ${box.displayName} and find $amount$name!")
        if (!inInventory) {
            mes("Your inventory is full, so the reward has been placed on the ground beneath you.")
        }
        if (box.isRare(reward)) {
            broadcast("<col=ff981f>${player.displayName} has just received $amount$name from a ${box.displayName}!</col>")
        }
    }

    private fun Cheat.giveDonator() {
        val (target, amount) = parseTargetAndAmount() ?: return
        DonatorPoints.add(target, amount)
        player.mes("Gave ${points(amount)} to ${target.displayName}. They now have ${target.donatorPoints}.")
        if (target !== player) {
            target.mes("<col=00a000>${points(amount)} have been added to your account. Thank you for donating!</col>")
        }
    }

    private fun Cheat.takeDonator() {
        val (target, amount) = parseTargetAndAmount() ?: return
        val removed = DonatorPoints.remove(target, amount)
        player.mes("Removed ${points(removed)} from ${target.displayName}. They now have ${target.donatorPoints}.")
    }

    private fun Cheat.checkDonator() {
        val target = if (args.isEmpty()) player else findPlayer(args.joinToString(" "))
        if (target == null) {
            player.mes("No online player named '${args.joinToString(" ")}'.")
            return
        }
        player.mes(
            "${target.displayName} has ${points(target.donatorPoints)} " +
                "(${"%,d".format(target.donatorPointsTotal)} donated in total).",
        )
    }

    private fun Cheat.parseTargetAndAmount(): Pair<Player, Int>? {
        val amount = args.lastOrNull()?.toIntOrNull()
        if (args.size < 2 || amount == null || amount <= 0) {
            player.mes("Usage: ::$command <player name> <amount>")
            return null
        }
        val name = args.dropLast(1).joinToString(" ")
        val target = findPlayer(name)
        if (target == null) {
            player.mes("No online player named '$name'.")
            return null
        }
        return target to amount
    }

    private fun findPlayer(name: String): Player? {
        val normalised = name.replace('_', ' ').trim()
        return playerList.firstOrNull {
            it.displayName.equals(normalised, ignoreCase = true) || it.username.equals(normalised, ignoreCase = true)
        }
    }

    private fun broadcast(text: String) {
        for (player in playerList) {
            player.mes(text, ChatType.Broadcast)
        }
    }

    private fun ProtectedAccess.drawPoints() {
        ifSetText("component.donator_shop:points", "Donator points: <col=ffffff>${"%,d".format(player.donatorPoints)}</col>")
    }

    private fun ProtectedAccess.drawCards() {
        val selected = selected()
        runClientScript(script("donator_shop_cards_clear"), component(BOXES))
        DonatorBox.entries.forEachIndexed { slot, box ->
            val colour = if (player.donatorPoints >= box.price) "00ff00" else "ff0000"
            runClientScript(
                script("donator_shop_card"),
                component(BOXES),
                slot,
                box.id,
                box.obj.asRSCM(RSCMType.OBJ),
                box.displayName,
                "<col=$colour>${points(box.price)}</col>",
                if (box == selected) 1 else 0,
            )
        }
    }

    private fun ProtectedAccess.drawDetails() {
        val box = selected()
        ifSetHide("component.donator_shop:hint", hide = box != null)
        ifSetHide("component.donator_shop:details", hide = box == null)
        if (box == null) {
            return
        }
        runClientScript(
            script("donator_shop_details_icon"),
            component("component.donator_shop:icon"),
            box.obj.asRSCM(RSCMType.OBJ),
        )
        ifSetText("component.donator_shop:name", box.displayName)
        ifSetText("component.donator_shop:price", "<col=ff981f>Price:</col> ${points(box.price)}")
        ifSetText("component.donator_shop:desc", box.description)
        runClientScript(script("donator_shop_rewards_clear"), component(REWARDS))
        box.rewards.take(DonatorBox.MAX_REWARDS).forEachIndexed { slot, reward ->
            runClientScript(
                script("donator_shop_reward"),
                component(REWARDS),
                slot,
                reward.obj.asRSCM(RSCMType.OBJ),
                reward.max,
            )
        }
    }

    private fun ProtectedAccess.selected(): DonatorBox? = DonatorBox.forId(player.selectedBox - 1)

    private fun pointsMessage(player: Player): String =
        "You have ${points(player.donatorPoints)}. 1 donator point = $1 donated."

    private fun points(amount: Int): String = if (amount == 1) "1 point" else "${"%,d".format(amount)} points"

    private fun objName(obj: String): String =
        ServerCacheManager.getItem(obj.asRSCM(RSCMType.OBJ))?.name ?: obj.removePrefix("obj.")

    private fun script(name: String): Int = "clientscript.$name".asRSCM(RSCMType.CLIENTSCRIPT)

    private fun component(name: String): Int = name.asRSCM(RSCMType.COMPONENT)
}
