package org.rsmod.content.other.bossatlas

import com.github.michaelbull.logging.InlineLogger
import dev.openrune.definition.type.widget.IfEvent
import dev.openrune.rscm.RSCM.asRSCM
import dev.openrune.rscm.RSCMType
import jakarta.inject.Inject
import java.util.WeakHashMap
import org.rsmod.api.instances.events.InstanceBossKillTimeEvent
import org.rsmod.api.market.MarketPrices
import org.rsmod.api.player.output.ClientScripts
import org.rsmod.api.player.output.mes
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.player.protect.ProtectedAccessLauncher
import org.rsmod.api.player.ui.IfScriptArgs
import org.rsmod.api.player.vars.boolVarBit
import org.rsmod.api.player.vars.intVarBit
import org.rsmod.api.repo.npc.NpcRepository
import org.rsmod.api.script.onCommand
import org.rsmod.api.script.onEvent
import org.rsmod.api.script.onGameStartup
import org.rsmod.api.script.onIfClose
import org.rsmod.api.script.onIfModalButton
import org.rsmod.api.script.onIfScriptTrigger
import org.rsmod.api.script.onOpNpc1
import org.rsmod.api.script.onOpNpc2
import org.rsmod.api.script.onOpNpc3
import org.rsmod.api.table.InstanceSettingsRow
import org.rsmod.game.cheat.Cheat
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.Player
import org.rsmod.map.CoordGrid
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

private const val INTERFACE = "interface.boss_atlas"
private const val LIST = "component.boss_atlas:list"
private const val SEARCH = "component.boss_atlas:searchtext"
private const val DROPS = "component.boss_atlas:drops"

private const val ROW_COMSUBS = 7
private const val MAX_DROPS = 20
private val GUIDE_COORDS = CoordGrid(3788, 2563, 0)

private val FAVOURITE_SLOTS = List(MAX_FAVOURITES) { "varbit.boss_atlas_fav$it" }

private var Player.atlasTab by intVarBit("varbit.boss_atlas_tab")
private var Player.atlasSelected by intVarBit("varbit.boss_atlas_selected")
private var Player.atlasDropsView by boolVarBit("varbit.boss_atlas_drops_view")

