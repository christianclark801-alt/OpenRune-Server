package org.rsmod.objtx

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class VarObjCertTest {
    @Test
    fun `notable obj with vars transfers from worn into inventory`() {
        val worn = arrayOfNulls<TransactionObj>(WORN_SIZE)
        val inv = arrayOfNulls<TransactionObj>(INV_SIZE)
        worn[HEAD_SLOT] = TransactionObj(DHAROK_HELM, vars = 5)

        val results =
            transaction {
                val from = select(worn)
                val into = select(inv)
                transfer {
                    this.from = from
                    this.into = into
                    fromSlot = HEAD_SLOT
                }
            }

        assertTrue(results.success)
        assertNull(worn[HEAD_SLOT])
        assertEquals(TransactionObj(DHAROK_HELM, vars = 5), inv[0])
    }

    @Test
    fun `notable obj with vars is never certed`() {
        val inv = arrayOfNulls<TransactionObj>(INV_SIZE)

        val results =
            transaction {
                val into = select(inv)
                insert {
                    this.into = into
                    obj = DHAROK_HELM
                    vars = 5
                    cert = true
                }
            }

        assertTrue(results.success)
        assertEquals(TransactionObj(DHAROK_HELM, vars = 5), inv[0])
    }

    @Test
    fun `certed obj with vars is rejected`() {
        val inv = arrayOfNulls<TransactionObj>(INV_SIZE)

        val results =
            transaction {
                val into = select(inv)
                insert {
                    this.into = into
                    obj = DHAROK_HELM_CERT
                    vars = 5
                }
            }

        assertEquals(TransactionResult.VarObjIncorrectlyHasCert, results.err)
        assertNull(inv[0])
    }

    private fun transaction(
        init: Transaction<TransactionObj>.() -> Unit
    ): TransactionResultList<TransactionObj> {
        val transaction = Transaction<TransactionObj>(input = { it }, output = { it })
        transaction.certLookup = CERT_LOOKUP
        try {
            transaction.apply(init)
        } catch (_: TransactionCancellation) {}
        val results = transaction.results()
        if (results.success) {
            results.commitAll()
        }
        return results
    }

    private fun Transaction<TransactionObj>.select(
        objs: Array<TransactionObj?>
    ): TransactionInventory<TransactionObj> {
        val image = Array(objs.size) { objs[it] }
        return register(TransactionInventory(TransactionInventory.NormalStack, objs, image))
    }

    private companion object {
        const val WORN_SIZE = 14
        const val INV_SIZE = 28
        const val HEAD_SLOT = 0

        const val DHAROK_HELM = 4716
        const val DHAROK_HELM_CERT = 4717
        const val TEMPLATE_FOR_CERT = 799

        val CERT_LOOKUP =
            mapOf(
                DHAROK_HELM to TransactionObjTemplate(DHAROK_HELM_CERT, 0),
                DHAROK_HELM_CERT to TransactionObjTemplate(DHAROK_HELM, TEMPLATE_FOR_CERT),
            )
    }
}
