// MetaMask Integration for IoMT-Blockchain Health Monitoring System

// Global variables
let currentAccount = null;
let web3 = null;

// Check if MetaMask is installed
async function checkMetaMaskInstalled() {
    if (typeof window.ethereum !== 'undefined') {
        console.log('MetaMask is installed!');
        return true;
    } else {
        console.log('MetaMask is not installed!');
        document.getElementById('metamask-status').innerHTML = 
            '<div class="alert alert-danger">MetaMask is not installed. Please install MetaMask to use blockchain features.</div>';
        return false;
    }
}

// Connect to MetaMask
async function connectMetaMask() {
    console.log("Connect MetaMask button clicked");
    if (await checkMetaMaskInstalled()) {
        try {
            // Request account access
            console.log("Requesting MetaMask accounts...");
            const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
            currentAccount = accounts[0];
            console.log("Connected to MetaMask account:", currentAccount);
            
            // Update UI
            document.getElementById('metamask-status').innerHTML = 
                `<div class="alert alert-success">Connected to MetaMask: ${currentAccount}</div>`;
            document.getElementById('metamask-connect').innerText = 'Connected';
            document.getElementById('metamask-connect').disabled = true;
            
            // Send the address to the server for authentication
            console.log("Starting authentication process...");
            await authenticateWithMetaMask(currentAccount);
            
            return currentAccount;
        } catch (error) {
            console.error('Error connecting to MetaMask:', error);
            document.getElementById('metamask-status').innerHTML = 
                `<div class="alert alert-danger">Error connecting to MetaMask: ${error.message}</div>`;
            return null;
        }
    }
}

// Authenticate with MetaMask
async function authenticateWithMetaMask(address) {
    try {
        console.log("Requesting nonce for address:", address);
        // Get the nonce from the server
        const response = await fetch('/api/get_nonce?address=' + address);
        const data = await response.json();
        const nonce = data.nonce;
        console.log("Received nonce:", nonce);
        
        // Sign the nonce with MetaMask
        console.log("Requesting signature from MetaMask...");
        const message = `I am signing my one-time nonce: ${nonce}`;
        console.log("Message to sign:", message);
        
        const signature = await window.ethereum.request({
            method: 'personal_sign',
            params: [
                message,
                address
            ]
        });
        console.log("Signature received:", signature);
        
        // Send the signature to the server for verification
        console.log("Sending signature to server for verification...");
        const authResponse = await fetch('/api/verify_signature', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                address: address,
                signature: signature,
                nonce: nonce
            })
        });
        
        const authData = await authResponse.json();
        console.log("Authentication response:", authData);
        
        if (authData.authenticated) {
            console.log('Successfully authenticated with MetaMask!');
            // Redirect to dashboard or update UI
            window.location.href = '/dashboard';
        } else {
            console.error('Authentication failed:', authData.error);
            document.getElementById('metamask-status').innerHTML = 
                `<div class="alert alert-danger">Authentication failed: ${authData.error || 'Unknown error'}</div>`;
        }
    } catch (error) {
        console.error('Error authenticating with MetaMask:', error);
        document.getElementById('metamask-status').innerHTML = 
            `<div class="alert alert-danger">Error authenticating: ${error.message}</div>`;
    }
}

// Initialize MetaMask
window.addEventListener('DOMContentLoaded', async () => {
    console.log("Page loaded, checking for MetaMask...");
    await checkMetaMaskInstalled();
    
    // Listen for account changes
    if (window.ethereum) {
        window.ethereum.on('accountsChanged', (accounts) => {
            if (accounts.length === 0) {
                // User disconnected from MetaMask
                currentAccount = null;
                document.getElementById('metamask-status').innerHTML = 
                    '<div class="alert alert-warning">Disconnected from MetaMask</div>';
                document.getElementById('metamask-connect').innerText = 'Connect MetaMask';
                document.getElementById('metamask-connect').disabled = false;
            } else {
                currentAccount = accounts[0];
                document.getElementById('metamask-status').innerHTML = 
                    `<div class="alert alert-success">Connected to MetaMask: ${currentAccount}</div>`;
            }
        });
    }
});
