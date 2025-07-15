"""
Free Proxy Manager for Morocco IP addresses
Fetches and manages free proxies to make Facebook think you're connecting from Morocco
Now supports local proxy through SSH tunnel for residential IP routing
"""
import asyncio
import aiohttp
import random
import json
import time
import subprocess
import requests
from typing import List, Dict, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('proxy_manager')

class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.working_proxies = []
        self.current_proxy_index = 0
        self.last_fetch_time = 0
        self.fetch_interval = 3600  # Refresh proxies every hour
        
        # Local proxy settings
        self.local_proxy_enabled = False
        self.local_proxy_url = None
        self.ssh_tunnel_process = None
        
    def enable_local_proxy(self, tunnel_port: int = 9999):
        """Enable local proxy through SSH tunnel"""
        # Check if it's a SOCKS proxy (for SSH tunnels)
        if hasattr(self, '_socks_proxy') and self._socks_proxy:
            self.local_proxy_url = f"socks5://127.0.0.1:{tunnel_port}"
        else:
            self.local_proxy_url = f"http://127.0.0.1:{tunnel_port}"
        
        self.local_proxy_enabled = True
        logger.info(f"Local proxy enabled: {self.local_proxy_url}")
        
    def enable_socks_proxy(self, tunnel_port: int = 9999):
        """Enable SOCKS5 proxy for SSH tunnels"""
        self._socks_proxy = True
        self.local_proxy_enabled = True
        self.local_proxy_url = f"socks5://127.0.0.1:{tunnel_port}"
        logger.info(f"SOCKS5 proxy enabled: {self.local_proxy_url}")
        
    def disable_local_proxy(self):
        """Disable local proxy and cleanup SSH tunnel"""
        self.local_proxy_enabled = False
        self.local_proxy_url = None
        if self.ssh_tunnel_process:
            self.cleanup_ssh_tunnel()
        logger.info("Local proxy disabled")
        
    def setup_ssh_tunnel(self, local_user: str, local_host: str, 
                        tunnel_port: int = 9999, local_port: int = 8888,
                        ssh_key_path: str = None) -> bool:
        """Set up SSH tunnel to local proxy"""
        try:
            # Build SSH command
            ssh_cmd = [
                'ssh',
                '-N',  # Don't execute remote command
                '-R', f'{tunnel_port}:127.0.0.1:{local_port}',  # Reverse tunnel
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'ServerAliveInterval=60',
                '-o', 'ServerAliveCountMax=3',
            ]
            
            if ssh_key_path:
                ssh_cmd.extend(['-i', ssh_key_path])
            
            ssh_cmd.append(f'{local_user}@{local_host}')
            
            logger.info(f"Creating SSH tunnel: {' '.join(ssh_cmd)}")
            
            # Start SSH tunnel
            self.ssh_tunnel_process = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Give tunnel time to establish
            time.sleep(3)
            
            # Check if tunnel is working
            if self.ssh_tunnel_process.poll() is None:
                logger.info("SSH tunnel established successfully")
                self.enable_local_proxy(tunnel_port)
                return True
            else:
                stderr = self.ssh_tunnel_process.stderr.read().decode()
                logger.error(f"SSH tunnel failed: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating SSH tunnel: {e}")
            return False
            
    def cleanup_ssh_tunnel(self):
        """Clean up SSH tunnel"""
        if self.ssh_tunnel_process and self.ssh_tunnel_process.poll() is None:
            logger.info("Terminating SSH tunnel...")
            self.ssh_tunnel_process.terminate()
            try:
                self.ssh_tunnel_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ssh_tunnel_process.kill()
            self.ssh_tunnel_process = None
            
    def test_local_proxy(self) -> bool:
        """Test if local proxy is working"""
        if not self.local_proxy_enabled or not self.local_proxy_url:
            return False
        
        try:
            # Handle SOCKS5 proxy testing
            if self.local_proxy_url.startswith('socks5://'):
                # Test SOCKS5 proxy using curl
                import subprocess
                port = self.local_proxy_url.split(':')[-1]
                result = subprocess.run([
                    'curl', '--socks5', f'127.0.0.1:{port}',
                    'http://httpbin.org/ip', '--max-time', '10'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    import json
                    data = json.loads(result.stdout)
                    ip = data.get('origin', 'Unknown')
                    logger.info(f"✅ SOCKS5 proxy working! IP: {ip}")
                    return True
                else:
                    logger.error(f"SOCKS5 proxy test failed: {result.stderr}")
                    return False
            
            # Handle HTTP proxy testing (original code)
            else:
                response = requests.get(
                    'http://httpbin.org/ip',
                    proxies={
                        'http': self.local_proxy_url,
                        'https': self.local_proxy_url
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    ip_info = response.json()
                    logger.info(f"✅ HTTP proxy working! IP: {ip_info.get('origin')}")
                    return True
                else:
                    logger.error(f"HTTP proxy test failed with status: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Local proxy test failed: {e}")
            return False
    
    async def fetch_free_proxies(self) -> List[Dict[str, str]]:
        """Fetch free proxies from multiple sources"""
        proxies = []
        
        # Source 1: ProxyList API (supports country filtering)
        try:
            proxies.extend(await self._fetch_from_proxylist_api())
        except Exception as e:
            logger.warning(f"Failed to fetch from ProxyList API: {e}")
        
        # Source 2: Free Proxy List
        try:
            proxies.extend(await self._fetch_from_free_proxy_list())
        except Exception as e:
            logger.warning(f"Failed to fetch from Free Proxy List: {e}")
        
        # Source 3: Backup hardcoded working proxies (general purpose)
        proxies.extend(self._get_backup_proxies())
        
        logger.info(f"Fetched {len(proxies)} proxies total")
        return proxies
    
    async def _fetch_from_proxylist_api(self) -> List[Dict[str, str]]:
        """Fetch proxies from proxy-list.download API"""
        proxies = []
        urls = [
            # Try Morocco-specific first
            "https://www.proxy-list.download/api/v1/get?type=http&country=MA",
            "https://www.proxy-list.download/api/v1/get?type=https&country=MA",
            # Fallback to nearby countries (Algeria, Tunisia)
            "https://www.proxy-list.download/api/v1/get?type=http&country=DZ",
            "https://www.proxy-list.download/api/v1/get?type=http&country=TN",
            # General Arabic region
            "https://www.proxy-list.download/api/v1/get?type=http&anon=elite",
        ]
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            for url in urls:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            proxy_list = await response.text()
                            for line in proxy_list.strip().split('\n'):
                                if ':' in line:
                                    ip, port = line.strip().split(':')
                                    proxies.append({
                                        'ip': ip,
                                        'port': port,
                                        'type': 'http',
                                        'country': 'MA',  # Assume Morocco for API results
                                        'source': 'proxy-list-api'
                                    })
                        if len(proxies) >= 20:  # Limit to avoid too many
                            break
                except Exception as e:
                    logger.warning(f"Failed to fetch from {url}: {e}")
                    continue
        
        return proxies[:20]  # Return max 20 proxies
    
    async def _fetch_from_free_proxy_list(self) -> List[Dict[str, str]]:
        """Fetch proxies from free-proxy-list.net"""
        proxies = []
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                # Try different proxy list APIs
                urls = [
                    "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=MA&format=textplain",
                    "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&format=textplain&limit=50",
                ]
                
                for url in urls:
                    try:
                        async with session.get(url) as response:
                            if response.status == 200:
                                proxy_list = await response.text()
                                for line in proxy_list.strip().split('\n'):
                                    if ':' in line and len(line.strip()) > 0:
                                        try:
                                            ip, port = line.strip().split(':')
                                            proxies.append({
                                                'ip': ip,
                                                'port': port,
                                                'type': 'http',
                                                'country': 'Unknown',
                                                'source': 'proxyscrape'
                                            })
                                        except ValueError:
                                            continue
                            if len(proxies) >= 30:
                                break
                    except Exception as e:
                        logger.warning(f"Failed to fetch from {url}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Error fetching from free proxy list: {e}")
        
        return proxies[:30]
    
    def _get_backup_proxies(self) -> List[Dict[str, str]]:
        """Backup list of working proxies (updated periodically)"""
        # These are sample working proxies - in practice, you'd maintain a list of known working ones
        backup_proxies = [
            {'ip': '41.77.129.154', 'port': '3128', 'type': 'http', 'country': 'MA', 'source': 'backup'},
            {'ip': '154.126.110.188', 'port': '8080', 'type': 'http', 'country': 'MA', 'source': 'backup'},
            {'ip': '41.77.11.178', 'port': '80', 'type': 'http', 'country': 'MA', 'source': 'backup'},
            {'ip': '41.77.188.178', 'port': '80', 'type': 'http', 'country': 'MA', 'source': 'backup'},
            {'ip': '196.200.176.89', 'port': '8080', 'type': 'http', 'country': 'MA', 'source': 'backup'},
            # North African alternatives
            {'ip': '41.111.204.186', 'port': '8080', 'type': 'http', 'country': 'DZ', 'source': 'backup'},
            {'ip': '41.111.213.190', 'port': '8080', 'type': 'http', 'country': 'DZ', 'source': 'backup'},
            {'ip': '197.230.241.195', 'port': '8080', 'type': 'http', 'country': 'TN', 'source': 'backup'},
        ]
        
        return backup_proxies
    
    async def test_proxy(self, proxy: Dict[str, str], timeout: int = 10) -> bool:
        """Test if a proxy is working"""
        proxy_url = f"http://{proxy['ip']}:{proxy['port']}"
        
        try:
            # Test with a simple HTTP request
            connector = aiohttp.ProxyConnector.from_url(proxy_url)
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                # Test with a lightweight endpoint
                async with session.get('http://httpbin.org/ip') as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Proxy {proxy['ip']}:{proxy['port']} working - IP: {result.get('origin', 'unknown')}")
                        return True
                    else:
                        return False
        except Exception as e:
            logger.debug(f"❌ Proxy {proxy['ip']}:{proxy['port']} failed: {e}")
            return False
    
    async def get_working_proxy(self) -> Optional[str]:
        """Get a working proxy URL - prioritizes local proxy if enabled"""
        # Check local proxy first if enabled
        if self.local_proxy_enabled and self.local_proxy_url:
            if self.test_local_proxy():
                logger.info(f"🏠 Using local proxy: {self.local_proxy_url}")
                return self.local_proxy_url
            else:
                logger.warning("❌ Local proxy test failed, falling back to free proxies")
        
        # Fall back to free proxies
        current_time = time.time()
        
        # Refresh proxy list if needed
        if (current_time - self.last_fetch_time) > self.fetch_interval or not self.working_proxies:
            await self.refresh_proxies()
        
        # Return a working proxy if available
        if self.working_proxies:
            # Rotate through working proxies
            proxy = self.working_proxies[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.working_proxies)
            
            proxy_url = f"http://{proxy['ip']}:{proxy['port']}"
            logger.info(f"🌍 Using free proxy: {proxy_url} (Country: {proxy.get('country', 'Unknown')})")
            return proxy_url
        else:
            logger.warning("❌ No working proxies available")
            return None
    
    async def refresh_proxies(self):
        """Refresh the list of working proxies"""
        logger.info("🔄 Refreshing proxy list...")
        
        # Fetch new proxies
        self.proxies = await self.fetch_free_proxies()
        
        # Test proxies in parallel (but limit concurrency)
        working_proxies = []
        semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent tests
        
        async def test_with_semaphore(proxy):
            async with semaphore:
                if await self.test_proxy(proxy, timeout=8):
                    return proxy
                return None
        
        # Test proxies
        logger.info(f"🧪 Testing {len(self.proxies)} proxies...")
        tasks = [test_with_semaphore(proxy) for proxy in self.proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect working proxies
        for result in results:
            if result is not None and not isinstance(result, Exception):
                working_proxies.append(result)
        
        # Prioritize Moroccan proxies
        moroccan_proxies = [p for p in working_proxies if p.get('country') == 'MA']
        other_proxies = [p for p in working_proxies if p.get('country') != 'MA']
        
        self.working_proxies = moroccan_proxies + other_proxies
        self.last_fetch_time = time.time()
        
        logger.info(f"✅ Found {len(self.working_proxies)} working proxies ({len(moroccan_proxies)} Moroccan)")
        if self.working_proxies:
            for proxy in self.working_proxies[:5]:  # Show first 5
                logger.info(f"   📍 {proxy['ip']}:{proxy['port']} ({proxy.get('country', 'Unknown')})")
    
    async def get_ip_info(self, proxy_url: str) -> Dict[str, str]:
        """Get IP information when using a proxy"""
        try:
            connector = aiohttp.ProxyConnector.from_url(proxy_url)
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                async with session.get('http://ip-api.com/json/') as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            logger.error(f"Failed to get IP info: {e}")
        
        return {"country": "Unknown", "regionName": "Unknown", "city": "Unknown"}

    def get_current_proxy_info(self) -> Dict[str, str]:
        """Get information about currently used proxy"""
        if self.local_proxy_enabled and self.local_proxy_url:
            return {
                'type': 'local',
                'url': self.local_proxy_url,
                'description': 'Local proxy through SSH tunnel'
            }
        elif self.working_proxies:
            proxy = self.working_proxies[self.current_proxy_index]
            return {
                'type': 'free',
                'url': f"http://{proxy['ip']}:{proxy['port']}",
                'country': proxy.get('country', 'Unknown'),
                'source': proxy.get('source', 'Unknown')
            }
        else:
            return {
                'type': 'none',
                'description': 'No proxy available'
            }

# Global proxy manager instance
proxy_manager = ProxyManager() 