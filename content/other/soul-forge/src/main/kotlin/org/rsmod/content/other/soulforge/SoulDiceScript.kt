package org.rsmod.content.other.soulforge

import dev.openrune.rscm.RSCM.asRSCM
import dev.openrune.rscm.RSCMType
import jakarta.inject.Inject
import org.rsmod.api.player.bonus.AttackSpeedModifiers
import org.rsmod.api.player.bonus.AttackSpeedStyle
import org.rsmod.api.player.output.mes
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.player.stat.StatLevelOffsets
import org.rsmod.api.player.stat.stat
import org.rsmod.api.player.stat.statAdd
import org.rsmod.api.player.stat.statBase
import org.rsmod.api.player.stat.statEffectiveBase
import org.rsmod.api.player.vars.boolVarBit
import org.rsmod.api.player.vars.intVarp
import org.rsmod.api.random.GameRandom
import org.rsmod.api.script.onIfModalButton
import org.rsmod.api.script.onOpLoc2
import org.rsmod.api.script.onPlayerLogin
import org.rsmod.game.entity.Player
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

private const val INTERFACE = "interface.soul_dice"
private const val ESSENCE = "component.soul_dice:essence"
private const val ROLL_INFO = "component.soul_dice:rollinfo"
private const val DIE = "component.soul_dice:die"
private const val ROLL = "component.soul_dice:roll"
private const val ROLL_COST = "component.soul_dice:rollcost"
private const val COMPLETE = "component.soul_dice:complete"
private const val STATUS = "component.soul_dice:status"

private const val ROLL_SYNTH = "synth.mizgog_beads"
private const val WIN_JINGLE = "jingle.dice_win"
private const val ROLL_DELAY = 5
private const val IDLE_FACE = 6

private const val STYLE_LOCKED = 0
private const val STYLE_AVAILABLE = 1
private const val STYLE_OWNED = 2
private const val STYLE_PARTIAL = 3

private val COMBAT_STATS =
    setOf(
        "stat.attack",
        "stat.strength",
        "stat.defence",
        "stat.ranged",
        "stat.magic",
        "stat.hitpoints",
    )

private var Player.soulDicePacked by intVarp("varp.soul_dice_perks")
private var Player.soulDiceRolling by boolVarBit("varbit.soul_dice_rolling")

internal var Player.soulDice: SoulDiceState
    get() = SoulDiceState(soulDicePacked)
    set(value) {
        soulDicePacked = value.packed
    }

class SoulDiceScript @Inject constructor(private val random: GameRandom) : PluginScript() {
    override fun ScriptContext.startup() {
        AttackSpeedModifiers.override = { player, style -> player.twoTickRate(style) }
        StatLevelOffsets.offset = { player, stat -> player.statOffset(stat) }

        onPlayerLogin { player.onLogin() }
        onOpLoc2(SOUL_FORGE) { openSoulDice() }
        onIfModalButton(ROLL) { roll() }
        for (perk in SoulPerk.entries) {
            if (perk.row != SoulRow.Starter) {
                onIfModalButton(tile(perk)) { buy(perk) }
            }
        }
    }

    private fun ProtectedAccess.openSoulDice() {
        ifOpenMainModal(INTERFACE)
        player.soulDiceRolling = false
        val last = SoulPerk.starters.lastOrNull { player.soulDice.has(it) }
        runClientScript(script("soul_dice_face"), component(DIE), last?.face ?: IDLE_FACE)
        val status =
            if (player.soulDice.freeRollAvailable) {
                "<col=00ff00>Your first roll is free!</col>"
            } else {
                "Bosses drop Soul Essence - spend it here on permanent perks."
            }
        ifSetText(STATUS, status)
        redraw()
    }

    private suspend fun ProtectedAccess.roll() {
        if (player.soulDiceRolling) {
            return
        }
        val state = player.soulDice
        val pool = state.rollPool
        if (pool.isEmpty()) {
            ifSetText(STATUS, "<col=00ff00>All Perks Unlocked.</col>")
            return
        }
        val cost = state.rollCost
        if (cost > 0 && invDel(player.inv, SOUL_ESSENCE, cost).failure) {
            ifSetText(STATUS, "<col=ff0000>You need $cost soul essence to roll the dice.</col>")
            return
        }
        val perk = pool[random.of(pool.size)]
        player.soulDice = state.withRollUsed().withLevel(perk, 1)
        player.soulDiceRolling = true

        drawEssence()
        ifSetText(STATUS, "The Soul Dice tumbles...")
        soundSynth(ROLL_SYNTH)
        runClientScript(script("soul_dice_roll"), component(DIE), perk.face)
        delay(ROLL_DELAY)

        player.soulDiceRolling = false
        if (perk == SoulPerk.CombatStats) {
            player.raiseToEffectiveLevels()
        }
        midiJingle(WIN_JINGLE)
        ifSetText(STATUS, "<col=00ff00>The Soul Dice grants you ${perk.label}!</col>")
        mes("<col=ff981f>Soul Dice:</col> you unlocked the permanent perk ${perk.label}.")
        redraw()
    }

