package org.rsmod.content.skills.poisonmastery

import jakarta.inject.Inject
import org.rsmod.api.combat.commons.CombatAttack
import org.rsmod.api.config.constants
import org.rsmod.api.player.output.CamShakeAxis
import org.rsmod.api.player.output.Camera
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.weapons.MeleeWeapon
import org.rsmod.api.weapons.WeaponAttackManager
import org.rsmod.api.weapons.WeaponMap
import org.rsmod.api.weapons.WeaponRepository
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.PathingEntity
import org.rsmod.game.entity.Player
import org.rsmod.game.queue.WorldQueueList

class PoisonBladesWeapon @Inject constructor(private val worldQueues: WorldQueueList) : WeaponMap {
    override fun WeaponRepository.register(manager: WeaponAttackManager) {
        register("obj.poison_blades", PoisonBlades(manager, worldQueues))
    }

    private class PoisonBlades(
        private val manager: WeaponAttackManager,
        private val worldQueues: WorldQueueList,
    ) : MeleeWeapon {
        override suspend fun ProtectedAccess.attack(
            target: Npc,
            attack: CombatAttack.Melee,
        ): Boolean {
            playAttackFx(attack)
            val totalDamage = rollAndQueueHits(target, attack)
            manager.giveCombatXp(this, target, attack, totalDamage)
            manager.continueCombat(this, target)
            return true
        }

        override suspend fun ProtectedAccess.attack(
            target: Player,
            attack: CombatAttack.Melee,
        ): Boolean {
            playAttackFx(attack)
            val totalDamage = rollAndQueueHits(target, attack)
            manager.giveCombatXp(this, target, attack, totalDamage)
            manager.continueCombat(this, target)
            return true
        }

        private fun ProtectedAccess.playAttackFx(attack: CombatAttack.Melee) {
            PoisonBladesIdle.hide(player)
            manager.playWeaponFx(this, attack)
            spotanim("spotanim.poison_blades_attack_fx", slot = constants.spotanim_slot_combat)
            shakeOnRightSlash(player)
        }

        /** The right blade's slash lands on frame 8, about one tick into the animation. */
        private fun shakeOnRightSlash(player: Player) {
            worldQueues.add(SHAKE_DELAY) {
                if (player.isSlotAssigned) {
                    Camera.camShake(
                        player,
                        CamShakeAxis.LEFT_RIGHT,
                        SHAKE_RANDOM,
                        SHAKE_AMPLITUDE,
                        SHAKE_RATE,
                    )
                }
            }
            worldQueues.add(SHAKE_DELAY + SHAKE_TICKS) {
                if (player.isSlotAssigned) {
                    Camera.camShakeReset(player, CamShakeAxis.LEFT_RIGHT)
                }
            }
        }

        private fun ProtectedAccess.rollAndQueueHits(
            target: PathingEntity,
            attack: CombatAttack.Melee,
        ): Int {
            var totalDamage = 0
            for ((delay, roundUp) in listOf(1 to false, 2 to true)) {
                val damage =
                    manager.rollMeleeDamage(
                        source = this,
                        target = target,
                        attack = attack,
                        accuracyMultiplier = 1.0,
                        maxHitMultiplier = 0.5,
                        roundMaxHitUp = roundUp,
                    )
                totalDamage += damage
                manager.queueMeleeHit(this, target, damage, delay = delay)
            }
            return totalDamage
        }
    }

    private companion object {
        const val SHAKE_DELAY = 1
        const val SHAKE_TICKS = 1
        const val SHAKE_RANDOM = 2
        const val SHAKE_AMPLITUDE = 4
        const val SHAKE_RATE = 25
    }
}
