import requests
from requests.auth import HTTPBasicAuth
import logging
import os
from urllib.parse import urljoin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger()


class XNATlistener:
    
    def __init__(self, username="admin", password="admin", base_url="http://digione-infrastructure-xnat-nginx-1:80"):
        self.username = username
        self.password = password
        self.base_url = base_url
        self.base_url_projects = f"{base_url}/data/projects"
        self.required_data_types = ["xnat:ctScanData", "xnat:rtImageScanData"]
        
    def _get(self, url):
        """Helper to make authenticated get requests and return parsed JSON."""
        resp = requests.get(url, auth=HTTPBasicAuth(self.username, self.password))
        resp.raise_for_status()
        return resp.json()

    def clear_output_folder(self, folder_path):
        """Creates or clears a folder"""
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            logger.info(f"Output folder created: {folder_path}")
        else:
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        
    def get_projects(self):
        """Get the projects in XNAT that contain data and save it in a dict with its corresponding URl"""
        data = self._get(self.base_url_projects)
        projects = data.get("ResultSet", {}).get("Result", [])
        
        project_urls = {
            proj["name"]: f"{self.base_url_projects}/{proj['ID']}/subjects"
            for proj in projects
        }

        # Filter project with no subjects
        filtered_projects = {
            name: url
            for name, url in project_urls.items()
            if int(self._get(url)["ResultSet"]["totalRecords"]) > 0
        }

        return filtered_projects

    def get_subjects(self, project_url):
        """Gets all the urls for for the subjects in a project"""
        subjects_data = self._get(project_url).get("ResultSet", {}).get("Result", [])
        subjects = {}
        
        for subject in subjects_data:
            subject_url = f"{project_url}/{subject['ID']}/experiments"
            experiments_data = self._get(subject_url).get("ResultSet", {}).get("Result", [])
            
            for experiment in experiments_data:
                # Directly map experiment label -> scan URL
                subjects[experiment["label"]] = f"{subject_url}/{experiment['ID']}/scans"
        
        return subjects
        
    def get_all_subjects(self, projects_dict):
        """Get all subjects for all projects."""
        return {project: self.get_subjects(url) for project, url in projects_dict.items()}
    
    def check_subject(self, subject_url):
        """Checks if the data types in self.required_data_types are also in the subject data types"""
        data_types = []
        
        for data in self._get(subject_url)["ResultSet"]["Result"]:
            data_types.append(data["xsiType"])
        
        return all(item in data_types for item in self.required_data_types)
    
    def processed_subjects(self, subjects_dict, processed_ID):
        """Remove the IDs that already have been processed from the subjects_dict."""
        for project in subjects_dict:
            subjects_dict[project] = {
                exp: url
                for exp, url in subjects_dict[project].items()
                if exp not in processed_ID
            }
        return subjects_dict
    
    def download_url(self, url, output_dir):
        """Download all the files from a url"""
        data = self._get(url)

        for file_entry in data.get("ResultSet", {}).get("Result", []):
            file_name = file_entry.get("Name") or file_entry.get("name")
            file_uri = file_entry.get("URI")

            # Build download URL
            download_url = urljoin(self.base_url, file_uri)
            local_path = os.path.join(output_dir, file_name)

            with requests.get(download_url, auth=HTTPBasicAuth(self.username, self.password), stream=True) as r:
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

        logging.info(f"All files downloaded from {url}")
    
    def download_all_files(self, subjects_dict):
        """Download all the xnat project data that is complete"""
        # A list to keep track which ids have been processsed
        checked_IDs = []
        
        # Go down to the urls in the subject dict
        for project in subjects_dict:
            for id, url in subjects_dict[project].items():
                folder = f"data/{id}"
                self.clear_output_folder(folder)
                checked_IDs.append(id)
                
                # Check if a all the required data types are available
                if not self.check_subject(url):
                    logging.info(f"Experiment: {id} misses certain required data types")
                    continue

                try:
                    for datatypes in self._get(url)["ResultSet"]["Result"]:
                        data_url = f"{url}/{datatypes['ID']}/resources"
                        data_url = f"{data_url}/{self._get(data_url)['ResultSet']['Result'][0]['label']}/files"
                        self.download_url(data_url, folder)
                except Exception as e:
                    self.clear_output_folder(folder)
                    os.rmdir(folder)
                    logger.error(f"Data is unretrievable or missing for: {id}/{datatypes['xsiType']} error: {e}")
        
        return checked_IDs
    
    def run(self, skip_ID=[]):
        projects = self.get_projects()
        subjects = self.get_all_subjects(projects)
        subjects = self.processed_subjects(subjects, skip_ID)
        ids = self.download_all_files(subjects)
        return ids
        
if __name__ == "__main__":
    listener = XNATlistener()
    listener.run()
    
    
    