    private fun ProtectedAccess.buy(perk: SoulPerk) {
        val state = player.soulDice
        if (!state.rowUnlocked(perk.row)) {
            ifSetText(STATUS, "<col=ff0000>${perk.row.requirement()}</col>")
            return
        }
        if (state.isMaxed(perk)) {
            ifSetText(STATUS, "${perk.label} is already fully unlocked.")
            return
        }
        if (invDel(player.inv, SOUL_ESSENCE, perk.cost).failure) {
            ifSetText(STATUS, "<col=ff0000>You need ${perk.cost} soul essence for that.</col>")
            return
        }
        val level = state.level(perk) + 1
        player.soulDice = state.withLevel(perk, level)
        val suffix = if (perk.maxLevel > 1) " (level $level/${perk.maxLevel})" else ""
        ifSetText(STATUS, "<col=00ff00>Unlocked ${perk.label}$suffix.</col>")
        mes("<col=ff981f>Soul Dice:</col> you unlocked ${perk.label}$suffix.")
        redraw()
    }

    private fun ProtectedAccess.redraw() {
        val state = player.soulDice
        drawEssence()
        drawDice(state)
        for (row in SoulRow.entries) {
            ifSetText(rowLabel(row), rowLabelText(state, row))
        }
        for (perk in SoulPerk.entries) {
            drawTile(state, perk)
        }
    }

    private fun ProtectedAccess.drawEssence() {
        val have = player.inv.count(SOUL_ESSENCE)
        ifSetText(ESSENCE, "Soul Essence: <col=ffffff>$have</col>")
    }

    private fun ProtectedAccess.drawDice(state: SoulDiceState) {
        val complete = state.starterComplete
        ifSetHide(DIE, complete)
        ifSetHide(ROLL, complete)
        ifSetHide(ROLL_INFO, complete)
        ifSetHide(ROLL_COST, complete)
        ifSetHide(COMPLETE, !complete)
        if (complete) {
            return
        }
        val remaining = state.rollPool.size
        ifSetText(
            ROLL_INFO,
            "Roll the Soul Dice to unlock a random starter perk.<br>" +
                "$remaining perk${if (remaining == 1) "" else "s"} left to roll. " +
                "You never roll the same perk twice.",
        )
        val cost =
            if (state.freeRollAvailable) {
                "<col=00ff00>Free roll available!</col>"
            } else {
                "Cost: ${SoulDiceState.ROLL_COST} soul essence"
            }
        ifSetText(ROLL_COST, cost)
    }

    private fun ProtectedAccess.drawTile(state: SoulDiceState, perk: SoulPerk) {
        val level = state.level(perk)
        val (text, style) =
            when {
                level >= perk.maxLevel && perk.maxLevel > 1 -> "Max level" to STYLE_OWNED
                level >= perk.maxLevel -> "Owned" to STYLE_OWNED
                !state.rowUnlocked(perk.row) -> "Locked" to STYLE_LOCKED
                perk.row == SoulRow.Starter -> "Roll to unlock" to STYLE_AVAILABLE
                perk.maxLevel == 1 -> "${perk.cost} essence" to STYLE_AVAILABLE
                level > 0 -> "Lv $level/${perk.maxLevel} - ${perk.cost} essence" to STYLE_PARTIAL
                else -> "Lv 0/${perk.maxLevel} - ${perk.cost} essence" to STYLE_AVAILABLE
            }
        runClientScript(
            script("soul_dice_tile"),
            component(tile(perk)),
            perk.label,
            text,
            perk.description,
            style,
        )
    }

    private fun rowLabelText(state: SoulDiceState, row: SoulRow): String {
        if (state.rowUnlocked(row)) {
            return row.label
        }
        return "${row.label} <col=9f9f9f>- ${row.requirement()}</col>"
    }

    private fun SoulRow.requirement(): String =
        when (this) {
            SoulRow.Starter -> ""
            SoulRow.BossSlayer -> "Requires all 5 starter perks"
            SoulRow.TrueHaste ->
                "Requires ${SoulDiceState.TRUE_HASTE_REQUIREMENT} Boss Slayer levels"
        }

    private fun Player.onLogin() {
        raiseToEffectiveLevels()
        if (soulDice.freeRollAvailable) {
            mes(
                "<col=ff981f>You have a free Soul Dice roll!</col> " +
                    "Use the Upgrades option on the Soul Forge to claim a permanent perk."
            )
        }
    }

    private fun Player.raiseToEffectiveLevels() {
        if (!soulDice.has(SoulPerk.CombatStats)) {
            return
        }
        for (type in COMBAT_STATS) {
            val current = stat(type)
            val target = statEffectiveBase(type)
            if (current >= statBase(type) && current < target) {
                statAdd(type, target - current, percent = 0)
            }
        }
    }

    private fun Player.twoTickRate(style: AttackSpeedStyle): Int? {
        val perk =
            when (style) {
                AttackSpeedStyle.Melee -> SoulPerk.TwoTickMelee
                AttackSpeedStyle.Ranged -> SoulPerk.TwoTickRange
                AttackSpeedStyle.Magic -> SoulPerk.TwoTickMagic
            }
        return if (soulDice.has(perk)) SoulDiceState.TWO_TICK_RATE else null
    }

    private fun Player.statOffset(stat: String): Int {
        if (stat !in COMBAT_STATS || !soulDice.has(SoulPerk.CombatStats)) {
            return 0
        }
        return SoulDiceState.STAT_BONUS
    }

    private val SoulPerk.face: Int
        get() = SoulPerk.starters.indexOf(this) + 1

    private fun tile(perk: SoulPerk): String = "component.soul_dice:tile${perk.ordinal}"

    private fun rowLabel(row: SoulRow): String = "component.soul_dice:row${row.ordinal + 1}label"

    private fun script(name: String): Int = "clientscript.$name".asRSCM(RSCMType.CLIENTSCRIPT)

    private fun component(name: String): Int = name.asRSCM(RSCMType.COMPONENT)
}
