# GM-Caller
Python script for executing GM contracts.

## Installation

1. **Extract project**
   ```bash
   unzip gm-caller.zip && cd gm-caller
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
   pip install web3 python-dotenv
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
├── .venv/
├── .env
├── gm_caller.py
└── gm_list.csv
```
