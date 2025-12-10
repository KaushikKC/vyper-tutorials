# Getting Started with Vyper

A simple guide to compile and deploy Vyper smart contracts.

## Quick Start

1. **Install Vyper:**
   ```bash
   pip3 install vyper
   ```

2. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Add your contract:**
   - Place your `.vy` file in the `contracts/` folder

4. **Compile manually:**
   ```bash
   # Make sure you're in the get-started directory
   mkdir -p build
   
   # Compile ABI
   python3 -m vyper -f abi contracts/YourContract.vy > build/YourContract.abi
   
   # Compile bytecode
   python3 -m vyper -f bytecode contracts/YourContract.vy > build/YourContract.bin
   ```
   
   **Example with SimpleStorage:**
   ```bash
   python3 -m vyper -f abi contracts/SimpleStorage.vy > build/SimpleStorage.abi
   python3 -m vyper -f bytecode contracts/SimpleStorage.vy > build/SimpleStorage.bin
   ```

5. **Deploy:**
   ```bash
   # Start Anvil in another terminal: anvil
   python3 scripts/deploy.py
   ```

## Project Structure

```
get-started/
├── contracts/          # Add your .vy files here
├── scripts/
│   └── deploy.py       # Deploy contracts
├── build/              # Put compiled .abi and .bin files here
├── requirements.txt
└── README.md
```

