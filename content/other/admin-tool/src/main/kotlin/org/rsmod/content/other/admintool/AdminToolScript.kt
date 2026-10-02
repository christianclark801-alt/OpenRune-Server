package org.rsmod.content.other.admintool

import dev.openrune.definition.type.widget.IfEvent
import dev.openrune.rscm.RSCM.asRSCM
import dev.openrune.rscm.RSCMType
import dev.or2.central.account.Rights
import jakarta.inject.Inject
import java.util.WeakHashMap
import org.rsmod.api.invtx.invAdd
import org.rsmod.api.player.output.mes
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.player.vars.intVarBit
import org.rsmod.api.script.onCommand
import org.rsmod.api.script.onIfModalButton
import org.rsmod.api.script.onOpHeld1
import org.rsmod.api.script.onOpHeld5
import org.rsmod.api.script.onPlayerSoftTimer
import org.rsmod.game.cheat.CheatCommandMap
import org.rsmod.game.entity.Player
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

private const val ITEM = "obj.admin_tool"
private const val INTERFACE = "interface.admin_tool"
private const val LIST = "component.admin_tool:list"
private const val STATUS = "component.admin_tool:status"
private const val RUN_TIMER = "timer.admin_tool_run"

private const val TAB_SLOTS = 5
private const val BUTTON_COMSUBS = 5

private const val LIST_W = 470
private const val COLUMNS = 3
private const val BUTTON_GAP = 4
private const val BUTTON_W = (LIST_W - BUTTON_GAP * (COLUMNS - 1)) / COLUMNS
private const val BUTTON_H = 30
private const val ROW_PITCH = BUTTON_H + BUTTON_GAP

private var Player.adminToolTab by intVarBit("varbit.admin_tool_tab")

private val Player.isAdmin: Boolean
    get() = modLevel.isAtLeast(Rights.ADMINISTRATOR)

class AdminToolScript @Inject constructor(private val commands: CheatCommandMap) : PluginScript() {
    private class PendingCommand(val command: String, val args: List<String>)

    private val pending = WeakHashMap<Player, PendingCommand>()

    override fun ScriptContext.startup() {
        onCommand("admintool") {
            desc = "Gives you the Admin Tool"
            requiredRights = Rights.ADMINISTRATOR
            cheat { giveTool(player) }
        }

        onOpHeld1(ITEM) { open() }
        onOpHeld5(ITEM) { destroy() }

        for (tab in 0 until TAB_SLOTS) {
            onIfModalButton("component.admin_tool:tab$tab") { selectTab(tab) }
        }

        onIfModalButton(LIST) {
            val entry = entriesFor(player.adminToolTab).getOrNull(it.comsub / BUTTON_COMSUBS)
            if (entry != null) run(entry)
        }

        onPlayerSoftTimer(RUN_TIMER) { runPending(player) }
    }

    private fun giveTool(player: Player) {
        if (ITEM in player.inv) {
            player.mes("You already have the Admin Tool.")
            return
        }
        val result = player.invAdd(player.inv, ITEM, strict = false)
        if (result.completed() == 0) {
            player.mes("You need a free inventory slot for the Admin Tool.")
        }
    }

    private suspend fun ProtectedAccess.open() {
        if (!player.isAdmin) {
            invDel(player.inv, ITEM)
            mes("The tome crumbles to dust in your hands.")
            return
        }
        ifOpenMainModal(INTERFACE)
        ifSetEvents(LIST, 0 until ADMIN_TOOL_ENTRIES.size * BUTTON_COMSUBS, IfEvent.Op1)
        if (player.adminToolTab >= AdminToolCategory.entries.size) {
            player.adminToolTab = 0
        }
        drawTabs()
        drawList()
    }

    private suspend fun ProtectedAccess.destroy() {
        val confirmed =
            choice2("Yes", true, "No", false, title = "Destroy the Admin Tool? Use ::admintool for another.")
        if (confirmed) {
            invDel(player.inv, ITEM)
        }
    }

    private fun ProtectedAccess.selectTab(tab: Int) {
        if (tab >= AdminToolCategory.entries.size) {
            return
        }
        player.adminToolTab = tab
        drawTabs()
        drawList()
    }

    private suspend fun ProtectedAccess.run(entry: AdminToolEntry) {
        if (!player.isAdmin) {
            ifClose()
            return
        }
        if (entry.confirm) {
            val confirmed = choice2("Yes", true, "No", false, title = "Run ${entry.hint}?")
            if (!confirmed) {
                return
            }
        }
        val extra =
            entry.argsPrompt?.let { prompt ->
                stringDialog(prompt).lowercase().split(" ").filter(String::isNotBlank)
            } ?: emptyList()
        val args = entry.args + extra
        pending[player] = PendingCommand(entry.command, args)
        player.softTimer(RUN_TIMER, 1)
        if (player.ui.containsModal(INTERFACE)) {
            ifSetText(STATUS, "Ran <col=ffffff>::${(listOf(entry.command) + args).joinToString(" ")}</col>")
        }
    }

    private fun runPending(player: Player) {
        player.clearSoftTimer(RUN_TIMER)
        val command = pending.remove(player) ?: return
        commands.execute(player, command.command, command.args)
    }

    private fun ProtectedAccess.drawTabs() {
        for (tab in 0 until TAB_SLOTS) {
            val component = "component.admin_tool:tab$tab"
            val category = AdminToolCategory.entries.getOrNull(tab)
            ifSetHide(component, hide = category == null)
            if (category == null) {
                continue
            }
            runClientScript(
                script("admin_tool_tab"),
                component.asRSCM(RSCMType.COMPONENT),
                if (tab == player.adminToolTab) 1 else 0,
                category.label,
            )
        }
    }

    private fun ProtectedAccess.drawList() {
        val entries = entriesFor(player.adminToolTab)
        val list = LIST.asRSCM(RSCMType.COMPONENT)
        runClientScript(script("admin_tool_list_clear"), list)
        entries.forEachIndexed { slot, entry ->
            runClientScript(
                script("admin_tool_button"),
                list,
                slot,
                (slot % COLUMNS) * (BUTTON_W + BUTTON_GAP),
                (slot / COLUMNS) * ROW_PITCH,
                BUTTON_W,
                BUTTON_H,
                entry.label,
                entry.hint,
            )
        }
        val rows = (entries.size + COLUMNS - 1) / COLUMNS
        runClientScript(
            script("admin_tool_list_done"),
            list,
            "component.admin_tool:scrollbar".asRSCM(RSCMType.COMPONENT),
            rows * ROW_PITCH - BUTTON_GAP,
            1,
        )
    }

    private fun entriesFor(tab: Int): List<AdminToolEntry> {
        val category = AdminToolCategory.entries.getOrNull(tab) ?: return emptyList()
        return ADMIN_TOOL_ENTRIES.filter { it.category == category }
    }

    private fun script(name: String): Int = "clientscript.$name".asRSCM(RSCMType.CLIENTSCRIPT)
}
