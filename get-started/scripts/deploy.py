"""
Deploy all compiled Vyper contracts from build/ directory.
Assumes contracts are already compiled (manual or via vyper CLI).
"""

from web3 import Web3
from eth_account import Account
import os
import json

# Configuration
RPC = os.getenv("RPC_URL", "http://127.0.0.1:8545")
DEPLOYER_PK = os.getenv("DEPLOYER_PRIVATE_KEY", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")

w3 = Web3(Web3.HTTPProvider(RPC))
deployer = Account.from_key(DEPLOYER_PK)

print("=" * 60)
print("Deploying Vyper Contracts")
print("=" * 60)
print(f"Deployer: {deployer.address}")
print(f"Network: {RPC}")
print(f"Chain ID: {w3.eth.chain_id}")
print()


def load_compiled_artifacts(contract_name, build_dir):
    """Load ABI and bytecode from build directory."""
    abi_path = os.path.join(build_dir, f"{contract_name}.abi")
    bin_path = os.path.join(build_dir, f"{contract_name}.bin")
    
    if not os.path.exists(abi_path):
        return None, None
    
    if not os.path.exists(bin_path):
        return None, None
    
    with open(abi_path, "r") as f:
        abi = json.load(f)
    
    with open(bin_path, "r") as f:
        bytecode = f.read().strip()
    
    return abi, bytecode


def deploy_contract(contract_name, abi, bytecode):
    """Deploy a contract."""
    print(f"Deploying {contract_name}...")
    
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    tx = contract.constructor().build_transaction({
        "from": deployer.address,
        "nonce": w3.eth.get_transaction_count(deployer.address),
        "gas": 2000000,
        "gasPrice": w3.eth.gas_price
    })
    
    signed = Account.sign_transaction(tx, DEPLOYER_PK)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"  Transaction: {w3.to_hex(tx_hash)}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    address = receipt.contractAddress
    
    print(f"  ✅ Deployed at: {address}")
    print(f"  Gas used: {receipt.gasUsed}")
    print()
    
    return address, abi


def main():
    """Deploy all compiled contracts."""
    # Get paths
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(scripts_dir)
    build_dir = os.path.join(project_root, "build")
    
    if not os.path.exists(build_dir):
        print(f"❌ Build directory not found: {build_dir}")
        print("   Compile your contracts first:")
        print("   python3 -m vyper -f abi contracts/YourContract.vy > build/YourContract.abi")
        print("   python3 -m vyper -f bytecode contracts/YourContract.vy > build/YourContract.bin")
        return 1
    
    # Find all compiled contracts
    abi_files = [f for f in os.listdir(build_dir) if f.endswith('.abi')]
    
    if not abi_files:
        print(f"❌ No compiled contracts found in {build_dir}")
        print("   Compile your contracts first")
        return 1
    
    deployed = {}
    
    for abi_file in abi_files:
        contract_name = os.path.splitext(abi_file)[0]
        
        abi, bytecode = load_compiled_artifacts(contract_name, build_dir)
        
        if abi is None or bytecode is None:
            print(f"⚠️  Skipping {contract_name} - missing ABI or bytecode")
            continue
        
        try:
            address, abi = deploy_contract(contract_name, abi, bytecode)
            deployed[contract_name] = {
                "address": address,
                "abi": abi
            }
        except Exception as e:
            print(f"❌ Failed to deploy {contract_name}: {e}\n")
    
    # Save deployment info
    if deployed:
        output = {
            "network": RPC,
            "chain_id": w3.eth.chain_id,
            "deployer": deployer.address,
            "contracts": {name: {"address": info["address"]} for name, info in deployed.items()}
        }
        
        output_path = os.path.join(project_root, "deployments.json")
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
        
        print("=" * 60)
        print("Deployment Summary")
        print("=" * 60)
        for name, info in deployed.items():
            print(f"{name:20} {info['address']}")
        print()
        print(f"📝 Saved to: {output_path}")
    
    return 0


if __name__ == "__main__":
    exit(main())

