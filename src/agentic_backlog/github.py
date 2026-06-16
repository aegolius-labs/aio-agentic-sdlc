import os
import json
import requests

class GitHubClient:
    def __init__(self, token=None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        
        if not self.token:
            cred_path = ".agentic-backlog-credentials"
            if os.path.exists(cred_path):
                with open(cred_path, "r", encoding="utf-8") as f:
                    self.token = f.read().strip()
                    
        if not self.token:
            raise ValueError("GitHub token not provided. Please set GITHUB_TOKEN environment variable or create .agentic-backlog-credentials.")
            
        self.url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.v3+json"
        }

    def execute(self, query, variables=None):
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
            
        resp = requests.post(self.url, headers=self.headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise ValueError(f"GraphQL Error: {json.dumps(data['errors'], indent=2)}")
        return data["data"]

    def get_repo_id(self, owner, name):
        query = """
        query($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            id
          }
        }
        """
        data = self.execute(query, {"owner": owner, "name": name})
        return data["repository"]["id"]

    def get_owner_id(self, owner, is_org=True):
        entity_type = "organization" if is_org else "user"
        query = f"""
        query($owner: String!) {{
          {entity_type}(login: $owner) {{
            id
          }}
        }}
        """
        data = self.execute(query, {"owner": owner})
        return data[entity_type]["id"]

    def create_project_v2(self, owner_id, title, repository_id=None):
        mutation = """
        mutation($input: CreateProjectV2Input!) {
          createProjectV2(input: $input) {
            projectV2 {
              id
              number
            }
          }
        }
        """
        input_data = {"ownerId": owner_id, "title": title}
        if repository_id:
            input_data["repositoryId"] = repository_id
            
        data = self.execute(mutation, {"input": input_data})
        return data["createProjectV2"]["projectV2"]

    def get_project_v2_info(self, owner, project_number, is_org=True):
        entity_type = "organization" if is_org else "user"
        query = f"""
        query($owner: String!, $number: Int!) {{
          {entity_type}(login: $owner) {{
            projectV2(number: $number) {{
              id
              fields(first: 50) {{
                nodes {{
                  ... on ProjectV2FieldCommon {{
                    id
                    name
                    dataType
                  }}
                  ... on ProjectV2SingleSelectField {{
                    id
                    name
                    dataType
                    options {{
                      id
                      name
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
        """
        data = self.execute(query, {"owner": owner, "number": int(project_number)})
        project = data[entity_type]["projectV2"]
        if not project:
            raise ValueError(f"Project V2 number {project_number} not found for {owner}.")
        return project

    def create_custom_field(self, project_id, name, data_type, single_select_options=None):
        mutation = """
        mutation($input: CreateProjectV2FieldInput!) {
          createProjectV2Field(input: $input) {
            projectV2Field {
              ... on ProjectV2FieldCommon {
                id
                name
              }
            }
          }
        }
        """
        input_data = {
            "projectId": project_id,
            "name": name,
            "dataType": data_type
        }
        if single_select_options and data_type == "SINGLE_SELECT":
            input_data["singleSelectOptions"] = [{"name": opt, "description": opt, "color": "BLUE"} for opt in single_select_options]
            
        return self.execute(mutation, {"input": input_data})
        
    def ensure_backlog_fields(self, owner, project_number, is_org=True):
        project = self.get_project_v2_info(owner, project_number, is_org)
        project_id = project["id"]
        existing_fields = {f["name"]: f for f in project["fields"]["nodes"] if f}
        
        expected_fields = [
            ("Impact", "NUMBER", None),
            ("Effort", "NUMBER", None),
            ("Requires", "TEXT", None),
            ("Final Score", "NUMBER", None),
            ("Blockers", "TEXT", None),
            ("AI Driven", "SINGLE_SELECT", ["True", "False"]),
            ("Category", "TEXT", None)
        ]
        
        for name, dtype, options in expected_fields:
            if name not in existing_fields:
                self.create_custom_field(project_id, name, dtype, options)
                
        # Re-fetch to get updated IDs
        project = self.get_project_v2_info(owner, project_number, is_org)
        return project

    def create_issue(self, repo_id, title, body=""):
        mutation = """
        mutation($input: CreateIssueInput!) {
          createIssue(input: $input) {
            issue {
              id
              number
            }
          }
        }
        """
        data = self.execute(mutation, {"input": {"repositoryId": repo_id, "title": title, "body": body}})
        return data["createIssue"]["issue"]

    def add_project_item(self, project_id, content_id):
        mutation = """
        mutation($input: AddProjectV2ItemByIdInput!) {
          addProjectV2ItemById(input: $input) {
            item {
              id
            }
          }
        }
        """
        data = self.execute(mutation, {"input": {"projectId": project_id, "contentId": content_id}})
        return data["addProjectV2ItemById"]["item"]["id"]

    def update_item_field(self, project_id, item_id, field_id, value, data_type):
        mutation = """
        mutation($input: UpdateProjectV2ItemFieldValueInput!) {
          updateProjectV2ItemFieldValue(input: $input) {
            projectV2Item {
              id
            }
          }
        }
        """
        input_data = {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": field_id
        }
        
        if data_type == "NUMBER":
            input_data["value"] = {"number": float(value)}
        elif data_type == "TEXT":
            input_data["value"] = {"text": str(value)}
        elif data_type == "SINGLE_SELECT":
            input_data["value"] = {"singleSelectOptionId": str(value)}
            
        return self.execute(mutation, {"input": input_data})

    def fetch_all_items(self, project_id):
        query = """
        query($id: ID!, $cursor: String) {
          node(id: $id) {
            ... on ProjectV2 {
              items(first: 100, after: $cursor) {
                pageInfo {
                  hasNextPage
                  endCursor
                }
                nodes {
                  id
                  isArchived
                  type
                  content {
                    ... on Issue {
                      title
                      body
                      number
                      state
                    }
                  }
                  fieldValues(first: 50) {
                    nodes {
                      ... on ProjectV2ItemFieldTextValue {
                        text
                        field { ... on ProjectV2FieldCommon { name } }
                      }
                      ... on ProjectV2ItemFieldNumberValue {
                        number
                        field { ... on ProjectV2FieldCommon { name } }
                      }
                      ... on ProjectV2ItemFieldSingleSelectValue {
                        name
                        field { ... on ProjectV2FieldCommon { name } }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        items = []
        cursor = None
        has_next = True
        
        while has_next:
            data = self.execute(query, {"id": project_id, "cursor": cursor})
            connection = data["node"]["items"]
            
            for node in connection["nodes"]:
                if node and not node.get("isArchived") and node.get("content"):
                    parsed_item = {
                        "id": node["id"],
                        "title": node["content"]["title"],
                        "body": node["content"]["body"],
                        "number": node["content"]["number"],
                        "state": node["content"]["state"],
                        "fields": {}
                    }
                    
                    for fv in node["fieldValues"]["nodes"]:
                        if not fv or not fv.get("field"): continue
                        fname = fv["field"]["name"]
                        if "text" in fv:
                            parsed_item["fields"][fname] = fv["text"]
                        elif "number" in fv:
                            parsed_item["fields"][fname] = fv["number"]
                        elif "name" in fv:
                            parsed_item["fields"][fname] = fv["name"]
                            
                    items.append(parsed_item)
                    
            has_next = connection["pageInfo"]["hasNextPage"]
            cursor = connection["pageInfo"]["endCursor"]
            
        return items
