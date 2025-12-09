#pragma version >0.3.10

# CommitRelease: commitment / reveal pattern for agent-triggered actions
# Purpose: Agent commits a hash of decision; later reveals to execute an action 
# (prevents frontrunning & gives verifiable intent).

owner: public(address)

struct Commit:
    committer: address
    value: uint256
    revealed: bool
    commit_ts: uint256

commits: public(HashMap[bytes32, Commit])

event Committed:
    key: indexed(bytes32)
    committer: indexed(address)

event Revealed:
    key: indexed(bytes32)
    committer: indexed(address)
    value: uint256

@deploy
def __init__():
    self.owner = msg.sender

# Agent stores commitment (off-chain agent computes hash(secret|data))
@external
@payable
def commit(key: bytes32):
    # optionally require deposit = msg.value as stake
    assert self.commits[key].committer == empty(address), "Commitment already exists"
    self.commits[key] = Commit(committer=msg.sender, value=msg.value, revealed=False, commit_ts=block.timestamp)
    log Committed(key=key, committer=msg.sender)

# Reveal: provide secret and action parameters; if hash matches, execute
@external
def reveal(secret: bytes32, to: address, amount: uint256):
    # Convert address and uint256 to bytes32 for hashing
    to_bytes: bytes32 = convert(to, bytes32)
    amount_bytes: bytes32 = convert(amount, bytes32)
    key: bytes32 = keccak256(concat(secret, to_bytes, amount_bytes))
    c: Commit = self.commits[key]
    assert c.committer == msg.sender, "Only committer can reveal"
    assert not c.revealed, "Commitment already revealed"
    # mark revealed
    self.commits[key].revealed = True
    # perform action: send funds that were deposited with commit OR allow action
    # Example: release value to `to` up to committed value
    send_amount: uint256 = amount
    if amount > c.value:
        send_amount = c.value
    send(to, send_amount)
    log Revealed(key=key, committer=msg.sender, value=amount)

