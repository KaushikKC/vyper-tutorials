"""
Agent Demo Script
Simulates an AI agent (wallet) interacting with Vyper contracts.
Uses web3.py to interact with local Anvil/Ganache or testnet.
"""

from web3 import Web3
from eth_account import Account
import time
import os

# Configuration
RPC = os.getenv("RPC_URL", "http://127.0.0.1:8545")  # Default to local Anvil
w3 = Web3(Web3.HTTPProvider(RPC))

# Agent private key (use dev account - NEVER use in production!)
# For local testing, use Anvil's default accounts or generate a test key
AGENT_PK = os.getenv("AGENT_PRIVATE_KEY", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
AGENT = Account.from_key(AGENT_PK)

# For local node, use first account as owner
try:
    OWNER = w3.eth.accounts[0]
except:
    OWNER = os.getenv("OWNER_ADDRESS", "0x0000000000000000000000000000000000000000")

print(f"Agent address: {AGENT.address}")
print(f"Owner address: {OWNER}")
print(f"Connected to: {RPC}")
print(f"Chain ID: {w3.eth.chain_id}\n")


def get_contract_abi(contract_name):
    """Load ABI from compiled contract in build/ directory."""
    import json
    build_dir = os.path.join(os.path.dirname(__file__), "..", "build")
    abi_path = os.path.join(build_dir, f"{contract_name}.abi")
    
    if os.path.exists(abi_path):
        with open(abi_path, "r") as f:
            return json.load(f)
    
    # Fallback to minimal ABI if build artifacts not found
    print(f"⚠️  Warning: ABI not found at {abi_path}. Using minimal ABI.")
    print("   Run 'python3 scripts/compile.py' to generate ABIs.\n")
    if contract_name == "ControlledSpender":
        return [
            {
                "inputs": [{"internalType": "address", "name": "", "type": "address"}],
                "name": "allowance",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "address", "name": "", "type": "address"}],
                "name": "expiry",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "amount", "type": "uint256"}
                ],
                "name": "spend",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
    elif contract_name == "StreamCap":
        return [
            {
                "inputs": [{"internalType": "uint256", "name": "id", "type": "uint256"}],
                "name": "withdrawable",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "uint256", "name": "id", "type": "uint256"}],
                "name": "withdraw",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
    elif contract_name == "CommitRelease":
        return [
            {
                "inputs": [{"internalType": "bytes32", "name": "key", "type": "bytes32"}],
                "name": "commit",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "bytes32", "name": "secret", "type": "bytes32"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "amount", "type": "uint256"}
                ],
                "name": "reveal",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
    return []


def call_spend(controlled_spender_addr, to_address, amount_wei):
    """Agent calls spend() on ControlledSpender contract."""
    print(f"\n=== ControlledSpender.spend() ===")
    contract = w3.eth.contract(address=controlled_spender_addr, abi=get_contract_abi("ControlledSpender"))
    
    # Check allowance first (view call)
    allowance = contract.functions.allowance(AGENT.address).call()
    expiry = contract.functions.expiry(AGENT.address).call()
    current_time = int(time.time())
    
    print(f"Agent allowance: {allowance} wei")
    print(f"Expiry timestamp: {expiry}")
    print(f"Current time: {current_time}")
    
    if expiry <= current_time:
        print("Allowance expired!")
        return False
    
    if allowance < amount_wei:
        print(f"Insufficient allowance: need {amount_wei}, have {allowance}")
        return False
    
    print(f"Conditions met, sending {amount_wei} wei to {to_address}")
    
    # Build transaction
    tx = contract.functions.spend(to_address, amount_wei).build_transaction({
        "from": AGENT.address,
        "nonce": w3.eth.get_transaction_count(AGENT.address),
        "gas": 200000,
        "gasPrice": w3.eth.gas_price
    })
    
    signed = Account.sign_transaction(tx, AGENT_PK)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Transaction sent: {w3.to_hex(tx_hash)}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block {receipt['blockNumber']}")
    return True


def call_withdraw(streamcap_addr, stream_id):
    """Agent (as recipient) calls withdraw() on StreamCap contract."""
    print(f"\n=== StreamCap.withdraw() ===")
    contract = w3.eth.contract(address=streamcap_addr, abi=get_contract_abi("StreamCap"))
    
    # Check withdrawable amount
    withdrawable_amt = contract.functions.withdrawable(stream_id).call()
    print(f"Withdrawable amount: {withdrawable_amt} wei")
    
    if withdrawable_amt == 0:
        print("No funds available to withdraw")
        return False
    
    print(f"Withdrawing {withdrawable_amt} wei")
    
    # Build transaction
    tx = contract.functions.withdraw(stream_id).build_transaction({
        "from": AGENT.address,
        "nonce": w3.eth.get_transaction_count(AGENT.address),
        "gas": 200000,
        "gasPrice": w3.eth.gas_price
    })
    
    signed = Account.sign_transaction(tx, AGENT_PK)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Transaction sent: {w3.to_hex(tx_hash)}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block {receipt['blockNumber']}")
    return True


