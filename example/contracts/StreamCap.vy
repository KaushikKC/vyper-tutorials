#pragma version >0.3.10

# StreamCap: simple token-like streaming with rate + cap
# Purpose: Owner creates a stream to recipient with a ratePerSecond and maxCap. 
# Recipient withdraws accumulated amount. Deterministic, gas-friendly math.

owner: public(address)

struct Stream:
    recipient: address
    start: uint256
    lastWithdraw: uint256
    ratePerSecond: uint256
    cap: uint256
    totalSent: uint256  # cumulative sent so far

streams: public(HashMap[uint256, Stream])
nextStreamId: public(uint256)

event StreamCreated:
    id: indexed(uint256)
    recipient: indexed(address)
    rate: uint256
    cap: uint256

@deploy
def __init__():
    self.owner = msg.sender
    self.nextStreamId = 1

# Owner funds the contract, then creates stream
@external
@payable
def create_stream(recipient: address, ratePerSecond: uint256, cap: uint256) -> uint256:
    assert msg.sender == self.owner, "Only owner can create stream"
    # require cap >= 0 and rate>0
    assert ratePerSecond > 0, "Rate must be greater than zero"
    assert cap > 0, "Cap must be greater than zero"
    id: uint256 = self.nextStreamId
    self.streams[id] = Stream(
        recipient=recipient,
        start=block.timestamp,
        lastWithdraw=block.timestamp,
        ratePerSecond=ratePerSecond,
        cap=cap,
        totalSent=0
    )
    self.nextStreamId += 1
    log StreamCreated(id=id, recipient=recipient, rate=ratePerSecond, cap=cap)
    return id

# view how much is withdrawable now (internal version)
@internal
@view
def _withdrawable(id: uint256) -> uint256:
    s: Stream = self.streams[id]
    elapsed: uint256 = block.timestamp - s.lastWithdraw
    amount: uint256 = elapsed * s.ratePerSecond
    remaining: uint256 = s.cap - s.totalSent
    if amount > remaining:
        return remaining
    return amount

# view how much is withdrawable now (external version)
@view
@external
def withdrawable(id: uint256) -> uint256:
    return self._withdrawable(id)

# recipient withdraws accumulated funds
@external
def withdraw(id: uint256):
    s: Stream = self.streams[id]
    assert msg.sender == s.recipient, "Only recipient can withdraw"
    amt: uint256 = self._withdrawable(id)
    assert amt > 0, "No funds available to withdraw"
    # update state before sending
    self.streams[id].lastWithdraw = block.timestamp
    self.streams[id].totalSent = s.totalSent + amt
    send(msg.sender, amt)

