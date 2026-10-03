package org.rsmod.content.other.bossatlas

import org.rsmod.map.CoordGrid

enum class BossCategory(val label: String) {
    Easy("Easy"),
    Mid("Mid"),
    Hard("Hard"),
    GodWars("God Wars"),
    Wilderness("Wilderness"),
    EndGame("Raids & End-game"),
}

sealed interface BossRequirement {
    val text: String

    data object None : BossRequirement {
        override val text: String = "None"
    }

    data class Slayer(val level: Int) : BossRequirement {
        override val text: String = "$level Slayer"
    }

    data class Note(override val text: String) : BossRequirement
}

class KillSource(val varp: String, val npcs: Set<String>)

private fun kills(varp: String, vararg npcs: String): List<KillSource> =
    listOf(KillSource(varp, npcs.toSet()))

/**
 * Every boss listed in the atlas. The ordinal is the boss id stored in player varbits
 * (favourites, last teleport), so entries must only ever be appended, never reordered or removed.
 */
enum class Boss(
    val key: String,
    val displayName: String,
    val category: BossCategory,
    val combatLevel: Int,
    val icon: String,
    val gear: String,
    val description: String,
    val coords: CoordGrid,
    val kills: List<KillSource> = emptyList(),
    val requirement: BossRequirement = BossRequirement.None,
    val instanceRow: String? = null,
    val implemented: Boolean = false,
) {
    Zulrah(
        key = "zulrah",
        displayName = "Zulrah",
        category = BossCategory.Mid,
        combatLevel = 725,
        icon = "obj.snakepet",
        gear = "obj.toxic_blowpipe",
        description = "A serpent that cycles between ranged, magic and melee forms, " +
            "leaving venom clouds and snakelings. Learn the rotations.",
        coords = CoordGrid(2200, 3055, 0),
        kills = kills(
            "varp.total_snakeboss_kills",
            "npc.snakeboss_boss_ranged",
            "npc.snakeboss_boss_melee",
            "npc.snakeboss_boss_magic",
        ),
    ),
    Vorkath(
        key = "vorkath",
        displayName = "Vorkath",
        category = BossCategory.Hard,
        combatLevel = 732,
        icon = "obj.vorkathpet",
        gear = "obj.dragonhunter_xbow",
        description = "An undead dragon with dragonfire, acid pools and a zombified " +
            "spawn. Bring anti-dragon protection and anti-venom.",
        coords = CoordGrid(2640, 3697, 0),
        kills = kills("varp.total_vorkath_kills", "npc.vorkath"),
    ),
    Cerberus(
        key = "cerberus",
        displayName = "Cerberus",
        category = BossCategory.Mid,
        combatLevel = 318,
        icon = "obj.hell_pet",
        gear = "obj.4doseprayerrestore",
        description = "The guardian of the River of Souls. Pray against her summoned " +
            "souls in order and dodge the lava pools.",
        coords = CoordGrid(2873, 9847, 0),
        kills = kills(
            "varp.total_cerberus_kills",
            "npc.cerberus_attacking",
            "npc.cerberus_resetting",
            "npc.cerberus_sitting",
        ),
        requirement = BossRequirement.Slayer(91),
    ),
    AbyssalSire(
        key = "sire",
        displayName = "Abyssal Sire",
        category = BossCategory.Mid,
        combatLevel = 350,
        icon = "obj.abyssalsire_pet",
        gear = "obj.abyssal_bludgeon",
        description = "Disorient the Sire, then survive its spawns, tentacles and the " +
            "deadly explosion phase in the Abyssal Nexus.",
        coords = CoordGrid(3039, 4768, 0),
        kills = kills(
            "varp.total_abyssalsire_kills",
            "npc.abyssalsire_sire_stasis_sleeping",
            "npc.abyssalsire_sire_stasis_awake",
            "npc.abyssalsire_sire_stasis_stunned",
            "npc.abyssalsire_sire_puppet",
            "npc.abyssalsire_sire_wandering",
            "npc.abyssalsire_sire_panicking",
            "npc.abyssalsire_sire_apocalypse",
        ),
        requirement = BossRequirement.Slayer(85),
    ),
    AlchemicalHydra(
        key = "hydra",
        displayName = "Alchemical Hydra",
        category = BossCategory.Hard,
        combatLevel = 426,
        icon = "obj.hydrapet",
        gear = "obj.dragonhunter_lance",
        description = "A four-phase hydra. Lure it through the coloured vents to strip " +
            "its armour and swap prayers on every attack switch.",
        coords = CoordGrid(1311, 3807, 0),
        kills = kills(
            "varp.total_hydraboss_kills",
            "npc.hydraboss",
            "npc.hydraboss_finaldeath",
        ),
        requirement = BossRequirement.Slayer(95),
    ),
    Kraken(
        key = "kraken",
        displayName = "Kraken",
        category = BossCategory.Mid,
        combatLevel = 291,
        icon = "obj.krakenpet",
        gear = "obj.toxic_tots_charged",
        description = "Wake the four tentacles, then the Kraken itself. A slow, safe " +
            "magic fight in a private cove.",
        coords = CoordGrid(2278, 3611, 0),
        kills = kills("varp.total_kraken_boss_kills", "npc.slayer_kraken_boss"),
        requirement = BossRequirement.Slayer(87),
    ),
    ThermonuclearSmokeDevil(
        key = "thermy",
        displayName = "Thermonuclear Smoke Devil",
        category = BossCategory.Mid,
        combatLevel = 301,
        icon = "obj.smokepet",
        gear = "obj.slayer_helm",
        description = "A smoke devil boss with fast magic attacks. A facemask or slayer " +
            "helm is required in the smoke dungeon.",
        coords = CoordGrid(2411, 3061, 0),
        kills = kills("varp.total_thermy_kills", "npc.smoke_devil_boss"),
        requirement = BossRequirement.Slayer(93),
    ),
    CorporealBeast(
        key = "corp",
        displayName = "Corporeal Beast",
        category = BossCategory.Hard,
        combatLevel = 785,
        icon = "obj.corppet",
        gear = "obj.dragon_warhammer",
        description = "A spirit that only takes full damage from spears and halberds. " +
            "Kill the dark energy core quickly when it spawns.",
        coords = CoordGrid(2966, 4383, 2),
        kills = kills("varp.total_corp_kills", "npc.corp_beast"),
    ),
    DagannothKings(
        key = "dks",
        displayName = "Dagannoth Kings",
        category = BossCategory.Mid,
        combatLevel = 303,
        icon = "obj.rexpet",
        gear = "obj.twisted_bow",
        description = "Rex, Prime and Supreme: one king for each combat style. Tank or " +
            "trap them in the Waterbirth Island lair.",
        coords = CoordGrid(2900, 4449, 0),
        kills = listOf(
            KillSource("varp.total_rex_kills", setOf("npc.dagcave_melee_boss")),
            KillSource("varp.total_prime_kills", setOf("npc.dagcave_magic_boss")),
            KillSource("varp.total_supreme_kills", setOf("npc.dagcave_ranged_boss")),
        ),
    ),
    GiantMole(
        key = "mole",
        displayName = "Giant Mole",
        category = BossCategory.Easy,
        combatLevel = 230,
        icon = "obj.molepet",
        gear = "obj.dragon_scimitar",
        description = "Burrows away at low health. Bring a light source and chase it " +
            "through the tunnels under Falador Park.",
        coords = CoordGrid(2995, 3377, 0),
        kills = kills("varp.total_mole_kills", "npc.mole_giant"),
    ),
    KalphiteQueen(
        key = "kq",
        displayName = "Kalphite Queen",
        category = BossCategory.Mid,
        combatLevel = 333,
        icon = "obj.kqpet_walking",
        gear = "obj.4doseantipoison",
        description = "Two forms: the first resists magic and ranged, the second " +
            "resists melee. Watch the bouncing lightning.",
        coords = CoordGrid(3227, 3107, 0),
        kills = kills("varp.total_kalphite_kills", "npc.kalphite_flyingqueen"),
    ),
    KingBlackDragon(
        key = "kbd",
        displayName = "King Black Dragon",
        category = BossCategory.Easy,
        combatLevel = 276,
        icon = "obj.kbdpet",
        gear = "obj.antidragonbreathshield",
        description = "A three-headed dragon with poison, ice and shock breath. An " +
            "anti-dragon shield is essential. Lair is in the Wilderness.",
        coords = CoordGrid(3067, 10254, 0),
        kills = kills("varp.total_kbd_kills", "npc.king_dragon"),
        instanceRow = "dbrow.instance_kbd",
        implemented = true,
    ),
    Sarachnis(
        key = "sarachnis",
        displayName = "Sarachnis",
        category = BossCategory.Easy,
        combatLevel = 318,
        icon = "obj.sarachnispet",
        gear = "obj.abyssal_whip",
        description = "A giant spider in the Forthos Dungeon. Kill her spawn quickly " +
            "and watch for the web attack.",
        coords = CoordGrid(1703, 3574, 0),
        kills = kills("varp.total_sarachnis_kills", "npc.sarachnis"),
    ),
    Scurrius(
        key = "scurrius",
        displayName = "Scurrius",
        category = BossCategory.Easy,
        combatLevel = 69,
        icon = "obj.scurriuspet",
        gear = "obj.dragon_scimitar",
        description = "The rat king of the Varrock sewers. Dodge falling debris and " +
            "kill his minions. A great first boss.",
        coords = CoordGrid(3281, 9870, 0),
        kills = kills(
            "varp.total_rat_boss_kills",
            "npc.rat_boss_normal",
            "npc.rat_boss_instance",
        ),
        instanceRow = "dbrow.instance_scurrius",
        implemented = true,
    ),
    Barrows(
        key = "barrows",
        displayName = "Barrows",
        category = BossCategory.Easy,
        combatLevel = 115,
        icon = "obj.barrows_ahrim_head",
        gear = "obj.4doseprayerrestore",
        description = "Defeat the six brothers in their crypts, solve the puzzle and " +
            "loot the chest for Barrows equipment.",
        coords = CoordGrid(3565, 3289, 0),
        kills = kills("varp.barrows_kills"),
        implemented = true,
    ),
    GeneralGraardor(
        key = "graardor",
        displayName = "General Graardor",
        category = BossCategory.GodWars,
        combatLevel = 624,
        icon = "obj.bandospet",
        gear = "obj.bgs",
        description = "The Bandos general hits hard with melee and ranged. Tank with " +
            "high defence and kill his bodyguards.",
        coords = CoordGrid(2882, 5311, 2),
        kills = kills("varp.total_bandos_kills", "npc.godwars_bandos_avatar"),
        requirement = BossRequirement.Note("40 Bandos kill count"),
        instanceRow = "dbrow.instance_graardor",
        implemented = true,
    ),
    KreeArra(
        key = "kreearra",
        displayName = "Kree'arra",
        category = BossCategory.GodWars,
        combatLevel = 580,
        icon = "obj.armadylpet",
        gear = "obj.acb",
        description = "The Armadyl general flies out of melee range. Use ranged, pray " +
            "against missiles and mind the knockback.",
        coords = CoordGrid(2882, 5311, 2),
        kills = kills("varp.total_armadyl_kills", "npc.godwars_armadyl_avatar"),
        requirement = BossRequirement.Note("40 Armadyl kill count"),
        instanceRow = "dbrow.instance_kreearra",
        implemented = true,
    ),
    CommanderZilyana(
        key = "zilyana",
        displayName = "Commander Zilyana",
        category = BossCategory.GodWars,
        combatLevel = 596,
        icon = "obj.saradominpet",
        gear = "obj.4dosepotionofsaradomin",
        description = "The fast-moving Saradomin general. Keep walking to avoid her " +
            "melee and pray against her magic.",
        coords = CoordGrid(2882, 5311, 2),
        kills = kills("varp.total_saradomin_kills", "npc.godwars_saradomin_avatar"),
        requirement = BossRequirement.Note("40 Saradomin kill count"),
        instanceRow = "dbrow.instance_zilyana",
        implemented = true,
    ),
    KrilTsutsaroth(
        key = "kril",
        displayName = "K'ril Tsutsaroth",
        category = BossCategory.GodWars,
        combatLevel = 650,
        icon = "obj.zamorakpet",
        gear = "obj.4doseprayerrestore",
        description = "The Zamorak general. His special hit ignores protect prayers " +
            "and drains prayer, so bring restores.",
        coords = CoordGrid(2882, 5311, 2),
        kills = kills("varp.total_zamorak_kills", "npc.godwars_zamorak_avatar"),
        requirement = BossRequirement.Note("40 Zamorak kill count"),
        instanceRow = "dbrow.instance_kril",
        implemented = true,
    ),
    Nex(
        key = "nex",
        displayName = "Nex",
        category = BossCategory.GodWars,
        combatLevel = 1001,
        icon = "obj.nexpet",
        gear = "obj.twisted_bow",
        description = "The Zarosian general with five phases and four mages. A team " +
            "fight in the Ancient Prison.",
        coords = CoordGrid(2904, 5203, 0),
        kills = kills("varp.total_nex_kills", "npc.nex", "npc.nex_dying"),
        requirement = BossRequirement.Note("Frozen key"),
    ),
    Nightmare(
        key = "nightmare",
        displayName = "The Nightmare",
        category = BossCategory.Hard,
        combatLevel = 814,
        icon = "obj.nightmarepet",
        gear = "obj.4doseprayerrestore",
        description = "A group boss that drains prayer, spawns totems and parasites. " +
            "Charge the totems to break her shield.",
        coords = CoordGrid(3727, 3300, 0),
        kills = kills("varp.total_nightmare_kills", "npc.nightmare_dying"),
    ),
    PhantomMuspah(
        key = "muspah",
        displayName = "Phantom Muspah",
        category = BossCategory.Hard,
        combatLevel = 798,
        icon = "obj.muspahpet",
        gear = "obj.twisted_bow",
        description = "Switches between ranged, melee and a shielded form that reflects " +
            "damage. Dodge the spikes and smite rings.",
        coords = CoordGrid(2909, 10317, 0),
        kills = kills("varp.total_muspah_kills", "npc.muspah_final"),
        instanceRow = "dbrow.instance_muspah",
        implemented = true,
    ),
    Hueycoatl(
        key = "huey",
        displayName = "The Hueycoatl",
        category = BossCategory.Mid,
        combatLevel = 696,
        icon = "obj.hueypet",
        gear = "obj.dinhs_bulwark",
        description = "A giant serpent in Varlamore fought in a group. Break its tail, " +
            "then attack the head between lightning strikes.",
        coords = CoordGrid(1511, 3277, 0),
        kills = kills("varp.total_huey_kills", "npc.huey_head_defeated"),
    ),
    Yama(
        key = "yama",
        displayName = "Yama",
        category = BossCategory.EndGame,
        combatLevel = 1016,
        icon = "obj.yamapet",
        gear = "obj.4dose2restore",
        description = "The master of pacts. A duo fight full of fire and shadow " +
            "mechanics and a judge phase.",
        coords = CoordGrid(1433, 3671, 0),
        kills = kills("varp.total_yama_kills", "npc.yama"),
    ),
    RoyalTitans(
        key = "titans",
        displayName = "Royal Titans",
        category = BossCategory.Easy,
        combatLevel = 520,
        icon = "obj.rtbrandapet",
        gear = "obj.dragon_scimitar",
        description = "Branda the Fire Queen and Eldric the Ice King fight together. " +
            "Extinguish the fire and melt the ice.",
        coords = CoordGrid(2951, 9572, 0),
        kills = kills("varp.total_royal_titan_kills", "npc.rt_fire_queen"),
    ),
    Amoxliatl(
        key = "amoxliatl",
        displayName = "Amoxliatl",
        category = BossCategory.Easy,
        combatLevel = 179,
        icon = "obj.amoxliatlpet",
        gear = "obj.dragon_scimitar",
        description = "An ice-themed boss beneath Varlamore. Melee only: dodge the ice " +
            "spikes and shatter her clones.",
        coords = CoordGrid(1602, 9631, 0),
        kills = kills("varp.kc_amoxliatl", "npc.amoxliatl"),
        instanceRow = "dbrow.instance_amoxliatl",
        implemented = true,
    ),
    Vardorvis(
        key = "vardorvis",
        displayName = "Vardorvis",
        category = BossCategory.Hard,
        combatLevel = 1131,
        icon = "obj.vardorvispet",
        gear = "obj.4dose2restore",
        description = "A fast melee duel against an axe-wielding warrior. React to his " +
            "head projectiles and dodge the spinning axes.",
        coords = CoordGrid(1117, 3428, 0),
        kills = kills("varp.total_vardorvis_kills", "npc.vardorvis"),
        instanceRow = "dbrow.instance_vardorvis",
        implemented = true,
    ),
    Leviathan(
        key = "leviathan",
        displayName = "The Leviathan",
        category = BossCategory.Hard,
        combatLevel = 1061,
        icon = "obj.leviathanpet",
        gear = "obj.4dose2restore",
        description = "Prayer-flick its rapid attack volleys and avoid the falling " +
            "rocks in a sunken arena.",
        coords = CoordGrid(2064, 6436, 0),
        kills = kills("varp.total_leviathan_kills", "npc.leviathan"),
        instanceRow = "dbrow.instance_leviathan",
        implemented = true,
    ),
    Whisperer(
        key = "whisperer",
        displayName = "The Whisperer",
        category = BossCategory.Hard,
        combatLevel = 1163,
        icon = "obj.whispererpet",
        gear = "obj.4dose2restore",
        description = "A magic boss in the Lassar Undercity. Survive the Shadow Realm " +
            "phase and its screeching attacks.",
        coords = CoordGrid(2656, 6393, 0),
        kills = kills("varp.total_whisperer_kills", "npc.whisperer"),
        instanceRow = "dbrow.instance_whisperer",
        implemented = true,
    ),
    DukeSucellus(
        key = "duke",
        displayName = "Duke Sucellus",
        category = BossCategory.Hard,
        combatLevel = 1146,
        icon = "obj.dukesucelluspet",
        gear = "obj.4dose2restore",
        description = "Brew the arder-musca poison, then fight a slow but deadly boss " +
            "while dodging gas vents and gazes.",
        coords = CoordGrid(3039, 6432, 0),
        kills = kills(
            "varp.total_duke_sucellus_kills",
            "npc.duke_sucellus_awake",
            "npc.duke_sucellus_dead",
        ),
        instanceRow = "dbrow.instance_duke_sucellus",
        implemented = true,
    ),
    Callisto(
        key = "callisto",
        displayName = "Callisto",
        category = BossCategory.Wilderness,
        combatLevel = 470,
        icon = "obj.callisto_pet",
        gear = "obj.4dose2restore",
        description = "A giant bear in the deep Wilderness. Dodge its traps and " +
            "shockwaves, and watch out for player killers.",
        coords = CoordGrid(3360, 10295, 0),
        kills = kills("varp.total_callisto_kills", "npc.callisto"),
        implemented = true,
    ),
    Venenatis(
        key = "venenatis",
        displayName = "Venenatis",
        category = BossCategory.Wilderness,
        combatLevel = 464,
        icon = "obj.venenatis_pet",
        gear = "obj.4doseantipoison",
        description = "A huge poisonous spider. Pray against its magic and ranged " +
            "attacks, and kill its spiderlings.",
        coords = CoordGrid(3320, 3796, 0),
        kills = kills("varp.total_venenatis_kills", "npc.venenatis"),
        implemented = true,
    ),
    Vetion(
        key = "vetion",
        displayName = "Vet'ion",
        category = BossCategory.Wilderness,
        combatLevel = 454,
        icon = "obj.vetion_pet",
        gear = "obj.4doseprayerrestore",
        description = "A reanimated skeleton champion with two forms. Kill both " +
            "hellhounds before it can be damaged again.",
        coords = CoordGrid(3220, 3790, 0),
        kills = kills("varp.total_vetion_kills", "npc.vetion_2"),
    ),
    ChaosElemental(
        key = "chaosele",
        displayName = "Chaos Elemental",
        category = BossCategory.Wilderness,
        combatLevel = 305,
        icon = "obj.chaoselepet",
        gear = "obj.4doseprayerrestore",
        description = "Unequips your gear and teleports you around. Bring spare items " +
            "and keep your inventory space free.",
        coords = CoordGrid(3263, 3916, 0),
        kills = kills("varp.total_chaosele_kills", "npc.chaoselemental"),
    ),
    Scorpia(
        key = "scorpia",
        displayName = "Scorpia",
        category = BossCategory.Wilderness,
        combatLevel = 225,
        icon = "obj.scorpia_pet",
        gear = "obj.4doseantipoison",
        description = "A scorpion queen whose guardians heal her. Kill the guardians " +
            "first and bring antipoison.",
        coords = CoordGrid(3233, 3945, 0),
        kills = kills("varp.total_scorpia_kills", "npc.scorpia"),
    ),
    ChambersOfXeric(
        key = "cox",
        displayName = "Chambers of Xeric",
        category = BossCategory.EndGame,
        combatLevel = 0,
        icon = "obj.olmpet",
        gear = "obj.twisted_bow",
        description = "Raid the chambers beneath Mount Quidamortem, ending with the " +
            "Great Olm. Solo or in teams.",
        coords = CoordGrid(1233, 3565, 0),
    ),
    TheatreOfBlood(
        key = "tob",
        displayName = "Theatre of Blood",
        category = BossCategory.EndGame,
        combatLevel = 0,
        icon = "obj.verzikpet",
        gear = "obj.scythe_of_vitur",
        description = "Six rooms of mechanics in Ver Sinhaza, ending with Verzik " +
            "Vitur. Best done in a team of four or five.",
        coords = CoordGrid(3650, 3219, 0),
    ),
    TombsOfAmascut(
        key = "toa",
        displayName = "Tombs of Amascut",
        category = BossCategory.EndGame,
        combatLevel = 0,
        icon = "obj.wardenpet_tumeken",
        gear = "obj.bow_of_faerdhinen",
        description = "Four path bosses and the Wardens, with invocations that scale " +
            "the difficulty and the rewards.",
        coords = CoordGrid(3358, 2742, 0),
    ),
    GoblinCook(
        key = "goblincook",
        displayName = "The Goblin COOK",
        category = BossCategory.Easy,
        combatLevel = 45,
        icon = "obj.chefs_hat",
        gear = "obj.knife",
        description = "A giant goblin chef. Step off the shadow before his knife lands and " +
            "hit him while he tastes his stew to spoil it.",
        coords = CoordGrid(3863, 3683, 0),
        kills = kills("varp.boss_atlas_kc_goblincook", "npc.goblin_cook_boss"),
        implemented = true,
    );

    val id: Int
        get() = ordinal

    val pbVarp: String
        get() = "varp.boss_atlas_pb_$key"

    val lootVarp: String
        get() = "varp.boss_atlas_loot_$key"

    val npcs: Set<String>
        get() = kills.flatMapTo(HashSet()) { it.npcs }

    fun matches(query: String): Boolean =
        displayName.contains(query, ignoreCase = true) ||
            category.label.contains(query, ignoreCase = true)

    companion object {
        const val MAX_ID: Int = 63

        private val byNpc: Map<String, Boss> =
            entries.flatMap { boss -> boss.npcs.map { it to boss } }.toMap()

        fun forId(id: Int): Boss? = entries.getOrNull(id)

        fun forNpc(npcSymbol: String): Boss? = byNpc[npcSymbol]
    }
}
