#pragma version >0.3.10

# RateLimiter: rate limiting for agent actions
# Purpose: Owner sets rate limits per agent (max amount per time window).
# Prevents agents from exceeding spending limits within a time period.

owner: public(address)

struct RateLimit:
    maxAmount: uint256  # max amount per window
    windowSeconds: uint256  # time window in seconds
    lastReset: uint256  # timestamp of last reset
    spentInWindow: uint256  # amount spent in current window

rateLimits: public(HashMap[address, RateLimit])

event RateLimitSet:
    agent: indexed(address)
    maxAmount: uint256
    windowSeconds: uint256

event ActionExecuted:
    agent: indexed(address)
    amount: uint256
    remaining: uint256

@deploy
def __init__():
    self.owner = msg.sender

# Owner sets rate limit for an agent
@external
def set_rate_limit(agent: address, maxAmount: uint256, windowSeconds: uint256):
    assert msg.sender == self.owner, "Only owner can set rate limit"
    assert maxAmount > 0, "Max amount must be greater than zero"
    assert windowSeconds > 0, "Window must be greater than zero"
    
    # Initialize or update rate limit
    if self.rateLimits[agent].maxAmount == 0:
        # First time setting - initialize
        self.rateLimits[agent] = RateLimit(
            maxAmount=maxAmount,
            windowSeconds=windowSeconds,
            lastReset=block.timestamp,
            spentInWindow=0
        )
    else:
        # Update existing - reset window if needed
        self.rateLimits[agent].maxAmount = maxAmount
        self.rateLimits[agent].windowSeconds = windowSeconds
        if self._is_window_expired(agent):
            self._reset_window(agent)
    
    log RateLimitSet(agent=agent, maxAmount=maxAmount, windowSeconds=windowSeconds)

# Check if window has expired (internal)
@internal
@view
def _is_window_expired(agent: address) -> bool:
    limit: RateLimit = self.rateLimits[agent]
    if limit.maxAmount == 0:
        return False  # no limit set
    return block.timestamp >= limit.lastReset + limit.windowSeconds

# Reset window (internal)
@internal
def _reset_window(agent: address):
    self.rateLimits[agent].lastReset = block.timestamp
    self.rateLimits[agent].spentInWindow = 0

# Check remaining allowance in current window
@view
@external
def remaining(agent: address) -> uint256:
    limit: RateLimit = self.rateLimits[agent]
    if limit.maxAmount == 0:
        return 0  # no limit set
    
    if self._is_window_expired(agent):
        return limit.maxAmount  # window expired, full allowance available
    
    return limit.maxAmount - limit.spentInWindow

# Agent executes action (checks rate limit, updates state)
@external
def execute_action(amount: uint256):
    limit: RateLimit = self.rateLimits[msg.sender]
    assert limit.maxAmount > 0, "No rate limit set for agent"
    
    # Reset window if expired
    if self._is_window_expired(msg.sender):
        self._reset_window(msg.sender)
    
    # Check if amount exceeds remaining allowance
    assert amount <= limit.maxAmount - limit.spentInWindow, "Rate limit exceeded"
    
    # Update spent amount
    self.rateLimits[msg.sender].spentInWindow += amount
    
    remaining_amt: uint256 = limit.maxAmount - self.rateLimits[msg.sender].spentInWindow
    log ActionExecuted(agent=msg.sender, amount=amount, remaining=remaining_amt)
