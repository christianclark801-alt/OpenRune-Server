package org.rsmod.content.other.gamemode

import dev.openrune.rscm.RSCM.asRSCM
import dev.openrune.rscm.RSCMType
import jakarta.inject.Inject
import org.rsmod.api.player.cinematic.Cinematic
import org.rsmod.api.player.gamemode.XpMode
import org.rsmod.api.player.gamemode.bossDropMultiplier
import org.rsmod.api.player.gamemode.xpModeId
import org.rsmod.api.player.ironman.PlayerGamemode
import org.rsmod.api.player.ironman.setGamemode
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.player.vars.boolVarBit
import org.rsmod.api.player.vars.intVarBit
import org.rsmod.api.script.onIfClose
import org.rsmod.api.script.onIfModalButton
import org.rsmod.api.script.onPlayerLogin
import org.rsmod.api.script.onPlayerQueue
import org.rsmod.game.entity.Player
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

private const val INTERFACE = "interface.game_mode_select"
private const val OPEN_QUEUE = "queue.game_mode_select"
private const val CARD_SCRIPT = "clientscript.game_mode_card"

private const val STATE_LEGACY = 0
private const val STATE_PENDING = 1
private const val STATE_DONE = 2

private const val STEP_ACCOUNT = 1
private const val STEP_XP = 2

private const val CARDS_WIDTH = 492
private const val CARD_COUNT = 4
private const val CARD_GAP = 12

private class CardSpec(val icon: String, val title: String, val desc: String)

private class AccountType(val mode: Int, val card: CardSpec)

private val ACCOUNT_TYPES =
    listOf(
        AccountType(
            PlayerGamemode.NORMAL,
            CardSpec(
                "obj.rune_full_helm",
                "Normal",
                "No restrictions.<br><br>Trade, use the Grand Exchange and play freely.",
            ),
        ),
        AccountType(
            PlayerGamemode.IRONMAN,
            CardSpec(
                "obj.ironman_helm",
                "Ironman",
                "No trading or Grand Exchange.<br><br><col=00ff00>+${XpMode.IRONMAN_DROP_BONUS}x</col> boss drop rate.",
            ),
        ),
        AccountType(
            PlayerGamemode.HARDCORE_IRONMAN,
            CardSpec(
                "obj.hardcore_ironman_helm",
                "Hardcore Ironman",
                "Ironman with one life. An unsafe death makes you an Ironman.<br><br><col=00ff00>+${XpMode.IRONMAN_DROP_BONUS}x</col> boss drop rate.",
            ),
        ),
        AccountType(
            PlayerGamemode.ULTIMATE_IRONMAN,
            CardSpec(
                "obj.ultimate_ironman_helm",
                "Ultimate Ironman",
                "Ironman with no bank and nothing kept on death.<br><br><col=00ff00>+${XpMode.IRONMAN_DROP_BONUS}x</col> boss drop rate.",
            ),
        ),
    )

private val XP_MODE_ICONS =
    mapOf(
        XpMode.Easy to "obj.bronze_full_helm",
        XpMode.Medium to "obj.dragon_scimitar",
        XpMode.Hard to "obj.abyssal_whip",
    )

private val Player.newAccount by boolVarBit("varbit.new_player_account")
private var Player.gameModeState by intVarBit("varbit.game_mode_state")
private var Player.gameModeStep by intVarBit("varbit.game_mode_step")
private var Player.accountPick by intVarBit("varbit.game_mode_account_pick")

class GameModeSelectScript @Inject constructor() : PluginScript() {
    override fun ScriptContext.startup() {
        onPlayerLogin { player.startSelectionIfPending() }

        onPlayerQueue(OPEN_QUEUE) { if (player.gameModeState == STATE_PENDING) open() }

        onIfClose(INTERFACE) {
            if (player.gameModeState == STATE_PENDING) {
                player.queue(OPEN_QUEUE, 1)
            }
        }

        for (index in 0 until CARD_COUNT) {
            onIfModalButton("component.game_mode_select:card$index") { select(index) }
        }

        onIfModalButton("component.game_mode_select:back") { back() }
    }

