package org.rsmod.content.other.special.weapons.ranged

import dev.openrune.rscm.RSCM
import dev.openrune.rscm.RSCMType
import org.rsmod.api.combat.commons.CombatAttack
import org.rsmod.api.config.constants
import org.rsmod.api.config.refs.params
import org.rsmod.api.player.protect.ProtectedAccess
import org.rsmod.api.weapons.RangedWeapon
import org.rsmod.api.weapons.WeaponAttackManager
import org.rsmod.api.weapons.WeaponMap
import org.rsmod.api.weapons.WeaponRepository
import org.rsmod.content.other.soulforge.HolyWaterForge
import org.rsmod.game.entity.Npc
import org.rsmod.game.entity.PathingEntity
import org.rsmod.game.entity.Player
import org.rsmod.game.type.getInvObj

class HolyWaterWeapons : WeaponMap {
    override fun WeaponRepository.register(manager: WeaponAttackManager) {
        register("obj.holy_water", HolyWater(manager))
    }

    private class HolyWater(private val manager: WeaponAttackManager) : RangedWeapon {
        override suspend fun ProtectedAccess.attack(
            target: Npc,
            attack: CombatAttack.Ranged,
        ): Boolean {
            val hitDelay = throwAt(target, attack) ?: return true
            HolyWaterPoison.apply(target, hitDelay, HolyWaterForge.tier(attack.weapon), player)
            return true
        }

        override suspend fun ProtectedAccess.attack(
            target: Player,
            attack: CombatAttack.Ranged,
        ): Boolean {
            throwAt(target, attack)
            return true
        }

        private fun ProtectedAccess.throwAt(
            target: PathingEntity,
            attack: CombatAttack.Ranged,
        ): Int? {
            val weaponType = getInvObj(attack.weapon)

            val travelSpotanim = weaponType.paramOrNull(params.proj_travel)
            if (travelSpotanim == null) {
                manager.stopCombat(this)
                mes("You are unable to fire your ammunition.")
                return null
            }

            manager.playWeaponFx(this, attack)

            val launchSpotanim =
                weaponType.paramOrNull(params.proj_launch)?.let {
                    RSCM.getReverseMapping(RSCMType.SPOTANIM, it.id)
                }
            spotanim(launchSpotanim, height = 96, slot = constants.spotanim_slot_combat)

            val travelSpotanimName = RSCM.getReverseMapping(RSCMType.SPOTANIM, travelSpotanim.id)
            val projanim =
                manager.spawnProjectile(this, target, travelSpotanimName, "projanim.thrown")
            val (serverDelay, clientDelay) = projanim.durations

            val damage = manager.rollRangedDamage(this, target, attack)
            manager.giveCombatXp(this, target, attack, damage)
            manager.queueRangedHit(this, target, null, damage, clientDelay, serverDelay)

            manager.continueCombat(this, target)
            return serverDelay
        }
    }
}
