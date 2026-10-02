package dtx.rs

import dtx.core.ArgMap
import dtx.core.RollResult
import dtx.core.Rollable
import dtx.core.flattenToList
import dtx.impl.chance.RateBoosts
import dtx.table.TableHooks

public class RSDropTable<T, R>(
    public override val tableIdentifier: String,
    public val npcs: List<String> = emptyList(),
    public val locs: List<String> = emptyList(),
    public val areas: List<String> = emptyList(),
    private val guaranteed: RSTable<T, R> = RSGuaranteedTable.Empty(),
    private val preRoll: RSTable<T, R> = RSPreRollTable.Empty(),
    separateRolls: RSTable<T, R> = RSPreRollTable.Empty(),
    private val mainTable: RSTable<T, R> = RSWeightedTable.Empty(),
    private val tertiaries: RSTable<T, R> = RSPreRollTable.Empty(),
    private val hooks: TableHooks<T, R> = TableHooks.Default(),
    public val mainRolls: Int = 1,
) : RSTable<T, R>, TableHooks<T, R> by hooks {

    private val separateRolls: RSTable<T, R> = mergeInlineSeparateRolls(separateRolls, mainTable)

    override val tableEntries: Collection<Rollable<T, R>> =
        listOf(guaranteed, preRoll, separateRolls, mainTable, tertiaries)

    override fun selectResult(target: T, otherArgs: ArgMap): RollResult<R> {
        val rare = otherArgs[RateBoosts.rareScope] ?: RateBoosts.rareMultiplierFor(target, otherArgs)
        val unboosted = RateBoosts.withRareScope(otherArgs, 1.0)
        val boosted = RateBoosts.withRareScope(otherArgs, rare)

        val results = mutableListOf<RollResult<R>>()
        results.add(guaranteed.roll(target, unboosted))
        results.add(preRoll.roll(target, boosted))
        results.add(separateRolls.roll(target, boosted))
        repeat(mainRolls) { results.add(mainTable.roll(target, boosted)) }
        results.add(tertiaries.roll(target, boosted))

        return results.flattenToList()
    }
}
