package dev.openrune.tools

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.databind.SerializationFeature
import dev.openrune.OsrsCacheProvider
import dev.openrune.cache.CacheManager
import dev.openrune.definition.codec.ModelCodec
import dev.openrune.filesystem.Cache
import dev.openrune.gamevals.GameValProvider
import dev.openrune.getCacheLocation
import dev.openrune.revision
import dev.openrune.rscm.RSCM
import io.netty.buffer.Unpooled
import java.io.File
import java.nio.ByteBuffer
import java.nio.file.Path

private const val ANIMATIONS = 0
private const val FRAME_MAPS = 1
private const val CONFIGS = 2
private const val MODELS = 7
private const val IDENTKIT_ARCHIVE = 3
private const val SPOTANIM_ARCHIVE = 13

/**
 * Dumps cache data the Blender tools need to author player animations and worn models: the
 * models of the given objs and identity kits, and the frames + frame maps of the given seqs.
 *
 * Args: `<out dir> [obj.<name>|idk.<id>|seq.<name>|spotanim.<name>]...`. Every model is written as JSON with
 * vertices, vertex labels, faces, colours, alphas and face labels; every seq as its frame list
 * with decoded transform values, and every frame map it uses as its transform types + labels.
 */
fun main(args: Array<String>) {
    require(args.isNotEmpty()) { "Usage: <out dir> [obj.<name>|idk.<id>|seq.<name>]..." }
    GameValProvider.load("../")
    val cache = Cache.load(Path.of(getCacheLocation()))
    CacheManager.init(OsrsCacheProvider(cache, revision.first))

    val out = File(args[0]).apply { mkdirs() }
    val json = ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT)
    val frameMaps = sortedSetOf<Int>()

    for (ref in args.drop(1)) {
        when {
            ref.startsWith("obj.") -> {
                val item = CacheManager.getItem(RSCM.getRSCM(ref))
                    ?: error("No obj for $ref")
                val models = mapOf(
                    "inventory" to item.inventoryModel,
                    "male0" to item.maleModel0,
                    "male1" to item.maleModel1,
                    "female0" to item.femaleModel0,
                    "female1" to item.femaleModel1,
                ).filterValues { it > 0 }
                val info = mapOf(
                    "id" to item.id,
                    "equipSlot" to item.equipSlot,
                    "maleOffset" to item.maleOffset,
                    "femaleOffset" to item.femaleOffset,
                    "models" to models,
                )
                json.writeValue(File(out, "${ref.removePrefix("obj.")}.json"), info)
                for ((slot, model) in models) {
                    dumpModel(cache, model, File(out, "${ref.removePrefix("obj.")}_$slot.json"), json)
                }
            }
            ref.startsWith("idk.") -> {
                val id = ref.removePrefix("idk.").toInt()
                val (bodyPart, models) = decodeIdentKit(
                    cache.data(CONFIGS, IDENTKIT_ARCHIVE, id) ?: error("No identkit $id"),
                )
                json.writeValue(
                    File(out, "idk_$id.json"),
                    mapOf("id" to id, "bodyPart" to bodyPart, "models" to models),
                )
                for (model in models) {
                    dumpModel(cache, model, File(out, "model_$model.json"), json)
                }
            }
            ref.startsWith("seq.") -> {
                val id = RSCM.getRSCM(ref)
                val seq = CacheManager.getAnim(id) ?: error("No seq for $ref")
                val frames = seq.frameIDs.orEmpty().map { frameId ->
                    val data = cache.data(ANIMATIONS, frameId ushr 16, frameId and 0xFFFF)
                        ?: error("Missing frame $frameId for $ref")
                    decodeFrame(frameId, data).also { frameMaps += it["frameMap"] as Int }
                }
                json.writeValue(
                    File(out, "${ref.removePrefix("seq.")}.json"),
                    mapOf(
                        "id" to id,
                        "skeletalId" to seq.skeletalId,
                        "frameDelays" to seq.frameDelays,
                        "leftHandItem" to seq.leftHandItem,
                        "rightHandItem" to seq.rightHandItem,
                        "priority" to seq.priority,
                        "forcedPriority" to seq.forcedPriority,
                        "precedenceAnimating" to seq.precedenceAnimating,
                        "replyMode" to seq.replyMode,
                        "frameStep" to seq.frameStep,
                        "interleaveLeave" to seq.interleaveLeave,
                        "frames" to frames,
                    ),
                )
            }
            ref.startsWith("spotanim.") -> {
                val id = RSCM.getRSCM(ref)
                val data = cache.data(CONFIGS, SPOTANIM_ARCHIVE, id) ?: error("No spotanim for $ref")
                val info = decodeSpotAnim(data) + ("id" to id)
                val name = ref.removePrefix("spotanim.")
                json.writeValue(File(out, "$name.json"), info)
                dumpModel(cache, info["modelId"] as Int, File(out, "${name}_model.json"), json)
            }
            else -> error("Unknown reference '$ref'")
        }
    }

    for (map in frameMaps) {
        val data = cache.data(FRAME_MAPS, map, 0) ?: error("Missing frame map $map")
        json.writeValue(File(out, "framemap_$map.json"), decodeFrameMap(map, data))
    }
    println("Dumped ${args.size - 1} reference(s) and ${frameMaps.size} frame map(s) to $out")
}

