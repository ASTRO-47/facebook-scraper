#!/usr/bin/env python3
"""
Manual Facebook Login with Virtual Display

This script:
1. Creates a virtual display using Xvfb
2. Starts a VNC server so you can see the browser
3. Opens Chrome/Chromium browser in the virtual display
4. Navigates to Facebook for manual login
5. Saves cookies after you login manually

Usage:
1. Run: python3 login_manual.py
2. Connect to VNC: use VNC viewer to connect to your-server-ip:5901
3. Login manually in the browser
4. Press Ctrl+C when done to save cookies and close

VNC Connection: your-server-ip:5901 (password will be shown)
"""

import asyncio
import os
import json
import signal
import sys
import subprocess
import time
from playwright.async_api import async_playwright

class SimpleX11Login:
    def __init__(self):
        self.cookies_file = "facebook_cookies.json"
        self.browser = None
        self.context = None
        self.page = None
        self.should_close = False
        self.playwright = None
        self.xvfb_process = None
        self.vnc_process = None
        self.display_num = ":1"

    def check_network_setup(self):
        """Check network configuration for VNC access"""
        print("🌐 Checking network setup for VNC access...")
        
        # Check if port 5901 is listening
        port_listening = False
        try:
            # Method 1: Socket test
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 5901))
            sock.close()
            if result == 0:
                port_listening = True
                print("✅ Port 5901 is listening (socket test)")
        except:
            pass
        
        # Method 2: Try netstat if available
        if not port_listening:
            try:
                result = subprocess.run(['netstat', '-an'], capture_output=True, text=True, timeout=5)
                if ':5901' in result.stdout:
                    port_listening = True
                    print("✅ Port 5901 is listening (netstat)")
            except:
                pass
        
        # Method 3: Try ss command
        if not port_listening:
            try:
                result = subprocess.run(['ss', '-an'], capture_output=True, text=True, timeout=5)
                if ':5901' in result.stdout:
                    port_listening = True
                    print("✅ Port 5901 is listening (ss)")
            except:
                pass
        
        if not port_listening:
            print("❌ Port 5901 is not listening")
            return False
        
        # Get server IP addresses
        try:
            ip_result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=5)
            ips = ip_result.stdout.strip().split()
            print(f"🔍 Server IP addresses: {', '.join(ips)}")
            
            # Show connection options
            for ip in ips:
                if not ip.startswith('127.'):  # Skip localhost
                    print(f"   Try connecting to: {ip}:5901")
        except:
            print("⚠️ Could not get server IP addresses")
        
        # Check firewall status
        try:
            ufw_result = subprocess.run(['ufw', 'status'], capture_output=True, text=True, timeout=5)
            if 'Status: active' in ufw_result.stdout:
                if '5901' in ufw_result.stdout:
                    print("✅ Firewall allows port 5901")
                else:
                    print("⚠️ Firewall may be blocking port 5901")
                    print("💡 Run: sudo ufw allow 5901")
            else:
                print("✅ Firewall is inactive")
        except:
            print("⚠️ Could not check firewall status")
        
        # Check if VNC process is running
        try:
            ps_result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
            if 'x11vnc' in ps_result.stdout:
                print("✅ VNC server process is running")
            else:
                print("❌ VNC server process not found")
            return False
        except:
            print("⚠️ Could not check VNC process")
        
        return True

    def install_novnc(self):
        """Install NoVNC system package for web browser access"""
        print("🌐 Setting up NoVNC for web browser access...")
        
        # Check if NoVNC system package is installed
        try:
            result = subprocess.run(['dpkg', '-l', 'novnc'], capture_output=True, timeout=5)
            if result.returncode == 0:
                print("✅ NoVNC system package already installed!")
                return '/usr/share/novnc'
        except:
            pass
        
        try:
            # Install NoVNC system package
            print("📦 Installing NoVNC system package...")
            subprocess.run(['apt', 'update'], check=True, timeout=30)
            subprocess.run(['apt', 'install', '-y', 'novnc'], check=True, timeout=120)
            
            # Also install websockify if not available
            try:
                subprocess.run(['which', 'websockify'], check=True, timeout=5)
            except:
                print("📦 Installing websockify...")
                subprocess.run(['apt', 'install', '-y', 'websockify'], check=True, timeout=60)
            
            print("✅ NoVNC system package installed successfully!")
            return '/usr/share/novnc'
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install NoVNC: {e}")
            return None
        except Exception as e:
            print(f"❌ Error installing NoVNC: {e}")
            return None

    def start_novnc(self, vnc_port, web_port):
        """Start NoVNC web server using system package"""
        novnc_dir = self.install_novnc()
        if not novnc_dir:
            return False
        
        try:
            # Kill any existing websockify processes
            subprocess.run(['pkill', '-f', 'websockify'], capture_output=True)
            time.sleep(1)
        
            # Start websockify in daemon mode (like the working script)
            websockify_cmd = [
                'websockify',
                '-D',  # Daemon mode
                f'--web={novnc_dir}',
                str(web_port),
                f'localhost:{vnc_port}'
            ]
            
            print(f"🚀 Starting NoVNC web server on port {web_port}...")
            print(f"🔧 Command: {' '.join(websockify_cmd)}")
            
            # Start websockify
            result = subprocess.run(websockify_cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✅ NoVNC websockify started successfully!")
                time.sleep(2)  # Give it time to start
            else:
                print(f"❌ websockify failed to start: {result.stderr}")
                return False
            
            # Test if NoVNC is accessible
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex(('localhost', web_port))
                sock.close()
                if result == 0:
                    print(f"✅ NoVNC web server is running on port {web_port}")
                return True
                else:
                    print(f"❌ NoVNC web server is not accessible on port {web_port}")
                    return False
            except Exception as e:
                print(f"❌ Could not test NoVNC web server: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start NoVNC: {e}")
            return False

    def start_simple_web_interface(self, vnc_port, web_port):
        """Start a simple web interface with connection instructions"""
        try:
            # Create a simple HTML page with connection instructions
            html_dir = '/tmp/vnc_web'
            os.makedirs(html_dir, exist_ok=True)
            
            # Get server IP
            try:
                ip_result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                server_ip = ip_result.stdout.strip().split()[0]
            except:
                server_ip = "YOUR_SERVER_IP"
            
            html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>VNC Connection Instructions</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #333; text-align: center; }}
        .connection-info {{
            background: #e8f4f8;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #007acc;
        }}
        .download-links {{
            background: #f0f8f0;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #28a745;
        }}
        .mobile-apps {{
            background: #fff3cd;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #ffc107;
        }}
        .code {{
            background: #f8f9fa;
            padding: 10px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            font-size: 18px;
            color: #d63384;
        }}
        a {{
            color: #007acc;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .status {{
            text-align: center;
            font-size: 14px;
            color: #666;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🖥️ VNC Connection Instructions</h1>
        
        <div class="connection-info">
            <h3>📱 VNC Client Connection</h3>
            <p><strong>Server:</strong> <span class="code">{server_ip}:{vnc_port}</span></p>
            <p><strong>Alternative:</strong> <span class="code">{server_ip}:{vnc_port - 5900}</span> (display number)</p>
            <p><strong>Password:</strong> Not required</p>
        </div>
        
        <div class="download-links">
            <h3>🔗 VNC Client Downloads (Desktop)</h3>
            <ul>
                <li><a href="https://www.realvnc.com/en/connect/download/viewer/" target="_blank">RealVNC Viewer</a> - Most popular, works on Windows/Mac/Linux</li>
                <li><a href="https://www.tightvnc.com/download.php" target="_blank">TightVNC</a> - Free, lightweight option</li>
                <li><a href="https://tigervnc.org/" target="_blank">TigerVNC</a> - Fast, open-source option</li>
                <li><a href="https://uvnc.com/downloads/ultravnc.html" target="_blank">UltraVNC</a> - Windows-focused client</li>
            </ul>
        </div>
        
        <div class="mobile-apps">
            <h3>📱 Mobile VNC Apps</h3>
            <ul>
                <li><strong>iOS:</strong> VNC Viewer, Jump Desktop, Remotix</li>
                <li><strong>Android:</strong> VNC Viewer, bVNC, MultiVNC</li>
            </ul>
        </div>
        
        <div class="connection-info">
            <h3>🔧 Connection Steps</h3>
            <ol>
                <li>Download and install a VNC client from the links above</li>
                <li>Open the VNC client</li>
                <li>Enter server address: <span class="code">{server_ip}:{vnc_port}</span></li>
                <li>Connect (no password required)</li>
                <li>You should see the desktop with Chrome browser open</li>
                <li>Login to Facebook manually in the browser</li>
                <li>Press Ctrl+C in the terminal when done</li>
            </ol>
        </div>
        
        <div class="status">
            <p>🔄 This page refreshes automatically every 30 seconds</p>
            <p>Facebook scraper is running - VNC server active on port {vnc_port}</p>
        </div>
    </div>
    
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(function() {{
            location.reload();
        }}, 30000);
    </script>
</body>
</html>'''
            
            with open(f'{html_dir}/index.html', 'w') as f:
                f.write(html_content)
            
            # Start simple HTTP server
            import http.server
            import socketserver
            import threading
            
            class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=html_dir, **kwargs)
            
            def start_server():
                with socketserver.TCPServer(("0.0.0.0", web_port), SimpleHTTPRequestHandler) as httpd:
                    httpd.serve_forever()
            
            # Start server in background thread
            server_thread = threading.Thread(target=start_server, daemon=True)
            server_thread.start()
            
            time.sleep(1)
            
            # Test if server is accessible
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex(('localhost', web_port))
                sock.close()
                if result == 0:
                    print(f"✅ Simple web interface is running on port {web_port}")
            return True
                else:
                    print(f"❌ Simple web interface is not accessible on port {web_port}")
                    return False
            except Exception as e:
                print(f"❌ Could not test simple web interface: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start simple web interface: {e}")
            return False

    def setup_virtual_display(self):
        """Set up virtual display with Xvfb and VNC server"""
        print("🖥️ Setting up virtual display with VNC access...")
        
        # Clean up any existing processes first
        print("🧹 Cleaning up existing processes...")
        subprocess.run(['pkill', '-f', 'Xvfb.*:1'], capture_output=True)
        subprocess.run(['pkill', '-f', 'x11vnc.*5901'], capture_output=True)
        subprocess.run(['pkill', '-f', 'fluxbox'], capture_output=True)
        time.sleep(2)
        
        # Remove X lock file if it exists
        try:
            os.remove('/tmp/.X1-lock')
        except:
            pass
        
        # Try different display numbers if :1 is busy
        display_numbers = [':1', ':2', ':3', ':4', ':5']
        display_found = False
        
        for display_num in display_numbers:
            try:
                # Check if display is available
                lock_file = f'/tmp/.X{display_num[1:]}-lock'
                if os.path.exists(lock_file):
                    continue
                
                self.display_num = display_num
                print(f"🎯 Trying display {display_num}...")
                break
            except:
                continue
        
        # Install required packages including web interface
        required_packages = ['xvfb', 'x11vnc', 'fluxbox', 'xterm']
        missing_packages = []
        
        for package in required_packages:
            try:
                result = subprocess.run(['dpkg', '-l', package], 
                                      capture_output=True, timeout=5)
                if result.returncode != 0:
                    missing_packages.append(package)
            except:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"📦 Installing {len(missing_packages)} required packages...")
            try:
                subprocess.run(['apt', 'update'], check=True, timeout=30)
                subprocess.run(['apt', 'install', '-y'] + missing_packages, 
                             check=True, timeout=120)
                print("✅ Virtual display packages installed!")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install packages: {e}")
                return False
        
        # Start Xvfb (virtual framebuffer)
        print("🚀 Starting virtual display...")
        try:
            self.xvfb_process = subprocess.Popen([
                'Xvfb', self.display_num, 
                '-screen', '0', '1366x768x24',
                '-ac', '+extension', 'GLX', '+render', '-noreset'
            ])
            time.sleep(2)  # Wait for Xvfb to start
            print(f"✅ Virtual display started on {self.display_num}")
        except Exception as e:
            print(f"❌ Failed to start Xvfb: {e}")
            return False
        
        # Set DISPLAY environment variable
        os.environ['DISPLAY'] = self.display_num
        
        # Start window manager (fluxbox)
        print("🪟 Starting window manager...")
        try:
            subprocess.Popen(['fluxbox'], env=os.environ.copy(), 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
            print("✅ Window manager started!")
        except Exception as e:
            print(f"⚠️ Window manager failed: {e}, continuing anyway...")
        
        # Start VNC server
        print("🔗 Starting VNC server...")
        try:
            # Kill any existing VNC servers on port 5901
            subprocess.run(['pkill', '-f', 'x11vnc.*5901'], capture_output=True)
            subprocess.run(['pkill', '-f', 'x11vnc.*6001'], capture_output=True)
            time.sleep(1)
            
            # Try different VNC ports if 5901 is busy
            vnc_ports = [5901, 5902, 5903, 5904, 5905]
            vnc_port = None
            
            for port in vnc_ports:
                # Check if port is available
                try:
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex(('localhost', port))
                    sock.close()
                    if result != 0:  # Port is available
                        vnc_port = port
                        print(f"🎯 Using VNC port {port}")
                        break
                except:
                    vnc_port = port
                    break
            
            if not vnc_port:
                vnc_port = 5901  # Default fallback
            
            web_port = 6080  # NoVNC web interface port (standard)
            
            # Open firewall ports for both VNC and web interface
            for port in [vnc_port, web_port]:
                try:
                    subprocess.run(['ufw', 'allow', str(port)], capture_output=True)
                    print(f"🔥 Firewall rule added for port {port}")
                except:
                    print(f"⚠️ Could not add firewall rule for port {port} (ufw may not be installed)")
                
                # For Digital Ocean - also try iptables
                try:
                    subprocess.run(['iptables', '-A', 'INPUT', '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT'], 
                                 capture_output=True)
                    print(f"🔥 iptables rule added for port {port}")
                except:
                    print(f"⚠️ Could not add iptables rule for port {port}")
            
            print("\n🌐 IMPORTANT: For Digital Ocean droplets:")
            print(f"   1. Make sure ports {vnc_port} and {web_port} are open in Digital Ocean Firewall")
            print("   2. Go to Digital Ocean Console > Networking > Firewalls")
            print(f"   3. Add inbound rules: TCP ports {vnc_port} and {web_port} from All IPv4/IPv6")
            print(f"   4. Or use: doctl compute firewall add-rules <firewall-id> --inbound-rules protocol:tcp,ports:{vnc_port},address:0.0.0.0/0 --inbound-rules protocol:tcp,ports:{web_port},address:0.0.0.0/0")
            print("")
            
            # Start VNC server with web interface
            print(f"🚀 Starting VNC server on display {self.display_num}...")
            vnc_cmd = [
                'x11vnc', 
                '-display', self.display_num,
                '-forever',           # Keep running
                '-nopw',             # No password
                '-shared',           # Allow multiple connections
                '-rfbport', str(vnc_port),   # VNC port
                '-bg',               # Run in background
                '-o', '/tmp/x11vnc.log',   # Log file
                '-xkb'               # Better keyboard handling
            ]
            
            print(f"🔧 VNC command: {' '.join(vnc_cmd)}")
            
            # Start VNC server
            result = subprocess.run(vnc_cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✅ VNC server started successfully!")
                time.sleep(2)  # Give it time to start
            else:
                print(f"❌ VNC server failed to start. Return code: {result.returncode}")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                print("🔍 Check VNC log: tail /tmp/x11vnc.log")
                return False
            
            # Start noVNC web server
            print("🌐 Starting noVNC web interface...")
            novnc_success = self.start_novnc(vnc_port, web_port)
            if not novnc_success:
                print("⚠️ noVNC web interface failed to start, trying simple web interface...")
                simple_web_success = self.start_simple_web_interface(vnc_port, web_port)
                if simple_web_success:
                    print("✅ Simple web interface started successfully!")
                else:
                    print("❌ Both noVNC and simple web interface failed - VNC client only")
            else:
                simple_web_success = False
            
            # Check if VNC server is running
            print(f"🔍 Testing VNC connection to port {vnc_port}...")
            try:
                # Check if we can connect to the port
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex(('localhost', vnc_port))
                sock.close()
                if result == 0:
                    print(f"✅ VNC server is accessible on port {vnc_port}")
                    
                    # Get server IP
                    try:
                        ip_result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                        server_ip = ip_result.stdout.strip().split()[0]
                        
                        print(f"\n🌐 CONNECTION OPTIONS:")
                        print(f"📱 VNC Client: {server_ip}:{vnc_port}")
                        if novnc_success:
                            print(f"🌐 Web Browser: http://{server_ip}:{web_port}/vnc.html")
                        elif simple_web_success:
                            print(f"🌐 Web Browser: http://{server_ip}:{web_port}")
                        else:
                            print(f"🌐 Web Browser: Not available (web interface setup failed)")
                        print(f"🔑 Password: Not required")
                        
                    except:
                        print(f"\n🌐 CONNECTION OPTIONS:")
                        print(f"📱 VNC Client: YOUR_SERVER_IP:{vnc_port}")
                        if novnc_success:
                            print(f"🌐 Web Browser: http://YOUR_SERVER_IP:{web_port}/vnc.html")
                        elif simple_web_success:
                            print(f"🌐 Web Browser: http://YOUR_SERVER_IP:{web_port}")
                        else:
                            print(f"🌐 Web Browser: Not available (web interface setup failed)")
                        print(f"🔑 Password: Not required")
                    
                    print(f"\n💡 VNC Client apps (RECOMMENDED):")
                    print(f"   • RealVNC Viewer: https://www.realvnc.com/en/connect/download/viewer/")
                    print(f"   • TightVNC: https://www.tightvnc.com/download.php")
                    print(f"   • TigerVNC: https://tigervnc.org/")
                    print(f"   • Mobile: VNC Viewer app (iOS/Android)")
                    
                    if novnc_success:
                        print(f"\n💡 Web Browser (MODERN INTERFACE):")
                        print(f"   • Use: http://YOUR_SERVER_IP:{web_port}/vnc.html")
                        print(f"   • Full-featured web-based VNC client")
                        print(f"   • Works on any device with a web browser")
                    elif simple_web_success:
                        print(f"\n💡 Web Browser (CONNECTION GUIDE):")
                        print(f"   • Use: http://YOUR_SERVER_IP:{web_port}")
                        print(f"   • Shows VNC client download links and instructions")
                        print(f"   • Helpful for getting started with VNC clients")
                    else:
                        print(f"\n💡 Web Browser (NOT AVAILABLE):")
                        print(f"   • Both noVNC and simple web interface failed")
                        print(f"   • Please use a VNC client instead")
                    
                    print(f"\n💡 If VNC client connection fails, try:")
                    print(f"   • {server_ip}:{vnc_port - 5900} (display number)")
                    print(f"   • Check firewall: sudo ufw status")
                    print(f"   • Check Digital Ocean firewall settings")
                    
                    # Test web port too
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(3)
                        web_result = sock.connect_ex(('localhost', web_port))
                        sock.close()
                        if web_result == 0:
                            print(f"✅ Web interface is accessible on port {web_port}")
                        else:
                            print(f"⚠️ Web interface may not be accessible on port {web_port}")
                    except:
                        print(f"⚠️ Could not test web interface port {web_port}")
                    
                    # Run network diagnostics
                    print("\n" + "="*50)
                    self.check_network_setup()
                    print("="*50)
                    
                else:
                    print(f"❌ Cannot connect to VNC port {vnc_port}")
                    print("🔍 Check VNC log: tail /tmp/x11vnc.log")
                    print("🔍 Check VNC process: ps aux | grep x11vnc")
                    return False
            except Exception as e:
                print(f"❌ Error testing VNC connection: {e}")
                print("🔍 Check VNC log: tail /tmp/x11vnc.log")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start VNC server: {e}")
            print("🔍 Manual VNC start command:")
            print(f"   x11vnc -display {self.display_num} -forever -nopw -listen 0.0.0.0 -rfbport 5901 -shared -bg")
            return False
        
            return True

    def cleanup_virtual_display(self):
        """Clean up virtual display and VNC server"""
        print("🧹 Cleaning up virtual display...")
        
        # Kill noVNC/websockify processes
        try:
            subprocess.run(['pkill', '-f', 'websockify'], capture_output=True)
            print("✅ noVNC web server stopped")
        except:
            pass
        
        if self.vnc_process:
            try:
                self.vnc_process.terminate()
                self.vnc_process.wait(timeout=5)
                print("✅ VNC server stopped")
            except:
                try:
                    self.vnc_process.kill()
                except:
                    pass
        
        # Also kill any remaining VNC processes
        try:
            subprocess.run(['pkill', '-f', 'x11vnc'], capture_output=True)
        except:
            pass
        
        if self.xvfb_process:
            try:
                self.xvfb_process.terminate()
                self.xvfb_process.wait(timeout=5)
                print("✅ Virtual display stopped")
            except:
                try:
                    self.xvfb_process.kill()
                except:
                    pass
        
        # Also kill any remaining Xvfb processes
        try:
            subprocess.run(['pkill', '-f', 'Xvfb'], capture_output=True)
        except:
            pass

    def check_system_dependencies(self):
        """Check and install system dependencies for browser operation"""
        print("🔧 Checking system dependencies...")
        
        # Required packages for Chrome/Chromium with X11
        required_packages = [
            'libgtk-3-0', 'libgdk-pixbuf2.0-0', 'libxss1', 'libxrandr2', 
            'libasound2', 'libatk-bridge2.0-0', 'libdrm2', 'libxcomposite1',
            'libxdamage1', 'libxfixes3', 'libxkbcommon0', 'libatspi2.0-0'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                result = subprocess.run(['dpkg', '-l', package], 
                                      capture_output=True, timeout=5)
                if result.returncode != 0:
                    missing_packages.append(package)
            except:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"⚠️ Missing {len(missing_packages)} system packages, installing...")
            try:
                subprocess.run(['apt', 'update'], check=True, timeout=30)
                subprocess.run(['apt', 'install', '-y'] + missing_packages, 
                             check=True, timeout=120)
                print("✅ System dependencies installed successfully!")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Could not install some packages: {e}")
                print("💡 You may need to run: sudo apt update && sudo apt install -y " + " ".join(missing_packages))
        else:
            print("✅ All system dependencies are installed!")

    def check_gtk_modules(self):
        """Check and install missing GTK modules"""
        print("🔧 Checking GTK modules...")
        try:
            # Check if libcanberra-gtk-module is available
            result = subprocess.run(['dpkg', '-l', 'libcanberra-gtk-module'], 
                                  capture_output=True, timeout=10)
            if result.returncode != 0:
                print("⚠️ libcanberra-gtk-module not found, installing...")
                try:
                    subprocess.run(['apt', 'update'], check=True, timeout=30)
                    subprocess.run(['apt', 'install', '-y', 'libcanberra-gtk-module', 'libcanberra-gtk3-module'], 
                                 check=True, timeout=60)
                    print("✅ GTK modules installed successfully!")
                except subprocess.CalledProcessError:
                    print("⚠️ Could not install GTK modules, continuing anyway...")
            else:
                print("✅ GTK modules already installed!")
        except Exception as e:
            print(f"⚠️ GTK module check failed: {e}, continuing anyway...")

    def check_playwright_installation(self):
        """Check if Playwright browsers are installed"""
        print("🎭 Checking Playwright browser installation...")
        try:
            # Check if playwright is available
            result = subprocess.run(['python3', '-m', 'playwright', '--help'], 
                                  capture_output=True, timeout=10)
            if result.returncode == 0:
                print("✅ Playwright is available!")
                return True
            else:
                print("❌ Playwright not available!")
                print("💡 Please install: pip install playwright")
                return False
        except subprocess.TimeoutExpired:
            print("⚠️ Playwright check timed out")
            return False
        except Exception as e:
            print(f"⚠️ Playwright check error: {e}")
            print("💡 Please install: pip install playwright")
            return False

    def setup_interrupt_handler(self):
        """Handle Ctrl+C to save cookies and exit gracefully"""
        def signal_handler(signum, frame):
            print(f"\n🛑 Interrupt received! Saving cookies and closing...")
            self.should_close = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def save_cookies(self):
        """Save browser cookies to file"""
        try:
            if self.context:
                cookies = await self.context.cookies()
                with open(self.cookies_file, 'w') as f:
                    json.dump(cookies, f, indent=2)
                print(f"✅ Cookies saved to: {self.cookies_file}")
                print(f"📊 Saved {len(cookies)} cookies")
                return True
        except Exception as e:
            print(f"❌ Error saving cookies: {e}")
            return False

    async def load_existing_cookies(self):
        """Load existing cookies if available"""
        try:
            if os.path.exists(self.cookies_file) and self.context:
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                await self.context.add_cookies(cookies)
                print(f"✅ Loaded {len(cookies)} existing cookies from file")
                return True
            else:
                print("💾 Using persistent browser profile - cookies will be saved automatically")
                return True
        except Exception as e:
            print(f"⚠️ Could not load existing cookies: {e}")
            print("💾 Browser profile will handle cookie persistence")
            return False

    async def open_facebook_browser(self):
        """Open browser and navigate to Facebook"""
        print("🚀 Launching browser in virtual display...")
        
        try:
            # Launch Playwright
            self.playwright = await async_playwright().start()
            
            # Create user data directory for persistent profile
            user_data_dir = os.path.abspath("./browser_profile")
            os.makedirs(user_data_dir, exist_ok=True)
            print(f"📁 Using browser profile: {user_data_dir}")
            
            # Set up browser args optimized for virtual display
            browser_args = [
                # Security and sandbox
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--no-first-run',
                
                # Basic optimizations
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-field-trial-config',
                '--disable-ipc-flooding-protection',
                
                # Automation and stealth
                '--disable-blink-features=AutomationControlled',
                
                # Performance
                '--memory-pressure-off',
                '--max_old_space_size=4096',
                '--disable-extensions',
                '--disable-default-apps',
                '--disable-sync',
                
                # Audio fixes
                '--no-audio-output',
                '--disable-audio-output',
                
                # Additional stability flags
                '--disable-crash-reporter',
                '--disable-logging',
                '--disable-breakpad',
                '--disable-hang-monitor',
                
                # Virtual display optimization
                '--force-device-scale-factor=1',
                '--disable-background-networking'
            ]
            
            # Launch browser with persistent context (will appear in VNC)
            print("🌐 Starting browser process...")
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,  # MUST be False to see in VNC
                args=browser_args,
                timeout=60000,  # 60 second timeout
                slow_mo=50,  # Small delay for stability
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ignore_https_errors=True,
                java_script_enabled=True,
                accept_downloads=True
            )
            
            print("✅ Browser launched successfully!")
            
            # Get the browser instance from the context
            self.browser = self.context.browser
            
            # Load existing cookies if any (for backup JSON file)
            await self.load_existing_cookies()
            
            # Create new page
            self.page = await self.context.new_page()
            
            # Add basic stealth
            await self.page.evaluate("""
                Object.defineProperty(navigator, 'webdriver', {get: () => false});
                delete window.chrome;
            """)
            
            print("🌐 Navigating to Facebook...")
            await self.page.goto('https://www.facebook.com', wait_until='domcontentloaded', timeout=30000)
            
            print("\n" + "="*60)
            print("📱 BROWSER IS NOW OPEN IN VIRTUAL DISPLAY!")
            print("="*60)
            print("🔗 VNC CONNECTION INFO:")
            print(f"   Server: YOUR_SERVER_IP:5901")
            print(f"   Display: {self.display_num}")
            print(f"   Password: Not required")
            print("="*60)
            print("👆 Complete these steps:")
            print("1. 🖥️ Connect to VNC using a VNC viewer")
            print("2. 🔐 Login to Facebook manually in the browser")
            print("3. ✅ Complete any security checks") 
            print("4. 🏠 Make sure you reach the main Facebook page")
            print("5. ⌨️ Press Ctrl+C in this terminal when done")
            print("="*60)
            print("💾 Using persistent browser profile at: ./browser_profile/")
            print("🍪 Cookies will be automatically saved to the profile!")
            print("="*60)
            
            # Wait for user interrupt
            try:
                while not self.should_close:
                    await asyncio.sleep(1)
            except:
                pass
            
        except Exception as e:
            print(f"❌ Error launching browser: {e}")
            
            # Provide specific troubleshooting based on error type
            error_str = str(e).lower()
            if "timeout" in error_str:
                print("💡 Browser launch timed out. This usually means:")
                print("   - Virtual display not properly started")
                print("   - VNC server connection issues")
                print("   - Missing display dependencies")
                print("\n🔧 Try these fixes:")
                print("   1. Check if Xvfb is running: ps aux | grep Xvfb")
                print("   2. Check if VNC is running: ps aux | grep x11vnc")
                print("   3. Test VNC connection: telnet localhost 5901")
                print("   4. Restart the script")
            else:
                print("💡 General browser launch issues:")
                print("   - Virtual display setup failed")
            print("   - Playwright browsers not installed")
                print("   - Missing system dependencies")
                print("\n🔧 General troubleshooting:")
                print("   1. Install packages: apt install -y xvfb x11vnc fluxbox")
                print("   2. Install browsers: python3 -m playwright install chromium")
                print("   3. Check display: echo $DISPLAY")
            
            raise e
        
        finally:
            # Save cookies before closing
            await self.save_cookies()
            
            # Close browser context
            if self.context:
                try:
                    await self.context.close()
                    print("✅ Browser closed successfully!")
                    print("💾 Cookies saved in both profile and JSON file!")
                except:
                    print("⚠️ Browser may not have closed properly")
            
            if self.playwright:
                try:
                    await self.playwright.stop()
                except:
                    print("⚠️ Playwright may not have stopped properly")
            
            # Clean up virtual display
            self.cleanup_virtual_display()

    async def run(self):
        """Main execution"""
        print("\n🖥️  FACEBOOK MANUAL LOGIN - VIRTUAL DISPLAY + VNC")
        print("="*60)
        
        # Set up virtual display with VNC
        if not self.setup_virtual_display():
            print("\n❌ Virtual display setup failed. Please:")
            print("1. Install required packages: apt install -y xvfb x11vnc fluxbox xterm")
            print("2. Check if ports are available: netstat -an | grep 5901")
            print("3. Try again")
            return False
        
        # Check Playwright installation
        if not self.check_playwright_installation():
            print("\n❌ Playwright setup failed. Please:")
            print("1. Install Playwright: pip install playwright")
            print("2. Install browsers: python3 -m playwright install chromium")
            print("3. Try again")
            return False
        
        # Setup interrupt handler
        self.setup_interrupt_handler()
        
        # Open browser for manual login
        await self.open_facebook_browser()
        
        return True

async def main():
    """Entry point"""
    login = SimpleX11Login()
    try:
        result = await login.run()
        if result:
            print("\n🎉 Login session completed!")
            print("💾 Cookies are saved for future automation")
            return True
        else:
            print("\n❌ Login session failed!")
            return False
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Install VNC packages: apt install -y xvfb x11vnc fluxbox xterm")
        print("2. Check if VNC port is available: netstat -an | grep 5901")
        print("3. Test VNC connection locally: telnet localhost 5901")
        print("4. Check virtual display: echo $DISPLAY")
        print("5. Install Playwright browsers: python3 -m playwright install chromium")
        print("6. Check firewall: sudo ufw allow 5901")
        print("7. Check VNC log: tail /tmp/x11vnc.log")
        print("8. Get server IP: hostname -I")
        print("9. Try different VNC clients (RealVNC, TightVNC, etc.)")
        print("10. If using cloud provider, check security groups/firewall rules")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            print("\n✅ Script completed successfully!")
        else:
            print("\n❌ Script failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1) 