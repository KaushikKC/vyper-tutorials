"""
Compilation script for Vyper contracts.
Compiles all contracts and saves artifacts to build/ directory.
"""

import os
import subprocess
import sys

def compile_contract(contract_name, contract_path, build_dir):
    """Compile a single Vyper contract."""
    print(f"Compiling {contract_name}...")
    
    abi_path = os.path.join(build_dir, f"{contract_name}.abi")
    bin_path = os.path.join(build_dir, f"{contract_name}.bin")
    
    try:
        # Compile ABI
        abi_result = subprocess.run(
            ["python3", "-m", "vyper", "-f", "abi", contract_path],
            capture_output=True,
            text=True,
            check=True
        )
        with open(abi_path, "w") as f:
            f.write(abi_result.stdout)
        
        # Compile bytecode
        bytecode_result = subprocess.run(
            ["python3", "-m", "vyper", "-f", "bytecode", contract_path],
            capture_output=True,
            text=True,
            check=True
        )
        with open(bin_path, "w") as f:
            f.write(bytecode_result.stdout.strip())
        
        print(f"  ✅ ABI: {abi_path}")
        print(f"  ✅ Bytecode: {bin_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Compilation failed: {e.stderr}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    """Compile all contracts."""
    # Get paths
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(scripts_dir)
    contracts_dir = os.path.join(project_root, "contracts")
    build_dir = os.path.join(project_root, "build")
    
    # Create build directory
    os.makedirs(build_dir, exist_ok=True)
    
    # Contracts to compile
    contracts = [
        ("ControlledSpender", os.path.join(contracts_dir, "ControlledSpender.vy")),
        ("StreamCap", os.path.join(contracts_dir, "StreamCap.vy")),
        ("CommitRelease", os.path.join(contracts_dir, "CommitRelease.vy")),
    ]
    
    print("=" * 60)
    print("Vyper Contract Compilation")
    print("=" * 60)
    print()
    
    success_count = 0
    for name, path in contracts:
        if not os.path.exists(path):
            print(f"❌ Contract file not found: {path}")
            continue
        
        if compile_contract(name, path, build_dir):
            success_count += 1
        print()
    
    print("=" * 60)
    print(f"Compilation complete: {success_count}/{len(contracts)} contracts compiled")
    print("=" * 60)
    
    if success_count < len(contracts):
        sys.exit(1)


if __name__ == "__main__":
    main()