def call_commit_reveal(commitrelease_addr, secret, to_address, amount):
    """Agent uses commit-reveal pattern."""
    print(f"\n=== CommitRelease: commit -> reveal ===")
    contract = w3.eth.contract(address=commitrelease_addr, abi=get_contract_abi("CommitRelease"))
    
    # Step 1: Compute commitment key
    # key = keccak256(secret || to || amount)
    secret_bytes = Web3.to_bytes(hexstr=secret) if isinstance(secret, str) else secret
    to_bytes = Web3.to_bytes(hexstr=to_address) if isinstance(to_address, str) else to_address
    amount_bytes = amount.to_bytes(32, 'big')
    
    key = Web3.keccak(secret_bytes + to_bytes + amount_bytes)
    print(f"Commitment key: {Web3.to_hex(key)}")
    
    # Step 2: Commit (with optional deposit)
    deposit = Web3.to_wei(0.1, 'ether')  # Example deposit
    print(f"Committing with deposit: {deposit} wei")
    
    tx = contract.functions.commit(key).build_transaction({
        "from": AGENT.address,
        "nonce": w3.eth.get_transaction_count(AGENT.address),
        "value": deposit,
        "gas": 200000,
        "gasPrice": w3.eth.gas_price
    })
    
    signed = Account.sign_transaction(tx, AGENT_PK)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Commit transaction: {w3.to_hex(tx_hash)}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Committed in block {receipt['blockNumber']}")
    
    # Step 3: Wait a bit (simulate time passing)
    print("⏳ Waiting before reveal...")
    time.sleep(2)
    
    # Step 4: Reveal
    print(f"🔓 Revealing: sending {amount} wei to {to_address}")
    
    # Convert secret to bytes32
    if isinstance(secret, str):
        if secret.startswith('0x'):
            secret_bytes32 = Web3.to_bytes(hexstr=secret)
        else:
            secret_bytes32 = Web3.keccak(text=secret)[:32]
    else:
        secret_bytes32 = secret
    
    tx = contract.functions.reveal(secret_bytes32, to_address, amount).build_transaction({
        "from": AGENT.address,
        "nonce": w3.eth.get_transaction_count(AGENT.address),
        "gas": 200000,
        "gasPrice": w3.eth.gas_price
    })
    
    signed = Account.sign_transaction(tx, AGENT_PK)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Reveal transaction: {w3.to_hex(tx_hash)}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Revealed in block {receipt['blockNumber']}")
    return True


if __name__ == "__main__":
    print("AI Agent Demo - Vyper Contract Interactions\n")
    
    # Try to load deployment addresses
    deployments_path = os.path.join(os.path.dirname(__file__), "..", "deployments.json")
    contract_addresses = {}
    
    if os.path.exists(deployments_path):
        import json
        with open(deployments_path, "r") as f:
            deployments = json.load(f)
            contract_addresses = deployments.get("contracts", {})
            print("Loaded contract addresses from deployments.json:")
            for name, addr in contract_addresses.items():
                print(f"   {name}: {addr}")
            print()
    
    if not contract_addresses:
        print("No contract addresses found. Please either:")
        print("   1. Run 'python3 scripts/test_agent_workflows.py' to deploy and test")
        print("   2. Or set contract addresses manually below\n")
        print("Example usage:")
        print("  call_spend(contract_addr, recipient_addr, amount_wei)")
        print("  call_withdraw(contract_addr, stream_id)")
        print("  call_commit_reveal(contract_addr, secret, recipient_addr, amount)")
        print()
        print("To use with deployed contracts, uncomment and modify:")
        print("  CONTROLLED_SPENDER = '0x...'")
        print("  STREAMCAP = '0x...'")
        print("  COMMITRELEASE = '0x...'")
    else:
        # Use loaded addresses for demo
        CONTROLLED_SPENDER = contract_addresses.get("ControlledSpender")
        STREAMCAP = contract_addresses.get("StreamCap")
        COMMITRELEASE = contract_addresses.get("CommitRelease")
        
        # Get a recipient address (use second account from Anvil or a test address)
        try:
            RECIPIENT_ADDR = w3.eth.accounts[2] if len(w3.eth.accounts) > 2 else "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
        except:
            RECIPIENT_ADDR = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
        
        if CONTROLLED_SPENDER:
            print("To test ControlledSpender:")
            print(f"   call_spend('{CONTROLLED_SPENDER}', '{RECIPIENT_ADDR}', Web3.to_wei(0.01, 'ether'))")
        
        if STREAMCAP:
            print("To test StreamCap:")
            print(f"   call_withdraw('{STREAMCAP}', 1)")
        
        if COMMITRELEASE:
            print("To test CommitRelease:")
            print(f"   call_commit_reveal('{COMMITRELEASE}', '0x1234...', '{RECIPIENT_ADDR}', Web3.to_wei(0.05, 'ether'))")
        
        print("\n For a complete end-to-end test, run:")
        print("   python3 scripts/test_agent_workflows.py")

