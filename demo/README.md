# DID WebVH Server Demo

## Pre-requisite

### Docker compose

Ensure you have docker compose installed. This can be verified with the following command.
`docker compose --version`

Instructions on how to install docker compose can be found here
https://docs.docker.com/compose/install/

### NGROK

We strongly recommend setting up a free ngrok account prior to going through this demo.

You can signup here:
https://dashboard.ngrok.com/

Once your account is created, you need to setup a free static endpoint and grab your API key.

You can setup a free static domain in the domain section once logged in:
https://dashboard.ngrok.com/domains

To get an API key, go to the API key section:
https://dashboard.ngrok.com/api-keys

Once you have your static domain and your API, proceed with the demo.

## Setting up your local deployment

Start by cloning the repository:
```bash
git clone https://github.com/identity-foundation/didwebvh-server-py.git
cd didwebvh-server-py/demo/
```

**Option 1: Quick Start (Recommended)**
```bash
./magic.sh
```

**Option 2: Manual Docker Compose**

Create your `.env` file (optional, has sensible defaults):
```bash
cp .env.example .env
# Edit .env if needed
```

Build and start the services:
```bash
docker compose up --build
```

This will run:
- **DID WebVH Server** on port 8000
- **ACA-Py Agent** with webvh plugin on ports 8020/8021

You can visit the WebVH explorer at `http://localhost:8000/explorer`

## Quick Start with Magic Script 🪄

The fastest way to start the server and run a load test:

```bash
cd demo
./magic.sh
```

This will:
1. Start the DID WebVH server in Docker
2. Wait for it to be healthy
3. Run a load test creating 10 DIDs with credentials
4. Display results and explorer links
5. **Keep the server running** for you to explore (default behavior)

**Common commands:**
```bash
# Quick test (10 DIDs, rebuilds with cache, server stays running)
./magic.sh

# Skip rebuild for faster startup (no code changes)
./magic.sh --no-rebuild

# Medium test (50 DIDs)
./magic.sh -c 50

# Fast concurrent test (100 DIDs)
./magic.sh -c 100 --concurrent

# Full rebuild without cache (clean slate)
./magic.sh --full-rebuild -c 20

# Clean volumes and rebuild
./magic.sh --clean -c 20

# Stop server after test (if needed)
./magic.sh -c 10 --stop

# See all options
./magic.sh --help
```

**After running**, the server stays running by default so you can:
- Browse DIDs: `http://localhost:8000/explorer/dids?namespace=loadtest`
- Browse Credentials: `http://localhost:8000/explorer/credentials?namespace=loadtest`
- Browse Resources: `http://localhost:8000/explorer/resources`

**Rebuild behavior:**
- **Default**: Rebuilds with cache (fast, picks up code changes)
- **--no-rebuild**: Skips rebuild (fastest, use when no code changes)
- **--full-rebuild**: Full rebuild without cache (slow, cleanest)

### Services Deployed

The magic script deploys:
1. **DID WebVH Server** (port 8000) - Main server with explorer UI
2. **ACA-Py Agent** (port 8020/8021) - Controller agent with webvh plugin enabled
   - Admin API: `http://localhost:8020`
   - Inbound transport: `http://localhost:8021`
   - Configured to use local WebVH server
   - Auto-provisioned wallet with askar-anoncreds

## Load Testing

The `load_test.py` script allows you to create multiple DIDs with log entries, WHOIS files, resources, and verifiable credentials for performance testing.

### Running the Load Test

The script must be run from the server directory to access the required dependencies:

```bash
# From the repository root
cd server

# Set the API key for witness registration (optional, defaults to "webvh")
export API_KEY="your-api-key-here"

# Run the load test
uv run python ../demo/load_test.py --help
```

**Note:** The load test automatically registers witness keys using the admin API. Make sure your API key has the necessary permissions.

### Usage Examples

