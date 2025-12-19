#pragma version >0.3.10

# Escrow: simple escrow for conditional fund release
# Purpose: Owner deposits funds that can be released to a recipient by an agent
# when certain conditions are met. Agent acts as arbiter/executor.

owner: public(address)

struct Escrow:
    depositor: address
    recipient: address
    amount: uint256
    released: bool
    created: uint256

escrows: public(HashMap[uint256, Escrow])
nextEscrowId: public(uint256)

event EscrowCreated:
    id: indexed(uint256)
    depositor: indexed(address)
    recipient: indexed(address)
    amount: uint256

event EscrowReleased:
    id: indexed(uint256)
    recipient: indexed(address)
    amount: uint256

event EscrowCancelled:
    id: indexed(uint256)
    depositor: indexed(address)
    amount: uint256

@deploy
def __init__():
    self.owner = msg.sender
    self.nextEscrowId = 1

# Depositor creates escrow (funds sent with this call)
@external
@payable
def create_escrow(recipient: address) -> uint256:
    assert msg.value > 0, "Must deposit funds"
    assert recipient != empty(address), "Recipient cannot be zero address"
    
    id: uint256 = self.nextEscrowId
    self.escrows[id] = Escrow(
        depositor=msg.sender,
        recipient=recipient,
        amount=msg.value,
        released=False,
        created=block.timestamp
    )
    self.nextEscrowId += 1
    log EscrowCreated(id=id, depositor=msg.sender, recipient=recipient, amount=msg.value)
    return id

# Agent (owner) releases escrow to recipient
@external
def release(id: uint256):
    assert msg.sender == self.owner, "Only owner can release escrow"
    escrow: Escrow = self.escrows[id]
    assert escrow.amount > 0, "Escrow does not exist"
    assert not escrow.released, "Escrow already released"
    
    amount: uint256 = escrow.amount
    recipient: address = escrow.recipient
    # mark as released before transfer
    self.escrows[id].released = True
    send(recipient, amount)
    log EscrowReleased(id=id, recipient=recipient, amount=amount)

# Depositor cancels escrow (refunds to depositor)
@external
def cancel(id: uint256):
    escrow: Escrow = self.escrows[id]
    assert escrow.amount > 0, "Escrow does not exist"
    assert msg.sender == escrow.depositor, "Only depositor can cancel"
    assert not escrow.released, "Escrow already released"
    
    amount: uint256 = escrow.amount
    depositor: address = escrow.depositor
    # mark as released (prevents double cancellation)
    self.escrows[id].released = True
    send(depositor, amount)
    log EscrowCancelled(id=id, depositor=depositor, amount=amount)
