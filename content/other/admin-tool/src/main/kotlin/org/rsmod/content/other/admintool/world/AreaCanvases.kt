package org.rsmod.content.other.admintool.world

import jakarta.inject.Inject
import jakarta.inject.Singleton
import org.rsmod.api.registry.region.RegionRegistry
import org.rsmod.api.repo.region.RegionRepository
import org.rsmod.api.repo.region.RegionTemplate
import org.rsmod.game.region.Region
import org.rsmod.game.region.util.RegionRotations
import org.rsmod.game.region.zone.RegionZoneCopy
import org.rsmod.map.CoordGrid
import org.rsmod.map.zone.ZoneKey

/**
 * Builds each [Area] as a protected large instance region and converts between [Spot]s and the
 * live coords of wherever the canvas landed this run.
 */
@Singleton
class AreaCanvases
@Inject
constructor(private val regionRepo: RegionRepository, private val regionReg: RegionRegistry) {
    private val built = LinkedHashMap<String, Region>()

    fun region(name: String): Region? = built[name]

    fun build(area: Area): Region? {
        destroy(area.name)
        val zones = composeZones(area.pieces)
        if (zones.isEmpty()) {
            return null
        }
        val template =
            RegionTemplate.createLarge {
                for ((dest, copy) in zones) {
                    this[dest.x, dest.z, dest.level] = copy
                }
            }
        val region = regionRepo.add(template) ?: return null
        regionRepo.protect(region)
        built[area.name] = region
        return region
    }

    fun destroy(name: String) {
        val region = built.remove(name) ?: return
        regionRepo.unprotect(region)
        regionReg.unregister(region)
    }

    fun toCoords(spot: Spot): CoordGrid? {
        if (spot.scope == Spot.WORLD) {
            return CoordGrid(spot.x, spot.z, spot.level)
        }
        val region = built[spot.scope] ?: return null
        return CoordGrid(region.southWest.x + spot.x, region.southWest.z + spot.z, spot.level)
    }

    fun toSpot(coords: CoordGrid): Spot {
        for ((name, region) in built) {
            if (coords.x in region.southWest.x until region.northEast.x &&
                coords.z in region.southWest.z until region.northEast.z
            ) {
                return Spot(name, coords.x - region.southWest.x, coords.z - region.southWest.z, coords.level)
            }
        }
        return Spot(Spot.WORLD, coords.x, coords.z, coords.level)
    }

    companion object {
        const val CANVAS_ZONES: Int = RegionRepository.LARGE_REGION_ZONE_LENGTH

        /**
         * Lays the pieces onto the canvas in order, so a later paste covers an earlier one where
         * they overlap. Each piece is copied on every level and turned as one block; zones that
         * would fall off the canvas are dropped.
         */
        fun composeZones(pieces: List<AreaPiece>): Map<ZoneKey, RegionZoneCopy> {
            val zones = LinkedHashMap<ZoneKey, RegionZoneCopy>()
            for (piece in pieces) {
                for (level in 0 until CoordGrid.LEVEL_COUNT) {
                    for (x in 0 until piece.widthZones) {
                        for (z in 0 until piece.lengthZones) {
                            val turned =
                                RegionRotations.translateZone(
                                    piece.rotation, x, z, piece.widthZones, piece.lengthZones)
                            val destX = piece.destZoneX + turned.x
                            val destZ = piece.destZoneZ + turned.z
                            if (destX !in 0 until CANVAS_ZONES || destZ !in 0 until CANVAS_ZONES) {
                                continue
                            }
                            val source = ZoneKey(piece.sourceZoneX + x, piece.sourceZoneZ + z, level)
                            zones[ZoneKey(destX, destZ, level)] =
                                RegionZoneCopy(source, piece.rotation, flag = null)
                        }
                    }
                }
            }
            return zones
        }
    }
}
