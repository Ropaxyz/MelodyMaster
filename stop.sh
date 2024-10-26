#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping MelodyMaster services...${NC}"

# Stop each screen session
for session in "ngrok" "callback" "bot"; do
    if screen -ls | grep -q "$session"; then
        echo -e "Stopping $session..."
        screen -S $session -X quit
    fi
done

# Kill any remaining ngrok processes
if pgrep ngrok > /dev/null; then
    echo "Cleaning up ngrok processes..."
    pkill ngrok
fi

echo -e "${GREEN}All services stopped${NC}"