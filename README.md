# Vyper Agent Workflows

Six Vyper smart contracts demonstrating safe, agent-controlled wallet automation patterns for AI agents and automated systems.

## Overview

This repository contains six production-ready Vyper contracts designed for AI agent interactions:

1. **ControlledSpender.vy** - Per-agent allowance with expiry (safe wallet automation)
2. **StreamCap.vy** - Simple token-like streaming with rate + cap
3. **CommitRelease.vy** - Commitment/reveal pattern for agent-triggered actions
4. **TimeLock.vy** - Time-locked vault for delayed withdrawals
5. **RateLimiter.vy** - Rate limiting for agent actions
6. **Escrow.vy** - Simple escrow for conditional fund release

Each contract is intentionally small, auditable, and comment-rich. They follow Vyper best practices with explicit checks, no hidden modifiers, and clear state management.

## Project Structure

```
vyper-agent-workflows/
├── contracts/
│   ├── ControlledSpender.vy
│   ├── StreamCap.vy
│   ├── CommitRelease.vy
│   ├── TimeLock.vy
│   ├── RateLimiter.vy
│   └── Escrow.vy
├── scripts/
│   ├── agent_demo.py
│   ├── compile.py
│   └── deploy.py
├── build/
│   ├── *.abi (compiled ABIs)
│   └── *.bin (compiled bytecode)
├── README.md
├── requirements.txt
└── images/
    ├── controlled_spender.png
    ├── streamcap.png
    ├── commitrelease.png
    ├── timelock.png
    ├── ratelimiter.png
    └── escrow.png
```

## Quick Start

### Prerequisites

