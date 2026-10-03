package org.rsmod.content.other.soulforge

import com.github.michaelbull.logging.InlineLogger
import dev.openrune.ServerCacheManager
import dev.openrune.definition.type.widget.IfEvent
import dev.openrune.rscm.RSCM.asRSCM
import dev.openrune.rscm.RSCMType
import dev.openrune.types.ItemServerType
import dev.openrune.types.aconverted.SpotanimType
import dev.or2.central.account.Rights
import jakarta.inject.Inject
import org.rsmod.api.player.bonus.WornBonusModifiers
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.player.vars.intVarBit
import org.rsmod.api.random.GameRandom
import org.rsmod.api.repo.loc.LocRepository
import org.rsmod.api.repo.world.WorldRepository
import org.rsmod.api.script.onGameStartup
import org.rsmod.api.script.onIfModalButton
import org.rsmod.api.script.onOpLoc1
import org.rsmod.api.script.onOpLoc3
import org.rsmod.game.entity.Player
import org.rsmod.game.inv.InvObj
import org.rsmod.game.loc.BoundLocInfo
import org.rsmod.game.loc.LocAngle
import org.rsmod.game.loc.LocInfo
import org.rsmod.game.loc.LocShape
import org.rsmod.game.queue.WorldQueueList
import org.rsmod.game.type.getInvObj
import org.rsmod.map.CoordGrid
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

internal const val SOUL_FORGE = "loc.raids_tekton_anvil"
private const val SOUL_SPOTANIM = "spotanim.whisperer_impact_soul_spotanim"
private const val SMOKE_SPOTANIM = "spotanim.smokepuff_large"

private const val INTERFACE = "interface.soul_forge"
private const val EQUIPMENT = "component.soul_forge:equipment"
private const val FORGE_BUTTON = "component.soul_forge:forge"
private const val ITEM_ICON = "component.soul_forge:itemicon"
private const val ITEM_NAME = "component.soul_forge:itemname"
private const val ITEM_LEVEL = "component.soul_forge:itemlevel"
private const val ITEM_BONUS = "component.soul_forge:itembonus"
private const val ESSENCE = "component.soul_forge:essence"
private const val ESSENCE_COST = "component.soul_forge:essencecost"
private const val ESSENCE_HAVE = "component.soul_forge:essencehave"
private const val CHANCE = "component.soul_forge:chance"
private const val NEXT_BONUS = "component.soul_forge:nextbonus"
private const val STATUS = "component.soul_forge:status"

private val FORGE_COORDS = CoordGrid(3790, 2561, 0)

private const val AMBIENT_INTERVAL = 3
private const val SMOKE_EVERY = 2
private const val SOUL_HEIGHT = 120
private const val SMOKE_HEIGHT = 40

private const val NO_SLOT = -1
private const val WELL_COUNT = 5

/** Worn slots in the order the equipment strip draws them; must match `soul_forge_worn_slot`. */
private val WORN_ORDER = intArrayOf(0, 1, 2, 13, 3, 4, 5, 7, 9, 10, 12)

private var Player.forgeSlotVar by intVarBit("varbit.soul_forge_slot")

private var Player.forgeSlot: Int
    get() = forgeSlotVar - 1
    set(value) {
        forgeSlotVar = value + 1
    }