    private fun Player.startSelectionIfPending() {
        if (gameModeState == STATE_LEGACY && newAccount) {
            gameModeState = STATE_PENDING
        }
        if (gameModeState != STATE_PENDING) {
            return
        }
        gameModeStep = STEP_ACCOUNT
        accountPick = PlayerGamemode.NORMAL
        queue(OPEN_QUEUE, 1)
    }

    private fun ProtectedAccess.open() {
        setLocked(player, locked = true)
        if (!player.ui.containsModal(INTERFACE)) {
            ifOpenMainModal(INTERFACE)
        }
        draw()
    }

    private fun ProtectedAccess.select(index: Int) {
        if (player.gameModeState != STATE_PENDING) {
            return
        }
        if (player.gameModeStep == STEP_XP) {
            val mode = XpMode.entries.getOrNull(index) ?: return
            confirm(mode)
            return
        }
        val account = ACCOUNT_TYPES.getOrNull(index) ?: return
        player.accountPick = account.mode
        player.gameModeStep = STEP_XP
        draw()
    }

    private fun ProtectedAccess.back() {
        if (player.gameModeState != STATE_PENDING) {
            return
        }
        player.gameModeStep = STEP_ACCOUNT
        draw()
    }

    private fun ProtectedAccess.confirm(mode: XpMode) {
        val account = accountTypeOf(player.accountPick)
        player.setGamemode(account.mode)
        player.xpModeId = mode.id
        player.xpRate = mode.xpRate
        player.gameModeState = STATE_DONE
        setLocked(player, locked = false)
        ifClose()

        val drop = bossDropMultiplier(mode, account.isIronman)
        mes(
            "You are playing as <col=ff0000>${account.card.title}</col> on " +
                "<col=ff0000>${mode.label}</col> mode: ${mode.xpRate.format()}x XP, " +
                "${drop.format()}x boss drop rate."
        )
    }

    private fun ProtectedAccess.draw() {
        if (player.gameModeStep == STEP_XP) {
            drawXpModes()
        } else {
            drawAccountTypes()
        }
    }

    private fun ProtectedAccess.drawAccountTypes() {
        ifSetText(
            "component.game_mode_select:subtitle",
            "Step 1 of 2: Choose your account type",
        )
        ifSetHide("component.game_mode_select:back", hide = true)
        drawCards(ACCOUNT_TYPES.map { it.card })
    }

    private fun ProtectedAccess.drawXpModes() {
        val account = accountTypeOf(player.accountPick)
        ifSetText(
            "component.game_mode_select:subtitle",
            "Step 2 of 2: Choose your XP mode (${account.card.title})",
        )
        ifSetHide("component.game_mode_select:back", hide = false)
        val cards =
            XpMode.entries.map { mode ->
                val drop = bossDropMultiplier(mode, account.isIronman)
                CardSpec(
                    XP_MODE_ICONS.getValue(mode),
                    mode.label,
                    "<col=00ff00>${mode.xpRate.format()}x</col> XP in all skills<br><br>" +
                        "<col=00ff00>${drop.format()}x</col> boss drop rate",
                )
            }
        drawCards(cards)
    }

    private fun ProtectedAccess.drawCards(cards: List<CardSpec>) {
        val width = (CARDS_WIDTH - CARD_GAP * (cards.size - 1)) / cards.size
        for (index in 0 until CARD_COUNT) {
            val component = "component.game_mode_select:card$index"
            val card = cards.getOrNull(index)
            ifSetHide(component, hide = card == null)
            if (card == null) {
                continue
            }
            runClientScript(
                CARD_SCRIPT.asRSCM(RSCMType.CLIENTSCRIPT),
                component.asRSCM(RSCMType.COMPONENT),
                index * (width + CARD_GAP),
                width,
                card.icon.asRSCM(RSCMType.OBJ),
                card.title,
                card.desc,
            )
        }
    }

    private fun setLocked(player: Player, locked: Boolean) {
        Cinematic.setHideToplevel(player, locked)
        Cinematic.setHideEntityOps(player, locked)
    }

    private fun accountTypeOf(mode: Int): AccountType =
        ACCOUNT_TYPES.firstOrNull { it.mode == mode } ?: ACCOUNT_TYPES.first()

    private val AccountType.isIronman: Boolean
        get() = mode != PlayerGamemode.NORMAL

    private fun Double.format(): String =
        if (this % 1.0 == 0.0) toInt().toString() else toString()
}
