import os
import time
import random
import requests
from web3 import Web3
from dotenv import load_dotenv
from eth_account import Account

load_dotenv()
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"

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

# Prompt user for configuration
print("🚀 GM Caller Setup")
print("--------------------")
RPC_URL = get_user_input("Enter node RPC URL")
CHAIN_ID = get_user_input("Enter network Chain ID", input_type=int)
CONTRACT_ADDRESS = get_user_input("Enter contract address")
INTERVAL_MIN = get_user_input("Enter minimum interval between transactions (seconds)", default=5, input_type=int)
INTERVAL_MAX = get_user_input("Enter maximum interval between transactions (seconds)", default=10, input_type=int)
MAX_TRANSACTIONS = get_user_input("Enter number of transactions to execute (0 = unlimited)", default=1, input_type=int)

CONTRACT_ABI = [
    {
        "inputs": [],
        "name": "GM",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

def get_random_interval():
    """Return random value between INTERVAL_MIN and INTERVAL_MAX"""
    return random.randint(INTERVAL_MIN, INTERVAL_MAX)

def get_eth_price():
    try:
        response = requests.get(COINGECKO_API_URL)
        return float(response.json()['ethereum']['usd'])
    except:
        return None

def initialize_web3():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
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


def send_gm_transaction(w3, contract, account):
    try:
        gas_params = get_gas_parameters(w3, contract, account)

        tx = {
            'chainId': CHAIN_ID,
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

def main():
    print(f"\n🚀 GM Caller for ChainID: {CHAIN_ID}")
    
    try:
        w3 = initialize_web3()
        account = Account.from_key(PRIVATE_KEY)
        contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
        eth_price = get_eth_price()

        print(f"\n🔗 Connected to: {RPC_URL[:20]}...{RPC_URL[-6:]}")
        print(f"👛 Address: {account.address}")
        print(f"📜 Contract: {CONTRACT_ADDRESS}")
        print(f"💰 Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")
        if eth_price:
            print(f"💵 Current ETH price: ${eth_price:.2f}")
        print(f"⏳ Transaction interval: {INTERVAL_MIN} - {INTERVAL_MAX} seconds")
        if MAX_TRANSACTIONS > 0:
            print(f"🔢 Transactions to execute: {MAX_TRANSACTIONS}")
        else:
            print("🔢 Transactions to execute: unlimited")
        print("\n🛑 Ctrl+C to stop\n")

        transaction_count = 0
        total_gas_used = 0 
        total_fee_eth = 0
        
        while True:
            try:
                # Check transaction limit
                if MAX_TRANSACTIONS > 0 and transaction_count >= MAX_TRANSACTIONS:
                    print(f"\n✅ Reached target transaction count ({MAX_TRANSACTIONS}). Exiting.")
                    break
                
                tx_hash, gas_used, fee_wei = send_gm_transaction(w3, contract, account)
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
            if MAX_TRANSACTIONS > 0 and transaction_count >= MAX_TRANSACTIONS:
                continue
            
            # Use random interval
            sleep_time = get_random_interval()
            print(f"⏳ Next transaction in {sleep_time} seconds...")
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    except Exception as e:
        print(f"\n💥 Critical error: {str(e)}")
    finally:
        print(f"\n📊 Total Results:")
        print(f"🔢 Transactions executed: {transaction_count}")
        print(f"⛽ Gas Used: {total_gas_used}")
        print(f"💸 Fees: {total_fee_eth:.8f} ETH")
        if eth_price:
            total_fee_usd = float(total_fee_eth) * eth_price
            print(f"💵 Fees (USD): ${total_fee_usd:.6f}")
        print("Program finished.")

if __name__ == "__main__":
    main()