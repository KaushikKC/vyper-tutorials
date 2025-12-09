"""
End-to-end test script for agent workflows.
Deploys contracts, configures them, and demonstrates agent interactions.
"""

from web3 import Web3
from eth_account import Account
import os
import json
import time

# Configuration
RPC = os.getenv("RPC_URL", "http://127.0.0.1:8545")
w3 = Web3(Web3.HTTPProvider(RPC))

# Use Anvil's default accounts
# Account 0 = Owner/Deployer
# Account 1 = Agent
# Account 2 = Recipient/Test recipient

OWNER_PK = os.getenv("OWNER_PRIVATE_KEY", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
AGENT_PK = os.getenv("AGENT_PRIVATE_KEY", "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d")
RECIPIENT_PK = os.getenv("RECIPIENT_PRIVATE_KEY", "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a")

OWNER = Account.from_key(OWNER_PK)
AGENT = Account.from_key(AGENT_PK)
RECIPIENT = Account.from_key(RECIPIENT_PK)

print("=" * 60)
print("Vyper Agent Workflows - End-to-End Test")
print("=" * 60)
print(f"Network: {RPC}")
print(f"Chain ID: {w3.eth.chain_id}")
print(f"Owner: {OWNER.address}")
print(f"Agent: {AGENT.address}")
print(f"Recipient: {RECIPIENT.address}")
print()


def load_abi(contract_name):
    """Load ABI from build directory."""
    build_dir = os.path.join(os.path.dirname(__file__), "..", "build")
    abi_path = os.path.join(build_dir, f"{contract_name}.abi")
    
    if not os.path.exists(abi_path):
        raise FileNotFoundError(f"ABI not found: {abi_path}. Run 'python3 scripts/compile.py' first.")
    
    with open(abi_path, "r") as f:
        return json.load(f)


def load_bytecode(contract_name):
    """Load bytecode from build directory."""
    build_dir = os.path.join(os.path.dirname(__file__), "..", "build")
    bin_path = os.path.join(build_dir, f"{contract_name}.bin")
    
    if not os.path.exists(bin_path):
        raise FileNotFoundError(f"Bytecode not found: {bin_path}. Run 'python3 scripts/compile.py' first.")
    
    with open(bin_path, "r") as f:
        return f.read().strip()


def deploy_contract(contract_name, deployer_pk, deployer_account):
    """Deploy a contract and return its address."""
    print(f"📦 Deploying {contract_name}...")
    
    abi = load_abi(contract_name)
    bytecode = load_bytecode(contract_name)
    
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    tx = contract.constructor().build_transaction({
        "from": deployer_account.address,
        "nonce": w3.eth.get_transaction_count(deployer_account.address),
        "gas": 2000000,
        "gasPrice": w3.eth.gas_price
    })
    
    signed = Account.sign_transaction(tx, deployer_pk)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    address = receipt.contractAddress
    print(f"  Deployed at: {address}")
    print(f"  Gas used: {receipt.gasUsed}\n")
    
    return address, abi


def send_eth(from_account, from_pk, to_address, amount_wei):
    """Send ETH from one account to another."""
    tx = {
        "from": from_account.address,
        "to": to_address,
        "value": amount_wei,
        "nonce": w3.eth.get_transaction_count(from_account.address),
        "gas": 21000,
        "gasPrice": w3.eth.gas_price
    }
    
    signed = Account.sign_transaction(tx, from_pk)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt


def test_controlled_spender(contract_addr, abi):
    """Test ControlledSpender contract."""
    print("\n" + "=" * 60)
    print("TEST 1: ControlledSpender")
    print("=" * 60)
    
    contract = w3.eth.contract(address=contract_addr, abi=abi)
    
    # Step 1: Fund the contract
    print("\n Funding contract with 1 ETH...")
    send_eth(OWNER, OWNER_PK, contract_addr, Web3.to_wei(1, 'ether'))
    print("  Contract funded")
    
    # Step 2: Owner sets allowance for agent
    print("\n Owner setting allowance for agent...")
    allowance_amount = Web3.to_wei(0.5, 'ether')
    expiry_time = int(time.time()) + 3600  # 1 hour from now
    
    tx = contract.functions.set_allowance(
        AGENT.address,
        allowance_amount,
        expiry_time
    ).build_transaction({
        "from": OWNER.address,
        "nonce": w3.eth.get_transaction_count(OWNER.address),
        "gas": 200000,
        "gasPrice": w3.eth.gas_price
    })
    
    signed = Account.sign_transaction(tx, OWNER_PK)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"   Allowance set: {allowance_amount} wei, expires at {expiry_time}")
    
    # Step 3: Agent checks allowance
    print("\n Agent checking allowance...")
    allowance = contract.functions.allowance(AGENT.address).call()
    expiry = contract.functions.expiry(AGENT.address).call()
    print(f"  Allowance: {allowance} wei")
    print(f"  Expiry: {expiry} (current: {int(time.time())})")
    
    # Step 4: Agent spends
    print("\n Agent spending 0.1 ETH to recipient...")
    spend_amount = Web3.to_wei(0.1, 'ether')
    
    tx = contract.functions.spend(RECIPIENT.address, spend_amount).build_transaction({
        "from": AGENT.address,
        "nonce": w3.eth.get_transaction_count(AGENT.address),
        "gas": 200000,
        "gasPrice": w3.eth.gas_price
    })
    
    signed = Account.sign_transaction(tx, AGENT_PK)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"  Spent {spend_amount} wei to {RECIPIENT.address}")
    
    # Check remaining allowance
    remaining = contract.functions.allowance(AGENT.address).call()
    print(f"  Remaining allowance: {remaining} wei")
    
    recipient_balance = w3.eth.get_balance(RECIPIENT.address)
    print(f"  Recipient balance: {recipient_balance} wei")


