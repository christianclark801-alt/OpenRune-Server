package org.rsmod.content.other.admintool.world

import dev.or2.central.account.Rights
import jakarta.inject.Inject
import org.rsmod.api.config.constants
import org.rsmod.api.player.events.interact.LocDefaultEvents
import org.rsmod.api.player.events.interact.OpDefaultEvent
import org.rsmod.api.player.hook.TeleportType
import org.rsmod.api.player.output.mes
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.player.protect.ProtectedAccessLauncher
import org.rsmod.api.script.onCommand
import org.rsmod.api.script.onGameStartup
import org.rsmod.api.script.onProtectedEvent
import org.rsmod.map.CoordGrid
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

/** Rebuilds the admin-built world on startup and lets players through linked area entrances. */
class AdminWorldScript
@Inject
constructor(
    private val editor: AdminWorldEditor,
    private val canvases: AreaCanvases,
    private val tools: WorldTools,
    private val launcher: ProtectedAccessLauncher,
) : PluginScript() {
    override fun ScriptContext.startup() {
        onGameStartup { editor.startup() }

        onProtectedEvent<LocDefaultEvents.Op1>(OpDefaultEvent.ID) { enter(it.loc.coords, it.loc.shapeId) }

        onCommand("area") {
            desc = "Teleport into an admin-built area"
            requiredRights = Rights.ADMINISTRATOR
            cheat {
                val name = args.joinToString(" ")
                val area = editor.area(name)
                if (area == null) {
                    player.mes("Areas: ${editor.areas.joinToString { it.name }.ifEmpty { "none" }}")
                    return@cheat
                }
                val coords = canvases.toCoords(tools.visitSpot(area))
                if (coords == null) {
                    player.mes("${area.name} isn't built right now.")
                    return@cheat
                }
                launcher.launch(player) { telejump(coords, TeleportType.Exempt) }
            }
        }
    }

    /**
     * Op1 on any loc without its own script lands here, so a loc that isn't a linked entrance
     * keeps the usual "Nothing interesting happens." response.
     */
    private fun ProtectedAccess.enter(coords: CoordGrid, shape: Int) {
        val entrance = editor.entranceAt(coords, shape)
        val area = entrance?.let { editor.area(it.area) }
        val arrival = area?.let { canvases.toCoords(tools.visitSpot(it)) }
        if (area == null || arrival == null) {
            mes(constants.dm_default)
            return
        }
        telejump(arrival)
    }
}