class BossAtlasScript
@Inject
constructor(
    private val protectedAccess: ProtectedAccessLauncher,
    private val teleporter: BossTeleporter,
    private val stats: BossStats,
    private val drops: BossDropPreview,
    private val prices: MarketPrices,
    private val npcRepo: NpcRepository,
) : PluginScript() {
    private val logger = InlineLogger()
    private val queries = WeakHashMap<Player, String>()

    private val bossByInstanceKey: Map<String, Boss> by lazy {
        Boss.entries
            .mapNotNull { boss ->
                val row = boss.instanceRow ?: return@mapNotNull null
                runCatching { InstanceSettingsRow.getRow(row).key }.getOrNull()?.let { it to boss }
            }
            .toMap()
    }

    internal data class SearchArgs(val comsub: Int, val op: Int, val text: String) : IfScriptArgs

    override fun ScriptContext.startup() {
        onGameStartup { spawnGuide() }

        for (command in listOf("bosses", "boss")) {
            onCommand(command) {
                desc = "Open the Boss Teleport Atlas"
                cheat { openAtlas() }
            }
        }

        onOpNpc1("npc.boss_guide") { open() }
        onOpNpc2("npc.boss_guide") { open() }
        onOpNpc3("npc.boss_guide") { teleportLast() }

        onIfClose(INTERFACE) {
            queries.remove(player)
            ClientScripts.chatDefaultRestoreInput(player)
        }

        onIfScriptTrigger<SearchArgs>(SEARCH) {
            if (player.ui.containsModal(INTERFACE)) search(it.text)
        }

        for (tab in 0 until TAB_COUNT) {
            onIfModalButton("component.boss_atlas:tab$tab") { selectTab(tab) }
        }

        onIfModalButton(LIST) {
            val boss = Boss.forId(it.comsub / ROW_COMSUBS) ?: return@onIfModalButton
            when (it.op.slot) {
                1 -> select(boss)
                2 -> teleporter.teleport(this, boss)
                3 -> toggleFavourite(boss)
            }
        }

        onIfModalButton("component.boss_atlas:teleport") {
            selectedBoss()?.let { teleporter.teleport(this, it) }
        }
        onIfModalButton("component.boss_atlas:favbtn") { selectedBoss()?.let { toggleFavourite(it) } }
        onIfModalButton("component.boss_atlas:dropsbtn") { toggleDropsView() }
        onIfModalButton("component.boss_atlas:instbtn") { selectedBoss()?.let { instanceOptions(it) } }
        onIfModalButton(DROPS) { it.obj?.let { obj -> mes("${obj.name}: ${formatGp((prices[obj] ?: 0).toLong())} gp each.") } }

        onEvent<InstanceBossKillTimeEvent> {
            val boss = bossByInstanceKey[key] ?: return@onEvent
            stats.recordKillTime(player, boss, elapsedTicks)
        }
    }

    private fun spawnGuide() {
        runCatching {
            npcRepo.add(
                Npc("npc.boss_guide", GUIDE_COORDS).apply { respawnDir = respawnDir.opposite },
                Int.MAX_VALUE,
            )
        }.onFailure { logger.warn(it) { "Unable to spawn the Boss Guide; rebuild the cache with buildCache." } }
    }

    private fun Cheat.openAtlas() {
        protectedAccess.launch(player, busyText = "You can't do that right now.") { open() }
    }

    private fun ProtectedAccess.open() {
        ifOpenMainModal(INTERFACE)
        ifSetEvents(LIST, 0 until (Boss.MAX_ID + 1) * ROW_COMSUBS, IfEvent.Op1, IfEvent.Op2, IfEvent.Op3)
        ifSetEvents(SEARCH, -1..-1, IfEvent.DeprecatedOp1, IfEvent.ScriptTrigger)
        ifSetEvents(DROPS, 0 until MAX_DROPS, IfEvent.Op1)
        queries[player] = ""
        player.atlasTab = TAB_ALL
        player.atlasDropsView = false
        drawTabs()
        drawList(resetScroll = true)
        drawDetails()
    }

    private suspend fun ProtectedAccess.teleportLast() {
        val boss = decodeFavourite(player.atlasLastTeleport)
        if (boss == null) {
            mes("You haven't teleported anywhere with the Boss Teleport Atlas yet.")
            return
        }
        teleporter.teleport(this, boss)
    }

    private fun ProtectedAccess.search(text: String) {
        queries[player] = text
        drawList(resetScroll = true)
    }

    private fun ProtectedAccess.selectTab(tab: Int) {
        player.atlasTab = tab
        queries[player] = ""
        runClientScript(script("boss_atlas_search_stop"))
        drawTabs()
        drawList(resetScroll = true)
    }

    private fun ProtectedAccess.select(boss: Boss) {
        player.atlasSelected = encodeFavourite(boss)
        player.atlasDropsView = false
        drawList(resetScroll = false)
        drawDetails()
    }

    private fun ProtectedAccess.toggleDropsView() {
        if (selectedBoss() == null) {
            return
        }
        player.atlasDropsView = !player.atlasDropsView
        drawDetails()
    }

    private fun ProtectedAccess.toggleFavourite(boss: Boss) {
        when (val result = toggledFavourites(favourites(), boss)) {
            is FavouriteToggle.Full -> {
                mes("You can only star $MAX_FAVOURITES bosses. Unstar one to make room.")
                return
            }
            is FavouriteToggle.Added -> {
                saveFavourites(result.favourites)
                mes("${boss.displayName} has been starred.")
            }
            is FavouriteToggle.Removed -> {
                saveFavourites(result.favourites)
                mes("${boss.displayName} has been unstarred.")
            }
        }
        drawList(resetScroll = false)
        if (selectedBoss() == boss) {
            drawDetails()
        }
    }

    private suspend fun ProtectedAccess.instanceOptions(boss: Boss) {
        val row = boss.instanceRow?.let { runCatching { InstanceSettingsRow.getRow(it) }.getOrNull() }
        if (row == null) {
            mes("${boss.displayName} has no instance. Use Teleport to travel to the public area.")
            return
        }
        ifClose()
        val fee = if (row.fee > 0) "${"%,d".format(row.fee)} coins" else "free"
        val players = if (row.maxPlayers == 1) "solo only" else "up to ${row.maxPlayers} players"
        mesbox(
            "${boss.displayName} instances are $players, entry fee: $fee. Use the entrance " +
                "to create a private instance, join a friend's or fight in the public room.",
        )
        val travel = choice2("Teleport to the entrance.", true, "Never mind.", false)
        if (travel) {
            teleporter.teleport(this, boss)
        }
    }

    private fun ProtectedAccess.drawTabs() {
        runClientScript(script("boss_atlas_tabs"), player.atlasTab)
    }

    private fun ProtectedAccess.drawList(resetScroll: Boolean) {
        val favourites = favourites()
        val query = queries[player].orEmpty()
        val bosses = bossesFor(player.atlasTab, query, favourites)
        val selected = selectedBoss()

        runClientScript(script("boss_atlas_list_clear"), component(LIST))
        bosses.forEachIndexed { slot, boss ->
            val sub = if (boss.implemented) levelLabel(boss) else "${levelLabel(boss)} <col=9f9f9f>(soon)</col>"
            runClientScript(
                script("boss_atlas_row"),
                component(LIST),
                slot,
                boss.id,
                boss.icon.asRSCM(RSCMType.OBJ),
                boss.displayName,
                sub,
                if (boss in favourites) 1 else 0,
                if (boss == selected) 1 else 0,
            )
        }

        val message =
            when {
                bosses.isNotEmpty() -> ""
                query.isNotBlank() -> "No bosses match<br>\"$query\"."
                else -> "No starred bosses.<br><br>Right-click a boss<br>and choose Star."
            }
        runClientScript(
            script("boss_atlas_list_done"),
            component(LIST),
            component("component.boss_atlas:scrollbar"),
            component("component.boss_atlas:status"),
            bosses.size,
            message,
            if (resetScroll) 1 else 0,
        )
        ifSetText(
            "component.boss_atlas:favcount",
            "Starred: ${favourites.size}/$MAX_FAVOURITES<br><br>Right-click a boss<br>to star it.",
        )
    }

    private fun ProtectedAccess.drawDetails() {
        val boss = selectedBoss()
        ifSetHide("component.boss_atlas:hint", hide = boss != null)
        ifSetHide("component.boss_atlas:details", hide = boss == null)
        if (boss == null) {
            return
        }
        runClientScript(
            script("boss_atlas_details_icons"),
            component("component.boss_atlas:icon"),
            boss.icon.asRSCM(RSCMType.OBJ),
            component("component.boss_atlas:gear"),
            boss.gear.asRSCM(RSCMType.OBJ),
        )
        ifSetText("component.boss_atlas:name", boss.displayName)
        ifSetText("component.boss_atlas:level", levelLabel(boss))
        ifSetText("component.boss_atlas:desc", boss.description)
        ifSetText("component.boss_atlas:kc", stat("Kill count", killCountText(boss)))
        ifSetText(
            "component.boss_atlas:pb",
            stat("Fastest kill", formatKillTime(stats.personalBestTicks(player, boss))),
        )
        ifSetText(
            "component.boss_atlas:loot",
            stat("Loot value", "${formatGp(stats.lootValue(player, boss))} gp"),
        )
        ifSetText("component.boss_atlas:req", stat("Requirement", requirementText(boss)))

        val dropsView = player.atlasDropsView
        ifSetHide("component.boss_atlas:info", hide = dropsView)
        ifSetHide(DROPS, hide = !dropsView)
        ifSetText("component.boss_atlas:tag", if (dropsView) drawDrops(boss) else tagText(boss))
        runClientScript(
            script("boss_atlas_buttons"),
            if (boss in favourites()) 1 else 0,
            if (dropsView) 1 else 0,
        )
    }

    private fun ProtectedAccess.drawDrops(boss: Boss): String {
        val items = drops.topDrops(boss, MAX_DROPS)
        runClientScript(script("boss_atlas_drops_clear"), component(DROPS))
        items.forEachIndexed { slot, item ->
            runClientScript(script("boss_atlas_drop"), component(DROPS), slot, item.objId, item.count)
        }
        return if (items.isEmpty()) {
            "<col=ef1020>No drop table data for this boss yet.</col>"
        } else {
            "<col=ff981f>Most valuable drops</col>"
        }
    }

    private fun ProtectedAccess.killCountText(boss: Boss): String =
        if (stats.hasKillCount(boss)) "%,d".format(stats.killCount(player, boss)) else "-"

    private fun ProtectedAccess.requirementText(boss: Boss): String =
        when (boss.requirement) {
            BossRequirement.None -> "None"
            is BossRequirement.Note -> boss.requirement.text
            is BossRequirement.Slayer -> {
                val colour = if (teleporter.meetsRequirement(player, boss)) "00ff00" else "ff0000"
                "<col=$colour>${boss.requirement.text}</col>"
            }
        }

    private fun tagText(boss: Boss): String {
        val status =
            if (boss.implemented) {
                "<col=00ff00>Available</col>"
            } else {
                "<col=ef1020>Not yet implemented</col>"
            }
        val instance = if (boss.instanceRow != null) " - Instanced" else ""
        return "${boss.category.label}$instance - $status"
    }

    private fun stat(label: String, value: String): String = "<col=ff981f>$label:</col> $value"

    private fun ProtectedAccess.selectedBoss(): Boss? = decodeFavourite(player.atlasSelected)

    private fun ProtectedAccess.favourites(): List<Boss> =
        FAVOURITE_SLOTS.mapNotNull { decodeFavourite(player.vars[it]) }.distinct()

    private fun ProtectedAccess.saveFavourites(favourites: List<Boss>) {
        FAVOURITE_SLOTS.forEachIndexed { index, varbit ->
            vars[varbit] = encodeFavourite(favourites.getOrNull(index))
        }
    }

    private fun script(name: String): Int = "clientscript.$name".asRSCM(RSCMType.CLIENTSCRIPT)

    private fun component(name: String): Int = name.asRSCM(RSCMType.COMPONENT)
}
