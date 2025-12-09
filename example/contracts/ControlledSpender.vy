#pragma version >0.3.10

# Controlled spender: owner grants allowance+expiry to specific agent addresses.
# Purpose: Owner gives an agent an allowance and expiry. Agent may call spend(to, amount) 
# up to its remaining allowance. Owner can revoke or top up. No backdoors, no modifiers — explicit checks.

owner: public(address)

# allowance[agent] => remaining wei allowance
allowance: public(HashMap[address, uint256])

# expiry[agent] => unix timestamp after which the agent cannot spend
expiry: public(HashMap[address, uint256])

event AllowanceSet:
    agent: indexed(address)
    amount: uint256
    expiry: uint256

@deploy
def __init__():
    self.owner = msg.sender

# Owner sets allowance and expiry for an agent
@external
def set_allowance(agent: address, amount: uint256, expiry_ts: uint256):
    assert msg.sender == self.owner, "Only owner can set allowance"
    # expiry must be in the future
    assert expiry_ts > block.timestamp, "Expiry must be in the future"
    self.allowance[agent] = amount
    self.expiry[agent] = expiry_ts
    log AllowanceSet(agent=agent, amount=amount, expiry=expiry_ts)

# Owner can revoke (set to 0)
@external
def revoke(agent: address):
    assert msg.sender == self.owner, "Only owner can revoke"
    self.allowance[agent] = 0
    self.expiry[agent] = 0
    log AllowanceSet(agent=agent, amount=0, expiry=0)

# Agent calls to transfer funds (the contract must hold funds)
@external
def spend(to: address, amount: uint256):
    # only allowed when not expired
    assert block.timestamp <= self.expiry[msg.sender], "Allowance expired"
    # sufficient allowance
    assert amount <= self.allowance[msg.sender], "Insufficient allowance"
    # reduce allowance first (effects before interactions)
    self.allowance[msg.sender] = self.allowance[msg.sender] - amount
    # transfer
    send(to, amount)