```bash
# Create 10 DIDs with default settings (2 updates + WHOIS + schema each)
uv run python ../demo/load_test.py

# Create 50 DIDs with 3 updates each
uv run python ../demo/load_test.py --count 50 --updates 3

# Create 100 DIDs concurrently (much faster!)
uv run python ../demo/load_test.py -c 100 --concurrent

# Use custom server URL and namespace
uv run python ../demo/load_test.py -c 20 -s http://localhost:8000 -n mytest

# Create 100 DIDs with minimal updates (fastest)
uv run python ../demo/load_test.py -c 100 -u 1 --concurrent
```

### Parameters

- `-c, --count`: Number of DIDs to create (default: 10)
- `-s, --server`: DID WebVH server URL (default: http://localhost:8000)
- `-n, --namespace`: Namespace for test DIDs (default: loadtest)
- `-u, --updates`: Number of updates per DID (default: 2, minimum: 1)
- `--concurrent`: Run tests concurrently using async HTTP (up to 10 DIDs at once for maximum performance)

### What the Load Test Does

For each DID created, the script will:
1. **Register the witness key** in the known witness registry (via admin API)
2. Create an initial DID with witness signature and **watcher configured** (`https://did.observer`)
3. Perform the specified number of updates (each with witness signature)
4. Add a verification method to the DID
5. Create and upload a WHOIS verifiable presentation
6. **Create and upload an AnonCreds schema** as an attested resource
7. **Publish a regular VerifiableCredential** with Data Integrity Proof ✨
8. **Publish an EnvelopedVerifiableCredential** in VC-JOSE format ✨

**DID Configuration:**
- Witness: Registered dynamically for each DID
- Watcher: `https://did.observer` (for monitoring and notification)

**Total log entries per DID**: `updates + 2` (initial + updates + verification method addition)  
**Resources per DID**: 1 AnonCreds schema  
**Credentials per DID**: 2 (1 regular VC + 1 enveloped VC-JOSE) ✨

### Performance Metrics

The script reports:
- Total DIDs created (successful and failed)
- Total execution time
- Average time per DID
- Total log entries created
- Total AnonCreds schemas uploaded
- **Total verifiable credentials published** (regular + enveloped) ✨
- Throughput (DIDs per second)

### Example Output

**Sequential Mode:**
```
══════════════════════════════════════════════════════════════════════
Starting Load Test
Server: http://localhost:8000
DIDs to create: 10
Namespace: loadtest
Updates per DID: 2
Total log entries per DID: 4
Run ID: a1b2c3d4
First identifier: a1b2c3d4-0000
══════════════════════════════════════════════════════════════════════

[1/10] Processing DID a1b2c3d4-0000
✓ Created DID: did:webvh:QmXyz...
  ✓ Update 1 complete
  ✓ Update 2 complete
  ✓ Verification method added
  ✓ WHOIS uploaded
  ✓ Schema uploaded: zQmfKEootUM8GUmgC...

...

Total DIDs: 10
✓ Successful: 10
Total Time: 48.75s
Avg Time per DID: 4.88s
Total Log Entries Created: 40
AnonCreds Schemas Created: 10
Throughput: 0.21 DIDs/second
══════════════════════════════════════════════════════════════════════
```

**Concurrent Mode (--concurrent):**
```
Running tests concurrently...
Max concurrent DIDs: 10

Batch 1: Processing DIDs 0 to 9
✓ [a1b2c3d4-0000] Created DID
✓ [a1b2c3d4-0001] Created DID
✓ [a1b2c3d4-0002] Created DID
  [a1b2c3d4-0000] Update 1/2
  [a1b2c3d4-0001] Update 1/2
  [a1b2c3d4-0003] Created DID
...
Progress: 10/10 completed (10 successful)

Total DIDs: 10
✓ Successful: 10
Total Time: 12.34s  ← Much faster!
Avg Time per DID: 1.23s
Total Log Entries Created: 40
AnonCreds Schemas Created: 10
Throughput: 0.81 DIDs/second  ← 4x improvement!
══════════════════════════════════════════════════════════════════════
```