def test_streamcap(contract_addr, abi):
    """Test StreamCap contract."""
    print("\n" + "=" * 60)
    print("TEST 2: StreamCap")
    print("=" * 60)
    
    contract = w3.eth.contract(address=contract_addr, abi=abi)
    
    # Step 1: Owner creates a stream
    print("\n Owner creating stream for agent...")
    rate_per_second = Web3.to_wei(0.001, 'ether')  # 0.001 ETH per second
    cap = Web3.to_wei(1, 'ether')  # Max 1 ETH
    funding = Web3.to_wei(1, 'ether')  # Fund with 1 ETH
    
    tx = contract.functions.create_stream(
        AGENT.address,
        rate_per_second,
        cap
    ).build_transaction({
        "from": OWNER.address,
        "nonce": w3.eth.get_transaction_count(OWNER.address),
        "value": funding,
        "gas": 200000,
        "gasPrice": w3.eth.gas_price
    })
    
    signed = Account.sign_transaction(tx, OWNER_PK)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Get stream ID from event
    stream_id = 1  # First stream
    print(f"  Stream created with ID: {stream_id}")
    print(f"  Rate: {rate_per_second} wei/second")
    print(f"  Cap: {cap} wei")
    
    # Step 2: Wait a bit (simulate time passing)
    print("\n Waiting 3 seconds for stream to accumulate...")
    time.sleep(3)
    
    # Step 3: Agent checks withdrawable
    print("\n Agent checking withdrawable amount...")
    withdrawable = contract.functions.withdrawable(stream_id).call()
    print(f"  Withdrawable: {withdrawable} wei")
    
    # Step 4: Agent withdraws
    if withdrawable > 0:
        print("\n Agent withdrawing...")
        tx = contract.functions.withdraw(stream_id).build_transaction({
            "from": AGENT.address,
            "nonce": w3.eth.get_transaction_count(AGENT.address),
            "gas": 200000,
            "gasPrice": w3.eth.gas_price
        })
        
        signed = Account.sign_transaction(tx, AGENT_PK)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"  Withdrew {withdrawable} wei")
        
        agent_balance = w3.eth.get_balance(AGENT.address)
        print(f"  Agent balance: {agent_balance} wei")
    else:
        print("  No funds available to withdraw yet")


