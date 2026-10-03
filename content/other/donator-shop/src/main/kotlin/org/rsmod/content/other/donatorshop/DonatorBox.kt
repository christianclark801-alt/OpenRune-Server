package org.rsmod.content.other.donatorshop

data class BoxReward(val obj: String, val min: Int = 1, val max: Int = min, val weight: Int)

private fun reward(obj: String, weight: Int, min: Int = 1, max: Int = min) =
    BoxReward("obj.$obj", min, max, weight)

enum class DonatorBox(
    val id: Int,
    val obj: String,
    val displayName: String,
    val price: Int,
    val description: String,
    val rewards: List<BoxReward>,
) {
    Bronze(
        id = 0,
        obj = "obj.donator_box_bronze",
        displayName = "Bronze Box",
        price = 5,
        description = "Coins, supplies and rune or dragon gear to kick-start an account.",
        rewards =
            listOf(
                reward("coins", 30, 1_000_000, 5_000_000),
                reward("cert_shark", 12, 100, 250),
                reward("cert_4doseprayerrestore", 10, 25, 75),
                reward("cert_4dose2restore", 8, 25, 50),
                reward("deathrune", 8, 500, 1_500),
                reward("bloodrune", 8, 500, 1_500),
                reward("rune_arrow", 6, 500, 1_000),
                reward("rune_platebody", 4),
                reward("rune_platelegs", 4),
                reward("rune_full_helm", 4),
                reward("rune_kiteshield", 4),
                reward("dragon_scimitar", 5),
                reward("dragon_dagger", 5),
                reward("dragon_longsword", 4),
                reward("amulet_of_glory_4", 4),
                reward("black_dragonhide_body", 4),
                reward("dragon_boots", 2),
                reward("abyssal_whip", 1),
            ),
    ),
    Silver(
        id = 1,
        obj = "obj.donator_box_silver",
        displayName = "Silver Box",
        price = 10,
        description = "Bigger coin stacks, dragon armour, Barrows pieces and a shot at a whip.",
        rewards =
            listOf(
                reward("coins", 25, 5_000_000, 15_000_000),
                reward("cert_anglerfish", 10, 100, 250),
                reward("cert_4dosepotionofsaradomin", 8, 30, 75),
                reward("cert_4dose2combat", 8, 25, 50),
                reward("cert_dragon_bones", 8, 100, 250),
                reward("dragon_arrow", 6, 250, 500),
                reward("dragon_med_helm", 5),
                reward("dragon_chainbody", 5),
                reward("dragon_platelegs", 5),
                reward("barrows_dharok_head", 3),
                reward("barrows_dharok_body", 3),
                reward("barrows_dharok_legs", 3),
                reward("barrows_karil_body", 3),
                reward("barrows_ahrim_body", 3),
                reward("dragon_boots", 4),
                reward("abyssal_whip", 4),
                reward("berzerker_ring", 3),
                reward("zenyte_amulet", 2),
            ),
    ),
    Gold(
        id = 2,
        obj = "obj.donator_box_gold",
        displayName = "Gold Box",
        price = 15,
        description = "God Wars armour, zenyte jewellery and top-tier weapons.",
        rewards =
            listOf(
                reward("coins", 25, 15_000_000, 30_000_000),
                reward("bandos_chestplate", 4),
                reward("bandos_skirt", 4),
                reward("armadyl_helmet", 4),
                reward("armadyl_chestplate", 4),
                reward("armadyl_skirt", 4),
                reward("abyssal_tentacle", 6),
                reward("toxic_tots_uncharged", 3),
                reward("dragonfire_shield", 5),
                reward("occult_necklace", 5),
                reward("zenyte_amulet_enchanted", 3),
                reward("zenyte_necklace_enchanted", 3),
                reward("zenyte_ring_enchanted", 3),
                reward("zenyte_bracelet_enchanted", 3),
                reward("bgs", 3),
                reward("toxic_blowpipe", 3),
                reward("primordial_boots", 2),
                reward("pegasian_boots", 2),
                reward("dragon_claws", 2),
                reward("ags", 1),
            ),
    ),
    Dragon(
        id = 3,
        obj = "obj.donator_box_dragon",
        displayName = "Dragon Box",
        price = 20,
        description = "End-game gear and a chance at the rarest items in the game.",
        rewards =
            listOf(
                reward("coins", 20, 30_000_000, 60_000_000),
                reward("ags", 8),
                reward("dragon_claws", 8),
                reward("toxic_blowpipe", 6),
                reward("primordial_boots", 6),
                reward("pegasian_boots", 6),
                reward("eternal_boots", 6),
                reward("dragon_warhammer", 6),
                reward("ancestral_hat", 3),
                reward("ancestral_robe_top", 3),
                reward("ancestral_robe_bottom", 3),
                reward("kodai_wand", 3),
                reward("elder_maul", 3),
                reward("ghrazi_rapier", 2),
                reward("sanguinesti_staff_uncharged", 2),
                reward("infernal_cape", 2),
                reward("elysian", 1),
                reward("scythe_of_vitur_uncharged", 1),
                reward("twisted_bow", 1),
            ),
    );

    val totalWeight: Int = rewards.sumOf { it.weight }

    fun rewardAt(roll: Int): BoxReward {
        var remaining = roll
        for (reward in rewards) {
            if (remaining < reward.weight) {
                return reward
            }
            remaining -= reward.weight
        }
        error("Roll $roll is outside $name's total weight $totalWeight.")
    }

    fun isRare(reward: BoxReward): Boolean = reward.weight * RARE_RATIO <= totalWeight

    fun chanceText(reward: BoxReward): String {
        val percent = reward.weight * 100.0 / totalWeight
        return if (percent < 1.0) "%.2f%%".format(percent) else "%.1f%%".format(percent)
    }

    companion object {
        const val MAX_REWARDS = 20
        private const val RARE_RATIO = 40

        fun forId(id: Int): DonatorBox? = entries.firstOrNull { it.id == id }

        fun forObj(obj: String): DonatorBox? = entries.firstOrNull { it.obj == obj }
    }
}
