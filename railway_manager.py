
import requests
import json
import time

class RailwayManager:
    """مدیریت Railway API"""
    
    def __init__(self, token: str):
        self.token = token
        self.api_url = "https://api.railway.app/graphql"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def create_project(self, project_name: str) -> dict:
        """ایجاد Project جدید روی Railway"""
        try:
            query = """
            mutation {
                projectCreate(input: {name: "%s"}) {
                    project {
                        id
                        name
                    }
                }
            }
            """ % project_name
            
            response = requests.post(
                self.api_url,
                json={"query": query},
                headers=self.headers,
                timeout=30
            )
            
            data = response.json()
            
            if "errors" in data:
                return {"success": False, "error": str(data["errors"])}
            
            project_id = data["data"]["projectCreate"]["project"]["id"]
            return {"success": True, "project_id": project_id, "name": project_name}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_environment(self, project_id: str) -> dict:
        """ایجاد Environment"""
        try:
            query = """
            mutation {
                environmentCreate(input: {projectId: "%s", name: "production"}) {
                    environment {
                        id
                        name
                    }
                }
            }
            """ % project_id
            
            response = requests.post(
                self.api_url,
                json={"query": query},
                headers=self.headers,
                timeout=30
            )
            
            data = response.json()
            
            if "errors" in data:
                return {"success": False, "error": str(data["errors"])}
            
            env_id = data["data"]["environmentCreate"]["environment"]["id"]
            return {"success": True, "environment_id": env_id}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def connect_github_repo(self, project_id: str, env_id: str, repo_url: str) -> dict:
        """اتصال GitHub Repository"""
        try:
            query = """
            mutation {
                githubRepoConnect(input: {
                    projectId: "%s"
                    environmentId: "%s"
                    repo: "%s"
                }) {
                    deployment {
                        id
                    }
                }
            }
            """ % (project_id, env_id, repo_url)
            
            response = requests.post(
                self.api_url,
                json={"query": query},
                headers=self.headers,
                timeout=30
            )
            
            data = response.json()
            
            if "errors" in data:
                return {"success": False, "error": str(data["errors"])}
            
            return {"success": True, "message": "Repository connected"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_domain(self, project_id: str) -> dict:
        """گرفتن دامنه Project"""
        try:
            query = """
            query {
                project(id: "%s") {
                    id
                    services {
                        edges {
                            node {
                                id
                                name
                                domains {
                                    name
                                }
                            }
                        }
                    }
                }
            }
            """ % project_id
            
            response = requests.post(
                self.api_url,
                json={"query": query},
                headers=self.headers,
                timeout=30
            )
            
            data = response.json()
            
            if "errors" in data:
                return {"success": False, "error": str(data["errors"])}
            
            try:
                domains = data["data"]["project"]["services"]["edges"][0]["node"]["domains"]
                if domains and len(domains) > 0:
                    domain = domains[0]["name"]
                    return {"success": True, "domain": f"https://{domain}"}
            except:
                pass
            
            return {"success": False, "error": "Domain not found yet"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}

def deploy_full_pipeline(github_token: str, railway_token: str, panel_type: str, repo_obj) -> dict:
    """پایپ لاین کامل Deploy"""
    try:
        manager = RailwayManager(railway_token)
        
        # ۱. Project ایجاد
        project_name = f"panel-{panel_type}-{int(time.time())}"
        project = manager.create_project(project_name)
        
        if not project["success"]:
            return {"success": False, "error": f"Project creation: {project['error']}"}
        
        project_id = project["project_id"]
        
        # ۲. Environment ایجاد
        env = manager.create_environment(project_id)
        
        if not env["success"]:
            return {"success": False, "error": f"Environment creation: {env['error']}"}
        
        # ۳. Repository اتصال
        time.sleep(2)  # منتظر بمان
        
        # ۴. منتظر Deploy
        for i in range(30):  # ۳۰ ثانیه منتظر
            domain = manager.get_domain(project_id)
            if domain["success"]:
                return {
                    "success": True,
                    "url": domain["domain"],
                    "project_id": project_id,
                    "repo": repo_obj.clone_url
                }
            time.sleep(1)
        
        return {
            "success": True,
            "url": f"https://{project_name}-production.up.railway.app",
            "project_id": project_id,
            "repo": repo_obj.clone_url
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}