- Python 3.8+
- [Vyper](https://vyper.readthedocs.io/) compiler
- Local blockchain node ([Anvil](https://github.com/foundry-rs/foundry) or [Ganache](https://trufflesuite.com/ganache/))

### Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Vyper:**
   ```bash
   pip install vyper
   ```

3. **Start a local blockchain node:**
   ```bash
   # Using Anvil (recommended)
   anvil
   
   # Or using Ganache
   ganache-cli
   ```

### Compilation

**Option 1: Using the compilation script (recommended)**

```bash
# Compile all contracts at once
python3 scripts/compile.py
```

This will compile all contracts and save ABI and bytecode files to the `build/` directory.

**Option 2: Using Vyper CLI directly**

```bash
# Create build directory
mkdir -p build

# Compile each contract
python3 -m vyper -f abi contracts/ControlledSpender.vy > build/ControlledSpender.abi
python3 -m vyper -f bytecode contracts/ControlledSpender.vy > build/ControlledSpender.bin

python3 -m vyper -f abi contracts/StreamCap.vy > build/StreamCap.abi
python3 -m vyper -f bytecode contracts/StreamCap.vy > build/StreamCap.bin

python3 -m vyper -f abi contracts/CommitRelease.vy > build/CommitRelease.abi
python3 -m vyper -f bytecode contracts/CommitRelease.vy > build/CommitRelease.bin

python3 -m vyper -f abi contracts/TimeLock.vy > build/TimeLock.abi
python3 -m vyper -f bytecode contracts/TimeLock.vy > build/TimeLock.bin

python3 -m vyper -f abi contracts/RateLimiter.vy > build/RateLimiter.abi
python3 -m vyper -f bytecode contracts/RateLimiter.vy > build/RateLimiter.bin

python3 -m vyper -f abi contracts/Escrow.vy > build/Escrow.abi
python3 -m vyper -f bytecode contracts/Escrow.vy > build/Escrow.bin

**Note:** If `vyper` is in your PATH, you can use `vyper` instead of `python3 -m vyper`.

**Option 3: Using Brownie (alternative workflow)**

```bash
pip install eth-brownie
brownie init
# Place contracts in contracts/ directory
brownie compile
```

### Deployment

**Using the deployment script (recommended):**

```bash
# Set your RPC URL (defaults to local Anvil)
export RPC_URL="http://127.0.0.1:8545"

# Set deployer private key (use a test key, never production!)
export DEPLOYER_PRIVATE_KEY="0x..."

# Deploy all contracts
python3 scripts/deploy.py
```

The script will:
1. Load pre-compiled artifacts from `build/` directory (or compile on-the-fly if missing)
2. Deploy all six contracts
3. Save deployment addresses to `deployments.json`

**Manual deployment with web3.py:**

Deploy contracts using web3.py or Brownie. Here's a minimal deployment script:

```python
from web3 import Web3
from vyper import compile_code

# Load and compile
with open('contracts/ControlledSpender.vy', 'r') as f:
    code = f.read()

compiled = compile_code(code, ['abi', 'bytecode'])
abi = compiled['abi']
bytecode = compiled['bytecode']

# Deploy
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
account = w3.eth.accounts[0]

contract = w3.eth.contract(abi=abi, bytecode=bytecode)
tx_hash = contract.constructor().transact({'from': account})
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
contract_address = tx_receipt.contractAddress

print(f"Deployed at: {contract_address}")
```

## Contract Explanations

### 1. ControlledSpender.vy

**Purpose:** Owner grants an allowance and expiry timestamp to specific agent addresses. Agents can call `spend()` to transfer funds up to their remaining allowance, but only before expiry.

**Key Features:**
- Per-agent allowance tracking
- Time-based expiry mechanism
- Owner can revoke or top up allowances
- Explicit checks (no modifiers)
- Effects before interactions pattern

**Workflow:**
1. Owner calls `set_allowance(agent, amount, expiry_ts)` to grant permission
2. Agent checks `allowance(agent)` and `expiry(agent)` via view calls
3. Agent calls `spend(to, amount)` when conditions are met
4. Contract validates expiry and allowance, then transfers funds

**Use Case:** AI agent holds an EOA (private key) and calls `spend()` when off-chain logic determines a payment should be made. Off-chain logic verifies allowance and expiry before sending transactions.

**Security Notes:**
- Contract must hold funds (owner funds it separately)
- Expiry is checked on every spend
- Allowance is decremented atomically before transfer
- No backdoors - only owner can set allowances

### 2. StreamCap.vy

**Purpose:** Owner creates a stream to a recipient with a `ratePerSecond` and `maxCap`. Recipient can withdraw accumulated funds at any time. Uses deterministic, gas-friendly math.

**Key Features:**
- Multiple streams per contract (stream IDs)
- Rate-based accumulation (`ratePerSecond`)
- Hard cap per stream
- Automatic calculation of withdrawable amount
- Tracks total sent to prevent over-withdrawal

**Workflow:**
1. Owner funds contract and calls `create_stream(recipient, ratePerSecond, cap)`
2. Stream accumulates funds based on elapsed time × rate
3. Recipient (or agent) calls `withdrawable(id)` to check available amount
4. Recipient calls `withdraw(id)` to claim accumulated funds
5. Contract updates `lastWithdraw` and `totalSent` before transfer

**Use Case:** Off-chain agent triggers `withdraw()` to collect earned funds, or monitors `withdrawable()` and alerts recipient when threshold is reached.

**Math:**
```
withdrawable = min(
    (block.timestamp - lastWithdraw) × ratePerSecond,
    cap - totalSent
)
```

**Security Notes:**
- Only recipient can withdraw from their stream
- Cap prevents over-accumulation
- State updated before external call (checks-effects-interactions)

### 3. CommitRelease.vy

**Purpose:** Agent commits a hash of a decision; later reveals the secret to execute an action. Prevents frontrunning and provides verifiable intent.

**Key Features:**
- Two-phase commit-reveal pattern
- Optional deposit with commitment
- Hash-based commitment verification
- Prevents frontrunning of agent decisions

**Workflow:**
1. Agent computes `key = keccak256(secret || to || amount)` off-chain
2. Agent calls `commit(key)` with optional deposit
3. Time passes (commitment is on-chain, but secret is hidden)
4. Agent calls `reveal(secret, to, amount)` to execute action
5. Contract verifies hash matches commitment, then executes

**Use Case:** Agent constructs commitment off-chain, commits it, then later reveals to trigger an on-chain action. Useful for preventing MEV/frontrunning and providing verifiable intent.

**Security Notes:**
- Commitment key must match reveal parameters
- Only committer can reveal their commitment
- Each commitment can only be revealed once
- Deposit can be used as stake or collateral

**Example Off-Chain Code:**
```python
import secrets
from web3 import Web3

secret = secrets.token_bytes(32)
to = "0x..."
amount = 1000000000000000000  # 1 ETH in wei

# Compute commitment
key = Web3.keccak(secret + Web3.to_bytes(hexstr=to) + amount.to_bytes(32, 'big'))

# Later, reveal with same parameters
contract.functions.reveal(secret, to, amount).transact(...)
```

### 4. TimeLock.vy

**Purpose:** Owner deposits funds that can only be withdrawn after a lock period expires. Provides a safety delay for agent-controlled funds.

**Key Features:**
- Time-based lock mechanism
- Multiple locks per contract (lock IDs)
- Owner-controlled withdrawals
- Prevents premature fund access

**Workflow:**
1. Owner calls `create_lock(unlockTime)` with ETH deposit
2. Lock is created with specified unlock timestamp
3. Agent or owner checks `is_unlocked(id)` to verify lock status
4. After unlock time, owner calls `withdraw(id, to)` to release funds
5. Funds are transferred to specified recipient

**Use Case:** Agent-controlled funds that need a safety delay. Owner can lock funds for a period, ensuring they cannot be withdrawn until the lock expires. Useful for time-gated releases or safety mechanisms.

**Security Notes:**
- Only owner can create locks and withdraw
- Unlock time must be in the future when creating lock
- Each lock can only be withdrawn once
- State updated before external call (checks-effects-interactions)

### 5. RateLimiter.vy

**Purpose:** Owner sets rate limits per agent (max amount per time window). Prevents agents from exceeding spending limits within a time period.

**Key Features:**
- Per-agent rate limiting
- Configurable time windows
- Automatic window reset
- Tracks spending within current window

**Workflow:**
1. Owner calls `set_rate_limit(agent, maxAmount, windowSeconds)` to configure limits
2. Agent checks `remaining(agent)` to see available allowance
3. Agent calls `execute_action(amount)` when performing actions
4. Contract validates rate limit and updates spent amount
5. Window automatically resets when time period expires

**Use Case:** Prevent agents from exceeding spending limits within a time period. Useful for controlling agent behavior and preventing rapid successive actions that could drain funds.

**Math:**
```
remaining = maxAmount - spentInWindow (if window not expired)
remaining = maxAmount (if window expired)
```

**Security Notes:**
- Only owner can set rate limits
- Window automatically resets when expired
- Amount cannot exceed remaining allowance
- State updated atomically before logging

### 6. Escrow.vy

**Purpose:** Owner deposits funds that can be released to a recipient by an agent when certain conditions are met. Agent acts as arbiter/executor.

**Key Features:**
- Conditional fund release
- Depositor can cancel and refund
- Agent-controlled release
- Multiple escrows per contract

**Workflow:**
1. Depositor calls `create_escrow(recipient)` with ETH deposit
2. Escrow is created with specified recipient
3. Agent (owner) monitors off-chain conditions
4. When conditions met, agent calls `release(id)` to send funds to recipient
5. Alternatively, depositor can call `cancel(id)` to refund

**Use Case:** Conditional fund release where an agent monitors off-chain conditions and releases funds when criteria are met. Useful for payment upon delivery, milestone-based releases, or arbitration scenarios.

**Security Notes:**
- Only owner (agent) can release escrow
- Only depositor can cancel escrow
- Each escrow can only be released or cancelled once
- State updated before external call (checks-effects-interactions)

## Agent Demo Script

The `agent_demo.py` script demonstrates how an AI agent interacts with each contract:

### Setup

1. Set your RPC URL (defaults to local Anvil):
   ```bash
   export RPC_URL="http://127.0.0.1:8545"
   ```

2. Set agent private key (use a test key, never production):
   ```bash
   export AGENT_PRIVATE_KEY="0x..."
   ```

3. Deploy contracts and note their addresses

4. Configure contracts (set allowances, create streams, etc.)

### Usage

```python
from scripts.agent_demo import call_spend, call_withdraw, call_commit_reveal
from web3 import Web3

# ControlledSpender
call_spend(
    controlled_spender_addr="0x...",
    to_address="0x...",
    amount_wei=Web3.to_wei(0.01, 'ether')
)

# StreamCap
call_withdraw(
    streamcap_addr="0x...",
    stream_id=1
)

# CommitRelease
call_commit_reveal(
    commitrelease_addr="0x...",
    secret="0x1234...",
    to_address="0x...",
    amount=Web3.to_wei(0.05, 'ether')
)
```

The script includes:
- View call examples (checking allowance, withdrawable amounts)
- Transaction building and signing
- Error handling and validation
- Transaction receipt waiting

## Testing

### Manual Testing Flow

1. **Start local node:**
   ```bash
   anvil
   ```

2. **Deploy contracts** (use deployment script or Brownie)

3. **Fund contracts:**
   - For ControlledSpender: Send ETH to contract address
   - For StreamCap: Send ETH when creating stream
   - For CommitRelease: Deposit when committing
   - For TimeLock: Send ETH when creating lock
   - For RateLimiter: No funding needed (rate limiting only)
   - For Escrow: Send ETH when creating escrow

4. **Configure contracts:**
   ```python
   # Set allowance for agent
   controlled_spender.functions.set_allowance(
       agent_address,
       Web3.to_wei(1, 'ether'),
       int(time.time()) + 3600  # 1 hour expiry
   ).transact({'from': owner})
   
   # Create stream
   streamcap.functions.create_stream(
       recipient_address,
       ratePerSecond=Web3.to_wei(0.001, 'ether'),  # 0.001 ETH/second
       cap=Web3.to_wei(10, 'ether')
   ).transact({'from': owner, 'value': Web3.to_wei(10, 'ether')})
   ```

5. **Run agent demo:**
   ```bash
   python scripts/agent_demo.py
   ```

### Using Brownie for Testing

```bash
# Create test file
brownie test tests/test_controlled_spender.py

# Run all tests
brownie test
```

## Vyper Documentation

- [Official Vyper Documentation](https://vyper.readthedocs.io/)
- [Vyper Language Reference](https://vyper.readthedocs.io/en/latest/vyper-by-example.html)
- [Vyper Best Practices](https://docs.vyperlang.org/en/stable/best-practices.html)
- [Vyper GitHub](https://github.com/vyperlang/vyper)

## Security Considerations

### General Best Practices

1. **Always audit contracts** before deploying to mainnet
2. **Use time-locks** for critical operations
3. **Test thoroughly** on testnets first
4. **Monitor contracts** after deployment
5. **Use multi-sig** for owner operations in production

### Contract-Specific Notes

- **ControlledSpender:** Ensure contract has sufficient balance before agent spends
- **StreamCap:** Monitor stream caps to prevent overflow issues
- **CommitRelease:** Use strong random secrets for commitments
- **TimeLock:** Verify unlock times are set correctly before creating locks
- **RateLimiter:** Monitor window sizes to ensure appropriate rate limits
- **Escrow:** Ensure clear off-chain conditions for release to prevent disputes

## Workflow Diagrams

The `images/` directory should contain workflow diagrams for each contract:

- `controlled_spender.png` - Shows owner → agent → spend flow
- `streamcap.png` - Shows stream creation → accumulation → withdrawal
- `commitrelease.png` - Shows commit → wait → reveal flow
- `timelock.png` - Shows lock creation → wait → withdrawal flow
- `ratelimiter.png` - Shows rate limit setting → action execution → window reset
- `escrow.png` - Shows escrow creation → release/cancel flow

*(Note: Create these diagrams using your preferred tool - Mermaid, draw.io, or similar)*

## Contributing

This is a demonstration repository. For production use:
1. Conduct thorough security audits
2. Add comprehensive test coverage
3. Consider gas optimization
4. Add events for better monitoring
5. Implement upgrade patterns if needed

## License

This code is provided as-is for educational and demonstration purposes. Use at your own risk.

## Acknowledgments

Built with [Vyper](https://vyper.readthedocs.io/) - a Pythonic smart contract language for the EVM.

---

**Disclaimer:** These contracts are provided for educational purposes. Always conduct security audits before deploying to mainnet.

