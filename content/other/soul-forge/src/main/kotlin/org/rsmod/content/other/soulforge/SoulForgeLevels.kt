package org.rsmod.content.other.soulforge

import dev.openrune.types.ItemServerType
import org.rsmod.api.config.refs.params
import org.rsmod.api.player.bonus.ObjBonus

internal data class ForgeLevel(val cost: Int, val chancePercent: Int)

internal enum class ForgeStyle(val label: String, private val unit: String) {
    Melee("Strength", ""),
    Ranged("Ranged strength", ""),
    Magic("Magic damage", "%");

    fun format(amount: Int): String = "+$amount$unit"
}

internal object SoulForgeLevels {
    const val BONUS_PER_LEVEL = 2
    const val ESSENCE_PER_WELL = 5

    private const val LEVEL_SHIFT = 24
    private const val LEVEL_MASK = 0x7
    private const val MAGIC_DMG_SCALE = 10

    private val levels =
        listOf(
            ForgeLevel(cost = 5, chancePercent = 50),
            ForgeLevel(cost = 10, chancePercent = 40),
            ForgeLevel(cost = 15, chancePercent = 30),
            ForgeLevel(cost = 20, chancePercent = 20),
            ForgeLevel(cost = 25, chancePercent = 10),
        )

    val maxLevel: Int = levels.size

    fun next(current: Int): ForgeLevel? = levels.getOrNull(current)

    fun all(): List<ForgeLevel> = levels

    fun level(vars: Int): Int = (vars ushr LEVEL_SHIFT) and LEVEL_MASK

    fun withLevel(vars: Int, level: Int): Int =
        (vars and (LEVEL_MASK shl LEVEL_SHIFT).inv()) or ((level and LEVEL_MASK) shl LEVEL_SHIFT)

    fun bonusAmount(level: Int): Int = level * BONUS_PER_LEVEL

    fun styleOf(type: ItemServerType): ForgeStyle =
        styleOf(
            melee =
                maxOf(
                    type.param(params.attack_stab),
                    type.param(params.attack_slash),
                    type.param(params.attack_crush),
                ),
            ranged = type.param(params.attack_ranged),
            magic = type.param(params.attack_magic),
        )

    fun styleOf(melee: Int, ranged: Int, magic: Int): ForgeStyle =
        when {
            ranged > melee && ranged >= magic -> ForgeStyle.Ranged
            magic > melee && magic > ranged -> ForgeStyle.Magic
            else -> ForgeStyle.Melee
        }

    fun bonusFor(style: ForgeStyle, level: Int): ObjBonus? {
        if (level <= 0) {
            return null
        }
        val amount = bonusAmount(level)
        return when (style) {
            ForgeStyle.Melee -> ObjBonus(meleeStr = amount)
            ForgeStyle.Ranged -> ObjBonus(rangedStr = amount)
            ForgeStyle.Magic -> ObjBonus(magicDmg = amount * MAGIC_DMG_SCALE)
        }
    }
}
