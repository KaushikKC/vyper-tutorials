#pragma version >0.3.10

# TimeLock: time-locked vault for delayed withdrawals
# Purpose: Owner deposits funds that can only be withdrawn after a lock period expires.
# Useful for agent-controlled funds that need a safety delay.

owner: public(address)

struct Lock:
    amount: uint256
    unlockTime: uint256
    withdrawn: bool

locks: public(HashMap[uint256, Lock])
nextLockId: public(uint256)

event LockCreated:
    id: indexed(uint256)
    amount: uint256
    unlockTime: uint256

event Withdrawn:
    id: indexed(uint256)
    amount: uint256
    recipient: indexed(address)

@deploy
def __init__():
    self.owner = msg.sender
    self.nextLockId = 1

# Owner creates a time lock (funds sent with this call)
@external
@payable
def create_lock(unlockTime: uint256) -> uint256:
    assert msg.sender == self.owner, "Only owner can create lock"
    assert msg.value > 0, "Must deposit funds"
    assert unlockTime > block.timestamp, "Unlock time must be in the future"
    
    id: uint256 = self.nextLockId
    self.locks[id] = Lock(
        amount=msg.value,
        unlockTime=unlockTime,
        withdrawn=False
    )
    self.nextLockId += 1
    log LockCreated(id=id, amount=msg.value, unlockTime=unlockTime)
    return id

# Check if a lock is ready to withdraw
@view
@external
def is_unlocked(id: uint256) -> bool:
    lock: Lock = self.locks[id]
    if lock.amount == 0:
        return False  # lock doesn't exist
    return block.timestamp >= lock.unlockTime and not lock.withdrawn

# Withdraw from unlocked vault (owner or designated recipient)
@external
def withdraw(id: uint256, to: address):
    lock: Lock = self.locks[id]
    assert lock.amount > 0, "Lock does not exist"
    assert not lock.withdrawn, "Lock already withdrawn"
    assert block.timestamp >= lock.unlockTime, "Lock not yet unlocked"
    assert msg.sender == self.owner, "Only owner can withdraw"
    
    amount: uint256 = lock.amount
    # mark as withdrawn before transfer
    self.locks[id].withdrawn = True
    send(to, amount)
    log Withdrawn(id=id, amount=amount, recipient=to)
