package home

import dev.openrune.rscm.RSCM
import dev.openrune.rscm.RSCMType
import dev.or2.central.account.Rights
import jakarta.inject.Inject
import org.rsmod.api.area.checker.AreaChecker
import org.rsmod.api.player.hook.PlayerTeleportValidator
import org.rsmod.api.player.hook.TeleportType
import org.rsmod.api.player.output.ChatType
import org.rsmod.api.player.output.clearMapFlag
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.player.protect.ProtectedAccessLauncher
import org.rsmod.api.script.onCommand
import org.rsmod.map.CoordGrid
import org.rsmod.plugin.scripts.PluginScript
import org.rsmod.plugin.scripts.ScriptContext

class HomePlugin
@Inject
constructor(
    private val protectedAccess: ProtectedAccessLauncher,
    private val teleportValidator: PlayerTeleportValidator,
    private val areaChecker: AreaChecker,
) : PluginScript() {
    private val startAnim by lazy { RSCM.getReverseMapping(RSCMType.SEQ, 714) }
    private val endAnim by lazy { RSCM.getReverseMapping(RSCMType.SEQ, 715) }
    private val spotanim by lazy { RSCM.getReverseMapping(RSCMType.SPOTANIM, 111) }

    override fun ScriptContext.startup() {
        onCommand("home") {
            desc = "Teleport to the spawn point."
            cheat {
                protectedAccess.launch(player, busyText = "You can't do that right now.") {
                    teleportHome()
                }
            }
        }
    }

    private suspend fun ProtectedAccess.teleportHome() {
        if (actionDelay > mapClock) {
            return
        }

        val type =
            if (player.modLevel.isAtLeast(Rights.ADMINISTRATOR)) {
                TeleportType.Exempt
            } else {
                TeleportType.Standard
            }

        val denial = teleportValidator.validate(player, type, areaChecker)
        if (denial != null) {
            player.clearMapFlag()
            mes(denial, ChatType.Engine)
            return
        }

        actionDelay = mapClock + TeleportActionDelay
        anim(startAnim)
        spotanim(spotanim, height = SpotanimHeight)
        soundSynth(TeleportSound)
        delay(TeleportDelay)
        telejump(HomeCoord, type)
        anim(endAnim)
    }

    private companion object {
        const val TeleportSound = "synth.teleport_all"
        const val SpotanimHeight = 92
        const val TeleportDelay = 4
        const val TeleportActionDelay = 5
        val HomeCoord = CoordGrid(0, 59, 40, 14, 8)
    }
}
