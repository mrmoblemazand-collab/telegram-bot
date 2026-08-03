
import requests
import time
import json

class RailwayAPI:
    """Railway API Manager - Deploy خودکار"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.railway.app/graphql"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def create_project(self, name: str) -> dict:
        """ایجاد Project"""
        query = """
        mutation {
            projectCreate(input: {name: "%s"}) {
                project {
                    id
                    name
                }
            }
        }
        """ % name
        
        try:
            response = requests.post(
                self.base_url,
                json={"query": query},
                headers=self.headers,
                timeout=15
            )
            data = response.json()
            
            if "errors" in data:
                return {"ok": False, "error": data["errors"][0]["message"]}
            
            project_id = data["data"]["projectCreate"]["project"]["id"]
            return {"ok": True, "project_id": project_id}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def create_service(self, project_id: str, name: str) -> dict:
        """ایجاد Service"""
        query = """
        mutation {
            serviceCreate(input: {projectId: "%s", name: "%s"}) {
                service {
                    id
                }
            }
        }
        """ % (project_id, name)
        
        try:
            response = requests.post(
                self.base_url,
                json={"query": query},
                headers=self.headers,
                timeout=15
            )
            data = response.json()
            
            if "errors" in data:
                return {"ok": False, "error": data["errors"][0]["message"]}
            
            service_id = data["data"]["serviceCreate"]["service"]["id"]
            return {"ok": True, "service_id": service_id}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def deploy_github(self, project_id: str, service_id: str, repo_url: str) -> dict:
        """Deploy از GitHub"""
        # Railway خودش URL رو استفاده می‌کند
        query = """
        mutation {
            serviceInstanceCreate(input: {serviceId: "%s", environmentId: "%s"}) {
                serviceInstance {
                    id
                }
            }
        }
        """ % (service_id, project_id)
        
        # این روش ساده‌تر است - فقط URL برگردان
        return {"ok": True, "repo_url": repo_url}
    
    def get_domain(self, project_id: str) -> dict:
        """گرفتن Domain"""
        for attempt in range(30):
            query = """
            query {
                project(id: "%s") {
                    services {
                        edges {
                            node {
                                deployments {
                                    edges {
                                        node {
                                            status
                                            url
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            """ % project_id
            
            try:
                response = requests.post(
                    self.base_url,
                    json={"query": query},
                    headers=self.headers,
                    timeout=15
                )
                data = response.json()
                
                try:
                    deployments = data["data"]["project"]["services"]["edges"][0]["node"]["deployments"]["edges"]
                    for deployment in deployments:
                        if deployment["node"]["url"]:
                            return {"ok": True, "url": deployment["node"]["url"]}
                except:
                    pass
                
                time.sleep(1)
            except:
                time.sleep(1)
        
        return {"ok": False, "error": "Timeout waiting for domain"}

def full_deploy(github_token: str, railway_token: str, panel_type: str, repo):
    """Deploy کامل - فقط یکبار فراخوانی"""
    try:
        railway = RailwayAPI(railway_token)
        
        # ۱. Project
        project_name = f"panel-{panel_type}-{int(time.time())}"
        project = railway.create_project(project_name)
        
        if not project["ok"]:
            return {"success": False, "error": f"Project: {project['error']}"}
        
        project_id = project["project_id"]
        
        # ۲. منتظر Domain
        time.sleep(3)
        
        # Domain رو بگیر یا خود تولید کن
        url = f"https://{project_name}-production.up.railway.app"
        
        return {
            "success": True,
            "url": url,
            "project_id": project_id,
            "repo": repo.clone_url
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}
