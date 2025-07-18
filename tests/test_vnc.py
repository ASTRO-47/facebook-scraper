#!/usr/bin/env python3
"""
Simple VNC Test Script

This script tests the VNC setup without launching the browser.
Use this to verify VNC connection works before running the main script.
"""

import subprocess
import time
import os
import signal
import sys

def test_vnc_setup():
    """Test VNC setup"""
    print("🧪 Testing VNC Setup")
    print("="*40)
    
    xvfb_process = None
    vnc_process = None
    
    try:
        # Start Xvfb
        print("🚀 Starting virtual display...")
        xvfb_process = subprocess.Popen([
            'Xvfb', ':1', 
            '-screen', '0', '1920x1080x24',
            '-ac', '+extension', 'GLX'
        ])
        time.sleep(2)
        
        # Set DISPLAY
        os.environ['DISPLAY'] = ':1'
        print("✅ Virtual display started")
        
        # Start window manager
        print("🪟 Starting window manager...")
        subprocess.Popen(['fluxbox'], env=os.environ.copy())
        time.sleep(1)
        
        # Start VNC server
        print("🔗 Starting VNC server...")
        vnc_process = subprocess.Popen([
            'x11vnc', 
            '-display', ':1',
            '-forever',
            '-nopw',
            '-listen', '0.0.0.0',
            '-rfbport', '5901',
            '-shared',
            '-geometry', '1920x1080',
            '-depth', '24',
            '-noxrecord',
            '-noxfixes',
            '-noxdamage',
            '-rfbauth', '/dev/null',
            '-o', '/tmp/x11vnc_test.log'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        time.sleep(3)
        
        # Check if VNC is running
        try:
            # Try multiple methods to check if VNC is running
            vnc_running = False
            
            # Method 1: Check if we can connect to the port
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', 5901))
                sock.close()
                if result == 0:
                    vnc_running = True
                    print("✅ VNC server is running on port 5901 (socket test)")
            except:
                pass
            
            # Method 2: Check process list
            if not vnc_running:
                try:
                    ps_result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
                    if 'x11vnc' in ps_result.stdout and '5901' in ps_result.stdout:
                        vnc_running = True
                        print("✅ VNC server process found (ps test)")
                except:
                    pass
            
            # Method 3: Try netstat if available
            if not vnc_running:
                try:
                    result = subprocess.run(['netstat', '-an'], capture_output=True, text=True, timeout=5)
                    if ':5901' in result.stdout:
                        vnc_running = True
                        print("✅ VNC server is running on port 5901 (netstat test)")
                except:
                    pass
            
            # Method 4: Try ss command (modern replacement for netstat)
            if not vnc_running:
                try:
                    result = subprocess.run(['ss', '-an'], capture_output=True, text=True, timeout=5)
                    if ':5901' in result.stdout:
                        vnc_running = True
                        print("✅ VNC server is running on port 5901 (ss test)")
                except:
                    pass
            
            if vnc_running:
                # Get server IP
                try:
                    ip_result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                    server_ip = ip_result.stdout.strip().split()[0]
                    print(f"🌐 Connect to: {server_ip}:5901")
                except:
                    print("🌐 Connect to: YOUR_SERVER_IP:5901")
                
                print("\n" + "="*40)
                print("✅ VNC TEST SUCCESSFUL!")
                print("="*40)
                print("Now try connecting with your VNC client.")
                print("You should see a desktop with a window manager.")
                print("Press Ctrl+C to stop the test.")
                print("="*40)
                
                # Keep running until interrupted
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n🛑 Test interrupted by user")
                    
            else:
                print("❌ VNC server not detected on port 5901")
                print("🔍 Check log: tail /tmp/x11vnc_test.log")
                print("🔍 Check VNC process: ps aux | grep x11vnc")
                
        except Exception as e:
            print(f"❌ Error checking VNC status: {e}")
            print("🔍 Check log: tail /tmp/x11vnc_test.log")
            
    except Exception as e:
        print(f"❌ Error during VNC test: {e}")
        
    finally:
        # Cleanup
        print("🧹 Cleaning up...")
        if vnc_process:
            try:
                vnc_process.terminate()
                vnc_process.wait(timeout=5)
            except:
                try:
                    vnc_process.kill()
                except:
                    pass
        
        if xvfb_process:
            try:
                xvfb_process.terminate()
                xvfb_process.wait(timeout=5)
            except:
                try:
                    xvfb_process.kill()
                except:
                    pass
        
        print("✅ Cleanup complete")

if __name__ == "__main__":
    try:
        test_vnc_setup()
    except KeyboardInterrupt:
        print("\n👋 Test cancelled")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1) 