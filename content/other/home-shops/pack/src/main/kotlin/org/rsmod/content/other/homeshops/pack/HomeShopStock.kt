package org.rsmod.content.other.homeshops.pack

internal enum class HomeShopFilter(val id: Int) {
    Supplies(1),
    Melee(2),
    RunesAmmo(3),
    RangedMagic(4),
}

internal data class HomeShopItem(val obj: String, val filter: HomeShopFilter)

private val METALS = listOf("bronze", "iron", "steel", "black", "mithril", "adamant", "rune", "dragon")
private val MELEE_PIECES =
    listOf("full_helm", "platebody", "platelegs", "kiteshield", "scimitar", "longsword", "2h_sword")

private fun meleeObj(metal: String, piece: String): String =
    if (metal == "dragon" && piece == "full_helm") "obj.brut_dragon_full_helm" else "obj.${metal}_$piece"

private fun items(filter: HomeShopFilter, vararg objs: String): List<HomeShopItem> =
    objs.map { HomeShopItem("obj.$it", filter) }

internal val HOME_SHOP_STOCK: List<HomeShopItem> =
    buildList {
        addAll(
            items(
                HomeShopFilter.Supplies,
                "mantaray",
                "anglerfish",
                "4doseprayerrestore",
                "4dose2strength",
                "4dose2attack",
                "4dose2defense",
            )
        )
        for (metal in METALS) {
            for (piece in MELEE_PIECES) {
                add(HomeShopItem(meleeObj(metal, piece), HomeShopFilter.Melee))
            }
        }
        addAll(
            items(
                HomeShopFilter.RunesAmmo,
                "airrune",
                "waterrune",
                "earthrune",
                "firerune",
                "mindrune",
                "bodyrune",
                "chaosrune",
                "deathrune",
                "bloodrune",
                "cosmicrune",
                "lawrune",
                "naturerune",
                "soulrune",
                "astralrune",
                "wrathrune",
                "bronze_arrow",
                "iron_arrow",
                "steel_arrow",
                "mithril_arrow",
                "adamant_arrow",
                "rune_arrow",
                "amethyst_arrow",
                "dragon_arrow",
                "bolt",
                "xbows_crossbow_bolts_iron",
                "xbows_crossbow_bolts_steel",
                "xbows_crossbow_bolts_mithril",
                "xbows_crossbow_bolts_adamantite",
                "xbows_crossbow_bolts_runite",
            )
        )
        addAll(
            items(
                HomeShopFilter.RangedMagic,
                "leather_cowl",
                "leather_armour",
                "leather_chaps",
                "leather_vambraces",
                "coif",
                "dragonhide_body",
                "dragonhide_chaps",
                "dragon_vambraces",
                "blue_dragonhide_body",
                "blue_dragonhide_chaps",
                "blue_dragon_vambraces",
                "red_dragonhide_body",
                "red_dragonhide_chaps",
                "red_dragon_vambraces",
                "black_dragonhide_body",
                "black_dragonhide_chaps",
                "black_dragon_vambraces",
                "shortbow",
                "oak_shortbow",
                "willow_shortbow",
                "maple_shortbow",
                "yew_shortbow",
                "magic_shortbow",
                "xbows_crossbow_bronze",
                "xbows_crossbow_iron",
                "xbows_crossbow_steel",
                "xbows_crossbow_mithril",
                "xbows_crossbow_adamantite",
                "xbows_crossbow_runite",
                "bluewizhat",
                "wizards_robe",
                "boots_wizard",
                "mystic_hat",
                "mystic_robe_top",
                "mystic_robe_bottom",
                "mystic_gloves",
                "mystic_boots",
                "staff_of_air",
                "staff_of_water",
                "staff_of_earth",
                "staff_of_fire",
                "mystic_air_staff",
                "mystic_water_staff",
                "mystic_earth_staff",
                "mystic_fire_staff",
                "amulet_of_magic",
            )
        )
    }
