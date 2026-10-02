package dtx.rs

import dtx.core.ArgMap
import dtx.core.RollResult
import dtx.impl.chance.RateBoosts
import dtx.impl.weighted.WeightedRollable
import dtx.impl.weighted.WeightedTable
import dtx.table.TableHooks
import kotlin.math.floor
import kotlin.random.Random

public class RSWeightedTable<T, R>(
    public override val tableIdentifier: String,
    public override val tableEntries: Collection<WeightedRollable<T, R>>,
    private val hooks: TableHooks<T, R> = TableHooks.Default(),
    public val inlineSeparateRolls: List<InlineSeparateRoll<T, R>> = emptyList(),
) : RSTable<T, R>, WeightedTable<T, R>, TableHooks<T, R> by hooks {

    override fun selectEntries(byTarget: T, otherArgs: ArgMap): List<RSWeightEntry<T, R>> = buildList {
        var total = 0

        tableEntries.forEach {
            if (it.includeInRoll(byTarget, otherArgs)) {
                val upper = total + it.weight
                val entry = RSWeightEntry(total, upper.toInt(), it.rollable, it.boosted)
                total = entry.rangeEnd
                add(entry)
            }
        }
    }

    public override val maxRoll: Double
        get() = tableEntries.maxOf { it.weight }

    override fun selectResult(target: T, otherArgs: ArgMap): RollResult<R> {
        val entries = selectEntries(target, otherArgs)

        if (tableEntries.isEmpty()) {
            return RollResult.Nothing()
        }

        val childArgs = RateBoosts.withRareScope(otherArgs, 1.0)

        if (tableEntries.size == 1) {
            return tableEntries.first().roll(target, childArgs)
        }

        val localMax = entries.maxOf { it.rangeEnd }

        val flagged =
            if (entries.any { it.boosted }) RateBoosts.multiplierFor(target, otherArgs) else 1.0
        val rare = RateBoosts.rareScopeOf(otherArgs)
        if (flagged != 1.0 || rare != 1.0) {
            val boosts = entries.map { boostFor(it, localMax, flagged, rare) }
            if (boosts.any { it != 1.0 }) {
                return selectBoosted(target, childArgs, entries, boosts, localMax)
            }
        }

        val baseRoll = Random.nextInt(0, localMax)
        val flatMod = rollModifier(target, 0.0)

        val roll = (baseRoll * flatMod).toInt()

        entries.forEach { entry ->
            if (entry checkWeight roll) {
                return entry.roll(target, childArgs)
            }
        }

        return RollResult.Nothing()
    }

    private fun boostFor(
        entry: RSWeightEntry<T, R>,
        total: Int,
        flagged: Double,
        rare: Double,
    ): Double =
        when {
            entry.boosted -> flagged * rare
            entry.weight / total < RateBoosts.RARE_SHARE -> rare
            else -> 1.0
        }

    private fun selectBoosted(
        target: T,
        childArgs: ArgMap,
        entries: List<RSWeightEntry<T, R>>,
        boosts: List<Double>,
        total: Int,
    ): RollResult<R> {
        val chances =
            entries.mapIndexed { index, entry ->
                val boost = boosts[index]
                if (boost == 1.0) {
                    0.0
                } else {
                    val boostedWeight = floor(total / (entry.weight * boost).coerceAtLeast(MIN_WEIGHT))
                    1.0 / boostedWeight.coerceAtLeast(1.0)
                }
            }
        val boostedSum = chances.sum()
        val scale = if (boostedSum > 1.0) 1.0 / boostedSum else 1.0

        val roll = Random.nextDouble()
        var cumulative = 0.0
        for (index in entries.indices) {
            if (chances[index] == 0.0) continue
            cumulative += chances[index] * scale
            if (roll < cumulative) {
                return entries[index].roll(target, childArgs)
            }
        }

        val rest = entries.filterIndexed { index, _ -> chances[index] == 0.0 }
        val restTotal = rest.sumOf { it.rangeEnd - it.rangeStart }
        if (restTotal <= 0) {
            return RollResult.Nothing()
        }
        var pick = Random.nextInt(restTotal)
        for (entry in rest) {
            pick -= entry.rangeEnd - entry.rangeStart
            if (pick < 0) {
                return entry.roll(target, childArgs)
            }
        }
        return RollResult.Nothing()
    }

    public companion object {
        private const val MIN_WEIGHT = 0.0001
        private val EmptyTable = RSWeightedTable<Any?, Any?>("", emptyList())

        @Suppress("UNCHECKED_CAST")
        public fun <T, R> Empty(): RSWeightedTable<T, R> = EmptyTable as RSWeightedTable<T, R>
    }
}