class SoulForgeScript
@Inject
constructor(
    private val locRepo: LocRepository,
    private val worldRepo: WorldRepository,
    private val worldQueues: WorldQueueList,
    private val random: GameRandom,
) : PluginScript() {
    private val logger = InlineLogger()

    private var forge: LocInfo? = null
    private var ambientCycle = 0

    private val soulSpotanim by lazy { SpotanimType(SOUL_SPOTANIM.asRSCM(RSCMType.SPOTANIM)) }
    private val smokeSpotanim by lazy { SpotanimType(SMOKE_SPOTANIM.asRSCM(RSCMType.SPOTANIM)) }

    override fun ScriptContext.startup() {
        WornBonusModifiers.perObj = { obj, type ->
            if (HolyWaterForge.isHolyWater(type)) {
                null
            } else {
                SoulForgeLevels.bonusFor(
                    SoulForgeLevels.styleOf(type),
                    SoulForgeLevels.level(obj.vars),
                )
            }
        }

        onGameStartup { spawnForge() }

        onOpLoc1(SOUL_FORGE) { openForge() }
        onOpLoc3(SOUL_FORGE) { destroy(it.loc) }

        onIfModalButton(EQUIPMENT) { select(it.comsub) }
        onIfModalButton(FORGE_BUTTON) { attemptForge() }
    }

    private fun ProtectedAccess.openForge() {
        ifOpenMainModal(INTERFACE)
        ifSetEvents(EQUIPMENT, WORN_ORDER.indices, IfEvent.Op1)
        player.forgeSlot = NO_SLOT
        redraw()
    }

    private fun ProtectedAccess.select(index: Int) {
        val slot = WORN_ORDER.getOrNull(index) ?: return
        val obj = player.worn[slot] ?: return
        if (!getInvObj(obj).isForgeable()) {
            ifSetText(STATUS, "<col=ff0000>That item cannot be forged.</col>")
            return
        }
        player.forgeSlot = slot
        ifSetText(STATUS, "Press Forge to sacrifice soul essence.")
        redraw()
    }

    private fun ProtectedAccess.attemptForge() {
        val slot = player.forgeSlot
        val obj = if (slot == NO_SLOT) null else player.worn[slot]
        if (obj == null) {
            ifSetText(STATUS, "<col=ff0000>Select a worn item first.</col>")
            return
        }
        val type = getInvObj(obj)
        if (HolyWaterForge.isHolyWater(type)) {
            forgeHolyWater(slot, obj, type)
            redraw()
            return
        }
        val level = SoulForgeLevels.level(obj.vars)
        val next = SoulForgeLevels.next(level)
        if (next == null) {
            ifSetText(STATUS, "<col=ff0000>${type.name} is already fully forged.</col>")
            return
        }
        if (invDel(player.inv, SOUL_ESSENCE, next.cost).failure) {
            ifSetText(STATUS, "<col=ff0000>You need ${next.cost} soul essence for this.</col>")
            return
        }
        if (random.of(100) < next.chancePercent) {
            val newLevel = level + 1
            player.worn[slot] = obj.copy(vars = SoulForgeLevels.withLevel(obj.vars, newLevel))
            ifSetText(STATUS, "<col=00ff00>Success! ${type.name} is now +$newLevel.</col>")
            mes("<col=00ff00>The Soul Forge empowers your ${type.name} to +$newLevel.</col>")
        } else {
            ifSetText(STATUS, "<col=ff0000>The souls resist. ${type.name} stays +$level.</col>")
            mes("<col=ff0000>The forge fails and the soul essence is lost.</col>")
        }
        redraw()
    }

    private fun ProtectedAccess.forgeHolyWater(slot: Int, obj: InvObj, type: ItemServerType) {
        val tier = HolyWaterForge.tier(obj)
        if (tier >= HolyWaterForge.MAX_TIER) {
            ifSetText(STATUS, "<col=ff0000>${type.name} is already fully forged.</col>")
            return
        }
        if (invDel(player.inv, SOUL_ESSENCE, HolyWaterForge.COST).failure) {
            ifSetText(
                STATUS,
                "<col=ff0000>You need ${HolyWaterForge.COST} soul essence for this.</col>",
            )
            return
        }
        val newTier = tier + 1
        player.worn[slot] = obj.copy(vars = SoulForgeLevels.withLevel(obj.vars, newTier))
        ifSetText(STATUS, "<col=00ff00>Success! ${type.name} is now +$newTier.</col>")
        mes("<col=00ff00>The Soul Forge empowers your ${type.name} to +$newTier.</col>")
    }

    private fun ProtectedAccess.redraw() {
        val slot = player.forgeSlot
        val obj = if (slot == NO_SLOT) null else player.worn[slot]
        runClientScript(script("soul_forge_equipment"), component(EQUIPMENT), slot)

        val have = player.inv.count(SOUL_ESSENCE)
        if (obj == null) {
            drawEmpty(have)
            return
        }
        val type = getInvObj(obj)
        if (HolyWaterForge.isHolyWater(type)) {
            drawHolyWater(obj, type, have)
            return
        }
        val level = SoulForgeLevels.level(obj.vars)
        val style = SoulForgeLevels.styleOf(type)
        val next = SoulForgeLevels.next(level)

        ifSetText(ITEM_NAME, type.name)
        ifSetText(ITEM_LEVEL, "Forge level: +$level")
        ifSetText(ITEM_BONUS, "${style.label} ${style.format(SoulForgeLevels.bonusAmount(level))}")

        if (next == null) {
            ifSetText(ESSENCE_COST, "Fully forged")
            ifSetText(ESSENCE_HAVE, "You have: $have")
            ifSetText(CHANCE, "MAX")
            ifSetText(NEXT_BONUS, "This item cannot be forged any further.")
            drawIcons(obj, WELL_COUNT)
            return
        }
        val haveColour = if (have >= next.cost) "ffffff" else "ff0000"
        ifSetText(ESSENCE_COST, "Cost: ${next.cost} soul essence")
        ifSetText(ESSENCE_HAVE, "You have: <col=$haveColour>$have</col>")
        ifSetText(CHANCE, "${next.chancePercent}%")
        ifSetText(
            NEXT_BONUS,
            "Next: +${level + 1}<br>${style.label} " +
                style.format(SoulForgeLevels.bonusAmount(level + 1)),
        )
        drawIcons(obj, next.cost / SoulForgeLevels.ESSENCE_PER_WELL)
    }

    private fun ProtectedAccess.drawHolyWater(obj: InvObj, type: ItemServerType, have: Int) {
        val tier = HolyWaterForge.tier(obj)
        ifSetText(ITEM_NAME, type.name)
        ifSetText(ITEM_LEVEL, "Forge level: +$tier")
        ifSetText(ITEM_BONUS, HolyWaterForge.describe(tier))

        if (tier >= HolyWaterForge.MAX_TIER) {
            ifSetText(ESSENCE_COST, "Fully forged")
            ifSetText(ESSENCE_HAVE, "You have: $have")
            ifSetText(CHANCE, "MAX")
            ifSetText(NEXT_BONUS, "This item cannot be forged any further.")
            drawIcons(obj, WELL_COUNT)
            return
        }
        val haveColour = if (have >= HolyWaterForge.COST) "ffffff" else "ff0000"
        ifSetText(ESSENCE_COST, "Cost: ${HolyWaterForge.COST} soul essence")
        ifSetText(ESSENCE_HAVE, "You have: <col=$haveColour>$have</col>")
        ifSetText(CHANCE, "${HolyWaterForge.CHANCE}%")
        ifSetText(NEXT_BONUS, "Next: +${tier + 1}<br>${HolyWaterForge.describe(tier + 1)}")
        drawIcons(obj, WELL_COUNT)
    }

    private fun ProtectedAccess.drawEmpty(have: Int) {
        ifSetText(ITEM_NAME, "None selected")
        ifSetText(ITEM_LEVEL, "")
        ifSetText(ITEM_BONUS, "")
        ifSetText(ESSENCE_COST, "")
        ifSetText(ESSENCE_HAVE, "You have: $have")
        ifSetText(CHANCE, "-")
        ifSetText(NEXT_BONUS, "Pick an item from your equipment above.")
        drawIcons(null, 0)
    }

    private fun ProtectedAccess.drawIcons(obj: InvObj?, litWells: Int) {
        runClientScript(
            script("soul_forge_update"),
            component(ITEM_ICON),
            obj?.id ?: -1,
            component(ESSENCE),
            SOUL_ESSENCE.asRSCM(RSCMType.OBJ),
            litWells,
        )
    }

    private fun ItemServerType.isForgeable(): Boolean =
        !isStackable || HolyWaterForge.isHolyWater(this)

    private fun spawnForge() {
        runCatching {
            val loc =
                locRepo.add(
                    FORGE_COORDS,
                    SOUL_FORGE,
                    Int.MAX_VALUE,
                    LocAngle.East,
                    LocShape.CentrepieceStraight,
                )
            forge = loc
            scheduleAmbient(loc.centre())
        }.onFailure { logger.warn(it) { "Unable to spawn the Soul Forge; run buildCache." } }
    }

    private fun scheduleAmbient(centre: CoordGrid) {
        worldQueues.add(AMBIENT_INTERVAL) {
            if (forge == null) {
                return@add
            }
            worldRepo.spotanimMap(soulSpotanim, centre, SOUL_HEIGHT)
            if (ambientCycle++ % SMOKE_EVERY == 0) {
                worldRepo.spotanimMap(smokeSpotanim, centre, SMOKE_HEIGHT)
            }
            scheduleAmbient(centre)
        }
    }

    private suspend fun ProtectedAccess.destroy(loc: BoundLocInfo) {
        if (!player.modLevel.isAtLeast(Rights.ADMINISTRATOR)) {
            mes("Only the owner can destroy this table.")
            return
        }
        val confirmed = choice2("Yes", true, "No", false, title = "Destroy the Soul Forge?")
        if (!confirmed) {
            return
        }
        locRepo.del(loc, Int.MAX_VALUE)
        forge = null
        mes("The Soul Forge collapses into ash.")
    }

    private fun LocInfo.centre(): CoordGrid {
        val type = ServerCacheManager.getObject(id) ?: return coords
        return coords.translate(type.width / 2, type.length / 2)
    }

    private fun script(name: String): Int = "clientscript.$name".asRSCM(RSCMType.CLIENTSCRIPT)

    private fun component(name: String): Int = name.asRSCM(RSCMType.COMPONENT)
}