private fun dumpModel(cache: Cache, id: Int, file: File, json: ObjectMapper) {
    val data = cache.data(MODELS, id, 0) ?: error("Missing model $id")
    val model = ModelCodec(id, emptyList()).read(Unpooled.wrappedBuffer(data))
    val vertexCount = model.vertexCount
    val faceCount = model.triangleCount
    json.writeValue(
        file,
        mapOf(
            "id" to id,
            "vertices" to (0 until vertexCount).map {
                listOf(model.vertexPositionsX!![it], model.vertexPositionsY!![it], model.vertexPositionsZ!![it])
            },
            "labels" to (0 until vertexCount).map { model.vertexSkins?.getOrNull(it) ?: 0 },
            "faces" to (0 until faceCount).map {
                listOf(model.triangleVertex1!![it], model.triangleVertex2!![it], model.triangleVertex3!![it])
            },
            "colors" to (0 until faceCount).map { model.triangleColors!![it].toInt() and 0xFFFF },
            "alphas" to (0 until faceCount).map { model.triangleAlphas?.getOrNull(it) ?: 0 },
            "faceLabels" to (0 until faceCount).map { model.triangleSkins?.getOrNull(it) ?: 0 },
            "priorities" to (0 until faceCount).map {
                model.triangleRenderPriorities?.getOrNull(it) ?: model.renderPriority
            },
        ),
    )
}

private fun decodeIdentKit(data: ByteArray): Pair<Int, List<Int>> {
    val buffer = ByteBuffer.wrap(data)
    var bodyPart = -1
    val models = mutableListOf<Int>()
    while (true) {
        when (val opcode = buffer.get().toInt() and 0xFF) {
            0 -> return bodyPart to models
            1 -> bodyPart = buffer.get().toInt() and 0xFF
            2 -> repeat(buffer.get().toInt() and 0xFF) { models += buffer.short.toInt() and 0xFFFF }
            3 -> Unit
            5 -> repeat(buffer.get().toInt() and 0xFF) { models += buffer.int }
            40, 41 -> repeat(buffer.get().toInt() and 0xFF) { buffer.int }
            in 60..70 -> buffer.short
            else -> return bodyPart to models
        }
    }
}

private fun decodeSpotAnim(data: ByteArray): Map<String, Any> {
    val buffer = ByteBuffer.wrap(data)
    val info = mutableMapOf<String, Any>()
    fun pairs(key: String) {
        val count = buffer.get().toInt() and 0xFF
        val from = mutableListOf<Int>()
        val to = mutableListOf<Int>()
        repeat(count) {
            from += buffer.short.toInt() and 0xFFFF
            to += buffer.short.toInt() and 0xFFFF
        }
        info["${key}From"] = from
        info["${key}To"] = to
    }
    while (true) {
        when (val opcode = buffer.get().toInt() and 0xFF) {
            0 -> return info
            1 -> info["modelId"] = buffer.short.toInt() and 0xFFFF
            2 -> info["animationId"] = buffer.short.toInt() and 0xFFFF
            3 -> info["modelId"] = buffer.int
            4 -> info["resizeX"] = buffer.short.toInt() and 0xFFFF
            5 -> info["resizeY"] = buffer.short.toInt() and 0xFFFF
            6 -> info["rotation"] = buffer.short.toInt() and 0xFFFF
            7 -> info["ambient"] = buffer.get().toInt() and 0xFF
            8 -> info["contrast"] = buffer.get().toInt() and 0xFF
            9 -> info["debugName"] = readString(buffer)
            10 -> info["rotate"] = false
            40 -> pairs("recolour")
            41 -> pairs("retexture")
            42 -> info["recolAll"] = buffer.short.toInt() and 0xFFFF
            else -> error("Unknown spotanim opcode $opcode")
        }
    }
}

private fun readString(buffer: ByteBuffer): String {
    val bytes = generateSequence { buffer.get() }.takeWhile { it != 0.toByte() }.toList()
    return String(bytes.toByteArray(), Charsets.ISO_8859_1)
}

private fun decodeFrame(frameId: Int, data: ByteArray): Map<String, Any> {
    val header = ByteBuffer.wrap(data)
    val frameMap = header.short.toInt() and 0xFFFF
    val count = header.get().toInt() and 0xFF
    val values = ByteBuffer.wrap(data, 3 + count, data.size - 3 - count)
    val transforms = mutableMapOf<Int, List<Int?>>()
    for (index in 0 until count) {
        val opcode = data[3 + index].toInt() and 0xFF
        if (opcode == 0) continue
        transforms[index] = listOf(1, 2, 4).map { bit ->
            if (opcode and bit != 0) readShortSmart(values) else null
        }
    }
    return mapOf("frameId" to frameId, "frameMap" to frameMap, "transforms" to transforms)
}

private fun readShortSmart(buffer: ByteBuffer): Int {
    val peek = buffer.get(buffer.position()).toInt() and 0xFF
    return if (peek < 128) {
        (buffer.get().toInt() and 0xFF) - 64
    } else {
        (buffer.short.toInt() and 0xFFFF) - 0xC000
    }
}

private fun decodeFrameMap(id: Int, data: ByteArray): Map<String, Any> {
    val buffer = ByteBuffer.wrap(data)
    val count = buffer.get().toInt() and 0xFF
    val types = (0 until count).map { buffer.get().toInt() and 0xFF }
    val labelCounts = (0 until count).map { buffer.get().toInt() and 0xFF }
    val labels = labelCounts.map { size -> (0 until size).map { buffer.get().toInt() and 0xFF } }
    return mapOf(
        "id" to id,
        "transforms" to types.zip(labels).map { (type, l) -> mapOf("type" to type, "labels" to l) },
    )
}
