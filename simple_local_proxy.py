#!/usr/bin/env python3
"""
Simple SSH SOCKS Proxy Setup for Digital Ocean
Run this ONLY on your Digital Ocean server
"""
import subprocess
import sys
import requests
import time
import argparse
import signal
import os

def create_socks_proxy(local_host, local_user, local_port=8888, ssh_key=None, ssh_port=22):
    """Create SSH SOCKS proxy to local machine"""
    print(f"🌊 Creating SOCKS proxy to {local_user}@{local_host}:{ssh_port}...")
    
    # Build SSH command for SOCKS proxy
    ssh_cmd = [
        'ssh',
        '-D', str(local_port),  # SOCKS proxy on this port
        '-N',  # Don't execute remote command
        '-p', str(ssh_port),  # SSH port
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        '-o', 'ServerAliveInterval=60',
        '-o', 'ServerAliveCountMax=3',
    ]
    
    if ssh_key:
        ssh_cmd.extend(['-i', ssh_key])
    
    ssh_cmd.append(f'{local_user}@{local_host}')
    
    print(f"🚀 Running: {' '.join(ssh_cmd)}")
    
    # Start SSH SOCKS proxy
    process = subprocess.Popen(ssh_cmd)
    
    # Wait for connection to establish
    time.sleep(3)
    
    # Check if process is still running
    if process.poll() is None:
        print(f"✅ SOCKS proxy established on port {local_port}")
        return process
    else:
        print("❌ Failed to establish SOCKS proxy")
        return None

def test_socks_proxy(port=9999):
    """Test if SOCKS proxy is working"""
    print(f"🧪 Testing SOCKS proxy on port {port}...")
    
    try:
        # Test with curl command
        result = subprocess.run([
            'curl', '--socks5', f'127.0.0.1:{port}', 
            'http://httpbin.org/ip', '--max-time', '10'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            ip = data.get('origin', 'Unknown')
            print(f"✅ SOCKS proxy working! Your IP appears as: {ip}")
            return True
        else:
            print(f"❌ SOCKS proxy test failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def update_scraper_proxy(port=9999):
    """Update scraper to use SOCKS proxy"""
    print("🔧 Updating scraper to use SOCKS proxy...")
    
    try:
        # Update the proxy manager
        from scraper.proxy_manager import proxy_manager
        proxy_manager.enable_socks_proxy(port)
        
        print(f"✅ Scraper updated to use SOCKS proxy: socks5://127.0.0.1:{port}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update scraper: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Setup SSH SOCKS Proxy')
    parser.add_argument('--local-host', required=True, help='Your local machine IP')
    parser.add_argument('--local-user', required=True, help='Your local machine username')
    parser.add_argument('--local-port', type=int, default=9999, help='SOCKS proxy port')
    parser.add_argument('--ssh-port', type=int, default=22, help='SSH port on local machine')
    parser.add_argument('--ssh-key', help='SSH private key path')
    parser.add_argument('--test-only', action='store_true', help='Only test existing proxy')
    
    args = parser.parse_args()
    
    if args.test_only:
        success = test_socks_proxy(args.local_port)
        sys.exit(0 if success else 1)
    
    print("🌊 Digital Ocean SSH SOCKS Proxy Setup")
    print("=" * 50)
    
    # Create SOCKS proxy
    process = create_socks_proxy(args.local_host, args.local_user, args.local_port, args.ssh_key, args.ssh_port)
    
    if not process:
        print("❌ Failed to create SOCKS proxy")
        sys.exit(1)
    
    # Test the proxy
    if not test_socks_proxy(args.local_port):
        print("❌ SOCKS proxy test failed")
        process.terminate()
        sys.exit(1)
    
    # Update scraper
    if not update_scraper_proxy(args.local_port):
        print("❌ Failed to update scraper")
        process.terminate()
        sys.exit(1)
    
    print("\n🎉 Setup complete!")
    print(f"✅ Facebook scraper will now use your home IP")
    print(f"✅ SOCKS proxy running on port {args.local_port}")
    print("\n🚀 You can now run: python3 main.py")
    print("\n🛑 Press Ctrl+C to stop the proxy")
    
    # Handle cleanup
    def signal_handler(sig, frame):
        print("\n🛑 Stopping SOCKS proxy...")
        process.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Keep proxy alive
    try:
        process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping SOCKS proxy...")
        process.terminate()

if __name__ == "__main__":
    main() 