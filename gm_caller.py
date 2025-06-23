import os
import time
import random
import requests
import csv
from web3 import Web3
from dotenv import load_dotenv
from eth_account import Account

load_dotenv()
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
CSV_DIR = "CSV"

def get_user_input(prompt, default=None, input_type=str):
    """Prompt user for input with optional default value and type conversion"""
    while True:
        if default is not None:
            user_input = input(f"{prompt} [default: {default}]: ").strip()
        else:
            user_input = input(f"{prompt}: ").strip()
        
        if not user_input and default is not None:
            return default
        
        if user_input:
            try:
                return input_type(user_input)
            except ValueError:
                print("Invalid input. Please try again.")
        else:
            print("This field is required. Please enter a value.")

def select_mode():
    """Let user select between manual and CSV modes"""
    print("\n🚀 GM Caller - Select Mode")
    print("1. Manual - Enter parameters manually")
    print("2. CSV - Select one configuration from a CSV file")
    print("3. CSV All - Run all configurations from a CSV file sequentially")
    
    while True:
        choice = input("Select mode (1/2/3): ").strip()
        if choice in ('1', '2', '3'):
            return choice
        print("Invalid choice. Please enter 1, 2 or 3.")

def find_csv_files():
    """Find all CSV files in CSV subdirectory"""
    if not os.path.exists(CSV_DIR):
        print(f"\n❌ Directory '{CSV_DIR}' not found")
        return []
    
    if not os.path.isdir(CSV_DIR):
        print(f"\n❌ '{CSV_DIR}' is not a directory")
        return []
    
    csv_files = [f for f in os.listdir(CSV_DIR) if f.endswith('.csv')]
    return csv_files

def select_csv_file():
    """Let user select a CSV file from available options"""
    csv_files = find_csv_files()
    
    if not csv_files:
        print(f"\n❌ No CSV files found in '{CSV_DIR}' directory")
        return None
    
    print(f"\n📂 Available CSV files in '{CSV_DIR}' folder:")
    for i, file in enumerate(csv_files, 1):
        print(f"{i}. {file}")
    
    while True:
        try:
            choice = int(input(f"Select CSV file (1-{len(csv_files)}): ").strip())
            if 1 <= choice <= len(csv_files):
                return os.path.join(CSV_DIR, csv_files[choice-1])
            print(f"Please enter a number between 1 and {len(csv_files)}")
        except ValueError:
            print("Invalid input. Please enter a number.")

def get_manual_config():
    """Get configuration from user in manual mode"""
    print("\n🚀 GM Caller Setup (Manual Mode)")
    print("--------------------")
    return {
        'name': 'Manual Configuration',
        'RPC_URL': get_user_input("Enter node RPC URL"),
        'CHAIN_ID': get_user_input("Enter network Chain ID", input_type=int),
        'CONTRACT_ADDRESS': get_user_input("Enter contract address"),
        'INTERVAL_MIN': get_user_input("Enter minimum interval between transactions (seconds)", default=5, input_type=int),
        'INTERVAL_MAX': get_user_input("Enter maximum interval between transactions (seconds)", default=10, input_type=int),
        'MAX_TRANSACTIONS': get_user_input("Enter number of transactions to execute (0 = unlimited)", default=1, input_type=int)
    }

