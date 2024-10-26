#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}Error: $1 is not installed${NC}"
        echo "Please install $1 and try again"
        exit 1
    fi
}

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${RED}Error: Port $1 is already in use${NC}"
        echo "Please free up port $1 and try again"
        exit 1
    fi
}

# Error handling
set -e

# Print banner
echo -e "${GREEN}"
echo "==============================================="
echo "              MelodyMaster Bot                 "
echo "==============================================="
echo -e "${NC}"

# Check for required commands
echo -e "${YELLOW}Checking dependencies...${NC}"
check_command python3
check_command screen
check_command ngrok

# Check required ports
echo -e "${YELLOW}Checking ports...${NC}"
check_port 8888  # Callback server port
check_port 4040  # ngrok API port

# Setup virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Setting up virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create a .env file with the required environment variables"
    exit 1
fi

# Function to create a screen with venv activated
create_screen() {
    screen -dmS $1 bash -c "source venv/bin/activate && python $2"
}

# Function to check if a screen exists
screen_exists() {
    screen -ls | grep -q "$1"
}

# Kill existing screens
echo -e "${YELLOW}Cleaning up existing sessions...${NC}"
for session in "ngrok" "callback" "bot"; do
    if screen_exists $session; then
        screen -S $session -X quit
    fi
done

# Create directory for logs if it doesn't exist
mkdir -p logs

# Create new screens
echo -e "${YELLOW}Starting ngrok...${NC}"
create_screen ngrok manage_ngrok.py
sleep 2

echo -e "${YELLOW}Starting callback server...${NC}"
create_screen callback callback_server.py
sleep 2

echo -e "${YELLOW}Starting bot...${NC}"
create_screen bot musicboy.py

# Wait for a moment to check if all processes started successfully
sleep 5

# Check if all screens are running
echo -e "\n${YELLOW}Checking services...${NC}"
all_running=true
for session in "ngrok" "callback" "bot"; do
    if ! screen_exists $session; then
        echo -e "${RED}Error: $session failed to start${NC}"
        all_running=false
    fi
done

if $all_running; then
    echo -e "\n${GREEN}All services started successfully!${NC}"
    echo -e "\n${YELLOW}Screen sessions:${NC}"
    screen -ls
    
    echo -e "\n${YELLOW}To view each service:${NC}"
    echo "  ngrok:     screen -r ngrok"
    echo "  callback:  screen -r callback"
    echo "  bot:       screen -r bot"
    echo -e "\n${YELLOW}To detach from a screen:${NC} Press Ctrl+A, then D"
    echo -e "\n${YELLOW}To stop all services:${NC} ./stop.sh"
    
    # Create a stop script if it doesn't exist
    if [ ! -f "stop.sh" ]; then
        cat > stop.sh << 'EOF'
#!/bin/bash
echo "Stopping MelodyMaster services..."
for session in "ngrok" "callback" "bot"; do
    if screen -ls | grep -q "$session"; then
        screen -S $session -X quit
    fi
done
echo "All services stopped"
EOF
        chmod +x stop.sh
    fi
else
    echo -e "\n${RED}Some services failed to start. Check the logs for more information.${NC}"
    exit 1
fi