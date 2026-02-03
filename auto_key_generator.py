# 🔄 Auto API Key Generator - Recovery System
# Automatically creates new Google Cloud projects and API keys when rate limited

import time
import logging
import os
from google.cloud.api_keys_v2 import ApiKeysClient
from google.cloud.api_keys_v2.types import Key
from google.auth import default
from googleapiclient import discovery
from google.cloud import resourcemanager_v3

logger = logging.getLogger(__name__)


class AutoKeyGenerator:
    """Automatically generate new API keys when all existing keys are rate limited"""
    
    def __init__(self):
        try:
            # Load credentials from environment or default
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path:
                logger.info(f"Using service account from: {credentials_path}")
            
            self.credentials, self.default_project_id = default()
            self.api_keys_client = ApiKeysClient(credentials=self.credentials)
            self.service_usage = discovery.build('serviceusage', 'v1', credentials=self.credentials)
            self.project_client = resourcemanager_v3.ProjectsClient(credentials=self.credentials)
            self.available = True
            logger.info("Auto Key Generator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Auto Key Generator: {e}")
            self.available = False
    
    def _enable_apis(self, project_id: str) -> bool:
        """Enable required APIs for the project"""
        services = [
            "generativelanguage.googleapis.com",  # AI Studio / Gemini API
            "aiplatform.googleapis.com"  # Vertex AI API
        ]
        
        logger.info(f"Enabling APIs for project {project_id}...")
        for service_name in services:
            try:
                logger.info(f"Enabling {service_name}...")
                request = self.service_usage.services().enable(
                    name=f"projects/{project_id}/services/{service_name}"
                )
                request.execute()
                logger.info(f"✓ {service_name} enabled")
            except Exception as e:
                logger.warning(f"Failed to enable {service_name}: {e}")
                return False
        
        # Wait for APIs to propagate
        logger.info("Waiting for APIs to propagate (10s)...")
        time.sleep(10)
        return True
    
    def _create_project(self) -> str:
        """Create a new Google Cloud project"""
        try:
            timestamp = int(time.time())
            project_id = f"bmkg-auto-{timestamp}"
            project_name = f"BMKG Automation {timestamp}"
            
            logger.info(f"Creating new project: {project_id}")
            
            # Create project request
            project = resourcemanager_v3.Project(
                project_id=project_id,
                display_name=project_name
            )
            
            operation = self.project_client.create_project(project=project)
            result = operation.result(timeout=120)
            
            logger.info(f"✓ Project created: {result.project_id}")
            
            # Wait for project to be fully ready
            time.sleep(10)
            
            return result.project_id
        
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            return None
    
    def _generate_api_keys(self, project_id: str, count: int = 5) -> list:
        """Generate API keys for the project"""
        api_keys = []
        parent = f"projects/{project_id}/locations/global"
        
        logger.info(f"Generating {count} API keys for project {project_id}...")
        
        for i in range(1, count + 1):
            try:
                key_id = f"gemini-{int(time.time())}-{i}"
                logger.info(f"Creating API key {i}/{count}...")
                
                operation = self.api_keys_client.create_key(
                    parent=parent,
                    key_id=key_id
                )
                response = operation.result(timeout=300)
                
                key_string = response.key_string
                api_keys.append(key_string)
                logger.info(f"✓ API Key {i} created: {key_string[:20]}...")
                
                # Small delay between requests
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to create API key {i}: {e}")
        
        return api_keys
    
    def _update_env_file(self, new_keys: list):
        """Update .env file with new API keys"""
        try:
            env_path = os.path.join(os.path.dirname(__file__), '.env')
            
            if not os.path.exists(env_path):
                logger.warning(".env file not found, creating new one")
                return self._create_env_file(new_keys)
            
            # Read existing .env
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find and update GOOGLE_GEMINI_API_KEYS line
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('GOOGLE_GEMINI_API_KEYS='):
                    # Get existing keys
                    existing_keys = line.split('=', 1)[1].strip().strip('"').strip("'")
                    existing_keys_list = [k.strip() for k in existing_keys.split(',') if k.strip()]
                    
                    # Merge with new keys
                    all_keys = existing_keys_list + new_keys
                    keys_string = ','.join(all_keys)
                    
                    lines[i] = f'GOOGLE_GEMINI_API_KEYS={keys_string}\n'
                    updated = True
                    logger.info(f"Updated .env with {len(new_keys)} new keys (total: {len(all_keys)})")
                    break
            
            if not updated:
                # Add new line if not found
                keys_string = ','.join(new_keys)
                lines.append(f'\nGOOGLE_GEMINI_API_KEYS={keys_string}\n')
                logger.info(f"Added GOOGLE_GEMINI_API_KEYS to .env with {len(new_keys)} keys")
            
            # Write back to .env
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update .env file: {e}")
            return False
    
    def _create_env_file(self, new_keys: list):
        """Create new .env file with API keys"""
        try:
            env_path = os.path.join(os.path.dirname(__file__), '.env')
            keys_string = ','.join(new_keys)
            
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(f'GOOGLE_GEMINI_API_KEYS={keys_string}\n')
            
            logger.info(f"Created .env file with {len(new_keys)} API keys")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create .env file: {e}")
            return False
    
    def generate_new_keys(self, num_keys: int = 5, project_id: str = None) -> tuple:
        """
        Main function to generate new API keys
        
        Args:
            num_keys: Number of API keys to generate
            project_id: Use existing project or create new one if None
        
        Returns:
            Tuple of (success: bool, keys: list)
        """
        if not self.available:
            logger.error("Auto Key Generator not available")
            return False, []
        
        try:
            # Use existing project or create new one
            if not project_id:
                logger.info("Creating new Google Cloud project...")
                project_id = self._create_project()
                
                if not project_id:
                    logger.error("Failed to create project")
                    return False, []
            
            # Enable required APIs
            if not self._enable_apis(project_id):
                logger.error("Failed to enable APIs")
                return False, []
            
            # Generate API keys
            api_keys = self._generate_api_keys(project_id, num_keys)
            
            if not api_keys:
                logger.error("No API keys generated")
                return False, []
            
            logger.info(f"✓ Successfully generated {len(api_keys)}/{num_keys} API keys")
            
            # Update .env file
            if self._update_env_file(api_keys):
                logger.info("✓ .env file updated successfully")
            else:
                logger.warning("Failed to update .env file, but keys are generated")
            
            return True, api_keys
            
        except Exception as e:
            logger.error(f"Error in generate_new_keys: {e}")
            import traceback
            traceback.print_exc()
            return False, []
    
    def is_available(self) -> bool:
        """Check if auto key generator is available"""
        return self.available


if __name__ == "__main__":
    # Test the auto key generator
    logging.basicConfig(level=logging.INFO)
    
    generator = AutoKeyGenerator()
    
    if generator.is_available():
        print("\n🔄 Testing Auto Key Generator...")
        success, keys = generator.generate_new_keys(num_keys=3)
        
        if success:
            print(f"\n✅ Success! Generated {len(keys)} API keys")
            for i, key in enumerate(keys, 1):
                print(f"{i}. {key[:20]}...")
        else:
            print("\n❌ Failed to generate API keys")
    else:
        print("\n❌ Auto Key Generator not available")
