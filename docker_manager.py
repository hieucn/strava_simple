#!/usr/bin/env python3
"""
Docker Container Management for AI Feature Deployment
Handles automatic container restart and deployment validation
"""

import subprocess
import time
import logging
import json
import os
from typing import Dict, List, Optional, Tuple

class DockerManager:
    """Manages Docker container operations for feature deployment"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def find_app_container(self) -> Optional[str]:
        """Find the running application container"""
        try:
            # Get all running containers
            result = subprocess.run(['docker', 'ps', '--format', 'json'], 
                                 capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                self.logger.error(f"Failed to list containers: {result.stderr}")
                return None
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        containers.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            
            # Look for app container based on common patterns
            app_keywords = ['strava', 'running', 'challenge', 'app', 'flask', 'python']
            
            for container in containers:
                name = container.get('Names', '').lower()
                image = container.get('Image', '').lower()
                
                # Check if container name or image contains app keywords
                if any(keyword in name for keyword in app_keywords) or \
                   any(keyword in image for keyword in app_keywords):
                    self.logger.info(f"Found app container: {name} ({image})")
                    return name
            
            # If no specific match, try to find a container on common ports
            for container in containers:
                ports = container.get('Ports', '')
                if '5000' in ports or '5001' in ports or '8000' in ports:
                    name = container.get('Names', '')
                    self.logger.info(f"Found container by port: {name}")
                    return name
            
            self.logger.warning("No app container found")
            return None
            
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout while listing containers")
            return None
        except Exception as e:
            self.logger.error(f"Error finding app container: {str(e)}")
            return None
    
    def restart_container(self, container_name: str) -> Tuple[bool, str]:
        """Restart a specific container"""
        try:
            self.logger.info(f"Restarting container: {container_name}")
            
            # Restart the container
            result = subprocess.run(['docker', 'restart', container_name], 
                                 capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.logger.info(f"Container {container_name} restarted successfully")
                return True, f"Container {container_name} restarted successfully"
            else:
                error_msg = f"Failed to restart container: {result.stderr}"
                self.logger.error(error_msg)
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            error_msg = "Container restart timeout (60s)"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error restarting container: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def wait_for_container_ready(self, container_name: str, max_wait: int = 60) -> Tuple[bool, str]:
        """Wait for container to be ready after restart"""
        try:
            self.logger.info(f"Waiting for container {container_name} to be ready...")
            
            start_time = time.time()
            while time.time() - start_time < max_wait:
                # Check if container is running
                result = subprocess.run(['docker', 'ps', '--filter', f'name={container_name}', '--format', '{{.Status}}'], 
                                     capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0 and 'Up' in result.stdout:
                    # Container is running, now check if app is responding
                    if self._check_app_health():
                        ready_msg = f"Container {container_name} is ready and responding"
                        self.logger.info(ready_msg)
                        return True, ready_msg
                
                time.sleep(2)
            
            timeout_msg = f"Container {container_name} not ready after {max_wait}s"
            self.logger.warning(timeout_msg)
            return False, timeout_msg
            
        except Exception as e:
            error_msg = f"Error waiting for container: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _check_app_health(self) -> bool:
        """Check if the application is responding"""
        try:
            import requests
            # Try to hit the health endpoint or home page
            response = requests.get('http://localhost:5001/', timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_container_logs(self, container_name: str, lines: int = 50) -> str:
        """Get recent logs from container"""
        try:
            result = subprocess.run(['docker', 'logs', '--tail', str(lines), container_name], 
                                 capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error getting logs: {result.stderr}"
                
        except Exception as e:
            return f"Error getting logs: {str(e)}"
    
    def deploy_feature(self, feedback_id: int) -> Dict:
        """Complete feature deployment workflow"""
        deployment_log = []
        deployment_log.append(f"Starting feature deployment for feedback {feedback_id}")
        deployment_log.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Find the application container
            deployment_log.append("1. Finding application container...")
            container_name = self.find_app_container()
            
            if not container_name:
                deployment_log.append("❌ No application container found")
                return {
                    'success': False,
                    'status': 'failed',
                    'message': 'No application container found',
                    'log': '\n'.join(deployment_log)
                }
            
            deployment_log.append(f"✅ Found container: {container_name}")
            
            # Get pre-restart logs
            deployment_log.append("2. Capturing pre-restart logs...")
            pre_logs = self.get_container_logs(container_name, 10)
            deployment_log.append(f"Pre-restart status: Container running")
            
            # Restart the container
            deployment_log.append("3. Restarting application container...")
            restart_success, restart_msg = self.restart_container(container_name)
            deployment_log.append(restart_msg)
            
            if not restart_success:
                return {
                    'success': False,
                    'status': 'failed',
                    'message': 'Container restart failed',
                    'log': '\n'.join(deployment_log)
                }
            
            # Wait for container to be ready
            deployment_log.append("4. Waiting for application to be ready...")
            ready_success, ready_msg = self.wait_for_container_ready(container_name)
            deployment_log.append(ready_msg)
            
            if ready_success:
                deployment_log.append("5. Validating deployment...")
                post_logs = self.get_container_logs(container_name, 5)
                deployment_log.append("✅ Deployment completed successfully")
                deployment_log.append("Application is responding and ready")
                
                return {
                    'success': True,
                    'status': 'deployed',
                    'message': 'Feature deployed successfully',
                    'log': '\n'.join(deployment_log),
                    'container': container_name
                }
            else:
                deployment_log.append("❌ Application not responding after restart")
                deployment_log.append("This may indicate a configuration or startup issue")
                
                return {
                    'success': False,
                    'status': 'partial',
                    'message': 'Container restarted but app not responding',
                    'log': '\n'.join(deployment_log)
                }
                
        except Exception as e:
            error_msg = f"Deployment error: {str(e)}"
            deployment_log.append(f"❌ {error_msg}")
            self.logger.error(error_msg)
            
            return {
                'success': False,
                'status': 'failed',
                'message': error_msg,
                'log': '\n'.join(deployment_log)
            }
    
    def rollback_deployment(self, container_name: str, backup_image: str = None) -> Dict:
        """Rollback to previous version if available"""
        deployment_log = []
        deployment_log.append("Starting deployment rollback...")
        
        try:
            if backup_image:
                deployment_log.append(f"Rolling back to image: {backup_image}")
                # This would involve stopping current container and starting backup
                # Implementation depends on your specific backup strategy
                deployment_log.append("❌ Rollback not implemented - manual intervention required")
                return {
                    'success': False,
                    'message': 'Rollback not implemented',
                    'log': '\n'.join(deployment_log)
                }
            else:
                deployment_log.append("No backup image specified - attempting container restart")
                restart_success, restart_msg = self.restart_container(container_name)
                deployment_log.append(restart_msg)
                
                return {
                    'success': restart_success,
                    'message': 'Attempted restart rollback',
                    'log': '\n'.join(deployment_log)
                }
                
        except Exception as e:
            error_msg = f"Rollback error: {str(e)}"
            deployment_log.append(f"❌ {error_msg}")
            
            return {
                'success': False,
                'message': error_msg,
                'log': '\n'.join(deployment_log)
            }

if __name__ == "__main__":
    # Test the Docker manager
    manager = DockerManager()
    
    print("Testing Docker Manager...")
    container = manager.find_app_container()
    if container:
        print(f"Found container: {container}")
        logs = manager.get_container_logs(container, 5)
        print(f"Recent logs:\n{logs}")
    else:
        print("No container found")