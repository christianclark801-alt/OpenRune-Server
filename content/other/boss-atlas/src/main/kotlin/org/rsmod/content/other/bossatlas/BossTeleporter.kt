package org.rsmod.content.other.bossatlas

import dev.or2.central.account.Rights
import jakarta.inject.Inject
import org.rsmod.api.area.checker.AreaChecker
import org.rsmod.api.area.checker.wildernessLevel
import org.rsmod.api.player.hook.PlayerTeleportValidator
import org.rsmod.api.player.hook.TeleportType
import org.rsmod.api.player.output.ChatType
import org.rsmod.api.player.output.clearMapFlag
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.player.stat.baseSlayerLvl
import org.rsmod.api.player.vars.intVarBit
import org.rsmod.api.player.vars.intVarp
import org.rsmod.game.entity.Player
import org.rsmod.map.CoordGrid

private const val TELEPORT_DELAY = 5
private const val COOLDOWN_TICKS = 17
private const val SPOTANIM_HEIGHT = 92

internal var Player.atlasCooldown by intVarp("varp.boss_atlas_cooldown")
internal var Player.atlasLastTeleport by intVarBit("varbit.boss_atlas_last")

class BossTeleporter
@Inject
constructor(
    private val validator: PlayerTeleportValidator,
    private val areaChecker: AreaChecker,
) {
    fun meetsRequirement(player: Player, boss: Boss): Boolean =
        when (val requirement = boss.requirement) {
            is BossRequirement.Slayer -> player.baseSlayerLvl >= requirement.level
            else -> true
        }

    fun wildernessLevel(coords: CoordGrid): Int = coords.wildernessLevel(areaChecker)

    suspend fun teleport(access: ProtectedAccess, boss: Boss, destination: CoordGrid = boss.coords) {
        with(access) {
            if (actionDelay > mapClock) {
                return
            }
            val wait = cooldownSecondsLeft(player.atlasCooldown, mapClock)
            if (wait > 0) {
                mes("You must wait $wait second${if (wait == 1) "" else "s"} before teleporting again.")
                return
            }
            val type = teleportType(player)
            if (!canDepart(access, type)) {
                return
            }
            if (!meetsRequirement(player, boss)) {
                mes("You need ${boss.requirement.text} to fight the ${boss.displayName}.")
                return
            }

            ifClose()
            val wilderness = wildernessLevel(destination)
            if (wilderness > 0) {
                val confirmed =
                    choice2(
                        "Yes, teleport me there.",
                        true,
                        "No, stay here.",
                        false,
                        title = "Teleport into level $wilderness Wilderness?",
                    )
                if (!confirmed || !canDepart(access, type)) {
                    return
                }
            }

            actionDelay = mapClock + TELEPORT_DELAY + 1
            player.atlasCooldown = mapClock + COOLDOWN_TICKS
            anim("seq.human_castteleport")
            spotanim("spotanim.teleport_casting", height = SPOTANIM_HEIGHT)
            soundSynth("synth.teleport_all")
            delay(TELEPORT_DELAY)

            if (!canDepart(access, type)) {
                player.atlasCooldown = 0
                mes("Your teleport was interrupted.")
                return
            }
            telejump(destination, type)
            anim("seq.human_castteleport_reverse")
            player.atlasLastTeleport = encodeFavourite(boss)
            if (!boss.implemented) {
                mes("<col=ef1020>${boss.displayName} has not been implemented on this server yet.</col>")
            }
        }
    }

    private fun canDepart(access: ProtectedAccess, type: TeleportType): Boolean {
        if (type != TeleportType.Exempt && access.isInCombat()) {
            access.mes("You can't teleport while you're in combat.")
            return false
        }
        val denial = validator.validate(access.player, type, areaChecker) ?: return true
        access.player.clearMapFlag()
        access.mes(denial, ChatType.Engine)
        return false
    }

    private fun teleportType(player: Player): TeleportType =
        if (player.modLevel.isAtLeast(Rights.ADMINISTRATOR)) {
            TeleportType.Exempt
        } else {
            TeleportType.Standard
        }
}