def test_commit_release(contract_addr, abi):
    """Test CommitRelease contract."""
    print("\n" + "=" * 60)
    print("TEST 3: CommitRelease")
    print("=" * 60)
    
    contract = w3.eth.contract(address=contract_addr, abi=abi)
    
    # Step 1: Agent computes commitment
    print("\n Agent computing commitment...")
    secret = Web3.keccak(text="my_secret_123")[:32]  # bytes32
    to_address = RECIPIENT.address
    amount = Web3.to_wei(0.1, 'ether')
    
    # Compute key = keccak256(secret || to || amount)
    to_bytes = Web3.to_bytes(hexstr=to_address)
    amount_bytes = amount.to_bytes(32, 'big')
    key = Web3.keccak(secret + to_bytes + amount_bytes)
    
    print(f"  Secret: {Web3.to_hex(secret)}")
    print(f"  Commitment key: {Web3.to_hex(key)}")
    
    # Step 2: Agent commits
    print("\n Agent committing...")
    deposit = Web3.to_wei(0.2, 'ether')
    
    tx = contract.functions.commit(key).build_transaction({
        "from": AGENT.address,
        "nonce": w3.eth.get_transaction_count(AGENT.address),
        "value": deposit,
        "gas": 200000,
        "gasPrice": w3.eth.gas_price
    })
    
    signed = Account.sign_transaction(tx, AGENT_PK)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"  Committed with deposit: {deposit} wei")
    
    # Step 3: Wait a bit
    print("\n Waiting before reveal...")
    time.sleep(2)
    
    # Step 4: Agent reveals
    print("\n Agent revealing...")
    tx = contract.functions.reveal(secret, to_address, amount).build_transaction({
        "from": AGENT.address,
        "nonce": w3.eth.get_transaction_count(AGENT.address),
        "gas": 200000,
        "gasPrice": w3.eth.gas_price
    })
    
    signed = Account.sign_transaction(tx, AGENT_PK)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"  Revealed and sent {amount} wei to {to_address}")
    
    recipient_balance = w3.eth.get_balance(RECIPIENT.address)
    print(f"  Recipient balance: {recipient_balance} wei")


def main():
    """Run all tests."""
    try:
        # Deploy all contracts
        print("DEPLOYMENT PHASE")
        print("=" * 60)
        
        controlled_spender_addr, controlled_spender_abi = deploy_contract("ControlledSpender", OWNER_PK, OWNER)
        streamcap_addr, streamcap_abi = deploy_contract("StreamCap", OWNER_PK, OWNER)
        commitrelease_addr, commitrelease_abi = deploy_contract("CommitRelease", OWNER_PK, OWNER)
        
        # Save deployment info
        deployments = {
            "network": RPC,
            "chain_id": w3.eth.chain_id,
            "contracts": {
                "ControlledSpender": controlled_spender_addr,
                "StreamCap": streamcap_addr,
                "CommitRelease": commitrelease_addr
            }
        }
        
        deployments_path = os.path.join(os.path.dirname(__file__), "..", "deployments.json")
        with open(deployments_path, "w") as f:
            json.dump(deployments, f, indent=2)
        print(f" Deployment info saved to: {deployments_path}\n")
        
        # Run tests
        print("\n TESTING PHASE")
        print("=" * 60)
        
        test_controlled_spender(controlled_spender_addr, controlled_spender_abi)
        test_streamcap(streamcap_addr, streamcap_abi)
        test_commit_release(commitrelease_addr, commitrelease_abi)
        
        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

