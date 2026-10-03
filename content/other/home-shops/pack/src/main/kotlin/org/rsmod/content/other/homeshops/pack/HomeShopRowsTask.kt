package org.rsmod.content.other.homeshops.pack

import dev.openrune.OsrsCacheProvider
import dev.openrune.cache.DBROW
import dev.openrune.cache.tools.TaskPriority
import dev.openrune.cache.tools.tasks.CacheTask
import dev.openrune.definition.codec.DBRowCodec
import dev.openrune.definition.type.DBRowType
import dev.openrune.definition.type.ItemType
import dev.openrune.filesystem.Cache
import dev.openrune.rscm.RSCM
import io.netty.buffer.Unpooled

/**
 * Appends the home shops to Jagex's omnishop tables. Packing them through `dbTable` would rewrite
 * the whole table and its index, dropping every official shop row, so the rows are written straight
 * into the dbrow archive instead. Column type ids are copied from the official Boat Emporium rows,
 * which also proves the column ids still line up with the cache.
 */
class HomeShopRowsTask : CacheTask() {
    override val priority: TaskPriority
        get() = TaskPriority.END

    override fun init(cache: Cache) {
        val rows = mutableMapOf<Int, DBRowType>()
        val items = mutableMapOf<Int, ItemType>()
        OsrsCacheProvider.DBRowDecoder().load(cache, rows)
        OsrsCacheProvider.ItemDecoder(revision).load(cache, items)

        val shopTypes = columnTypes(rows, REFERENCE_SHOP, SHOP_COLUMNS)
        val stockTypes = columnTypes(rows, REFERENCE_STOCK, STOCK_COLUMNS)
        val shopTable = RSCM.getRSCM("dbtable.omnishop_shop_data")
        val stockTable = RSCM.getRSCM("dbtable.omnishop_stock_data")
        val coins = RSCM.getRSCM("dbrow.currency_coins")

        val stockRows =
            HOME_SHOP_STOCK.mapIndexed { index, item ->
                val rowId = RSCM.getRSCM("dbrow.home_shop_stock_$index")
                val obj = RSCM.getRSCM(item.obj)
                val price = (items[obj]?.cost ?: 1).coerceAtLeast(1)
                val columns =
                    mapOf(
                        STOCK_OBJ to arrayOf<Any>(obj),
                        STOCK_FILTER to arrayOf<Any>(item.filter.id),
                        STOCK_COST to arrayOf<Any>(coins, price),
                        STOCK_SHOW_UNLIMITED to arrayOf<Any>(1),
                    )
                write(cache, row(rowId, stockTable, columns, stockTypes))
                rowId
            }

        for (shop in HomeShop.entries) {
            val columns =
                mapOf(
                    SHOP_NAME to arrayOf<Any>(shop.title),
                    SHOP_CURRENCY to arrayOf<Any>(coins),
                    SHOP_FILTER_TITLES to arrayOf<Any>(RSCM.getRSCM("enum.home_shop_filters")),
                    SHOP_STOCK to stockRows.toTypedArray<Any>(),
                    SHOP_INFO_TITLE to arrayOf<Any>("Welcome to the ${shop.title}."),
                    SHOP_INFO_INSTRUCTIONS to arrayOf<Any>(shop.instructions),
                    SHOP_MAIN_OP to arrayOf<Any>("Buy"),
                    SHOP_ALLOW_SELLING to arrayOf<Any>(0),
                )
            write(cache, row(RSCM.getRSCM(shop.row), shopTable, columns, shopTypes))
        }
    }

    private fun columnTypes(rows: Map<Int, DBRowType>, reference: String, columns: List<Int>): Map<Int, IntArray> {
        val row = rows[RSCM.getRSCM(reference)] ?: error("Missing omnishop reference row $reference")
        return columns.associateWith { column ->
            row.field5306?.getOrNull(column) ?: error("$reference has no column $column; omnishop layout changed")
        }
    }

    private fun row(id: Int, table: Int, columns: Map<Int, Array<Any>>, types: Map<Int, IntArray>): DBRowType {
        val row = DBRowType(id)
        row.tableId = table
        row.ensureColumnStorage(columns.keys.max() + 1)
        for ((column, values) in columns) {
            row.field5306!![column] = types.getValue(column)
            row.columnTypes!![column] = Array(values.size) { values[it] }
        }
        return row
    }

    private fun write(cache: Cache, row: DBRowType) {
        val buffer = Unpooled.buffer()
        with(codec) { buffer.encode(row) }
        val bytes = ByteArray(buffer.readableBytes()).also(buffer::readBytes)
        cache.write(CONFIG_INDEX, DBROW, row.id, bytes)
    }

    private enum class HomeShop(val row: String, val title: String, val instructions: String) {
        Ironman(
            "dbrow.home_ironman_shop",
            "Ironman Store",
            "Supplies for those who stand alone. Only Ironmen may trade here.",
        ),
        General(
            "dbrow.home_general_shop",
            "General Store",
            "Supplies for every adventurer. Ironmen must use the Ironman Store instead.",
        ),
    }

    private companion object {
        val codec = DBRowCodec()

        const val CONFIG_INDEX = 2
        const val REFERENCE_SHOP = "dbrow.sailing_boat_shop"
        const val REFERENCE_STOCK = "dbrow.sailing_ship_stock_raft"

        const val SHOP_NAME = 0
        const val SHOP_CURRENCY = 2
        const val SHOP_FILTER_TITLES = 3
        const val SHOP_STOCK = 5
        const val SHOP_INFO_TITLE = 10
        const val SHOP_INFO_INSTRUCTIONS = 12
        const val SHOP_MAIN_OP = 13
        const val SHOP_ALLOW_SELLING = 16
        val SHOP_COLUMNS =
            listOf(
                SHOP_NAME,
                SHOP_CURRENCY,
                SHOP_FILTER_TITLES,
                SHOP_STOCK,
                SHOP_INFO_TITLE,
                SHOP_INFO_INSTRUCTIONS,
                SHOP_MAIN_OP,
                SHOP_ALLOW_SELLING,
            )

        const val STOCK_OBJ = 0
        const val STOCK_FILTER = 6
        const val STOCK_COST = 7
        const val STOCK_SHOW_UNLIMITED = 17
        val STOCK_COLUMNS = listOf(STOCK_OBJ, STOCK_FILTER, STOCK_COST, STOCK_SHOW_UNLIMITED)
    }
}
