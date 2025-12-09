"""
Deployment script for Vyper contracts.
Uses web3.py to deploy contracts to a local or remote network.
"""

from web3 import Web3
from eth_account import Account
import os
import subprocess
import json

# Configuration
RPC = os.getenv("RPC_URL", "http://127.0.0.1:8545")
DEPLOYER_PK = os.getenv("DEPLOYER_PRIVATE_KEY", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")

w3 = Web3(Web3.HTTPProvider(RPC))
deployer = Account.from_key(DEPLOYER_PK)

print(f"Deployer: {deployer.address}")
print(f"Network: {RPC}")
print(f"Chain ID: {w3.eth.chain_id}\n")


def load_compiled_artifacts(contract_name):
    """Load pre-compiled ABI and bytecode from build directory."""
    build_dir = os.path.join(os.path.dirname(__file__), "..", "build")
    abi_path = os.path.join(build_dir, f"{contract_name}.abi")
    bin_path = os.path.join(build_dir, f"{contract_name}.bin")
    
    if os.path.exists(abi_path) and os.path.exists(bin_path):
        with open(abi_path, "r") as f:
            abi = json.load(f)
        with open(bin_path, "r") as f:
            bytecode = f.read().strip()
        return abi, bytecode
    return None, None


def compile_vyper(contract_path):
    """Compile Vyper contract and return ABI and bytecode."""
    try:
        # Try using python -m vyper (works even if vyper not in PATH)
        abi_result = subprocess.run(
            ["python3", "-m", "vyper", "-f", "abi", contract_path],
            capture_output=True,
            text=True,
            check=True
        )
        abi = json.loads(abi_result.stdout)
        
        bytecode_result = subprocess.run(
            ["python3", "-m", "vyper", "-f", "bytecode", contract_path],
            capture_output=True,
            text=True,
            check=True
        )
        bytecode = bytecode_result.stdout.strip()
        
        return abi, bytecode
    except subprocess.CalledProcessError as e:
        print(f"Error compiling {contract_path}: {e}")
        print("Make sure vyper is installed: pip install vyper")
        raise
    except FileNotFoundError:
        print("Python3 not found. Please install Python 3.11+")
        raise


def deploy_contract(contract_name, contract_path):
    """Deploy a Vyper contract."""
    # Try to load pre-compiled artifacts first
    abi, bytecode = load_compiled_artifacts(contract_name)
    
    if abi is None or bytecode is None:
        print(f"Compiled artifacts not found. Compiling {contract_name}...")
        abi, bytecode = compile_vyper(contract_path)
    else:
        print(f"Using pre-compiled artifacts for {contract_name}...")
    
    print(f"Deploying {contract_name}...")
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Build transaction
    tx = contract.constructor().build_transaction({
        "from": deployer.address,
        "nonce": w3.eth.get_transaction_count(deployer.address),
        "gas": 2000000,
        "gasPrice": w3.eth.gas_price
    })
    
    # Sign and send
    signed = Account.sign_transaction(tx, DEPLOYER_PK)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    print(f"  Transaction: {w3.to_hex(tx_hash)}")
    
    # Wait for receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = receipt.contractAddress
    
    print(f"✅ {contract_name} deployed at: {contract_address}")
    print(f"   Gas used: {receipt.gasUsed}\n")
    
    return contract_address, abi


def main():
    """Deploy all contracts."""
    contracts_dir = os.path.join(os.path.dirname(__file__), "..", "contracts")
    
    contracts = [
        ("ControlledSpender", os.path.join(contracts_dir, "ControlledSpender.vy")),
        ("StreamCap", os.path.join(contracts_dir, "StreamCap.vy")),
        ("CommitRelease", os.path.join(contracts_dir, "CommitRelease.vy")),
    ]
    
    deployed = {}
    
    for name, path in contracts:
        try:
            address, abi = deploy_contract(name, path)
            deployed[name] = {
                "address": address,
                "abi": abi
            }
        except Exception as e:
            print(f"❌ Failed to deploy {name}: {e}\n")
    
    # Save deployment info
    if deployed:
        output = {
            "network": RPC,
            "chain_id": w3.eth.chain_id,
            "deployer": deployer.address,
            "contracts": {name: {"address": info["address"]} for name, info in deployed.items()}
        }
        
        output_path = os.path.join(os.path.dirname(__file__), "..", "deployments.json")
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"📝 Deployment info saved to: {output_path}")
        print("\n" + "="*60)
        print("Deployment Summary:")
        print("="*60)
        for name, info in deployed.items():
            print(f"{name:20} {info['address']}")


if __name__ == "__main__":
    main()