def get_csv_configs(csv_file):
    """Read configurations from CSV file"""
    if not os.path.exists(csv_file):
        print(f"\n❌ Error: File {csv_file} not found")
        return None
    
    configs = []
    with open(csv_file, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            configs.append({
                'name': row['Chain'],
                'RPC_URL': row['RPC'],
                'CHAIN_ID': int(row['Chain ID']),
                'CONTRACT_ADDRESS': row['Contract'],
                'INTERVAL_MIN': int(row['Time Min']),
                'INTERVAL_MAX': int(row['Time Max']),
                'MAX_TRANSACTIONS': int(row['TXs'])
            })
    
    if not configs:
        print(f"\n❌ Error: No valid configurations found in {csv_file}")
        return None
    
    return configs

def select_csv_config(configs):
    """Let user select configuration from CSV list"""
    print("\n🚀 GM Caller - Available Configurations:")
    for i, config in enumerate(configs, 1):
        print(f"{i}. {config['name']} (ChainID: {config['CHAIN_ID']})")
    
    while True:
        try:
            choice = int(input(f"Select configuration (1-{len(configs)}): ").strip())
            if 1 <= choice <= len(configs):
                return configs[choice-1]
            print(f"Please enter a number between 1 and {len(configs)}")
        except ValueError:
            print("Invalid input. Please enter a number.")

CONTRACT_ABI = [
    {
        "inputs": [],
        "name": "GM",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

def get_random_interval(interval_min, interval_max):
    """Return random value between interval_min and interval_max"""
    return random.randint(interval_min, interval_max)

def get_eth_price():
    try:
        response = requests.get(COINGECKO_API_URL)
        return float(response.json()['ethereum']['usd'])
    except:
        return None

def initialize_web3(rpc_url):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError("Failed to connect to node")
    return w3

def get_gas_parameters(w3, contract, account):
    try:
        w3.eth.default_account = account.address
        gas_estimate = contract.functions.GM().estimate_gas({'from': account.address})
        
        if hasattr(w3.eth, 'max_priority_fee'):
            priority_fee = w3.eth.max_priority_fee
            base_fee = w3.eth.get_block('latest')['baseFeePerGas']
            max_fee = priority_fee + base_fee
            return {
                'type': '0x2',
                'maxFeePerGas': max_fee,
                'maxPriorityFeePerGas': priority_fee,
                'gas': gas_estimate
            }
        else:
            gas_price = w3.eth.gas_price
            return {
                'type': '0x0',
                'gasPrice': gas_price,
                'gas': gas_estimate
            }
    except Exception as e:
        raise Exception(f"Gas estimation error: {str(e)}")

def send_gm_transaction(w3, contract, account, chain_id):
    try:
        gas_params = get_gas_parameters(w3, contract, account)

        tx = {
            'chainId': chain_id,
            'nonce': w3.eth.get_transaction_count(account.address),
            **gas_params
        }
        
        built_tx = contract.functions.GM().build_transaction(tx)
        signed_tx = w3.eth.account.sign_transaction(built_tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        # Calculate transaction fee
        if receipt.type == 2:  # EIP-1559
            fee_wei = receipt.effectiveGasPrice * receipt.gasUsed
        else:  # Legacy
            fee_wei = receipt.gasUsed * gas_params['gasPrice']
            
        return tx_hash.hex(), receipt.gasUsed, fee_wei

    except Exception as e:
        raise Exception(f"Error: {str(e)}")

def run_session(config):
    print(f"\n🚀 GM Caller for {config['name']} (ChainID: {config['CHAIN_ID']})")
    
    try:
        w3 = initialize_web3(config['RPC_URL'])
        account = Account.from_key(PRIVATE_KEY)
        contract = w3.eth.contract(address=config['CONTRACT_ADDRESS'], abi=CONTRACT_ABI)
        eth_price = get_eth_price()

        print(f"\n🔗 Connected to: {config['RPC_URL'][:20]}...{config['RPC_URL'][-6:]}")
        print(f"👛 Address: {account.address}")
        print(f"📜 Contract: {config['CONTRACT_ADDRESS']}")
        print(f"💰 Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")
        if eth_price:
            print(f"💵 Current ETH price: ${eth_price:.2f}")
        print(f"⏳ Transaction interval: {config['INTERVAL_MIN']} - {config['INTERVAL_MAX']} seconds")
        if config['MAX_TRANSACTIONS'] > 0:
            print(f"🔢 Transactions to execute: {config['MAX_TRANSACTIONS']}")
        else:
            print("🔢 Transactions to execute: unlimited")
        print("\n🛑 Ctrl+C to stop\n")

        transaction_count = 0
        total_gas_used = 0 
        total_fee_eth = 0
        
        while True:
            try:
                # Check transaction limit
                if config['MAX_TRANSACTIONS'] > 0 and transaction_count >= config['MAX_TRANSACTIONS']:
                    print(f"\n✅ Reached target transaction count ({config['MAX_TRANSACTIONS']}).")
                    break
                
                tx_hash, gas_used, fee_wei = send_gm_transaction(w3, contract, account, config['CHAIN_ID'])
                fee_eth = w3.from_wei(fee_wei, 'ether')
                transaction_count += 1
                total_gas_used += gas_used
                total_fee_eth += fee_eth                
                
                print(f"\n✅ {time.ctime()} | Transaction #{transaction_count} | Success!")
                print(f"🔗 Tx hash: {tx_hash}")
                print(f"⛽ Gas used: {gas_used}")
                print(f"💸 Fee: {fee_eth:.8f} ETH")
                
                if eth_price:
                    fee_usd = float(fee_eth) * eth_price
                    print(f"💵 Fee (USD): ${fee_usd:.6f}")
                
            except Exception as e:
                print(f"\n❌ {time.ctime()} | Error: {str(e)}")
                if "insufficient funds" in str(e):
                    print("⚠️ Insufficient funds for gas fee!")
                    break
                elif "gas" in str(e).lower():
                    print("⚠️ Gas calculation problem!")
            
            # Check transaction limit before waiting
            if config['MAX_TRANSACTIONS'] > 0 and transaction_count >= config['MAX_TRANSACTIONS']:
                continue
            
            # Use random interval
            sleep_time = get_random_interval(config['INTERVAL_MIN'], config['INTERVAL_MAX'])
            print(f"⏳ Next transaction in {sleep_time} seconds...")
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    except Exception as e:
        print(f"\n💥 Critical error: {str(e)}")
    finally:
        print(f"\n📊 Session Results for {config['name']}:")
        print(f"🔢 Transactions executed: {transaction_count}")
        print(f"⛽ Gas Used: {total_gas_used}")
        print(f"💸 Fees: {total_fee_eth:.8f} ETH")
        if eth_price:
            total_fee_usd = float(total_fee_eth) * eth_price
            print(f"💵 Fees (USD): ${total_fee_usd:.6f}")
        print("Session finished.\n")

def run_all_csv_configs(configs):
    """Run all configurations from CSV sequentially"""
    print(f"\n🚀 Starting CSV All mode with {len(configs)} configurations")
    
    for config in configs:
        print(f"\n🔹 Processing configuration: {config['name']}")
        run_session(config)
        
        # Skip pause after last configuration
        if config != configs[-1]:
            pause_time = get_random_interval(config['INTERVAL_MIN'], config['INTERVAL_MAX'])
            print(f"\n⏳ Preparing next configuration in {pause_time} seconds...")
            time.sleep(pause_time)
    
    print("\n✅ All configurations completed!")

def main():
    while True:
        try:
            mode = select_mode()
            
            if mode == '1':  # Manual mode
                config = get_manual_config()
                run_session(config)
            elif mode == '2':  # CSV single mode
                csv_file = select_csv_file()
                if csv_file:
                    configs = get_csv_configs(csv_file)
                    if configs:
                        config = select_csv_config(configs)
                        run_session(config)
            elif mode == '3':  # CSV All mode
                csv_file = select_csv_file()
                if csv_file:
                    configs = get_csv_configs(csv_file)
                    if configs:
                        run_all_csv_configs(configs)
            
            # Ask user if they want to start a new session
            choice = input("\nDo you want to start a new session? (y/n): ").strip().lower()
            if choice != 'y':
                print("Goodbye!")
                break
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\n💥 Error in main loop: {str(e)}")
            time.sleep(1)

if __name__ == "__main__":
    main()