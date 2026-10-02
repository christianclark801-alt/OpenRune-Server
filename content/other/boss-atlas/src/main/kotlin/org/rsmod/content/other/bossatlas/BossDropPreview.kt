package org.rsmod.content.other.bossatlas

import dev.openrune.ServerCacheManager
import dev.openrune.rscm.RSCM.asRSCM
import dev.openrune.rscm.RSCMType
import dtx.core.AllOf
import dtx.core.AnyOf
import dtx.core.Rollable
import dtx.core.Single
import dtx.impl.chance.ChanceRollable
import dtx.impl.weighted.WeightedRollable
import dtx.table.Table
import jakarta.inject.Inject
import jakarta.inject.Singleton
import java.util.IdentityHashMap
import org.rsmod.api.droptable.DropRollItem
import org.rsmod.api.droptable.DropTableRegistry
import org.rsmod.api.market.MarketPrices

class DropPreviewItem(val obj: String, val objId: Int, val count: Int, val unitPrice: Int)

@Singleton
class BossDropPreview
@Inject
constructor(private val registry: DropTableRegistry, private val prices: MarketPrices) {
    private val cache = HashMap<Boss, List<DropPreviewItem>>()

    fun topDrops(boss: Boss, limit: Int): List<DropPreviewItem> =
        cache.getOrPut(boss) { collect(boss) }.take(limit)

    private fun collect(boss: Boss): List<DropPreviewItem> {
        val table = boss.npcs.sorted().firstNotNullOfOrNull { registry.forNpcSymbol(it) } ?: return emptyList()
        val drops = LinkedHashMap<String, DropRollItem>()
        walk(table, drops, IdentityHashMap())
        return drops.values
            .mapNotNull { drop ->
                val id = runCatching { drop.obj.asRSCM(RSCMType.OBJ) }.getOrNull() ?: return@mapNotNull null
                val type = ServerCacheManager.getItem(id) ?: return@mapNotNull null
                DropPreviewItem(drop.obj, type.id, drop.count.last.coerceAtLeast(1), prices[type] ?: 0)
            }
            .sortedByDescending { it.unitPrice.toLong() * it.count }
    }

    private fun walk(
        rollable: Rollable<*, *>,
        drops: MutableMap<String, DropRollItem>,
        visited: IdentityHashMap<Rollable<*, *>, Unit>,
    ) {
        if (visited.put(rollable, Unit) != null) {
            return
        }
        when (rollable) {
            is Single<*, *> -> (rollable.result as? DropRollItem)?.let { add(it, drops) }
            is Table<*, *> -> rollable.tableEntries.forEach { walk(it, drops, visited) }
            is WeightedRollable<*, *> -> walk(rollable.rollable, drops, visited)
            is ChanceRollable<*, *> -> walk(rollable.rollable, drops, visited)
            is AnyOf<*, *> -> rollable.rollables.forEach { walk(it, drops, visited) }
            is AllOf<*, *> -> rollable.rollables.forEach { walk(it, drops, visited) }
        }
    }

    private fun add(drop: DropRollItem, drops: MutableMap<String, DropRollItem>) {
        if (!drop.isNothing) {
            drops.putIfAbsent(drop.obj, drop)
        }
        drop.bonusDrops.forEach { add(it, drops) }
    }
}
