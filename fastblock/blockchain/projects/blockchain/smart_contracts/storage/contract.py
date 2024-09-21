from algopy import ARC4Contract, String, arc4, BoxMap, op, Bytes, Global, gtxn
from typing import TypeAlias

Hash: TypeAlias = Bytes


class Storage(ARC4Contract):
    def __init__(self) -> None:
        self.content = BoxMap(Hash, String)

    @arc4.abimethod()
    def store(self, payment: gtxn.PaymentTransaction, code: String) -> None:
        mbr_before = Global.current_application_address.min_balance

        content_hash = op.sha256(code.bytes)
        # Saves the user paying txn fee if the content is already stored
        assert content_hash not in self.content, "Content already stored"
        self.content[content_hash] = code

        mbr_after = Global.current_application_address.min_balance

        assert (
            payment.receiver == Global.current_application_address
        ), "Receiver must be the app address"
        assert (
            payment.amount >= mbr_after - mbr_before
        ), "Payment amount must >= the minimum balance requirement delta"
