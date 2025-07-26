# GM-Caller
Python script for executing [GM contracts](https://github.com/StanleyMorgan/GM-Logger).

## Installation

1. **Download project**
   ```bash
   git clone https://github.com/StanleyMorgan/GM-Caller.git
   cd GM-Caller
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate environment**
   - Windows:
     ```bash
     .venv\\Scripts\\activate
     ```
   - Linux/MacOS:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install web3 eth-account python-dotenv
   ```

## Configuration

Create `.env` file:
```ini
PRIVATE_KEY=your_wallet_key_without_0x
```

## Usage
```bash
python gm_caller.py
```

## Structure
```
.
├── .venv/            # Python virtual environment
├── CSV/              # Directory for CSV configs
│   ├── gm_list.csv   # Config 1
│   └── testnets.csv  # Config 2
├── .env              # Environment variables
└── gm_caller.py      # Main script
```
