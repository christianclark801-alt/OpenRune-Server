package org.rsmod.content.other.admintool

enum class AdminToolCategory(val label: String) {
    Teleport("Teleport"),
    Spawn("Spawn"),
    Player("Player"),
    Debug("Debug"),
    Server("Server"),
}

/**
 * One button on the Admin Tool panel. Clicking it runs `::[command]` exactly as if it were typed,
 * so any registered command (including ones added later) can be exposed by adding an entry to
 * [ADMIN_TOOL_ENTRIES].
 *
 * @param args fixed arguments always passed to the command.
 * @param argsPrompt when set, the player is asked for extra arguments with this prompt; they are
 *   appended after [args].
 * @param confirm asks "are you sure?" before running.
 */
data class AdminToolEntry(
    val label: String,
    val command: String,
    val category: AdminToolCategory,
    val args: List<String> = emptyList(),
    val argsPrompt: String? = null,
    val confirm: Boolean = false,
) {
    val hint: String
        get() =
            buildString {
                append("::").append(command)
                args.forEach { append(' ').append(it) }
                if (argsPrompt != null) append(" ...")
            }
}

val ADMIN_TOOL_ENTRIES: List<AdminToolEntry> =
    listOf(
        AdminToolEntry("Teleport", "tele", AdminToolCategory.Teleport, argsPrompt = "Enter x z [level]:"),
        AdminToolEntry("Teleport to zone", "telezone", AdminToolCategory.Teleport, argsPrompt = "Enter zoneX zoneZ level:"),
        AdminToolEntry("My position", "mypos", AdminToolCategory.Teleport),
        AdminToolEntry("Up a level", "up", AdminToolCategory.Teleport),
        AdminToolEntry("Down a level", "down", AdminToolCategory.Teleport),
        AdminToolEntry("North 5", "forward", AdminToolCategory.Teleport, args = listOf("5")),
        AdminToolEntry("South 5", "backwards", AdminToolCategory.Teleport, args = listOf("5")),
        AdminToolEntry("West 5", "left", AdminToolCategory.Teleport, args = listOf("5")),
        AdminToolEntry("East 5", "right", AdminToolCategory.Teleport, args = listOf("5")),
        AdminToolEntry("Instance exit", "instanceexit", AdminToolCategory.Teleport, argsPrompt = "Enter instance key:"),
        AdminToolEntry("Spawn item", "item", AdminToolCategory.Spawn, argsPrompt = "Enter item name/id [amount]:"),
        AdminToolEntry("Spawn npc", "npc", AdminToolCategory.Spawn, argsPrompt = "Enter duration npcName:"),
        AdminToolEntry("Npc grid", "npcgrid", AdminToolCategory.Spawn, argsPrompt = "Enter npcName [duration]:"),
        AdminToolEntry("Spawn object", "object", AdminToolCategory.Spawn, argsPrompt = "Enter duration locName:"),
        AdminToolEntry("Remove object", "locdel", AdminToolCategory.Spawn, argsPrompt = "Enter duration:"),
        AdminToolEntry("Test loot", "testloot", AdminToolCategory.Spawn, argsPrompt = "Enter npcName [count]:"),
        AdminToolEntry("Max stats", "master", AdminToolCategory.Player),
        AdminToolEntry("Reset stats", "reset", AdminToolCategory.Player, confirm = true),
        AdminToolEntry("God mode", "god", AdminToolCategory.Player),
        AdminToolEntry("Always max hit", "maxhit", AdminToolCategory.Player),
        AdminToolEntry("Open bank", "openbank", AdminToolCategory.Player),
        AdminToolEntry("Clear inventory", "invclear", AdminToolCategory.Player, confirm = true),
        AdminToolEntry("Standard book", "spellbook", AdminToolCategory.Player, args = listOf("standard")),
        AdminToolEntry("Ancient book", "spellbook", AdminToolCategory.Player, args = listOf("ancients")),
        AdminToolEntry("Lunar book", "spellbook", AdminToolCategory.Player, args = listOf("lunars")),
        AdminToolEntry("Arceuus book", "spellbook", AdminToolCategory.Player, args = listOf("arceuus")),
        AdminToolEntry("Game mode", "gamemode", AdminToolCategory.Player, argsPrompt = "Enter normal|ironman|uim|hcim:"),
        AdminToolEntry("Transmog", "transmog", AdminToolCategory.Player, argsPrompt = "Enter npc name/id (blank to reset):"),
        AdminToolEntry("Animation", "anim", AdminToolCategory.Debug, argsPrompt = "Enter seq name:"),
        AdminToolEntry("Spotanim", "spot", AdminToolCategory.Debug, argsPrompt = "Enter spotanim name [height]:"),
        AdminToolEntry("Sound", "synth", AdminToolCategory.Debug, argsPrompt = "Enter synth name/id:"),
        AdminToolEntry("Get varp", "getvarp", AdminToolCategory.Debug, argsPrompt = "Enter varp name:"),
        AdminToolEntry("Set varp", "varp", AdminToolCategory.Debug, argsPrompt = "Enter varp name value:"),
        AdminToolEntry("Get varbit", "getvarbit", AdminToolCategory.Debug, argsPrompt = "Enter varbit name:"),
        AdminToolEntry("Set varbit", "varbit", AdminToolCategory.Debug, argsPrompt = "Enter varbit name value:"),
        AdminToolEntry("Open interface", "interface", AdminToolCategory.Debug, argsPrompt = "Enter interface name/id:"),
        AdminToolEntry("Component debug", "componentdebug", AdminToolCategory.Debug),
        AdminToolEntry("Poison", "poison", AdminToolCategory.Debug, argsPrompt = "Enter initialDamage [severity]:"),
        AdminToolEntry("Venom", "venom", AdminToolCategory.Debug),
        AdminToolEntry("Clear venom", "venomclear", AdminToolCategory.Debug),
        AdminToolEntry("Disease", "disease", AdminToolCategory.Debug, argsPrompt = "Enter drain per tick:"),
        AdminToolEntry("Clear disease", "diseaseclear", AdminToolCategory.Debug),
        AdminToolEntry("Die", "die", AdminToolCategory.Debug, argsPrompt = "Enter pvm|pvp [true|false]:"),
        AdminToolEntry("Plugins", "plugins", AdminToolCategory.Server),
        AdminToolEntry("Load plugin", "loadplugin", AdminToolCategory.Server, argsPrompt = "Enter plugin name:"),
        AdminToolEntry("Reboot timer", "slowreboot", AdminToolCategory.Server, argsPrompt = "Enter cycles (0 cancels):"),
        AdminToolEntry("Reboot now", "reboot", AdminToolCategory.Server, confirm = true),
    )
